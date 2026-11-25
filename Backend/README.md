# Guardian backend

FastAPI foundation for Nemo's Guardian anti-fraud application. Python 3.12, Pydantic settings, SQLAlchemy/psycopg, Alembic and a locked uv environment.

## Current implementation

- `GET /api/v1/health` returns `{"status":"ok"}` without contacting PostgreSQL or an AI provider.
- Responses include a server-generated `X-Request-ID` and `Cache-Control: no-store`.
- HTTP, validation and unexpected errors use the shared JSON error envelope with safe public messages.
- `create_app(settings)` supports isolated test instances and lifespan-managed database engines.
- Request-scoped sessions close and roll back uncommitted work. Business services will explicitly own commits.
- Alembic configuration and domain package boundaries are prepared for the next milestone.

Product requirements, the 19-table schema and full API contract live in [the delivery pack](../docs/guardian/README.md). The domain packages currently establish source boundaries. Authentication, transfers, inference and operator endpoints are future tasks. This migration scaffold has no schema revisions yet. Add domain models and the initial migration from the agreed schema before initializing product tables.

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

The current skeleton has not provisioned a provider project or the 19 product tables. Add the agreed domain models and initial migration in the next milestone. `alembic upgrade head` currently checks the empty migration chain.

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

Expected output is `1`. A successful liveness response only proves the API process is running; use this database query to confirm connectivity. At this skeleton milestone the database is empty of Guardian's 19 product tables. Alembic's initial domain migration is the next database implementation task. Running `alembic upgrade head` currently checks the empty migration chain.

### Hosted deployment

The [cloud runbook](../docs/guardian/cloud-deployment.md) uses Cloud Run for frontend/backend, managed Neon PostgreSQL by default, private Neon Object Storage via an S3 adapter and Secret Manager. Supabase can replace Neon with the same schema and API.

Cloud Run receives the provider's TLS DATABASE_URL directly. The API and migration/maintenance jobs use their own credentials. No Cloud SQL instance or Cloud SQL attachment is required for this plan. Provider access, quotas and actual billing must be verified during deployment.

## Configuration

Settings load environment variables and optional `.env` in the working directory. Environment values take precedence. Keep credentials out of source control.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Development, test or production |
| `PORT` | `8080` | Listener used by `python -m app` and Cloud Run |
| `PUBLIC_APP_ORIGIN` | `http://localhost:3000` | Exact HTTP/HTTPS origin reserved for the forthcoming CSRF layer |
| `DATABASE_URL` | Unset | `postgresql+psycopg://...`, masked in settings output |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | `3`, `2` | Bounded connections with pre-ping |
| `EVIDENCE_BUCKET` | Unset | Private storage for the evidence milestone |
| `AI_PROVIDER`, `AI_MODEL`, `AI_API_KEY` | Unset | Configuration for the inference milestone |
| `AI_TIMEOUT_SECONDS` | `20` | Planned total inference deadline |
| `HOLD_TTL_SECONDS` | `900` | Planned hold lifetime |
| `DRAFT_TTL_SECONDS` | `1800` | Planned draft lifetime |
| `ASSESSMENT_TTL_SECONDS` | `300` | Planned assessment lifetime |
| `AI_SANDBOX_HOURLY_LIMIT` | `20` | Planned analysis quota |
| `GROUP_SANDBOX_HOURLY_LIMIT` | `5` | Planned grouping quota |
| `AI_DAILY_GLOBAL_LIMIT` | `300` | Planned global model quota |

A configured DB creates a lazy engine during lifespan. Liveness stays available when that DB is unreachable. Financial/readiness endpoints will check their required dependencies explicitly. The origin setting is validated here; session authentication, CORS and CSRF enforcement belong to the auth milestone.

## Source layout

```text
app/
  __main__.py       Environment-configured listener
  main.py           App factory and lifespan
  settings.py       Validated environment and masked secrets
  errors.py         Public error models and handlers
  middleware.py     Request IDs and no-store headers
  health.py         Liveness route
  db.py             Metadata, engine factory and request sessions
  auth/             Identity and session milestone
  demo/             Isolated fixture milestone
  transfers/        Transfer and ledger milestone
  risk/             Risk evaluator milestone
  evidence/         Upload and storage milestone
  investigation/    AI evidence and trace milestone
  operations/       Operator decisions and notice milestone
migrations/
  env.py            Independent migration runtime
  script.py.mako    Revision template
  versions/         Initial domain migration to implement
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

`alembic heads` is empty for this skeleton. After the initial models and revision exist, configure `DATABASE_URL` and run `uv run alembic upgrade head`. Migration jobs use separate database-user credentials. Their settings do not require an AI key.

## Container

Run from the repository root.

```powershell
docker build -t guardian-backend:skeleton Backend
docker run --rm -p 8080:8080 -e PORT=8080 guardian-backend:skeleton
```

The image runs as an unprivileged user, installs locked runtime dependencies and includes Alembic for future migration jobs. Inject secrets through the deployment environment. [Cloud deployment plan](../docs/guardian/cloud-deployment.md) describes the planned public Next frontend, private API, managed database and scheduled jobs.

For backend and PostgreSQL running in separate Docker containers, put both on the same network and use the database container name as the host. Run these commands from the repository root after creating `guardian-postgres` above. Create/connect the network once.

```powershell
docker network create guardian-local
docker network connect guardian-local guardian-postgres
docker run --rm --network guardian-local -p 8080:8080 -e PORT=8080 -e DATABASE_URL=postgresql+psycopg://guardian:guardian-local@guardian-postgres:5432/guardian guardian-backend:skeleton
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
| Health succeeds but tables are missing | Liveness is independent of DB readiness; implement/apply the initial domain migration in the next milestone |
| Container cannot reach DB at localhost | Use the shared Docker network and `guardian-postgres:5432` when both run in containers |

## AI documentation update — 25 November

The approved [AI investigation design](../docs/guardian/ai-investigation.md) adds bounded read-only function calling and optional dossier responses to the planned Analysis/Investigation APIs. [Guardian API contract v1.1 (OpenAPI 3.1)](../docs/guardian/openapi.yaml) remains the full future contract: 32 operations; runtime still implements health only. No AI provider/tool adapter, business route, domain migration or storage integration is implemented by this documentation change.

Neon Object Storage through an S3 adapter is the evidence-storage target. Endpoint/region/scoped storage credentials and bounded-runner settings are documented in the [cloud runbook](../docs/guardian/cloud-deployment.md); they are future settings until implemented. An existing .env or successful health request does not prove DB/storage/model connectivity. Do not add secrets to shared docs or assume that changing AI_MODEL enables an absent adapter.
