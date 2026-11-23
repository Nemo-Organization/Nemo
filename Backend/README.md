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

## Local setup

Install Python 3.12 and [uv](https://docs.astral.sh/uv/getting-started/installation/). Run from `Backend/`. On Windows open PowerShell and enter the repository's Backend directory first.

```powershell
cd "D:\Momo Tech Day\Nemo\Backend"
uv sync --locked
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uv run python -m app
```

The service listens at `http://localhost:8080`. `PORT` selects another port. Development reload uses `uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8080`.

Interactive documentation is at `/docs`; implemented operations are at `/openapi.json`. The full planned contract is `../docs/guardian/openapi.yaml`.

Open `http://localhost:8080/docs`, expand GET `/api/v1/health`, choose **Try it out**, then **Execute**. Expected response is `{"status":"ok"}`. Keep the terminal open while using the API. Press Ctrl+C to stop it. If 8080 is already occupied, stop the earlier backend or choose a different port.

If this checkout already has `.venv` from the skeleton setup, the installed interpreter can start the service directly.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

That direct command assumes dependencies have already been installed. New checkouts use `uv sync --locked` first. Open the `Backend/` working directory so imports and the optional `.env` file resolve consistently.

## Where PostgreSQL runs

| Environment | Database location | How backend connects |
| --- | --- | --- |
| Everyday development | PostgreSQL 16 in Docker on each developer's computer | Local `.env` points to `127.0.0.1:5433` |
| Backend integration tests | A dedicated local `guardian_test` database | `TEST_DATABASE_URL` points to that disposable test database |
| Shared online demo | Managed PostgreSQL, proposed Cloud SQL in GCP | Cloud Run receives a versioned DB secret and a Cloud SQL attachment |

Use local PostgreSQL for routine development. The hosted demo has its own managed database. Each environment has separate credentials and data. Changing `DATABASE_URL` selects the target; tables and application behavior follow the agreed schema/migrations.

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

### Use a cloud database

The [cloud runbook](../docs/guardian/cloud-deployment.md) specifies the online demo's Cloud SQL PostgreSQL 16, migration job, secrets and service identities. Create those resources during the cloud deployment task. The current skeleton setup has not provisioned a cloud database.

In Cloud Run, inject the application `DATABASE_URL` through Secret Manager and attach the SQL instance. The migration job uses a separate database-user secret. With an existing external managed PostgreSQL, use the provider's direct TLS connection details and the psycopg driver prefix. URI-encode special characters in credentials and verify the provider's transaction/connection-pool behavior.

For an external managed provider, the local `.env` shape is illustrated below. Replace values only in your private environment file.

```dotenv
DATABASE_URL=postgresql+psycopg://USER:URL_ENCODED_PASSWORD@HOST:5432/DATABASE?sslmode=require
```

A developer connecting to Cloud SQL from a laptop should use an authorized Cloud SQL Auth Proxy connection or another explicitly configured secure connection. The `/cloudsql/...` Unix socket path in a Cloud Run secret applies to the attached cloud service environment. The web frontend never receives the database URL.

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
