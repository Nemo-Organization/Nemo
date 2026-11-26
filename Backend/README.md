# Guardian backend

FastAPI foundation for Nemo's Guardian anti-fraud application. Python 3.12, Pydantic settings, SQLAlchemy/psycopg, Alembic and a locked uv environment.

## Current implementation

- `GET /api/v1/health` returns `{"status":"ok"}` without contacting PostgreSQL or an AI provider.
- Responses include a server-generated `X-Request-ID` and `Cache-Control: no-store`.
- HTTP, validation and unexpected errors use the shared JSON error envelope with safe public messages.
- `create_app(settings)` supports isolated test instances and lifespan-managed database engines.
- Request-scoped sessions close and roll back uncommitted work. Top-level services own commits; helpers only flush.
- Schema (backend Task 1): SQLAlchemy models for the 19 tables in `app/models.py` and Alembic revision `0001_guardian`, a frozen copy of `docs/guardian/schema.sql`.
- Contract DTOs (Task 2): `app/api/schemas.py` mirrors every JSON schema in OpenAPI v1.3; a test fails when they drift apart.
- Demo sessions (Task 3): `POST /api/v1/demo/sessions` (createDemo), `POST /api/v1/demo/actors/select` (selectActor) and `GET /api/v1/me` (getMe). See [Demo sessions](#demo-sessions).
- Customer reference lists (Task 4): `GET /api/v1/recipients` (listRecipients) and `GET /api/v1/orders` (listOrders), paginated with `limit` (1-100, default 20) and `offset` (>= 0).
- Transfers and risk (Tasks 5-7): createTransfer, getTransfer, listTransfers, assessTransfer, confirmTransfer and cancelTransfer. See [Transfers and holds](#transfers-and-holds).
- Hold review and refunds (Task 8): listHolds and reviewHold for operators, and settleDemoRefund for the demo controller.

These are 15 of the 32 contract operations, including health. Not implemented yet: evidence upload and AI analysis/investigation, customer and operator reports, exact trace, recipient restrictions, notices and the audit list (backend Tasks 9-13). Product requirements, the 19-table schema and full API contract live in [the delivery pack](../docs/guardian/README.md).

## Start on Windows, macOS or Linux

From `Backend/`, choose the launcher for your operating system. The Python environment must already be installed using the one-time setup below.

| Terminal | Daily start command |
| --- | --- |
| Windows CMD | `run.bat` |
| Windows PowerShell | `.\run.bat` or `.\run.ps1` |
| macOS / Linux terminal | `bash run.sh` |

For this Windows checkout, CMD can run the following.

```bat
cd /d "D:\Momo Tech Day\Nemo\Backend"
run.bat
```

PowerShell can run the following.

```powershell
cd "D:\Momo Tech Day\Nemo\Backend"
.\run.bat
```

On macOS/Linux, adjust the checkout location.

```bash
cd /path/to/Nemo/Backend
bash run.sh
```

Open `http://localhost:8080/docs`, expand GET `/api/v1/health`, choose **Try it out** and **Execute**. Expected response is `{"status":"ok"}`. Keep the terminal open and press Ctrl+C to stop. Stop an earlier backend on port 8080 before starting another instance.

### One-time setup for a fresh checkout

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) using the official instructions for the operating system, then open a new terminal. In `Backend/`, run this command on Windows, macOS or Linux.

```text
uv sync --locked
```

uv installs the project's locked dependencies into `.venv`, using Python 3.12 or its managed Python installation. Each teammate runs this on their own machine. Do not copy a Windows `.venv` to a Mac or the reverse. After checkout or dependency changes, run `uv sync --locked` again.

The launchers create `.env` from `.env.example` only when missing and preserve existing configuration. Set the private database URL there, then run the launcher again. The `.bat` option also works from PowerShell without changing its script execution policy.

## What the commands mean

| Name | Purpose |
| --- | --- |
| FastAPI | Framework defining the backend APIs |
| Uvicorn | HTTP server running the FastAPI application; installed with the project |
| uv | Dependency and Python-environment manager, similar to npm; `uv sync --locked` installs the agreed versions |
| `.venv` | Isolated Python interpreter and project libraries |
| `run.bat` / `run.ps1` / `run.sh` | Platform launchers for the same backend |
| Docker | Container packaging used for deployment and optional local DB testing |

For optional automatic reload while editing, use `uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8080`. The one-command launcher is sufficient for ordinary startup.

Implemented operations are at `/openapi.json`. The full planned contract is `../docs/guardian/openapi.yaml`.

## Where PostgreSQL runs

| Environment | Database location | Backend configuration |
| --- | --- | --- |
| Everyday development | Dedicated Neon development branch/database | Private `.env` contains that branch's TLS connection URL |
| Shared online demo | Separate Neon demo branch/database | Cloud Run injects the demo URL from Secret Manager |
| Backend integration tests | Dedicated disposable PostgreSQL database | `TEST_DATABASE_URL`, isolated from development and the live demo |
| Alternative provider | Supabase PostgreSQL | Use a direct connection or the session pooler and retain TLS |

Neon is the proposed default because this application already implements its own backend and primarily needs PostgreSQL. Supabase is a supported alternative. Verify current quotas in [Neon pricing](https://neon.com/pricing) or [Supabase pricing](https://supabase.com/pricing) before exposing the judging URL. A free plan has resource and availability limits.

### Connect Neon or Supabase

1. Create a project in the selected provider. Choose a region close to the Cloud Run service where available.
2. Keep separate development and demo databases/branches. Obtain the development connection string through the provider console.
3. For Neon, start with a direct connection. For Supabase, use direct PostgreSQL when reachable, otherwise the session pooler. Verify IPv4/IPv6 reachability and connection limits.
4. Open the private `.env` created by the launcher. Change `postgresql://` in the copied string to `postgresql+psycopg://` and retain the actual host, port, database and TLS query parameters.

```dotenv
DATABASE_URL=postgresql+psycopg://USER:URL_ENCODED_PASSWORD@HOST:5432/DATABASE?sslmode=require
```

URI-encode special characters in the password. Keep credentials in `.env` or Secret Manager. The backend uses SQLAlchemy/psycopg directly. Supabase client API keys are not database passwords.

5. Restart with the launcher for your OS after changing `.env`. Liveness works before a database is configured. The database-query example below uses PowerShell; other shells can run the same Python statements in an interpreter started with `uv run python`.

The migration owner and runtime application role should be separate for the hosted demo. The direct migration URL is supplied to the migration job. Direct/session connections are the initial baseline. A transaction pooler needs a deliberate compatibility check before use because advisory-lock lifetime, prepared statements and migration behavior depend on the mode. Guardian uses transaction-scoped advisory locks in its planned money services.

For Supabase, ensure application tables are not exposed through an unprotected Data API. Configure its exposed schemas/RLS appropriately or disable the unused Data API. The browser accesses the FastAPI backend; it does not receive DB credentials.

This repository does not provision a provider project. After setting `DATABASE_URL`, create the 19 tables with `uv run alembic upgrade head`.

### Start a local database

Install/start Docker Desktop. This example creates an empty PostgreSQL database with a persistent local volume. The credentials shown are development-only. Port 5433 on the host maps to 5432 inside PostgreSQL, leaving a separately installed local PostgreSQL free to use its normal port.

```powershell
docker run -d --name guardian-postgres -e POSTGRES_USER=guardian -e POSTGRES_PASSWORD=guardian-local -e POSTGRES_DB=guardian -p 127.0.0.1:5433:5432 -v guardian-pgdata:/var/lib/postgresql/data postgres:16-alpine
docker exec guardian-postgres pg_isready -U guardian -d guardian
```

Wait for `accepting connections`. On later days use `docker start guardian-postgres`. To stop this database use `docker stop guardian-postgres`. The named `guardian-pgdata` volume retains data when the container stops. The POSTGRES_USER/PASSWORD/DB initialization settings take effect when the data volume is empty; changing the command later does not reset existing credentials.

Edit `Backend/.env` and add this connection line.

```dotenv
DATABASE_URL=postgresql+psycopg://guardian:guardian-local@127.0.0.1:5433/guardian
```

Restart the backend after editing `.env`. To verify an actual database connection, run the following from `Backend/`.

```powershell
@'
from sqlalchemy import text
from app.db import create_database_engine
from app.settings import Settings

engine = create_database_engine(Settings())
try:
    with engine.connect() as connection:
        print(connection.execute(text("SELECT 1")).scalar_one())
finally:
    engine.dispose()
'@ | uv run python -
```

Expected output is `1`. A successful liveness response only proves the API process is running; use this database query to confirm connectivity.

Then create Guardian's 19 tables and check the revision.

```powershell
uv run alembic upgrade head
uv run alembic current
```

`alembic current` should print `0001_guardian (head)`. Running `upgrade head` again changes nothing.

### Hosted deployment

The [cloud runbook](../docs/guardian/cloud-deployment.md) uses Cloud Run for frontend/backend, managed Neon PostgreSQL by default, private Neon Object Storage via an S3 adapter and Secret Manager. Supabase can replace Neon with the same schema and API.

Cloud Run receives the provider's TLS DATABASE_URL directly. The API and migration/maintenance jobs use their own credentials. No Cloud SQL instance or Cloud SQL attachment is required for this plan. Provider access, quotas and actual billing must be verified during deployment.

## Configuration

Settings load environment variables and optional `.env` in the working directory. Environment values take precedence. Keep credentials out of source control.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Development, test or production |
| `PORT` | `8080` | Listener used by `python -m app` and Cloud Run |
| `PUBLIC_APP_ORIGIN` | `http://localhost:3000` | Exact browser origin every mutation's `Origin` header must equal; also decides the cookie Secure flag |
| `DATABASE_URL` | Unset | `postgresql+psycopg://...`, masked in settings output |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | `3`, `2` | Bounded connections with pre-ping |
| `EVIDENCE_BUCKET` | Unset | Private evidence storage; not used until Task 9 |
| `AI_PROVIDER`, `AI_MODEL`, `AI_API_KEY` | Unset | Model provider; not used until Task 9 |
| `AI_TIMEOUT_SECONDS` | `20` | Planned total inference deadline; not used until Task 9 |
| `SANDBOX_TTL_SECONDS` | `86400` | Demo sandbox lifetime |
| `SESSION_TTL_SECONDS` | `86400` | Controller/actor session lifetime, capped at the sandbox expiry |
| `HOLD_TTL_SECONDS` | `900` | Review deadline of a held transfer |
| `DRAFT_TTL_SECONDS` | `1800` | Draft lifetime |
| `ASSESSMENT_TTL_SECONDS` | `300` | How long an assessment can be acknowledged |
| `AI_SANDBOX_HOURLY_LIMIT` | `20` | Planned analysis quota; not used until Task 9 |
| `GROUP_SANDBOX_HOURLY_LIMIT` | `5` | Planned investigation quota; not used until Task 12 |
| `AI_DAILY_GLOBAL_LIMIT` | `300` | Planned global model quota; not used until Task 9 |

A configured DB creates a lazy engine during lifespan. Liveness stays available when that DB is unreachable. Endpoints that need the database return 503 `SERVICE_UNAVAILABLE` when `DATABASE_URL` is not set. The origin setting is validated here and enforced on every mutation (see below). The app adds no CORS policy; the frontend reaches the API through a same-origin proxy.

## Demo sessions

`POST /api/v1/demo/sessions` with `{"scenario": "MAIN_REFUND"}` (or `FALSE_POSITIVE`, `INSUFFICIENT_EVIDENCE`) seeds a fresh isolated sandbox from server-held fixtures (`app/demo/fixtures.py`) in one transaction. It sets two opaque HttpOnly cookies, `guardian_demo` (demo controller) and `guardian_session` (actor, initially Linh), and returns both CSRF tokens in the 201 Bootstrap body. The database stores only SHA-256 hashes of the cookies and CSRF tokens.

| Rule | Behavior |
| --- | --- |
| Origin | Every mutation, including bootstrap, requires `Origin` exactly equal to `PUBLIC_APP_ORIGIN`; otherwise 403 `ORIGIN_DENIED` |
| CSRF | `X-CSRF-Token` must match the endpoint's own credential: controller token for `/demo/*` controls, actor token for customer/operator actions; otherwise 403 `CSRF_FAILED` |
| Session | Missing, unknown, revoked or expired session, or an expired sandbox: 401 `SESSION_EXPIRED` |
| Actor selection | `POST /demo/actors/select` with `{"actor_id": ...}` issues a new actor cookie and CSRF token and revokes the presented actor cookie. An actor outside the controller's sandbox is 404 `NOT_FOUND` |
| `/me` | Returns the actor, its accounts with masked identifiers and the same actor CSRF token, re-derived from the cookie without changing state. Ops gets its identity and no accounts |
| Role | `/recipients` and `/orders` are CUSTOMER-only: an authenticated operator gets 403 `FORBIDDEN` |
| `/recipients` | The sandbox's seeded external accounts (never a customer wallet), masked, ordered by display_name then ID |
| `/orders` | The caller's own orders with nested refund or null, newest `fee_verified_at` first (unknown last) then ID descending. An unknown fee is `null`, distinct from a verified `0` |
| Cookies | HttpOnly, SameSite=Lax, Path=/, Max-Age up to 24 hours. Secure unless `PUBLIC_APP_ORIGIN` is `http://` on localhost/127.0.0.1/::1 outside `APP_ENV=production` |

Browsers set `Origin` themselves. To try these operations in Swagger at `http://localhost:8080/docs`, start the backend with `PUBLIC_APP_ORIGIN=http://localhost:8080`. A manual client sends the header explicitly, for example `curl -i -X POST http://localhost:8080/api/v1/demo/sessions -H "Origin: http://localhost:3000" -H "Content-Type: application/json" -d '{"scenario":"MAIN_REFUND"}'`.

## Transfers and holds

All amounts are integer VND. Every mutation needs the Origin and the actor CSRF token described above. Money rules come from `docs/guardian/data-model.md`.

| Operation | Behavior |
| --- | --- |
| `POST /transfers` (createTransfer) | CUSTOMER only. The sender must be the caller's wallet and the recipient must come from `/recipients`; otherwise 404. Sending to yourself is 422. A new draft is 201 and reserves nothing. Repeating the same `client_request_id` with the same fields is 200 with `replayed: true`; with different fields it is 409 `IDEMPOTENCY_CONFLICT` |
| `POST /transfers/{id}/assess` | Behavioral rule: at least five settled outgoing transfers in the last 30 days, and an amount of at least three times the median and at least 2,000,000 gives WARN. Fewer samples give `INSUFFICIENT_HISTORY`. An active recipient restriction gives WARN or HOLD. The assessment lasts `ASSESSMENT_TTL_SECONDS` and changes no money |
| `POST /transfers/{id}/confirm` | Re-checks risk at confirmation time. HOLD reserves the amount once and sets `RISK_HELD` with a `HOLD_TTL_SECONDS` deadline. WARN needs a current `acknowledged_assessment_id`; otherwise 409 `ACKNOWLEDGEMENT_REQUIRED` with a fresh `error.assessment`. ALLOW or an acknowledged WARN writes one debit and one credit. Too little available money is 409 `INSUFFICIENT_FUNDS`. Confirming again returns the stored result |
| `POST /transfers/{id}/cancel` | Releases a reservation exactly once. Cancelling again returns the same result |
| `GET /ops/holds`, `POST /ops/transfers/{id}/review` | OPERATOR only. APPROVE sets `READY` without moving money and keeps the original deadline; the customer must confirm again. REJECT releases the reservation. A new restriction before reconfirmation holds the transfer again without a second reservation |
| `POST /demo/refunds/{id}/settle` | Demo controller only. Credits an approved refund once, even while an outgoing transfer is held |

Deadlines use database time. `/me`, transfer reads, the hold queue and every command first expire due drafts and holds, so an expired reservation never authorizes a payment. Writers take locks in one order: the recipient advisory lock, then account rows sorted by ID, then transfer rows sorted by ID.

## Source layout

```text
app/
  __main__.py       Environment-configured listener
  main.py           App factory, lifespan and routers
  settings.py       Validated environment and masked secrets
  errors.py         Public error envelope and handlers
  middleware.py     Request IDs and no-store headers
  health.py         Liveness route
  db.py             Metadata, engine factory and request sessions
  models.py         SQLAlchemy mappings for the 19 tables
  api/              Contract DTOs and pagination
  auth/             Hashed sessions, Origin/CSRF checks, roles and /me
  demo/             Scenario fixtures, sandbox bootstrap, reference lists and refund settlement
  transfers/        Drafts, confirmation, cancellation, locking and expiry
  risk/             Behavioral and recipient risk evaluation
  operations/       Hold review and audit events
  evidence/         Evidence upload and storage (Task 9, empty)
  investigation/    AI analysis, investigation and trace (Tasks 9 and 12, empty)
migrations/
  env.py            Migration runtime; accepts -x url=... or a test connection
  script.py.mako    Revision template
  versions/         0001_guardian, the frozen schema.sql revision
```

## Verification

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run alembic heads
```

The default suite skips PostgreSQL integration checks unless `TEST_DATABASE_URL` points to a dedicated disposable database. The rollback test creates and removes `skeleton_session_probe`. Run this only against a test database. With the local container above, create a separate test database once.

```powershell
docker exec guardian-postgres createdb -U guardian guardian_test
$env:TEST_DATABASE_URL = 'postgresql+psycopg://guardian:guardian-local@127.0.0.1:5433/guardian_test'
uv run pytest -q
$env:TEST_DATABASE_URL = $null
```

If `guardian_test` already exists, reuse it. Keep the integration test URL separate from the database used for the live demo.

The schema tests drop and recreate the `public` schema of `TEST_DATABASE_URL`, then apply the migrations. They refuse to run when the database name does not contain `test`, and they never read `DATABASE_URL` from `.env`. To apply migrations to an explicit database without `.env`, pass the URL: `uv run alembic -x url=<url> upgrade head`.

`alembic heads` reports `0001_guardian`, the frozen copy of `docs/guardian/schema.sql`. Migration jobs use separate database-user credentials. Their settings do not require an AI key.

### Continuous integration

[`backend-ci.yml`](../.github/workflows/backend-ci.yml) runs on pull requests and pushes to `dev` and `master` that change `Backend/`, `docs/guardian/openapi.yaml` or `docs/guardian/schema.sql`. It can also be started manually from the Actions tab.

| Job | Checks |
| --- | --- |
| Lint, contract, tests and migrations | `uv sync --locked`, `uv lock --check`, ruff check and format, OpenAPI validation, the full pytest suite on a PostgreSQL 16 service container (any skipped test fails the job), then downgrade, upgrade twice and offline SQL generation |
| Container image and health smoke | Builds `Backend/Dockerfile`, starts it and expects `{"status":"ok"}` from `/api/v1/health` with the process running as UID 10001 |

The workflow has read-only repository permission and uses no secrets. It does not deploy.

## Container

Run from the repository root.

```powershell
docker build -t guardian-backend:local Backend
docker run --rm -p 8080:8080 -e PORT=8080 guardian-backend:local
```

The image runs as an unprivileged user, installs locked runtime dependencies and includes Alembic, so a migration job can run `alembic upgrade head` from the same image. Inject secrets through the deployment environment. [Cloud deployment plan](../docs/guardian/cloud-deployment.md) describes the planned public Next frontend, private API, managed database and scheduled jobs.

For backend and PostgreSQL running in separate Docker containers, put both on the same network and use the database container name as the host. Run these commands from the repository root after creating `guardian-postgres` above. Create/connect the network once.

```powershell
docker network create guardian-local
docker network connect guardian-local guardian-postgres
docker run --rm --network guardian-local -p 8080:8080 -e PORT=8080 -e DATABASE_URL=postgresql+psycopg://guardian:guardian-local@guardian-postgres:5432/guardian guardian-backend:local
```

Inside the backend container, `guardian-postgres:5432` reaches the database container. A backend running directly on your computer uses `127.0.0.1:5433` instead. Stop any earlier backend bound to 8080 before starting another one.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `uv` is not recognized | Install uv using its official instructions, reopen PowerShell, or use the existing `.venv` interpreter command |
| `No module named app` | Run from `Backend/` after installing dependencies |
| Address already in use | Stop the existing backend process or choose another port |
| `Connection refused` on DB query | Check Docker Desktop, container status, `pg_isready`, port 5433 and the URL in `.env` |
| Password authentication failed | Use the credentials that initialized the persistent volume; later environment changes do not replace them |
| Health succeeds but tables are missing | Liveness does not check tables; run `uv run alembic upgrade head` against that database |
| A mutation returns 403 `ORIGIN_DENIED` | The `Origin` header must equal `PUBLIC_APP_ORIGIN` exactly; see [Demo sessions](#demo-sessions) for Swagger and curl |
| Container cannot reach DB at localhost | Use the shared Docker network and `guardian-postgres:5432` when both run in containers |

## AI and evidence status

The approved [AI investigation design](../docs/guardian/ai-investigation.md) adds bounded read-only function calling and optional dossier responses to the planned Analysis/Investigation APIs. [Guardian API contract v1.3 (OpenAPI 3.1)](../docs/guardian/openapi.yaml) is the full contract with 32 operations. Version 1.2 added optional additional_actions and finding signals, and 1.3 added optional claimed_transfer_direction; earlier versions are in [the archive](../docs/guardian/archive/README.md). The DTOs already include these fields, but no AI provider/tool adapter, evidence storage or analysis route is implemented yet.

Neon Object Storage through an S3 adapter is the evidence-storage target. Endpoint/region/scoped storage credentials and bounded-runner settings are documented in the [cloud runbook](../docs/guardian/cloud-deployment.md); they are future settings until implemented. An existing .env or successful health request does not prove DB/storage/model connectivity. Do not add secrets to shared docs or assume that changing AI_MODEL enables an absent adapter.
