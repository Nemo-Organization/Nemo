"""Task 4: scoped customer context and discovery lists (/me, /recipients, /orders).

Fixture IDs are discovered through these APIs and cross-checked against persisted rows. Rulings
encoded here: recipients are the sandbox's ownerless (external) seeded accounts, ordered by
display_name then id; orders are the caller's own, newest fee_verified_at first (NULL last) then
id descending; both lists are CUSTOMER-only, while /me serves both roles.
"""

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, inspect, select, update
from sqlalchemy.orm import Session

from app import models
from app.api.schemas import Me, OrderList, RecipientList
from tests.conftest import API, TEST_ORIGIN, start_demo

ORIGIN = {"Origin": TEST_ORIGIN}
ME = f"{API}/me"
RECIPIENTS = f"{API}/recipients"
ORDERS = f"{API}/orders"
CUSTOMERS = ("Linh", "An", "Binh", "Mai")
ORDER_FIELDS = {
    "id",
    "order_reference",
    "merchant_name",
    "original_amount_vnd",
    "return_fee_vnd",
    "fee_source",
    "fee_verified_at",
    "refund",
}
OPENAPI = yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "docs/guardian/openapi.yaml").read_text(encoding="utf-8")
)


def actor_named(bootstrap: dict[str, Any], name: str) -> dict[str, Any]:
    return next(actor for actor in bootstrap["actors"] if actor["display_name"] == name)


def select_actor(client: TestClient, bootstrap: dict[str, Any], name: str) -> dict[str, Any]:
    response = client.post(
        f"{API}/demo/actors/select",
        json={"actor_id": actor_named(bootstrap, name)["id"]},
        headers={**ORIGIN, "X-CSRF-Token": bootstrap["controller_csrf_token"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def get_ok(client: TestClient, path: str, **params: Any) -> dict[str, Any]:
    response = client.get(path, params=params)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in {name.lower() for name, _ in response.headers.multi_items()}
    return response.json()


def error_code(response) -> str:
    return response.json()["error"]["code"]


def ids(page: dict[str, Any]) -> list[str]:
    return [item["id"] for item in page["items"]]


def rows(db: Session, model, sandbox_id: str) -> list[Any]:
    return list(db.scalars(select(model).where(model.sandbox_id == uuid.UUID(sandbox_id))))


def external_ids(pg_engine: Engine, sandbox_id: str) -> list[str]:
    """Ownerless seeded accounts of one sandbox in the contract order (display_name, id)."""
    with Session(pg_engine) as db:
        accounts = [a for a in rows(db, models.Account, sandbox_id) if a.owner_actor_id is None]
    return [str(a.id) for a in sorted(accounts, key=lambda a: (a.display_name, a.id))]


def snapshot(pg_engine: Engine, sandbox_id: str) -> dict[str, dict[Any, tuple[Any, ...]]]:
    """Every column of the state that a read could plausibly touch, keyed by primary key."""
    tables = (
        models.AuthSession,
        models.Account,
        models.Order,
        models.Refund,
        models.Transfer,
        models.LedgerEntry,
        models.AuditEvent,
    )
    with Session(pg_engine) as db:
        return {
            model.__tablename__: {
                inspect(row).identity: tuple(
                    getattr(row, column.key) for column in model.__table__.columns
                )
                for row in rows(db, model, sandbox_id)
            }
            for model in tables
        }


def test_lists_are_scoped_paginated_and_deterministic(browser, pg_engine: Engine):
    first, second = browser(), browser()
    boot_a = start_demo(first, "FALSE_POSITIVE")
    boot_b = start_demo(second)
    expected_a = external_ids(pg_engine, boot_a["sandbox_id"])
    expected_b = external_ids(pg_engine, boot_b["sandbox_id"])
    assert len(expected_a) == 4 and len(expected_b) == 3, "SHOP_REAL only in FALSE_POSITIVE"

    full_a = get_ok(first, RECIPIENTS)
    RecipientList.model_validate(full_a)
    assert (full_a["total"], full_a["limit"], full_a["offset"]) == (4, 20, 0)
    assert ids(full_a) == expected_a
    full_b = get_ok(second, RECIPIENTS)
    assert (full_b["total"], ids(full_b)) == (3, expected_b)
    assert not set(expected_a) & set(expected_b)
    assert get_ok(first, RECIPIENTS) == full_a, "repeat reads are identical"

    pages = [get_ok(first, RECIPIENTS, limit=1, offset=offset) for offset in range(5)]
    assert [(p["total"], p["limit"], p["offset"]) for p in pages] == [(4, 1, i) for i in range(5)]
    assert [item for page in pages for item in ids(page)] == expected_a
    assert pages[-1]["items"] == []
    window = get_ok(first, RECIPIENTS, limit=2, offset=1)
    assert (window["total"], ids(window)) == (4, expected_a[1:3])
    beyond = get_ok(first, RECIPIENTS, limit=100, offset=50)
    assert (beyond["total"], beyond["items"], beyond["limit"]) == (4, [], 100)

    # Linh in sandbox A gets three more orders: a same-timestamp pair and an unknown-fee order.
    with Session(pg_engine) as db, db.begin():
        linh = next(
            a for a in rows(db, models.Actor, boot_a["sandbox_id"]) if a.display_name == "Linh"
        )
        (shop,) = [
            o
            for o in rows(db, models.Order, boot_a["sandbox_id"])
            if o.customer_actor_id == linh.id
        ]
        newer = shop.fee_verified_at + timedelta(hours=12)
        extras = [
            models.Order(
                id=uuid.uuid4(),
                sandbox_id=linh.sandbox_id,
                customer_actor_id=linh.id,
                order_reference=f"SHOP-90{n}",
                merchant_name="Extra test merchant (synthetic)",
                original_amount_vnd=100_000,
                return_fee_vnd=None if n == 3 else 0,
                fee_source=None if n == 3 else "Test confirmation",
                fee_verified_at=None if n == 3 else newer,
            )
            for n in (1, 2, 3)
        ]
        db.add_all(extras)
        shop_id = str(shop.id)
        tied, undated = [str(o.id) for o in extras[:2]], str(extras[2].id)
    expected_orders = [*sorted(tied, key=uuid.UUID, reverse=True), shop_id, undated]

    orders = get_ok(first, ORDERS)
    OrderList.model_validate(orders)
    assert (orders["total"], orders["limit"], orders["offset"]) == (4, 20, 0)
    assert ids(orders) == expected_orders, "newest timestamp first, then id; unknown time last"
    assert get_ok(first, ORDERS) == orders
    sliced = get_ok(first, ORDERS, limit=1, offset=2)
    assert (sliced["total"], ids(sliced)) == (4, [shop_id])
    tail = get_ok(first, ORDERS, limit=2, offset=3)
    assert (tail["total"], ids(tail)) == (4, expected_orders[3:])

    before = snapshot(pg_engine, boot_b["sandbox_id"])
    orders_b = get_ok(second, ORDERS)
    assert orders_b["total"] == 1 and orders_b["items"][0]["order_reference"] == "SHOP-4502"
    assert not set(ids(orders_b)) & set(expected_orders)
    get_ok(second, RECIPIENTS, limit=2)
    get_ok(second, ME)
    assert snapshot(pg_engine, boot_b["sandbox_id"]) == before, "GET must not mutate state"

    select_actor(first, boot_a, "An")
    an_orders = get_ok(first, ORDERS)
    assert an_orders["total"] == 1
    assert [o["order_reference"] for o in an_orders["items"]] == ["SHOP-4518"]
    assert an_orders["items"][0]["refund"] is None
    assert ids(get_ok(first, RECIPIENTS)) == expected_a

    for query in (
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"limit": "ten"},
        {"limit": 1.5},
        {"offset": "true"},
    ):
        for path in (RECIPIENTS, ORDERS):
            invalid = second.get(path, params=query)
            assert invalid.status_code == 422, (path, query, invalid.text)
            assert error_code(invalid) == "VALIDATION_ERROR"


def test_own_wallet_is_not_a_recipient(browser, pg_engine: Engine):
    client = browser()
    bootstrap = start_demo(client)
    expected = external_ids(pg_engine, bootstrap["sandbox_id"])

    wallets: set[str] = set()
    for name in CUSTOMERS:
        me = select_actor(client, bootstrap, name)
        own = {account["id"] for account in me["accounts"]}
        assert len(own) == 1, name
        listed = get_ok(client, RECIPIENTS, limit=100)
        assert not own & set(ids(listed)), f"{name} sees own wallet as a recipient"
        assert ids(listed) == expected, "every customer sees the same seeded recipients"
        wallets |= own
    assert len(wallets) == 4 and not wallets & set(expected)

    with Session(pg_engine) as db:
        accounts = {str(a.id): a for a in rows(db, models.Account, bootstrap["sandbox_id"])}
        assert all(accounts[recipient].owner_actor_id is None for recipient in expected)
        assert {i for i, a in accounts.items() if a.owner_actor_id is not None} == wallets
        linh_wallet = next(
            a
            for a in accounts.values()
            if a.owner_actor_id == uuid.UUID(actor_named(bootstrap, "Linh")["id"])
        )
        familiar = {
            str(t.recipient_account_id)
            for t in rows(db, models.Transfer, bootstrap["sandbox_id"])
            if t.sender_account_id == linh_wallet.id
        }
    assert len(familiar) == 1 and familiar <= set(expected), "CAFE is discoverable"


def test_order_fee_zero_and_unknown_are_distinct(browser, pg_engine: Engine):
    known, unknown = browser(), browser()
    boot_known = start_demo(known, "MAIN_REFUND")
    boot_unknown = start_demo(unknown, "INSUFFICIENT_EVIDENCE")

    results: dict[str, dict[str, Any]] = {}
    for label, client, bootstrap in (
        ("known", known, boot_known),
        ("unknown", unknown, boot_unknown),
    ):
        (wallet,) = get_ok(client, ME)["accounts"]
        response = client.get(ORDERS)
        assert response.status_code == 200, response.text
        (order,) = response.json()["items"]
        assert set(order) == ORDER_FIELDS, "required nullable fields stay present"
        assert (order["order_reference"], order["original_amount_vnd"]) == ("SHOP-4502", 500_000)
        assert order["merchant_name"]
        assert order["refund"] == {
            "id": order["refund"]["id"],
            "order_id": order["id"],
            "account_id": wallet["id"],
            "amount_vnd": 500_000,
            "status": "APPROVED",
            "settled_at": None,
        }
        with Session(pg_engine) as db:
            stored = db.get(models.Order, uuid.UUID(order["id"]))
            refund = db.get(models.Refund, uuid.UUID(order["refund"]["id"]))
            assert stored is not None and refund is not None
            assert str(stored.sandbox_id) == bootstrap["sandbox_id"]
            assert stored.return_fee_vnd == order["return_fee_vnd"]
            assert refund.order_id == stored.id
        results[label] = {"order": order, "text": response.text}

    zero = results["known"]["order"]
    assert zero["return_fee_vnd"] == 0 and type(zero["return_fee_vnd"]) is int
    assert zero["fee_source"] == "Synthetic merchant fee confirmation"
    verified_at = datetime.fromisoformat(zero["fee_verified_at"])
    assert verified_at.utcoffset() == timedelta(0) and verified_at < datetime.now(UTC)
    assert '"return_fee_vnd":0,' in results["known"]["text"]

    missing = results["unknown"]["order"]
    assert (missing["return_fee_vnd"], missing["fee_source"], missing["fee_verified_at"]) == (
        None,
        None,
        None,
    )
    assert '"return_fee_vnd":null,' in results["unknown"]["text"]

    select_actor(unknown, boot_unknown, "An")
    (an_order,) = get_ok(unknown, ORDERS)["items"]
    assert set(an_order) == ORDER_FIELDS
    assert (an_order["return_fee_vnd"], an_order["refund"]) == (0, None)
    assert an_order["fee_source"] is not None and an_order["fee_verified_at"] is not None


def test_account_identifiers_masked(browser, pg_engine: Engine):
    client = browser()
    bootstrap = start_demo(client, "FALSE_POSITIVE")
    with Session(pg_engine) as db:
        accounts = {str(a.id): a for a in rows(db, models.Account, bootstrap["sandbox_id"])}
    identifiers = [account.account_identifier for account in accounts.values()]

    def assert_masked(response) -> None:
        assert response.status_code == 200, response.text
        for identifier in identifiers:
            assert identifier not in response.text
        assert "DEMO-WALLET" not in response.text and "DEMO-ACCT" not in response.text

    for name in CUSTOMERS:
        select_actor(client, bootstrap, name)
        me_response, recipients_response, orders_response = (
            client.get(ME),
            client.get(RECIPIENTS),
            client.get(ORDERS),
        )
        for response in (me_response, recipients_response, orders_response):
            assert_masked(response)

        me = Me.model_validate(me_response.json())
        (wallet,) = me.accounts
        stored = accounts[str(wallet.id)]
        assert stored.owner_actor_id == me.actor.id
        assert wallet.masked_identifier == "****" + stored.account_identifier[-4:]
        assert (wallet.bank_code, wallet.display_name) == (stored.bank_code, stored.display_name)
        assert wallet.available_vnd == stored.balance_vnd - stored.reserved_vnd

        for item in recipients_response.json()["items"]:
            assert set(item) == {"id", "display_name", "bank_code", "masked_identifier"}
            stored = accounts[item["id"]]
            assert item["masked_identifier"] == "****" + stored.account_identifier[-4:]
            assert (item["bank_code"], item["display_name"]) == (
                stored.bank_code,
                stored.display_name,
            )

    ops = select_actor(client, bootstrap, "Ops")
    ops_me = client.get(ME)
    assert_masked(ops_me)
    assert ops_me.json() == ops
    assert ops_me.json()["actor"] == actor_named(bootstrap, "Ops")
    assert ops_me.json()["accounts"] == [], "Ops has an identity but no invented wallet"
    assert ops_me.json()["sandbox_id"] == bootstrap["sandbox_id"]


def test_operator_cannot_read_customer_only_lists(browser, pg_engine: Engine):
    client = browser()
    bootstrap = start_demo(client)
    linh_token = client.cookies.get("guardian_session")
    assert get_ok(client, RECIPIENTS)["total"] == 3
    assert get_ok(client, ORDERS)["total"] == 1

    select_actor(client, bootstrap, "Ops")
    linh = actor_named(bootstrap, "Linh")
    for path in (RECIPIENTS, ORDERS):
        for headers in ({}, {"X-Actor-Role": "CUSTOMER", "X-Actor-ID": linh["id"]}):
            denied = client.get(path, params={"limit": 5}, headers=headers)
            assert denied.status_code == 403, (path, headers, denied.text)
            assert error_code(denied) == "FORBIDDEN"
            assert "items" not in denied.json()
            assert denied.headers["cache-control"] == "no-store"
        invalid_page = client.get(path, params={"limit": 0})
        assert invalid_page.status_code == 403, "role is checked before query validation"
    ops_me = get_ok(client, ME)
    assert ops_me["actor"]["role"] == "OPERATOR" and ops_me["accounts"] == []

    stale = browser()
    stale.cookies.set("guardian_session", linh_token)
    anonymous = browser()
    garbage = browser()
    garbage.cookies.set("guardian_session", "not-a-session")
    expired = browser()
    expired_sandbox = uuid.UUID(start_demo(expired)["sandbox_id"])
    with pg_engine.begin() as connection:
        connection.execute(
            update(models.AuthSession)
            .where(models.AuthSession.sandbox_id == expired_sandbox)
            .values(expires_at=func.now() - timedelta(seconds=1))
        )
    for unauthenticated in (stale, anonymous, garbage, expired):
        for path in (RECIPIENTS, ORDERS, ME):
            for params in ({}, {"limit": 0}):
                response = unauthenticated.get(path, params=params)
                assert response.status_code == 401, (path, params, response.text)
                assert error_code(response) == "SESSION_EXPIRED"


def test_task4_operations_match_contract(guardian_app):
    generated = TestClient(guardian_app).get("/openapi.json").json()["paths"]

    def bounds(parameters: list[dict[str, Any]]) -> dict[str, tuple[Any, ...]]:
        keys = ("type", "minimum", "maximum", "default")
        return {
            p["name"]: (p["in"], p.get("required", False), *(p["schema"].get(k) for k in keys))
            for p in parameters
        }

    for path, model in (("/recipients", "RecipientList"), ("/orders", "OrderList"), ("/me", "Me")):
        operation = generated[f"{API}{path}"]["get"]
        contract = OPENAPI["paths"][path]["get"]
        assert operation["operationId"] == contract["operationId"]
        assert operation["tags"] == contract["tags"]
        assert operation["security"] == contract["security"] == [{"actorCookie": []}]
        assert bounds(operation.get("parameters", [])) == bounds(contract.get("parameters", []))
        success = operation["responses"]["200"]["content"]["application/json"]["schema"]
        assert success["$ref"] == f"#/components/schemas/{model}"
