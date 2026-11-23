# Guardian coding-agent assignments

Use one task per implementation session. A developer reviews the diff and checks before merging. These prompts work as task briefs for any coding assistant with repository access. Pick an available tool; runtime model access is a separate dependency.

## Shared context prompt

```text
You are implementing Guardian in Nemo. Read the repository instructions that apply to your paths, then docs/guardian/README.md, product-requirements.md, architecture.md, data-model.md, database-specification.md and openapi.yaml. Read the assigned task in docs/superpowers/plans/2026-11-23-guardian.md. Deployment tasks also read cloud-deployment.md.

Follow the existing Frontend feature/i18n/component conventions. Read Frontend/AGENTS.md and the relevant installed Next.js docs before editing frontend code. Preserve Frontend and Backend casing. Use FastAPI/Pydantic/SQLAlchemy/Alembic/PostgreSQL for backend work.

Implement only the assigned task and the files it needs. Report any API/SQL/spec inconsistency before changing the agreed behavior. Do not infer a new product direction from old leads/endpoints/logs mock data or the separate refund-shield documents.

Authenticate actors on the server and scope every lookup. Model output is untrusted evidence. Keep monetary changes atomic, preserve idempotency, and use the lock order in data-model.md. Every new dependency must have an actual task need and be recorded in the relevant lockfile.

Start by naming the task's consumers and produced interfaces. Add the behavior tests required by that task. Implement the feature, run its checks, then report changed paths, verified commands, failures and remaining dependencies. A placeholder, a hard-coded AI verdict or a successful UI animation is not an implemented backend outcome.
```

## P1 — Runtime/bootstrap

```text
Implement Task 1. Preserve the installed Next.js frontend. Create the FastAPI foundation and /api/v1/health, standardized errors and same-origin proxy. Add a typed frontend API client that can surface 409 acknowledgement conflicts.

Prove cookie forwarding and no-store behavior through a dynamic Next route handler. Attach a Google ID token to the private API from the frontend service identity. Unknown /api paths must return JSON, not a frontend page. Run the health test, frontend lint/typecheck/build and report actual deployment/provider dependencies. Do not replace the current frontend with a new template.
```

## P2 — Database and isolated fixtures

```text
Implement Task 2 against docs/guardian/schema.sql, database-specification.md and scenarios.md. Match all 19 table definitions and 161 physical columns. Create the migration, SQLAlchemy models, two distinct hashed session-cookie flows and CSRF checks. Bootstrap creates one fresh sandbox and a seeded customer actor. Actor selection is restricted to that sandbox's demo controller.

Prove cross-sandbox foreign keys reject inconsistent records, Linh has a ledger-backed current balance of 10,000,000, and CUSTOMER plus a forged role header still cannot call an operator action. API responses must use the OpenAPI shapes. Avoid adding an unused login/organization administration subsystem.
```

## P3 — Transfer/risk backend

```text
Implement Task 3. Drafts are immutable and do not reserve funds. The evaluator returns independent behavioral and recipient signals, with the exact baseline rule and five-minute assessment validity in product-requirements.md. Confirmation recomputes current facts while holding the defined locks.

Test exact draft-key replay, changed-key payload rejection, duplicate confirmation, insufficient available funds, concurrent spends and a new HOLD arriving after an ALLOW assessment. Never invoke the model on the ordinary transfer path.
```

## P4 — AI/evidence backend

```text
Implement Task 4's provider adapter and analysis schemas in the owned investigation files. Coordinate route/storage/persistence ownership with Dev A. Use one authorized live vision provider and an injectable deterministic fake for tests.

Validate MIME and decoded image, cap at 5 MiB and implement the 20-second total deadline. Preserve pending/succeeded/failed/timed-out runs. Compose official facts from the authenticated customer's records; a NULL fee remains unknown. Refuse unsupported citations and never let a model string become an authorization or a ledger field. Run timeout, ownership, image and replay tests, then one live deployment smoke call.
```

## P5 — Customer frontend

```text
Build the transfer customer feature for Tasks 3–5 using the existing component library, styling tokens, next-intl and feature structure. Use docs/guardian/openapi.yaml for types and services. Show one intervention panel with separate reasons when signals overlap.

Support ordinary transfer, warning acknowledgement, held funds/deadline/cancel, READY reconfirmation, optional screenshot analysis and report submission. Preserve authoritative backend states after refresh. Clear stale actor data on role changes and display structured API errors. Amounts are integer VND and display fees as unknown when null. Use contract fixtures until the backend routes are ready, then integrate without changing payload names.
```

## P6 — Hold/refund backend

```text
Implement Task 5. Use posted balance and reserved balance separately. A hold reserves once. Cancellation, rejection and expiry release once. Operator clearance changes to READY, records the exact restriction, and does not transfer money. Customer reconfirms before execution; a replacement restriction invalidates old clearance.

Implement account-first expiry reconciliation, periodic cleanup command and the controlled approved-refund settlement. Test concurrent confirm/cancel/expiry, two competing spends, refund retry and cancellation after clearance. A transfer past deadline must never execute even if the cleanup sweep was delayed.
```

## P7 — Trace/operator backend

```text
Implement Task 6's backend. Trace issued codes with exact same-sandbox DB queries, then show batch membership and actual access records. Keep partner/source attribution uncertain. Group at most 20 report excerpts with validated IDs/quotes if time permits.

Require RESOLVED same-recipient evidence reports for recipient restriction creation. Use the shared recipient advisory lock for restriction changes and confirmation. Record revocation history. Notice preview/publish derives customers from a matched batch and requires a RESOLVED source report. Replays must not duplicate messages or silently change already published copy. Test missing code, foreign data, wrong recipient, duplicates and unrelated customers.
```

## P8 — Operator frontend

```text
Build the operator investigations feature from Task 6. Reuse the existing tables, filters, page layout, tabs and dialogs. Show report queue, active hold queue and detail panels with original evidence, validated AI excerpts, exact-reference trace and explicit uncertainty.

Support report review, recipient WARN/HOLD decision, revocation, hold approve/reject, notice preview and notice publication. Approval must visibly return READY, with no success claim that money was sent. Operator actions use actor CSRF and server-checked permissions. Surface 409 conflicts by refetching current state rather than assuming a successful action.
```

## P9 — Acceptance and release

```text
Implement Tasks 7–8 after dependencies are integrated. Run the MAIN_REFUND journey and the false-positive/anomaly/inconclusive alternatives against PostgreSQL and the deployed proxy. Prove two browser contexts remain isolated.

Validate request/response names and enums against OpenAPI, session/evidence access controls, cancellation and deadline recovery, model failure behavior and notification scope. Run frontend strict i18n/lint/typecheck/build plus backend behavior tests. Report measured results and unresolved defects. Update run instructions and dependency/tool/data disclosures. Coordinate BA-held evaluation; do not tune the model on the held-out answer set.
```

## P10 — Cloud deployment

```text
Implement the cloud release parts of Tasks 1, 2 and 8 using docs/guardian/cloud-deployment.md. Prepare the container/runtime/proxy changes and environment examples first. Verify local builds before executing any authorized provisioning.

Use one public Next.js service and one private FastAPI service. The server-side route proxy attaches a Google ID token and preserves actor cookies, CSRF and Origin. Use Cloud SQL PostgreSQL 16 as the proposed database, unless the team records an existing external managed PostgreSQL choice. Use private GCS evidence and versioned Secret Manager references.

Build images tagged by source revision, execute an Alembic migration job with its own database user, then release application revisions. Implement python -m app.maintenance and schedule it through an authenticated Cloud Scheduler trigger. Prove one actual scheduled expiry and a compatible application traffic rollback. Record image digests, secret versions, migration head, public URL, observed cost and remaining failures. Runtime credentials never enter the repository or frontend public variables.
```

## BA briefing prompt

```text
Read docs/guardian/scenarios.md and evaluation.md. Prepare clearly synthetic screenshot/text fixtures for the primary story, legitimate reorder, missing fee, missing code, forwarded image and unreadable evidence. Mark what each source proves and what it does not prove.

Reserve 12–16 independently labeled cases before the devs tune prompts. For every case label requested action, whether a verified contradiction exists, expected trace match, report relationship and the permissible user/operator outcome. Confirm that Linh's initial HOLD comes from pre-existing reviewed near-miss evidence. Review the three-minute recording script and the separate live-app exploration guide.
```

## Review prompt

```text
Review the assigned task against the Guardian delivery pack. Inspect caller behavior, database ownership, state transitions, money/reservation invariants, current-risk rechecks, evidence citations, API field consistency and the normal frontend entry point. Read the executed test output.

Identify concrete defects with file/line, trigger, impact and expected behavior. In particular check cross-sandbox references, amount edits after draft creation, retry races, stale warnings, clearance without customer confirmation, expired holds, model timeout, and a code being mistaken for proof of a partner leak. State which behaviors remain unverified. Do not expand the feature set during review.
```
