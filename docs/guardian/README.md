# Guardian delivery pack

Guardian protects a customer before a transfer and helps an operator investigate the evidence behind recipient warnings. Refund impersonation is the primary contest scenario. This pack specifies the application to build in Nemo.

Status — approved direction updated on 25 November 2026; specifications, not completed product APIs. Current backend implements health and technical scaffolding; frontend business screens still use mocks. This revision adds bounded AI tools/source-linked dossiers and retains exact tracing. No implementation, provider billing or cloud provisioning is performed by the documentation update.

## Reading order

| Document | Purpose |
| --- | --- |
| [Team brief](team-brief.md) | Shareable product scope, AI role, demo, assignments and changes in this revision |
| [Specification changes](CHANGELOG.md) | Revision history and what changed in the shared contract |
| [Product requirements](product-requirements.md) | User journeys, mandatory scope, state transitions, acceptance criteria |
| [Bounded AI investigation](ai-investigation.md) | Read-only tool allowlists, trust boundaries, run limits, dossier, UI and provider decisions |
| [Architecture](architecture.md) | Existing repository, module boundaries, trust boundaries, deployment |
| [Data model](data-model.md) | ERD, ownership, transaction rules, extension rules |
| [Database specification](database-specification.md) | All 19 tables and 161 columns, with types, nullability, defaults, keys and explanations |
| [PostgreSQL schema](schema.sql) | Executable baseline schema, keys, indexes and constraints |
| [OpenAPI contract](openapi.yaml) | Frontend/backend request and response agreement |
| [API examples](api-examples.md) | Concrete request sequence, acknowledgement and failure handling |
| [Scenarios and demo](scenarios.md) | Fixture blueprint, three-minute video, judge walkthrough |
| [AI evaluation](evaluation.md) | Model output, baselines, held-out cases and failure handling |
| [Delivery plan](../superpowers/plans/2026-11-23-guardian.md) | Tasks, owners, exact files, interfaces, schedule and checks |
| [Backend API implementation plan](../superpowers/plans/2026-11-24-guardian-backend-api.md) | Detailed backend tasks, all 32 operations, transaction rules, tests and FE handoff gates |
| [Frontend integration notes](frontend-integration-notes.md) | Current mock/contract differences, DTO mapping, auth and integration sequence |
| [Cloud deployment](cloud-deployment.md) | Provisioning, IAM, secrets, images, migrations, jobs, acceptance, costs and rollback |
| [Agent prompts](agent-prompts.md) | Small implementation assignments with acceptance gates |
| [Decisions and expansion](decisions-and-expansion.md) | Assumptions, open dependencies and post-contest expansion |
| [Validation record](validation.md) | Checks already performed and implementation checks still pending |

## Implementation baseline

- Repository `Nemo-Organization/Nemo`, branch `dev`, inspected commit `2202141e89100516c38744608507284137874fd6` on 23 November 2026.
- Existing frontend — Next.js App Router, React, TypeScript, Tailwind, next-intl, shared shadcn components and TanStack tables.
- Proposed backend — Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL 16+.
- Proposed hosting — two services, Next.js and FastAPI, with one public browser origin. PostgreSQL is hosted on Neon by default, with Supabase as an alternative. Google Cloud Run is the first application hosting target.
- Contest theme — Anti-Fraud. AI interprets evidence and selects bounded read-only verification steps, returning validated source-linked dossiers. Exact system tracing supports investigation. Server code authenticates users, calculates money and enforces human-approved decisions.
- Customer and operator are the two application roles. The demo controller only manages synthetic scenarios.
- All payment balances, orders, partners and financial outcomes in the contest build are synthetic. Release requirement: model calls, database writes, permission checks and risk decisions must execute online when implemented; current skeleton/mock screens do not yet satisfy this gate.

## Decisions made for this pack

These choices make the design concrete and can be revised before implementation.

1. A verified recipient restriction can be `WARN` or `HOLD`. Only an authorized operator creates it.
2. Behavioral anomalies produce warnings. A new report alone creates a review item.
3. A held transfer reserves funds for 15 minutes by default. Cancellation, rejection or expiry releases the reservation. Operator clearance requires a fresh customer confirmation before execution.
4. Uploads accept PNG/JPEG/WebP up to 5 MiB. A vision-capable provider handles image transcription and interpretation through one adapter.
5. A draft does not reserve funds. The first confirmation attempt re-evaluates risk and either executes or enters a hold atomically.
6. System tracing matches issued reference codes and corroborating access records. Partner attribution remains a hypothesis.
7. Core scope includes operator-approved notifications to customers in an evidenced batch. Partner suspension, policy replay and account-wide receive-only controls are expansion work.

## Contract authority

Product requirements define behavior. `openapi.yaml` defines the external payloads. `schema.sql` defines storage constraints. The data-model document defines transactions that SQL constraints alone cannot enforce. Update all affected documents in the same change when a contract changes. FastAPI-generated OpenAPI must match the agreed paths, fields and enums. Framework metadata and generated schema names may differ.

`Frontend/` and `Backend/` keep their existing casing. Local documents under the separate `refund-shield` folder describe earlier product variants. Reuse a behavior only after comparing it to this pack.

## Submission

Target submission is 3 December 2026 at 23:59:59 Asia/Bangkok. Deliver a live URL with isolated demo sessions, a one-page A4 PDF guide, a source ZIP with a reproducible README and asset disclosures, a description PDF of at most ten slides, and an MP4 of at most three minutes. Prepare and verify the actual deployed version before recording.
