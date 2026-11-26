"""Task 3: isolated demo bootstrap, hashed credentials, Origin/CSRF checks and actor rotation.

Every test creates its own sandboxes through HTTP and inspects persisted state through the
disposable PostgreSQL engine. Browsers are separate cookie jars sharing one app instance.
"""

import hashlib
import uuid
from datetime import timedelta
from http.cookies import SimpleCookie
from typing import Annotated, Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, update
from sqlalchemy.orm import Session

from app import models
from app.api.schemas import Bootstrap, Me
from app.auth.dependencies import actor_mutation
from app.auth.principal import Principal
from app.auth.service import derive_csrf
from app.main import create_app
from app.settings import Settings
from tests.conftest import API, TEST_ORIGIN, guardian_test_settings, start_demo

ORIGIN = {"Origin": TEST_ORIGIN}
ACTOR_COOKIE = "guardian_session"
CONTROLLER_COOKIE = "guardian_demo"
PROBE = f"{API}/test/actor-probe"


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def response_cookies(response) -> dict[str, Any]:
    cookies: dict[str, Any] = {}
    for name, value in response.headers.multi_items():
        if name.lower() == "set-cookie":
            parsed = SimpleCookie()
            parsed.load(value)
            cookies.update(parsed)
    return cookies


def install_actor_probe(app: FastAPI) -> None:
    """Test-only actor mutation using the production Origin + actor-CSRF dependency."""

    @app.post(PROBE)
    def actor_probe(principal: Annotated[Principal, Depends(actor_mutation)]) -> dict[str, str]:
        return {
            "sandbox_id": str(principal.sandbox_id),
            "actor_id": str(principal.actor_id),
            "role": principal.role,
            "request_id": principal.request_id,
        }


def choose(client: TestClient, actor_id: str, csrf: str | None, headers=None):
    request_headers = dict(ORIGIN if headers is None else headers)
    if csrf is not None:
        request_headers["X-CSRF-Token"] = csrf
    return client.post(
        f"{API}/demo/actors/select", json={"actor_id": actor_id}, headers=request_headers
    )


def actor_named(bootstrap: dict[str, Any], name: str) -> dict[str, Any]:
    return next(actor for actor in bootstrap["actors"] if actor["display_name"] == name)


def operator(bootstrap: dict[str, Any]) -> dict[str, Any]:
    return next(actor for actor in bootstrap["actors"] if actor["role"] == "OPERATOR")


def error_code(response) -> str:
    return response.json()["error"]["code"]


def sessions_of(pg_engine: Engine, sandbox_id: str) -> list[models.AuthSession]:
    with Session(pg_engine) as db:
        return list(
            db.scalars(
                select(models.AuthSession).where(
                    models.AuthSession.sandbox_id == uuid.UUID(sandbox_id)
                )
            )
        )


def test_bootstrap_sets_distinct_hashed_credentials(browser, pg_engine: Engine):
    client = browser()
    response = client.post(f"{API}/demo/sessions", json={"scenario": "MAIN_REFUND"}, headers=ORIGIN)

    assert response.status_code == 201, response.text
    bootstrap = Bootstrap.model_validate(response.json())
    assert bootstrap.scenario == "MAIN_REFUND"
    assert sorted(actor.display_name for actor in bootstrap.actors if actor.role == "CUSTOMER") == [
        "An",
        "Binh",
        "Linh",
        "Mai",
    ]
    assert [actor.role for actor in bootstrap.actors].count("OPERATOR") == 1
    assert bootstrap.current_actor.display_name == "Linh"
    assert bootstrap.current_actor.role == "CUSTOMER"

    cookies = response_cookies(response)
    assert set(cookies) == {CONTROLLER_COOKIE, ACTOR_COOKIE}
    for morsel in cookies.values():
        assert morsel["httponly"] is True
        assert morsel["samesite"].lower() == "lax"
        assert morsel["path"] == "/"
        assert not morsel["secure"], "local HTTP origin must not mark cookies Secure"
        assert int(morsel["max-age"]) == 24 * 60 * 60
    controller_token = cookies[CONTROLLER_COOKIE].value
    actor_token = cookies[ACTOR_COOKIE].value
    assert len(controller_token) >= 32 and len(actor_token) >= 32
    assert controller_token != actor_token
    assert bootstrap.controller_csrf_token != bootstrap.actor_csrf_token
    secrets = {
        controller_token,
        actor_token,
        bootstrap.controller_csrf_token,
        bootstrap.actor_csrf_token,
    }
    assert len(secrets) == 4
    assert controller_token not in response.text and actor_token not in response.text

    rows = sessions_of(pg_engine, str(bootstrap.sandbox_id))
    by_kind = {row.kind: row for row in rows}
    assert len(rows) == 2 and set(by_kind) == {"DEMO_CONTROL", "ACTOR"}
    assert by_kind["DEMO_CONTROL"].actor_id is None
    assert by_kind["ACTOR"].actor_id == bootstrap.current_actor.id
    assert by_kind["DEMO_CONTROL"].token_hash == sha256(controller_token)
    assert by_kind["ACTOR"].token_hash == sha256(actor_token)
    assert by_kind["DEMO_CONTROL"].csrf_hash == sha256(bootstrap.controller_csrf_token)
    assert by_kind["ACTOR"].csrf_hash == sha256(bootstrap.actor_csrf_token)
    for row in rows:
        assert row.revoked_at is None
        stored = " ".join(str(value) for value in vars(row).values())
        assert not any(secret in stored for secret in secrets), "plaintext credential stored"
    with Session(pg_engine) as db:
        sandbox = db.get(models.Sandbox, bootstrap.sandbox_id)
        assert sandbox is not None and sandbox.scenario == "MAIN_REFUND"
        assert sandbox.expires_at - sandbox.created_at == timedelta(hours=24)
        assert bootstrap.expires_at == sandbox.expires_at
        for row in rows:
            assert row.expires_at == sandbox.expires_at


def test_hosted_https_origin_sets_secure_cookies(pg_engine: Engine):
    origin = "https://guardian.example.test"
    app = create_app(guardian_test_settings(public_app_origin=origin))
    with TestClient(app) as client:
        response = client.post(
            f"{API}/demo/sessions", json={"scenario": "MAIN_REFUND"}, headers={"Origin": origin}
        )
    assert response.status_code == 201, response.text
    cookies = response_cookies(response)
    assert set(cookies) == {CONTROLLER_COOKIE, ACTOR_COOKIE}
    assert all(morsel["secure"] is True for morsel in cookies.values())


@pytest.mark.parametrize(
    ("app_env", "origin", "secure"),
    [
        ("development", "http://localhost:3000", False),
        ("test", "http://127.0.0.1:3000", False),
        ("development", "https://localhost:3000", True),
        ("development", "http://guardian.example.test", True),
        ("production", "https://guardian.example.test", True),
        ("production", "http://localhost:3000", True),
    ],
)
def test_cookie_secure_only_disabled_for_local_http(app_env, origin, secure):
    settings = Settings(_env_file=None, app_env=app_env, public_app_origin=origin)
    assert settings.cookie_secure is secure


def test_csrf_derivation_is_deterministic_and_domain_separated():
    token = "a" * 43
    assert derive_csrf(token) == derive_csrf(token)
    assert derive_csrf(token) != derive_csrf("b" * 43)
    assert derive_csrf(token, "ACTOR") == derive_csrf(token)
    assert derive_csrf(token, "DEMO_CONTROL") != derive_csrf(token, "ACTOR")
    assert token not in derive_csrf(token)


def test_me_restores_matching_csrf_after_refresh(browser, guardian_app, pg_engine: Engine):
    client = browser()
    bootstrap = start_demo(client)
    install_actor_probe(guardian_app)
    before = sessions_of(pg_engine, bootstrap["sandbox_id"])

    first = client.get(f"{API}/me")
    second = client.get(f"{API}/me")

    assert first.status_code == 200, first.text
    me = Me.model_validate(first.json())
    assert me.actor_csrf_token == bootstrap["actor_csrf_token"]
    assert second.json() == first.json()
    assert me.actor.id == uuid.UUID(bootstrap["current_actor"]["id"])
    assert me.sandbox_id == uuid.UUID(bootstrap["sandbox_id"])
    assert "set-cookie" not in {name.lower() for name, _ in first.headers.multi_items()}
    assert first.headers["cache-control"] == "no-store"
    after = sessions_of(pg_engine, bootstrap["sandbox_id"])
    snapshot = sorted((r.id, r.token_hash, r.csrf_hash, r.expires_at, r.revoked_at) for r in before)
    assert snapshot == sorted(
        (r.id, r.token_hash, r.csrf_hash, r.expires_at, r.revoked_at) for r in after
    ), "GET /me must not mutate or rotate session state"

    restored = client.post(PROBE, headers={**ORIGIN, "X-CSRF-Token": me.actor_csrf_token})
    assert restored.status_code == 200, restored.text
    assert restored.json()["actor_id"] == bootstrap["current_actor"]["id"]
    assert restored.json()["request_id"] == restored.headers["x-request-id"]

    ops = choose(client, operator(bootstrap)["id"], bootstrap["controller_csrf_token"])
    assert ops.status_code == 200, ops.text
    refreshed = client.get(f"{API}/me")
    assert refreshed.json()["actor_csrf_token"] == ops.json()["actor_csrf_token"]


def test_two_sandboxes_are_isolated(browser, pg_engine: Engine):
    first, second = browser(), browser()
    boot_a, boot_b = start_demo(first), start_demo(second)

    assert boot_a["sandbox_id"] != boot_b["sandbox_id"]
    assert not {a["id"] for a in boot_a["actors"]} & {b["id"] for b in boot_b["actors"]}

    me_a = first.get(f"{API}/me")
    me_b = second.get(f"{API}/me")
    assert me_a.status_code == 200 and me_b.status_code == 200
    assert me_a.json()["sandbox_id"] == boot_a["sandbox_id"]
    assert me_b.json()["sandbox_id"] == boot_b["sandbox_id"]
    accounts_a = {account["id"] for account in me_a.json()["accounts"]}
    accounts_b = {account["id"] for account in me_b.json()["accounts"]}
    assert accounts_a and accounts_b and not accounts_a & accounts_b

    forged = first.get(
        f"{API}/me",
        headers={
            "X-Actor-Role": "OPERATOR",
            "X-Sandbox-ID": boot_b["sandbox_id"],
            "X-Actor-ID": operator(boot_b)["id"],
        },
    )
    assert forged.status_code == 200
    assert forged.json() == me_a.json(), "client headers must not change the resolved principal"

    with Session(pg_engine) as db:
        for boot, account_ids in ((boot_a, accounts_a), (boot_b, accounts_b)):
            sandbox_id = uuid.UUID(boot["sandbox_id"])
            actors = db.scalars(
                select(models.Actor).where(models.Actor.sandbox_id == sandbox_id)
            ).all()
            assert {str(actor.id) for actor in actors} == {a["id"] for a in boot["actors"]}
            for account_id in account_ids:
                account = db.get(models.Account, uuid.UUID(account_id))
                assert account is not None and account.sandbox_id == sandbox_id


def test_foreign_actor_selection_is_404(browser, pg_engine: Engine):
    first, second = browser(), browser()
    boot_a, boot_b = start_demo(first), start_demo(second)
    csrf = boot_a["controller_csrf_token"]

    foreign_customer = choose(first, actor_named(boot_b, "Linh")["id"], csrf)
    foreign_operator = choose(first, operator(boot_b)["id"], csrf)
    unknown = choose(first, str(uuid.uuid4()), csrf)

    for response in (foreign_customer, foreign_operator, unknown):
        assert response.status_code == 404, response.text
        assert error_code(response) == "NOT_FOUND"
        assert ACTOR_COOKIE not in response_cookies(response)
    assert foreign_customer.json()["error"]["message"] == unknown.json()["error"]["message"]

    malformed = choose(first, "not-a-uuid", csrf)
    assert malformed.status_code == 422 and error_code(malformed) == "VALIDATION_ERROR"
    extra = first.post(
        f"{API}/demo/actors/select",
        json={"actor_id": operator(boot_a)["id"], "sandbox_id": boot_b["sandbox_id"]},
        headers={**ORIGIN, "X-CSRF-Token": csrf},
    )
    assert extra.status_code == 422 and error_code(extra) == "VALIDATION_ERROR"

    still_linh = first.get(f"{API}/me")
    assert still_linh.status_code == 200
    assert still_linh.json()["actor"]["id"] == boot_a["current_actor"]["id"]
    assert all(row.revoked_at is None for row in sessions_of(pg_engine, boot_a["sandbox_id"]))
    other_me = second.get(f"{API}/me")
    assert other_me.json()["actor"]["id"] == boot_b["current_actor"]["id"]


def test_wrong_origin_and_csrf_denied(browser, guardian_app, pg_engine: Engine):
    client = browser()
    with Session(pg_engine) as db:
        sandboxes_before = db.scalar(select(func.count()).select_from(models.Sandbox))

    for headers in (
        {},
        {"Origin": "http://evil.example"},
        {"Origin": f"{TEST_ORIGIN}/"},
        {"Origin": "http://localhost:3001"},
        {"Origin": "null"},
    ):
        denied = client.post(
            f"{API}/demo/sessions", json={"scenario": "MAIN_REFUND"}, headers=headers
        )
        assert denied.status_code == 403, (headers, denied.text)
        assert error_code(denied) == "ORIGIN_DENIED"
        assert not response_cookies(denied)
    with Session(pg_engine) as db:
        assert db.scalar(select(func.count()).select_from(models.Sandbox)) == sandboxes_before

    bootstrap = start_demo(client)
    install_actor_probe(guardian_app)
    ops_id = operator(bootstrap)["id"]
    controller_csrf = bootstrap["controller_csrf_token"]
    actor_csrf = bootstrap["actor_csrf_token"]

    wrong_origin = choose(
        client, ops_id, controller_csrf, headers={"Origin": "http://evil.example"}
    )
    no_origin = choose(client, ops_id, controller_csrf, headers={})
    assert wrong_origin.status_code == 403 and error_code(wrong_origin) == "ORIGIN_DENIED"
    assert no_origin.status_code == 403 and error_code(no_origin) == "ORIGIN_DENIED"
    tampered = controller_csrf[:-1] + ("1" if controller_csrf.endswith("0") else "0")
    for csrf in (None, "", actor_csrf, tampered, "x" * 64):
        denied = choose(client, ops_id, csrf)
        assert denied.status_code == 403, (csrf, denied.text)
        assert error_code(denied) == "CSRF_FAILED"

    actor_only = browser()
    actor_only.cookies.set(ACTOR_COOKIE, client.cookies.get(ACTOR_COOKIE))
    no_controller = choose(actor_only, ops_id, actor_csrf)
    assert no_controller.status_code == 401 and error_code(no_controller) == "SESSION_EXPIRED"

    probe_with_controller_csrf = client.post(
        PROBE, headers={**ORIGIN, "X-CSRF-Token": controller_csrf}
    )
    assert probe_with_controller_csrf.status_code == 403
    assert error_code(probe_with_controller_csrf) == "CSRF_FAILED"
    probe_wrong_origin = client.post(
        PROBE, headers={"Origin": "http://evil.example", "X-CSRF-Token": actor_csrf}
    )
    assert probe_wrong_origin.status_code == 403
    assert error_code(probe_wrong_origin) == "ORIGIN_DENIED"
    forged_role = client.post(
        PROBE, headers={**ORIGIN, "X-CSRF-Token": actor_csrf, "X-Actor-Role": "OPERATOR"}
    )
    assert forged_role.status_code == 200, forged_role.text
    assert forged_role.json()["role"] == "CUSTOMER"
    assert forged_role.json()["sandbox_id"] == bootstrap["sandbox_id"]

    still_linh = client.get(f"{API}/me")
    assert still_linh.json()["actor"]["id"] == bootstrap["current_actor"]["id"]
    allowed = choose(client, ops_id, controller_csrf)
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["actor"]["role"] == "OPERATOR"


def test_actor_rotation_revokes_old_cookie(browser, guardian_app, pg_engine: Engine):
    client = browser()
    bootstrap = start_demo(client)
    install_actor_probe(guardian_app)
    controller_token = client.cookies.get(CONTROLLER_COOKIE)
    linh_token = client.cookies.get(ACTOR_COOKIE)
    linh_csrf = bootstrap["actor_csrf_token"]

    selected = choose(client, operator(bootstrap)["id"], bootstrap["controller_csrf_token"])

    assert selected.status_code == 200, selected.text
    ops_me = Me.model_validate(selected.json())
    assert ops_me.actor.role == "OPERATOR"
    assert ops_me.accounts == [], "Ops has an identity but no invented wallet"
    cookies = response_cookies(selected)
    assert set(cookies) == {ACTOR_COOKIE}, "selection rotates only the actor cookie"
    assert cookies[ACTOR_COOKIE]["httponly"] is True
    ops_token = cookies[ACTOR_COOKIE].value
    assert ops_token != linh_token
    assert ops_me.actor_csrf_token != linh_csrf
    assert client.cookies.get(ACTOR_COOKIE) == ops_token
    assert client.cookies.get(CONTROLLER_COOKIE) == controller_token

    rows = {row.token_hash: row for row in sessions_of(pg_engine, bootstrap["sandbox_id"])}
    assert rows[sha256(linh_token)].revoked_at is not None
    assert rows[sha256(ops_token)].revoked_at is None
    assert rows[sha256(ops_token)].actor_id == ops_me.actor.id
    assert rows[sha256(ops_token)].csrf_hash == sha256(ops_me.actor_csrf_token)
    assert rows[sha256(controller_token)].revoked_at is None

    stale = browser()
    stale.cookies.set(ACTOR_COOKIE, linh_token)
    old_cookie = stale.get(f"{API}/me")
    assert old_cookie.status_code == 401 and error_code(old_cookie) == "SESSION_EXPIRED"
    old_csrf = client.post(PROBE, headers={**ORIGIN, "X-CSRF-Token": linh_csrf})
    assert old_csrf.status_code == 403 and error_code(old_csrf) == "CSRF_FAILED"
    current = client.get(f"{API}/me")
    assert current.json() == selected.json()

    back = choose(client, actor_named(bootstrap, "Linh")["id"], bootstrap["controller_csrf_token"])
    assert back.status_code == 200
    assert back.json()["actor"]["display_name"] == "Linh"
    stale.cookies.set(ACTOR_COOKIE, ops_token)
    assert stale.get(f"{API}/me").status_code == 401
    assert client.get(f"{API}/me").json()["actor"]["display_name"] == "Linh"
    active = [
        row
        for row in sessions_of(pg_engine, bootstrap["sandbox_id"])
        if row.kind == "ACTOR" and row.revoked_at is None
    ]
    assert len(active) == 1


def expire(pg_engine: Engine, table, *conditions) -> None:
    with pg_engine.begin() as connection:
        connection.execute(
            update(table).where(*conditions).values(expires_at=func.now() - timedelta(seconds=1))
        )


def test_expired_session_and_sandbox_denied(browser, pg_engine: Engine):
    client = browser()
    bootstrap = start_demo(client)
    ops_id = operator(bootstrap)["id"]
    csrf = bootstrap["controller_csrf_token"]

    expire(
        pg_engine,
        models.AuthSession,
        models.AuthSession.token_hash == sha256(client.cookies.get(ACTOR_COOKIE)),
    )
    expired_actor = client.get(f"{API}/me")
    assert expired_actor.status_code == 401 and error_code(expired_actor) == "SESSION_EXPIRED"
    reselected = choose(client, ops_id, csrf)
    assert reselected.status_code == 200, "the controller can issue a fresh actor session"
    assert client.get(f"{API}/me").status_code == 200

    expire(
        pg_engine,
        models.AuthSession,
        models.AuthSession.token_hash == sha256(client.cookies.get(CONTROLLER_COOKIE)),
    )
    expired_controller = choose(client, ops_id, csrf)
    assert expired_controller.status_code == 401
    assert error_code(expired_controller) == "SESSION_EXPIRED"

    other = browser()
    other_boot = start_demo(other)
    expire(pg_engine, models.Sandbox, models.Sandbox.id == uuid.UUID(other_boot["sandbox_id"]))
    sandbox_me = other.get(f"{API}/me")
    sandbox_select = choose(other, operator(other_boot)["id"], other_boot["controller_csrf_token"])
    assert sandbox_me.status_code == 401 and error_code(sandbox_me) == "SESSION_EXPIRED"
    assert sandbox_select.status_code == 401 and error_code(sandbox_select) == "SESSION_EXPIRED"

    anonymous = browser()
    assert anonymous.get(f"{API}/me").status_code == 401
    missing = choose(anonymous, ops_id, csrf)
    assert missing.status_code == 401 and error_code(missing) == "SESSION_EXPIRED"
    garbage = browser()
    garbage.cookies.set(ACTOR_COOKIE, "not-a-session")
    assert garbage.get(f"{API}/me").status_code == 401


def test_linh_ledger_backed_balance(browser, pg_engine: Engine):
    client = browser()
    bootstrap = start_demo(client)

    response = client.get(f"{API}/me")

    assert response.status_code == 200, response.text
    me = Me.model_validate(response.json())
    assert me.actor.display_name == "Linh"
    assert len(me.accounts) == 1
    wallet = me.accounts[0]
    assert (wallet.balance_vnd, wallet.reserved_vnd, wallet.available_vnd) == (
        10_000_000,
        0,
        10_000_000,
    )
    with Session(pg_engine) as db:
        account = db.get(models.Account, wallet.id)
        sandbox = db.get(models.Sandbox, uuid.UUID(bootstrap["sandbox_id"]))
        assert account is not None and sandbox is not None
        assert account.owner_actor_id == me.actor.id
        assert account.account_identifier not in response.text
        assert wallet.masked_identifier.endswith(account.account_identifier[-4:])
        assert wallet.bank_code == account.bank_code

        entries = db.scalars(
            select(models.LedgerEntry).where(models.LedgerEntry.account_id == account.id)
        ).all()
        assert sum(entry.amount_vnd for entry in entries) == account.balance_vnd == 10_000_000
        assert [e.amount_vnd for e in entries if e.kind == "OPENING"] == [11_500_000]
        debits = sorted(-e.amount_vnd for e in entries if e.kind == "TRANSFER_DEBIT")
        assert debits == [100_000, 200_000, 300_000, 400_000, 500_000]

        transfers = db.scalars(
            select(models.Transfer).where(models.Transfer.sender_account_id == account.id)
        ).all()
        assert sorted(t.amount_vnd for t in transfers) == debits
        assert {t.status for t in transfers} == {"SUCCEEDED"}
        assert len({t.recipient_account_id for t in transfers}) == 1
        for transfer in transfers:
            assert transfer.completed_at is not None and transfer.reserved_amount_vnd == 0
            assert sandbox.created_at - timedelta(days=10) <= transfer.created_at
            assert transfer.created_at < sandbox.created_at
            legs = db.scalars(
                select(models.LedgerEntry).where(models.LedgerEntry.transfer_id == transfer.id)
            ).all()
            assert sorted((leg.kind, leg.account_id, leg.amount_vnd) for leg in legs) == [
                ("TRANSFER_CREDIT", transfer.recipient_account_id, transfer.amount_vnd),
                ("TRANSFER_DEBIT", account.id, -transfer.amount_vnd),
            ]


def test_task3_operations_match_contract(guardian_app):
    schema = TestClient(guardian_app).get("/openapi.json").json()
    paths = schema["paths"]

    create = paths[f"{API}/demo/sessions"]["post"]
    choose = paths[f"{API}/demo/actors/select"]["post"]
    me = paths[f"{API}/me"]["get"]
    assert (create["operationId"], choose["operationId"], me["operationId"]) == (
        "createDemo",
        "selectActor",
        "getMe",
    )
    assert "201" in create["responses"] and "security" not in create
    assert choose["security"] == [{"demoCookie": []}]
    assert me["security"] == [{"actorCookie": []}]
    csrf = [p for p in choose.get("parameters", []) if p["name"] == "X-CSRF-Token"]
    assert csrf and csrf[0]["in"] == "header" and csrf[0]["required"] is True
    schemes = schema["components"]["securitySchemes"]
    assert schemes["actorCookie"] == {"type": "apiKey", "in": "cookie", "name": ACTOR_COOKIE}
    assert schemes["demoCookie"] == {"type": "apiKey", "in": "cookie", "name": CONTROLLER_COOKIE}
    fixture_writes = [
        path for path in paths if path.startswith(f"{API}/demo") and "fixture" in path.lower()
    ]
    assert fixture_writes == []
