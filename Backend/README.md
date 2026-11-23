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

Install Python 3.12 and [uv](https://docs.astral.sh/uv/getting-started/installation/). Run from `Backend/`.

```powershell
uv sync --locked
Copy-Item .env.example .env
uv run python -m app
```

The service listens at `http://localhost:8080`. `PORT` selects another port. Development reload uses `uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8080`.

Interactive documentation is at `/docs`; implemented operations are at `/openapi.json`. The full planned contract is `../docs/guardian/openapi.yaml`.

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

The default suite skips PostgreSQL integration checks unless `TEST_DATABASE_URL` points to a dedicated disposable database. The rollback test creates and removes `skeleton_session_probe`. Run this only against a test database.

```powershell
$env:TEST_DATABASE_URL = 'postgresql+psycopg://guardian:guardian-test-only@127.0.0.1:5432/guardian_test'
uv run pytest -q
$env:TEST_DATABASE_URL = $null
```

`alembic heads` is empty for this skeleton. After the initial models and revision exist, configure `DATABASE_URL` and run `uv run alembic upgrade head`. Migration jobs use separate database-user credentials. Their settings do not require an AI key.

## Container

Run from the repository root.

```powershell
docker build -t guardian-backend:skeleton Backend
docker run --rm -p 8080:8080 -e PORT=8080 guardian-backend:skeleton
```

The image runs as an unprivileged user, installs locked runtime dependencies and includes Alembic for future migration jobs. Inject secrets through the deployment environment. [Cloud deployment plan](../docs/guardian/cloud-deployment.md) describes the planned public Next frontend, private API, managed database and scheduled jobs.
