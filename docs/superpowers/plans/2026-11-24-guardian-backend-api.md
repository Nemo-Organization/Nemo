# Guardian Backend API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for inline execution, or superpowers:subagent-driven-development if selected by the developer. Steps use checkbox (`- [ ]`) syntax for tracking. Implement and verify one task at a time; commit each completed task separately. Do not treat this document as completed implementation.

**Goal:** Implement all 32 Guardian API operations with persistent PostgreSQL state, enforceable synthetic money flows, isolated demo identities, evidence-linked AI and reviewed operator interventions.

**Architecture:** Preserve the existing FastAPI modular monolith and synchronous SQLAlchemy/psycopg sessions. Thin HTTP routers call application services that own transaction completion; subordinate domain helpers never commit. External AI and object-storage calls run outside financial/database lock windows. The existing Next.js UI integrates through a separate same-origin proxy task.

**Tech Stack:** Python 3.12, FastAPI/Pydantic v2, SQLAlchemy 2, psycopg, Alembic, PostgreSQL 16+, Neon-compatible S3 object storage via an adapter, and one explicitly configured vision/text provider.

**Spec:** `docs/guardian/product-requirements.md`, `data-model.md`, `database-specification.md`, `schema.sql`, `openapi.yaml`, `scenarios.md`, `evaluation.md`, `architecture.md`. The 23 November delivery plan remains the product-wide plan; this document expands its backend tasks. Conflicts resolve against the product requirements and shared API/SQL contract, with an explicit recorded ruling.

## Global Constraints

- Preserve `Frontend/` and `Backend/` casing and the existing dependency lock workflow.
- Money is synthetic, positive-integer VND, with at most 1,000,000,000 per transfer. No real payment dispatch or MoMo production access.
- Exactly two application roles: CUSTOMER and OPERATOR. DEMO_CONTROL is a separate sandbox-management credential, not a third privileged employee role.
- Every resource lookup uses server-resolved sandbox and actor scope. Inaccessible IDs return 404; authenticated callers with the wrong role receive 403.
- Mutating requests verify exact Origin and the CSRF token matching that endpoint's actor/controller credential. UUIDs and role headers never authorize access.
- Session and sandbox default lifetimes: 24 hours. Draft: 30 minutes. Hold: 15 minutes. Assessment acknowledgement: five minutes. Server/database time is authoritative.
- A draft reserves nothing. A hold reserves once. Operator approval produces READY, never a debit. The customer reconfirms; a new restriction invalidates the old clearance.
- Acquire recipient advisory lock, sorted account row locks, then sorted transfer/refund locks. Never acquire the advisory lock after account locks.
- Anomaly rule: at least five settled outgoing observations in 30 days; amount >= three times median AND >= 2,000,000 => WARN. Sparse history remains INSUFFICIENT_HISTORY. Behavioral risk alone does not create HOLD.
- Model output is untrusted evidence; it cannot query arbitrary SQL, invoke shell tools, authorize transfers or change restrictions. Normal transfer/risk endpoints never call the model.
- Images: PNG/JPEG/WebP, maximum 5 MiB. Text: maximum 12,000 characters. Inference deadline: 20 seconds total. Grouping input: at most 20 reports.
- Provider limits: 20 analyses and five grouping runs per sandbox per hour; 300 total provider calls per deployment per day by default. Tests use injected adapters; no hard-coded production AI verdict.
- Runtime secrets stay out of git, logs, browser bundles and prompts. Never echo a live connection string while checking configuration.
- Disposable PostgreSQL is mandatory for money/concurrency verification. Never run reset/downgrade/test fixtures against the user's Neon production branch.
- No deployment, shared-branch push, merge, production migration or account provisioning is part of this backend implementation pass. Prepare commands and report those gates separately.

## Review Focus

1. A sender's amount is WARN, then Ops adds HOLD before confirm: current restriction wins, and no stale acknowledgement bypasses it (Tasks 6, 11).
2. Expiry, cancellation, confirmation and duplicate submissions race: exactly one result and no stranded/double reservation (Tasks 5, 7, 8).
3. A caller supplies a foreign UUID, forged role, old actor CSRF or another actor's evidence: no data disclosure or elevation (Tasks 3, 4, 9, 10, 12).
4. A process dies after persisting PENDING or uploading a private object: replay stays one logical run, cleanup is retryable, money APIs remain available (Tasks 9, 10, 14).
5. A forwarded screenshot contains a real issued code: exact trace may identify an exposure scope but must not accuse a partner or automatically publish/restrict (Tasks 12, 13).

## Baseline and concrete findings

Inspected `dev` at `6f96e51` on 24 November 2026. Working branch: `feat/guardian-api-implementation`.

- Implemented: health, request IDs, safe errors, settings, lazy DB engine/session helper, Alembic scaffold, Docker, launchers and skeleton tests.
- Not implemented: domain models/migration, session/demo endpoints, transfers, AI/evidence, reports or Ops endpoints. Current generated OpenAPI exposes only health.
- Shared contract: 32 operations across 28 paths; SQL: 19 tables, 161 physical columns.
- FE has transfer/operator UI but mock DTOs and decision logic differ from the contract. See `docs/guardian/frontend-integration-notes.md`; do not copy the local mock engine into BE.
- The existing docs still prescribe GCS. This plan proposes a storage adapter with Neon S3 as the selected deployment target, matching the team's current Neon setup. Update architecture/cloud examples when this choice is implemented; do not claim the storage adapter already exists.
- Docker engine was unavailable at inspection. Start the installed Docker engine or use an existing local PostgreSQL binary to create a disposable test instance. This is a verification dependency, not a reason to substitute SQLite or use production data.
- Neon and AI credentials/live connectivity are not established by this plan. An existing `.env` does not prove that a provider works.

## Implementation decisions to carry into execution

| Decision | Implementation and consequence |
| --- | --- |
| SQL authority | Build a frozen initial Alembic revision from schema.sql, preserving checks, composite FKs, partial unique indexes and types. Do not make a released migration load mutable docs at runtime or execute nested BEGIN/COMMIT. |
| Model layout | Put initial SQLAlchemy mappings in `app/models.py`, using the shared Base; 19 tables do not justify a generic repository framework. Split domain services by responsibility. |
| Unit of work | Auth queries may already start a SQLAlchemy transaction. Top-level application services complete that existing transaction explicitly; helpers only flush. Do not call `Session.begin()` blindly after resolving identity. Roll back on failure. |
| Durable conflict response | When a 409 must include a newly persisted assessment or reconciled expiry, commit that intended state first and then return the structured conflict. A dependency rollback must not silently undo the assessment referenced in the response. |
| CSRF recovery | Derive an actor/controller CSRF token deterministically with HMAC-SHA256 keyed by the high-entropy opaque session token and a domain-separated constant. Persist only its hash, compare in constant time. `/me` can rederive actor CSRF from the authenticated HttpOnly cookie without storing plaintext tokens or rotating state on GET. Add tests before adopting this implementation detail. |
| Cookie policy | HttpOnly, SameSite=Lax, Path=/; Secure in hosted HTTPS, disabled only for local HTTP. Keep controller and actor cookies distinct; rotate/revoke the prior actor session on selection within that sandbox. |
| Bootstrap protection | Bootstrap has no existing CSRF credential, but still requires configured Origin. Define its API docs and tests explicitly so Swagger/manual requests send that Origin too. |
| Strict schemas | Reject extra request fields and invalid UUIDs, non-integer/bool/fractional VND, oversized notes, duplicate evidence IDs and naive timestamps. Required nullable response fields are present as null, not omitted. Multipart fields are parsed using their form-specific types. |
| Read consistency | `/me`, transfer reads, holds and money writes reconcile due reservations using the same account-first service. Reads may commit expiry reconciliation; they never debit or create an unrelated payment. |
| Stable pagination | All list operations return items/total/limit/offset with deterministic created_at/id or display_name/id ordering; default 20, maximum 100, offset >= 0. Total counts the authorized set before slicing. |
| Restriction identity | Immutable decision rows; one active row per recipient. Override only the exact cleared restriction ID. Expired ACTIVE rows are normalized under the recipient lock before insertion. |
| Evidence storage | Private server-generated object keys; bucket and endpoint come from settings, never user input. No public URLs or file paths supplied by the browser. Read through the authenticated evidence endpoint. |
| AI persistence | Persist canonical input digest and official-fact snapshot before inference; commit PENDING, release transaction, invoke provider, then finalize in a short transaction. Existing logical runs never silently re-invoke on replay. |
| External dependency failure | Missing/failed provider returns an explicit unavailable/failed/inconclusive outcome. Test adapters are dependency overrides, not an undisclosed production fallback. Storage failures never result in an evidence_available=true lie. |
| Runtime provider checkpoint | Before Task 9's concrete provider adapter, inspect only configured provider/model names and credential presence, then select the team's actually authorized vision/text API. Coding-agent credits are not runtime credentials. Record the SDK/model/region and one synthetic smoke result. If none is available, ask for that missing runtime choice while continuing deterministic backend tasks; do not silently switch billing providers. |
| Trace authority | Only exact issued codes from permitted evidence link to a batch. Access logs corroborate legitimate reads, not guilt. Notice recipients derive from trace_references -> orders -> customer actors. |
| Integration boundary | Backend returns snake_case wire DTOs. FE may map them to camelCase view models. Shared field/enum changes require updating OpenAPI and examples in the same commit. |

## File map

| Path | Responsibility |
| --- | --- |
| `Backend/app/models.py`, `migrations/versions/0001_guardian.py` | Typed tables and frozen schema revision |
| `Backend/app/api/schemas.py`, `pagination.py` | Contract DTOs/enums and bounded list inputs |
| `Backend/app/auth/principal.py`, `service.py`, `dependencies.py`, `router.py` | Hashed sessions, identity/role resolution, Origin/CSRF, `/me` |
| `Backend/app/demo/fixtures.py`, `service.py`, `router.py`, `refunds.py` | Isolated fixtures, controller actions and refund settlement |
| `Backend/app/transfers/router.py`, `service.py`, `locking.py`, `expiry.py`, `serialization.py` | Draft/confirm/cancel, lock order, ledger/reservations and state reads |
| `Backend/app/risk/service.py`, `facts.py` | Pure evaluator, history queries and assessment fingerprints |
| `Backend/app/evidence/storage.py`, `validation.py`, `router.py` | Object-store protocol/S3 implementation, image validation and authenticated bytes |
| `Backend/app/investigation/provider.py`, `schemas.py`, `prompts.py`, `service.py`, `grouping.py`, `trace.py` | Provider boundary, bounded analysis/grouping and exact-reference investigation |
| `Backend/app/operations/reports.py`, `holds.py`, `restrictions.py`, `notices.py`, `audit.py`, `router.py` | Operator cases and reviewed decisions |
| `Backend/app/maintenance.py` | One-shot expiry/stale-run/retention work using shared services |
| `Backend/tests/conftest.py`, domain test files, `test_contract.py`, `test_primary_journey.py` | Disposable PostgreSQL, authorized clients, deterministic adapters and whole-flow proof |
| `Backend/README.md`, `.env.example`, `docs/guardian/validation.md` | Setup, external configuration and observed delivery status |

Keep routers limited to validation/dependencies/status serialization. Avoid a single catch-all endpoint dispatcher, giant service file, universal JSON model or reflection-loaded runtime contract in place of real Pydantic DTOs.

## Delivery gates and dependencies

| Gate | Tasks | FE handoff | Exit condition |
| --- | --- | --- | --- |
| A: data and identity | 1-4 | Bootstrap, actor selection, `/me`, recipients/orders | Migrated real PG; two isolated clients; ledger-backed fixtures; exact DTOs |
| B: money lifecycle | 5-8 | Transfer form, risk, hold/cancel/reconfirm, refund | Normal/WARN/HOLD and retries/races pass without AI |
| C: evidence and cases | 9-10 | Upload, analysis, report submission/queue | Private evidence, persistent AI statuses, exact replay and permissions |
| D: operations | 11-13 | Reviews, restrictions, trace, notices, audit | Scoped reviewed decisions; batch recipients correct; no duplicates |
| E: integration readiness | 14-15 | Replace remaining mock services through agreed proxy | 32 operations covered, primary journey, maintenance and run instructions verified |

Tasks 1 -> 2 -> 3 -> 4 precede all domain HTTP work. Tasks 5-8 share money state and are sequential. Task 9 can be assigned to the AI developer after Task 3 only with explicit file ownership; Task 10 consumes it. Task 11 consumes Tasks 7 and 10; Tasks 12-13 consume reports. Task 14 consumes all persistence lifecycles; Task 15 is the final gate.

Planning allowance: roughly 45-70 backend engineering hours including meaningful tests/review and uncertainty, not a promise based on code-generation speed. Prefer Gate A on 24-25 November, B by 26-27 November, C/D by 28-29 November, and E by 30 November-1 December. Keep 2 December for hosted integration/submission preparation. Re-estimate after Gate A using observed throughput. Agent assistance accelerates implementation but does not replace concurrency, live-provider or FE integration checks.

## Common task execution contract

For every task below:

1. Read its referenced spec sections and consumed interfaces. Record the starting commit and any ruling in a git-ignored execution ledger.
2. Write the named behavioral tests before implementation and run the task command. The test must fail for the intended missing behavior, not a typo or missing test credentials. Unit-only task failures may be missing symbols; API tasks must demonstrate missing/incorrect behavior through HTTP.
3. Implement the listed interfaces, with no unrelated FE changes. Run the task tests until green, then the already-completed dependent tests.
4. Run `uv run ruff check .` and `uv run ruff format --check .` from Backend. Record exact command, counts, skips and failures; a skipped money test is not a passed gate.
5. Commit the task using its proposed message, with only relevant paths. Update the implementation ledger and handoff gate status. No automatic push/merge/deploy.

The task assertions below are test outcomes to encode in the named tests; helpers such as authenticated clients and fixture discovery are established in Tasks 1-4 rather than repeated as pseudo-production code.

### Task 1: Disposable PostgreSQL harness and complete initial schema

**Files:** create `Backend/tests/conftest.py`, `tests/test_schema.py`, `app/models.py`, `migrations/versions/0001_guardian.py`; modify `migrations/env.py` to load model metadata.

**Interfaces:** produces all 19 mapped tables through `Base.metadata`; migration revision `0001_guardian`; `pg_engine` and `db_session` pytest fixtures. `TEST_DATABASE_URL` must name a dedicated test DB; `.env` DATABASE_URL is never an implicit test target.

- [ ] RED: `test_initial_migration_has_19_tables_and_161_columns`, `test_models_match_migrated_columns`, `test_cross_sandbox_fk_rejected`, `test_reservation_exceeds_balance_rejected`, `test_nullable_fee_requires_provenance`, `test_duplicate_ledger_and_active_restriction_rejected`.
- [ ] Run `uv run pytest tests/test_schema.py -q`; expected RED on absent revision/tables, after verifying the test database is reachable.
- [ ] Implement typed mappings and explicit migration constraints/indexes equivalent to schema.sql. Compare model/migration metadata; tests exclude Alembic's own bookkeeping table from the 19-table count. Do not use `create_all` to hide a missing migration.
- [ ] GREEN: same command passes on PostgreSQL 16+; run upgrade twice and offline SQL generation. Downgrade/re-upgrade, if used, is restricted to the fresh disposable DB and reported separately.
- [ ] Commit `feat(backend): implement Guardian schema and initial migration`.

### Task 2: Contract DTOs, pagination and structured conflicts

**Files:** create `Backend/app/api/__init__.py`, `schemas.py`, `pagination.py`, `tests/test_api_schemas.py`; modify `app/errors.py` and relevant error tests.

**Interfaces:** produces Pydantic request/response classes with the exact OpenAPI names/enums; `Page[T]`; `PageParams(limit=20, offset=0)`; `ApplicationError(..., current_transfer: Transfer | None, assessment: RiskAssessment | None)` and omission of absent optional error context.

- [ ] RED: `test_amount_rejects_bool_float_zero_and_over_limit`, `test_required_nullable_fields_remain_present`, `test_extra_body_fields_rejected`, `test_error_context_matches_contract`, `test_pagination_bounds`.
- [ ] Run `uv run pytest tests/test_api_schemas.py tests/test_errors.py -q`; expected RED for missing DTOs/context support.
- [ ] Implement strict JSON DTOs, aware timestamps and length/uniqueness rules. Keep evidence upload parsing distinct from strict JSON integer parsing. Preserve safe error text and request IDs; do not expose raw Pydantic input or secrets.
- [ ] GREEN: valid 20,000 and null fee serialize; amount 0, fractional/bool values and 1,000,000,001 fail; limit 0/101 and negative offset fail. Existing skeleton error tests still pass.
- [ ] Commit `feat(backend): define Guardian API schemas and conflict responses`.

### Task 3: Isolated scenario bootstrap and authenticated actor selection

**Files:** create `auth/principal.py`, `auth/service.py`, `auth/dependencies.py`, `auth/router.py`, `demo/fixtures.py`, `demo/service.py`, `demo/router.py`, `tests/test_sessions.py`, `tests/test_fixtures.py`; modify main/settings/env examples only where consumed.

**Interfaces:** `Principal(sandbox_id: UUID, actor_id: UUID, role: Literal['CUSTOMER','OPERATOR'], request_id: str)`; `DemoPrincipal(sandbox_id: UUID, request_id: str)`; `SystemPrincipal(sandbox_id: UUID, request_id: str)` for audited maintenance; `derive_csrf(session_token: str) -> str`; `resolve_actor(session: Session, cookie: str) -> Principal`; `resolve_controller(session: Session, cookie: str) -> DemoPrincipal`; `create_sandbox(session: Session, scenario: Scenario) -> Bootstrap`; `select_actor(session: Session, controller: DemoPrincipal, actor_id: UUID) -> Me`. Produces createDemo/selectActor/getMe.

- [ ] RED: `test_bootstrap_sets_distinct_hashed_credentials`, `test_me_restores_matching_csrf_after_refresh`, `test_two_sandboxes_are_isolated`, `test_foreign_actor_selection_is_404`, `test_wrong_origin_and_csrf_denied`, `test_actor_rotation_revokes_old_cookie`, `test_expired_session_and_sandbox_denied`, `test_linh_ledger_backed_balance`.
- [ ] Run `uv run pytest tests/test_sessions.py tests/test_fixtures.py -q`; expected RED because demo/auth routes are absent.
- [ ] Seed every sandbox atomically with new UUIDs: four customers, Ops, seeded recipients, ledger-backed history, orders/refunds, two resolved near-miss reports and a reviewed restriction, two partners/batches and issued references/access events. FALSE_POSITIVE adds the mistaken restriction; INSUFFICIENT_EVIDENCE uses NULL fee. No public fixture-write route.
- [ ] GREEN: Linh opening 11,500,000 less five historical amounts 100k/200k/300k/400k/500k equals 10,000,000; An has two historical transfers. Session DB stores token/CSRF hashes only. Actor CSRF cannot authorize controller actions and vice versa. Origin mismatch fails even with a valid cookie.
- [ ] Commit `feat(backend): add isolated demo sessions and authenticated actors`.

### Task 4: Scoped customer context and discovery endpoints

**Files:** create `Backend/app/demo/queries.py`, `tests/test_customer_queries.py`; extend auth/demo routers and serialization.

**Interfaces:** `list_recipients(session: Session, principal: Principal, page: PageParams) -> RecipientList`; `list_orders(...) -> OrderList`; `get_me(...) -> Me`. Produces listRecipients/listOrders and finalized getMe response. Account reconciliation hook is introduced in Task 7 and then used here.

- [ ] RED: `test_lists_are_scoped_paginated_and_deterministic`, `test_own_wallet_is_not_a_recipient`, `test_order_fee_zero_and_unknown_are_distinct`, `test_account_identifiers_masked`, `test_operator_cannot_read_customer_only_lists`.
- [ ] Run `uv run pytest tests/test_customer_queries.py -q`; expected RED for absent list routes.
- [ ] Implement DTO projection without full identifiers, ownership filtering, stable order and total before pagination. `/me` for Ops returns its actor identity and no invented customer wallet. Fixture IDs are discoverable from API, not compiled UI constants.
- [ ] GREEN: second sandbox sees only its recipients/orders; Linh sees her own refund/order; no provider call is required.
- [ ] Commit `feat(backend): expose scoped customer context and reference lists`.

### Task 5: Immutable transfer drafts and exact request replay

**Files:** create `transfers/router.py`, `service.py`, `serialization.py`, `tests/test_transfer_drafts.py`; extend main router registration.

**Interfaces:** `create_transfer(session: Session, principal: Principal, command: CreateTransfer) -> Transfer`; `get_transfer(...) -> Transfer`; `list_transfers(...) -> TransferList`. Produces createTransfer/getTransfer/listTransfers; maps `replayed` to 201 or 200 for creation.

- [ ] RED: `test_new_draft_does_not_reserve`, `test_exact_draft_replay_is_200`, `test_changed_replay_is_409`, `test_parallel_duplicate_drafts_create_one_row`, `test_foreign_sender_or_recipient_is_404`, `test_self_transfer_rejected`, `test_expired_draft_cannot_confirm` (last assertion completed in Task 7).
- [ ] Run `uv run pytest tests/test_transfer_drafts.py -q`; expected RED for missing transfer behavior. Stage expiry assertion with Task 7 rather than leaving a permanent expected-failure marker.
- [ ] Implement DB-enforced key `(sandbox, sender, client_request_id)`, race-safe lookup/insert and canonical immutable field comparison. Reject invalid ownership; server supplies recipient display details. A retry cannot edit an existing draft.
- [ ] GREEN: one draft, unchanged balance/reservation and exact 201/200/409 semantics, including concurrent same-key creation.
- [ ] Commit `feat(backend): add immutable transfer drafts and request replay`.

### Task 6: Independent behavioral and recipient assessments

**Files:** create `risk/service.py`, `risk/facts.py`, `tests/test_risk.py`, `tests/test_assessments.py`; extend transfers router/serialization.

**Interfaces:** `RiskFacts` includes amount, sample count, median, current restriction ID/action and policy version; `evaluate_risk(facts: RiskFacts) -> RiskDecision` is pure; `assess_transfer(session: Session, principal: Principal, transfer_id: UUID) -> RiskAssessment`; `fingerprint_facts(facts: RiskFacts) -> str`. Produces assessTransfer and persisted acknowledgement source.

- [ ] RED: `test_8m_against_300k_median_warns`, `test_2m_threshold_is_inclusive`, `test_four_samples_are_insufficient`, `test_20k_verified_recipient_holds`, `test_expired_restriction_ignored`, `test_assessment_fingerprint_changes_with_relevant_facts`.
- [ ] Run `uv run pytest tests/test_risk.py tests/test_assessments.py -q`; expected RED for missing evaluator/route.
- [ ] Use last 30 days settled history and a stable version string. Amount 8,000,000 with five samples/median 300,000 is ANOMALOUS/WARN with recipient NONE. 20,000 to HOLD is HOLD regardless of normal/sparse behavior. Preserve reason code/restriction ID and exact five-minute TTL.
- [ ] GREEN: no model invocation, no balance change, expired restrictions ignored, and all response fields conform to RiskAssessment.
- [ ] Commit `feat(backend): implement independent risk assessments`.

### Task 7: Atomic confirmation, cancellation, reservations and expiry

**Files:** create `transfers/locking.py`, `transfers/expiry.py`, `tests/test_transfers.py`, `tests/test_holds.py`, `tests/test_money_concurrency.py`; extend transfer service, queries and audit helper.

**Interfaces:** `lock_recipient_policy(session: Session, sandbox_id: UUID, recipient_id: UUID) -> None`; `reconcile_account_expiry(session: Session, account_id: UUID, now: datetime) -> int`; `confirm_transfer(session: Session, principal: Principal, transfer_id: UUID, acknowledged_assessment_id: UUID | None) -> Transfer`; `cancel_transfer(...) -> Transfer`; `expire_due_transfers(session: Session, sandbox_id: UUID | None) -> int`. Produces confirmTransfer/cancelTransfer and deadline-safe reads.

- [ ] RED: `test_normal_transfer_posts_one_debit_credit_pair`, `test_warning_requires_current_acknowledgement`, `test_allow_then_new_hold_cannot_bypass`, `test_hold_reserves_once`, `test_cancel_releases_once`, `test_expiry_reconciled_on_me_and_commands`, `test_concurrent_confirm_is_once`, `test_competing_spends_cannot_overspend`, `test_confirm_cancel_expiry_race`.
- [ ] Run `uv run pytest tests/test_transfers.py tests/test_holds.py tests/test_money_concurrency.py -q`; expected RED for missing command behavior. Use independent committed PG connections with barriers and bounded lock timeouts; no sleep-based assertion of race success.
- [ ] Apply advisory -> sorted accounts -> sorted due/current transfers lock order. Recompute current risk inside locks. HOLD takes precedence over warning acknowledgement. Preserve terminal outcomes and idempotency. Use DB time for expiry and current facts. Reconcile reservations before reading available balance; commit intended expiry/assessment before structured conflicts.
- [ ] GREEN: 20,000 normal payment changes 10,000,000 to 9,980,000; held 20,000 leaves posted 9,980,000/reserved 20,000/available 9,960,000. Cancel restores available 9,980,000. No overdraft, duplicate ledger entry or negative/stranded reservation in race tests.
- [ ] Commit `feat(backend): enforce atomic transfers and hold lifecycle`.

### Task 8: Operator hold review and controlled refund settlement

**Files:** create `operations/holds.py`, `demo/refunds.py`, `tests/test_hold_reviews.py`, `tests/test_refunds.py`; extend Ops/demo routers and transfer confirmation READY handling.

**Interfaces:** `review_hold(session: Session, principal: Principal, transfer_id: UUID, command: ReviewHold) -> Transfer`; `settle_refund(session: Session, controller: DemoPrincipal, refund_id: UUID) -> Refund`. Produces listHolds/reviewHold/settleDemoRefund.

- [ ] RED: `test_approve_is_ready_without_debit`, `test_ready_requires_customer_reconfirm`, `test_new_restriction_invalidates_clearance`, `test_ready_keeps_original_deadline`, `test_reject_releases_once`, `test_customer_forged_role_cannot_review`, `test_refund_once_while_outgoing_held`.
- [ ] Run `uv run pytest tests/test_hold_reviews.py tests/test_refunds.py -q`; expected RED for absent review/settlement.
- [ ] Bind clearance to the current exact restriction and keep reservation/deadline. Reject releases once. Refund validates approved order/customer/account consistency, locks account then refund, and credits once; only controller can trigger this synthetic fixture event.
- [ ] GREEN: APPROVE leaves posted balance unchanged, creates READY, and customer confirmation executes once. A replacement restriction re-holds without a second reservation or deadline extension. Refund retry produces one REFUND_CREDIT, including during a hold.
- [ ] Commit `feat(backend): add hold reviews and idempotent demo refunds`.

### Task 9: Private evidence and bounded AI analysis

**Files:** create evidence storage/validation/router modules, investigation provider/schemas/prompts/service modules, `tests/test_evidence.py`, `tests/test_analysis.py`, `tests/test_ai_quotas.py`; extend settings/env/dependencies only as required.

**Interfaces:** `EvidenceStore.put(key: str, content: bytes, mime: str) -> None`, `get(key: str) -> StoredEvidence`, `delete(key: str) -> None`; `EvidenceAnalyzer.analyze(input: AnalysisInput) -> ModelEvidence`; `create_analysis(session_factory: Callable[[], Session], principal: Principal, input: AnalysisInput) -> Analysis`; `get_analysis(...) -> Analysis`. Produces createAnalysis/getAnalysis/getEvidence. Injectable test adapters never become automatic runtime verdicts.

- [ ] RED: `test_fee_zero_plus_pay_fee_is_mismatch`, `test_new_purchase_has_no_refund_fee_mismatch`, `test_missing_fee_is_uncertain`, `test_timeout_keeps_official_facts`, `test_duplicate_key_does_not_call_provider_twice`, `test_changed_image_or_text_key_is_409`, `test_foreign_order_transfer_or_image_is_404`, `test_invalid_mime_decoding_and_size_rejected`, `test_quota_race_and_model_outage_do_not_block_cancel`.
- [ ] Run `uv run pytest tests/test_evidence.py tests/test_analysis.py tests/test_ai_quotas.py -q`; expected RED for absent adapters/routes.
- [ ] Validate decoded images as well as MIME; check decompression limits. Persist canonical input SHA-256 and official facts from owned records. Reserve run/quota atomically using separate consistent AI advisory namespaces, commit PENDING, release the DB transaction, then call store/provider with bounded timeouts and finalize. Idempotency key lock precedes shared quota lock; replays consume no quota/call. Do not infer successful AI from keyword-only rules.
- [ ] Implement S3 adapter with explicit Neon endpoint, region, bucket and scoped credentials plus Python path-style/SigV4 configuration. Keep private object keys unguessable/scoped; compensate failed DB/upload steps with retryable deletion. Pin dependencies such as boto3, image decoder, multipart and the selected provider SDK only when used.
- [ ] GREEN: exact output schema, correct known/unknown facts, private evidence access for owner or same-sandbox operator only, no tool execution from image text, and one logical run under duplicate concurrent submissions. Honor the total 20-second inference deadline, including validation/repair attempts.
- [ ] Run a separately authorized live storage round trip and one model analysis using synthetic evidence once credentials/provider selection exist. Record provider/model/latency; never describe injected-adapter tests as proof of a live provider.
- [ ] Commit `feat(backend): add private evidence and bounded AI analysis`.

### Task 10: Customer reports and operator case review

**Files:** create `operations/reports.py`, `tests/test_reports.py`, `tests/test_report_reviews.py`; extend customer/Ops routers.

**Interfaces:** `create_report(session: Session, principal: Principal, command: CreateReport) -> Report`; `get_report_detail(...) -> ReportDetail`; `review_report(..., command: ReviewReport) -> Report`. Produces createReport/listOwnReports/listOpsReports/getOpsReport/reviewReport. Trace projection initially delegates to Task 12's shared interface; complete the detail acceptance there rather than fabricating matches.

- [ ] RED: `test_report_replay_and_payload_conflict`, `test_report_ownership_and_recipient_consistency`, `test_canceled_transfer_remains_reportable`, `test_new_report_does_not_restrict_recipient`, `test_review_transition_matrix_and_terminal_conflict`, `test_customer_cannot_list_ops_cases`.
- [ ] Run `uv run pytest tests/test_reports.py tests/test_report_reviews.py -q`; expected RED for absent report behavior.
- [ ] Validate linked analysis/draft ownership and recipient agreement, including disagreement between linked analysis transfer and separately supplied transfer. Compare canonical fields on replay. RECEIVED can become IN_REVIEW/RESOLVED/DISMISSED; IN_REVIEW can resolve/dismiss; repeated same terminal decision is idempotent, conflicting terminal decisions are 409. Record reason and operator atomically.
- [ ] GREEN: customer sees only own reports, Ops sees same sandbox, forged role fails, report creation changes no restriction or money. No missing analysis is invented in details.
- [ ] Commit `feat(backend): implement reports and reviewed case lifecycle`.

### Task 11: Reviewed recipient restrictions

**Files:** create `operations/restrictions.py`, `tests/test_restrictions.py`; extend Ops router and concurrent transfer tests.

**Interfaces:** `create_restriction(session: Session, principal: Principal, command: CreateRestriction) -> Restriction`; `revoke_restriction(..., reason: str) -> Restriction`; consumes Task 7 recipient advisory lock. Produces listRestrictions/createRestriction/revokeRestriction.

- [ ] RED: `test_only_resolved_same_recipient_reports_support_restriction`, `test_active_duplicate_conflict`, `test_expired_active_row_allows_replacement`, `test_revocation_is_audited_idempotent_and_retains_evidence`, `test_future_expiry_required`, `test_restriction_create_vs_confirm_is_serialized`.
- [ ] Run `uv run pytest tests/test_restrictions.py tests/test_money_concurrency.py -q`; expected RED for missing restriction commands.
- [ ] Require nonempty distinct same-recipient RESOLVED evidence IDs, operator role and future aware expiry. Serialize with confirmations using the exact same recipient lock. New/revoked decisions preserve immutable history; no report-count auto-block rule.
- [ ] GREEN: parallel creates produce one active row; expiry/revocation changes subsequent assessments, and approval of one held transfer does not revoke the global restriction.
- [ ] Commit `feat(backend): add reviewed recipient restriction decisions`.

### Task 12: Exact-reference trace and bounded report investigation

**Files:** create `investigation/trace.py`, `grouping.py`, `tests/test_trace.py`, `tests/test_grouping.py`; finalize Ops report detail/trace/investigation routes.

**Interfaces:** `trace_report(session: Session, principal: Principal, report_id: UUID) -> Trace`; `ReportGrouper.group(input: GroupInput) -> GroupEvidence`; `investigate_report(session_factory: Callable[[], Session], principal: Principal, report_id: UUID, client_request_id: UUID) -> Investigation`. Produces getOpsReport/traceReport/investigateReport.

- [ ] RED: `test_a017_matches_batch_and_real_read`, `test_missing_and_unknown_reference_results`, `test_forwarded_reference_keeps_limitations`, `test_no_cross_sandbox_trace`, `test_grouping_caps_20_and_replays_snapshot`, `test_invalid_report_ids_and_quotes_are_dropped`.
- [ ] Run `uv run pytest tests/test_trace.py tests/test_grouping.py -q`; expected RED for missing trace/grouping.
- [ ] Match references exactly against immutable issued records; never create issuance from extracted strings or use substring/partial matches for attribution. Join actual batch/partner/access records. Validate related-report IDs and source quotations against the immutable run input snapshot; drop unsupported links with citation_warnings. Use the same bounded run lifecycle/quota discipline as analysis.
- [ ] GREEN: A-017 -> BATCH_A -> A READ -> three distinct candidate customers; absent code returns NO_REFERENCE, unknown code NO_MATCH. All cases preserve source uncertainty. New reports do not change a replayed grouping snapshot, and a grouping response cannot execute an Ops action.
- [ ] Commit `feat(backend): implement exact tracing and validated report investigation`.

### Task 13: Previewed batch notices and audit projection

**Files:** create `operations/notices.py`, `operations/audit.py`, `tests/test_notices.py`, `tests/test_audit.py`; extend routers and all state-changing audit call sites.

**Interfaces:** `append_audit(session: Session, principal: Principal | DemoPrincipal | SystemPrincipal, event_type: str, target_type: str, target_id: UUID | None, details: dict) -> None`; `preview_notices(..., report_id: UUID, batch_id: UUID) -> NoticePreview`; `publish_notices(..., command: PublishNotice) -> PublishResult`. Produces previewNotice/publishNotices/listNotifications/listAudit.

- [ ] RED: `test_preview_matches_linh_an_binh_not_mai`, `test_publish_requires_resolved_report_and_traced_batch`, `test_publication_retry_and_parallel_retry_create_no_duplicates`, `test_changed_copy_cannot_silently_overwrite_publication`, `test_customer_notices_are_private`, `test_audit_records_actor_reason_target_without_secrets`.
- [ ] Run `uv run pytest tests/test_notices.py tests/test_audit.py -q`; expected RED for absent notice/audit endpoints.
- [ ] Derive audience from batch references/orders; require the selected batch appears in the source report trace. Preview can support investigation before resolution; publication must require RESOLVED. Serialize publication by sandbox/report/batch, retain original copy on exact retry and return 409 on changed title/body after publication. Use uniqueness as final duplicate guard. Include actor/reason/policy/evidence metadata where relevant in audit JSON.
- [ ] GREEN: first publish created_count=3, retry created_count=0, recipient_count=3; Mai receives none. Safe plain-text precautionary copy never names the partner as a proven offender. Audit reads stay Ops-only and same-sandbox.
- [ ] Commit `feat(backend): add scoped batch notices and audit history`.

### Task 14: Maintenance and recovery for expiring state

**Files:** create `app/maintenance.py`, `tests/test_maintenance.py`; extend expiry, AI reconciliation and storage cleanup helpers/settings.

**Interfaces:** `reconcile_stale_runs(session: Session, cutoff: datetime) -> int`; `purge_expired_sandboxes(...) -> CleanupResult`; `python -m app.maintenance` exits nonzero on incomplete failures and emits redacted counts. No public unauthenticated cleanup endpoint.

- [ ] RED: `test_overlapping_sweeps_release_once`, `test_abandoned_pending_run_becomes_timed_out`, `test_grace_period_preserves_live_sandbox`, `test_failed_object_delete_preserves_retryable_sandbox`, `test_second_cleanup_is_safe`.
- [ ] Run `uv run pytest tests/test_maintenance.py tests/test_money_concurrency.py -q`; expected RED for missing maintenance command/recovery.
- [ ] Reuse account-first expiry routines; mark abandoned runs only after an explicit stale cutoff beyond their allowed runtime and perform conditional updates so late results cannot overwrite a timed-out run. Sandbox cleanup begins only after expiry plus 24-hour grace. Delete scoped private evidence before cascading DB removal; keep a durable retryable anchor on failures. Migration/cleanup owner has separate credentials from normal append-only runtime grants.
- [ ] GREEN: repeat/overlapping jobs converge; model or storage outage cannot prevent cancellation or transfer expiry. Prepare Cloud Run Job/Scheduler invocation in docs, but do not deploy it in this pass.
- [ ] Commit `feat(backend): add idempotent maintenance and recovery`.

### Task 15: Whole-contract acceptance and FE handoff

**Files:** create `tests/test_contract.py`, `test_authorization.py`, `test_primary_journey.py`, `test_false_positive_journey.py`; update Backend README/env, `docs/guardian/validation.md`, architecture/storage/cloud notes and API examples only where implementation proves a required change.

**Interfaces:** all 32 operations in the coverage matrix below; no stub route returning a fabricated success counts as implemented.

- [ ] RED: `test_all_32_contract_operations_are_implemented`, response/request enum/required-nullable/extra-field validation, `test_every_protected_operation_denies_missing_or_wrong_identity`, `test_main_refund_exact_balances_and_audience`, `test_false_positive_requires_reconfirmation`, `test_independent_sandbox_same_journey`.
- [ ] Run `uv run pytest tests/test_contract.py tests/test_authorization.py tests/test_primary_journey.py tests/test_false_positive_journey.py -q`; expected RED until all owned routes are complete. Resolve OpenAPI 3.1 schemas with a validator rather than shallow path counting alone.
- [ ] Test exact primary journey from scenarios.md: normal 20k -> held 20k -> live-shape analysis with fake adapter -> cancel -> report -> Ops review/trace -> publish -> An notice/Mai none -> approved refund. Final posted balance: 10,480,000. Prove failed and timed-out AI variants independently.
- [ ] GREEN: run `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`, `uv lock --check`, `uv run alembic heads`, and Docker image smoke when engine is available. Mandatory PG tests run without skips for acceptance. Test Windows/Unix launcher startup and DB connectivity separately from liveness.
- [ ] Independently review the entire branch, fix important defects with failing regression tests, then repeat the affected tests/full suite. Record exact implemented operation count, migration head, provider/storage configuration still missing and live-smoke evidence if available.
- [ ] Publish the local handoff note for FE: commit IDs, env names, auth/bootstrap sequence, DTO adapters required and 409 handling. Frontend typecheck/build and browser end-to-end proof require the FE proxy/service integration task; backend tests alone do not satisfy that gate.
- [ ] Commit `test(backend): verify Guardian contract and end-to-end journeys`.

## API operation coverage

All routes use `/api/v1` as server prefix. Customer mutations use actor CSRF; controller mutations use controller CSRF; all mutations verify Origin. Health is public and bootstrap has no prior session. Read operations still authenticate the indicated identity.

| Operation | Method and path | Identity | Task | Success response |
| --- | --- | --- | --- | --- |
| `getHealth` | `GET /health` | Public | existing | 200 Health |
| `createDemo` | `POST /demo/sessions` | Public + Origin | 3 | 201 Bootstrap |
| `selectActor` | `POST /demo/actors/select` | Controller | 3 | 200 Me |
| `settleDemoRefund` | `POST /demo/refunds/{id}/settle` | Controller | 8 | 200 Refund |
| `getMe` | `GET /me` | Actor | 3-4, 7 | 200 Me |
| `listRecipients` | `GET /recipients` | Customer | 4 | 200 RecipientList |
| `listOrders` | `GET /orders` | Customer | 4 | 200 OrderList |
| `listTransfers` | `GET /transfers` | Customer | 5, 7 | 200 TransferList |
| `createTransfer` | `POST /transfers` | Customer | 5 | 201/200 Transfer |
| `getTransfer` | `GET /transfers/{id}` | Customer | 5, 7 | 200 Transfer |
| `assessTransfer` | `POST /transfers/{id}/assess` | Customer | 6 | 200 RiskAssessment |
| `confirmTransfer` | `POST /transfers/{id}/confirm` | Customer | 7-8 | 200 Transfer |
| `cancelTransfer` | `POST /transfers/{id}/cancel` | Customer | 7 | 200 Transfer |
| `createAnalysis` | `POST /analyses` | Customer | 9 | 201/200 Analysis |
| `getAnalysis` | `GET /analyses/{id}` | Owner or same-sandbox Ops | 9 | 200 Analysis |
| `getEvidence` | `GET /analyses/{id}/evidence` | Owner or same-sandbox Ops | 9 | 200 Private image bytes |
| `createReport` | `POST /reports` | Customer | 10 | 201/200 Report |
| `listOwnReports` | `GET /reports` | Customer | 10 | 200 ReportList |
| `listNotifications` | `GET /notifications` | Customer | 13 | 200 NoticeList |
| `listOpsReports` | `GET /ops/reports` | Operator | 10 | 200 ReportList |
| `getOpsReport` | `GET /ops/reports/{id}` | Operator | 10, 12 | 200 ReportDetail |
| `reviewReport` | `PATCH /ops/reports/{id}` | Operator | 10 | 200 Report |
| `investigateReport` | `POST /ops/reports/{id}/investigate` | Operator | 12 | 200 Investigation |
| `traceReport` | `GET /ops/reports/{id}/trace` | Operator | 12 | 200 Trace |
| `listHolds` | `GET /ops/holds` | Operator | 8 | 200 TransferList |
| `reviewHold` | `POST /ops/transfers/{id}/review` | Operator | 8 | 200 Transfer |
| `listRestrictions` | `GET /ops/recipient-restrictions` | Operator | 11 | 200 RestrictionList |
| `createRestriction` | `POST /ops/recipient-restrictions` | Operator | 11 | 201 Restriction |
| `revokeRestriction` | `POST /ops/recipient-restrictions/{id}/revoke` | Operator | 11 | 200 Restriction |
| `previewNotice` | `GET /ops/reports/{id}/notice-preview` | Operator | 13 | 200 NoticePreview |
| `publishNotices` | `POST /ops/reports/{id}/notices` | Operator | 13 | 200 PublishResult |
| `listAudit` | `GET /ops/audit-events` | Operator | 13 | 200 AuditEventList |

## Acceptance examples that must remain true

```python
# Primary monetary story, from separate API requests and persisted DB reads:
assert opening_posted == 10_000_000
assert after_normal_posted == 9_980_000
assert (held_posted, held_reserved, held_available) == (9_980_000, 20_000, 9_960_000)
assert after_cancel_available == 9_980_000
assert after_refund_posted == 10_480_000
assert after_refund_retry_posted == 10_480_000
assert notice_customer_names == {"Linh", "An", "Binh"}
assert second_publish_created_count == 0
```

These assertions do not authorize hard-coded runtime amounts or identities. Each sandbox discovers real generated IDs and reads actual ledger/decision state. Fixture names are symbolic construction/test labels only.

## Requirement coverage self-review

| Product requirements | Tasks |
| --- | --- |
| G01 isolation/identity | 1, 3, 4, 15 |
| G02 draft ownership/input | 2, 5 |
| G03-G05 risk independence/history/restrictions | 6, 11 |
| G06-G07 current confirm/once-only money | 5, 7, 15 |
| G08-G09 hold/cancel/clearance/reconfirm | 7, 8, 14, 15 |
| G10-G11 AI sources/facts/statuses | 9, 14 |
| G12 report lifecycle | 10 |
| G13 validated related-report evidence | 12 |
| G14 exact trace and uncertainty | 12 |
| G15 reviewed recipient decisions | 11 |
| G16 reviewed batch publication | 13 |
| G17 refund fixture | 8, 15 |
| G18 secrets/evidence access/untrusted prompt | 3, 9, 12, 15 |
| Quality: money races, deadlines, schemas | 1, 2, 5-8, 11, 14-15 |
| Live-provider/storage and hosted experience | 9 live smoke; FE/cloud integration remains a separately reported release gate |

## Execution boundaries and reporting

- Keep an execution ledger identifying this plan and task BASE/commit/test results. Resume from committed task evidence after compaction instead of repeating completed migrations or tests blindly.
- Before the first code task, settle plan review and use an isolated feature branch/current checkout per workspace policy. The branch above is prepared; no business code was changed while preparing this plan.
- A task is complete only after its behavioral tests pass and consumers can use its produced interface. A Swagger path, importable module, placeholder adapter, or skipped live dependency is not evidence of completed integration.
- Distinguish automated proof with fake adapters, real PostgreSQL proof, real object-store proof, real provider proof and hosted browser proof in every delivery report.
- Update any intentional behavior change in product requirements, SQL/API specification, tests and FE notes together. Do not silently implement FE mock behavior as a new product requirement.
