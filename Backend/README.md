# Nemo — Backend

> **Template README:** Replace the `<TODO>` placeholders below as the backend stack, architecture, and endpoints are finalized.

## Overview

Backend service for **Nemo**, providing APIs for `<TODO: core domains, e.g., leads, endpoints, usage analytics, logs, authentication>`.

### Tech Stack

- **Language / Runtime:** `<TODO: e.g., TypeScript (Node.js 20+) / Go 1.23 / Python 3.12 / Java 21>`
- **Framework:** `<TODO: e.g., NestJS / Fastify / Gin / FastAPI / Spring Boot>`
- **Database:** `<TODO: e.g., PostgreSQL 16>`
- **ORM / Query Builder:** `<TODO: e.g., Prisma / Drizzle / GORM / SQLAlchemy>`
- **Cache / Queue:** `<TODO: e.g., Redis / BullMQ / RabbitMQ (optional)>`
- **API Documentation:** `<TODO: e.g., OpenAPI 3.1 / Swagger UI>`

## Prerequisites

- `<TODO: Runtime & version>`
- `<TODO: Package manager / build tool>`
- `<TODO: Database / Docker Compose (if used for local services)>`

## Getting Started

```bash
# 1. Install dependencies
<TODO: e.g., npm install / go mod download / uv sync>

# 2. Configure environment variables
cp .env.example .env

# 3. Start local dependencies (database, cache, etc.)
<TODO: e.g., docker compose up -d>

# 4. Run database migrations (and optional seed)
<TODO: e.g., npm run db:migrate && npm run db:seed>

# 5. Start the development server
<TODO: e.g., npm run dev>
```

Once running, the service should be available at `http://localhost:<PORT>` (health check at `GET /health`).

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values. Never commit real secrets.

| Variable | Required | Description | Default / Example |
| --- | --- | --- | --- |
| `APP_ENV` | Yes | Runtime environment (`development`, `staging`, `production`) | `development` |
| `PORT` | No | HTTP server port | `8000` |
| `DATABASE_URL` | Yes | Primary database connection string | `postgres://user:pass@localhost:5432/nemo` |
| `REDIS_URL` | No | Cache / queue connection string | `redis://localhost:6379` |
| `CORS_ORIGINS` | Yes | Comma-separated allowed frontend origins | `http://localhost:3000` |
| `JWT_SECRET` | Yes | Secret key for signing auth tokens | `<change-me>` |
| `LOG_LEVEL` | No | Logging verbosity (`debug`, `info`, `warn`, `error`) | `info` |

## Scripts / Commands

| Command | Purpose |
| --- | --- |
| `<TODO: dev command>` | Start development server with hot reload |
| `<TODO: build command>` | Compile / build for production |
| `<TODO: start command>` | Run production build |
| `<TODO: lint command>` | Run linter & formatter checks |
| `<TODO: test command>` | Run unit and integration tests |
| `<TODO: migrate command>` | Apply pending database migrations |
| `<TODO: seed command>` | Seed local development data |

## Project Structure

```text
<TODO: update to match chosen framework>
src/
├─ config/          Environment loading, validation, and app configuration
├─ modules/         Domain modules (e.g., leads/, endpoints/, analytics/, auth/)
│  └─ <module>/
│     ├─ controller / handler   HTTP route handlers & request validation
│     ├─ service                Business logic
│     ├─ repository             Database access
│     └─ dto / schema           Request & response schemas
├─ common/          Shared middleware, error handling, guards, interceptors, utils
├─ database/        Migrations, seeds, and database client setup
└─ main.<ext>       Application entry point
```

## API Conventions

- **Base Path:** `/api/v1`
- **Interactive Docs:** `http://localhost:<PORT>/docs` *(when enabled in non-production)*
- **Health Check:** `GET /health` → `200 OK`
- **Authentication:** `<TODO: e.g., Bearer JWT / API Key header>`
- **Pagination:** `<TODO: e.g., ?page=1&limit=20 or cursor-based>`
- **Error Format:**

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Lead not found",
    "details": []
  }
}
```

## Database & Migrations

- Create a migration: `<TODO: command>`
- Apply migrations: `<TODO: command>`
- Rollback last migration: `<TODO: command>`
- Seed sample data: `<TODO: command>`

## Testing

```bash
# Unit tests
<TODO: command>

# Integration / E2E tests
<TODO: command>

# Coverage report
<TODO: command>
```

## Coding Conventions

- Validate all incoming payloads, query params, and environment variables at the boundary.
- Keep controllers/handlers thin; place business rules in services and data access in repositories.
- Return consistent, structured error responses and never leak stack traces in production.
- Use structured JSON logging with request correlation IDs.

## Frontend Integration

- Allow the Frontend dev server origin (`http://localhost:3000`) in `CORS_ORIGINS`.
- Set `API_BASE_URL` in `../Frontend/.env.local` to point to this backend service.
- As endpoints become ready, replace mock data in `../Frontend/src/features/*/mocks/` with real API service calls.

## Deployment & CI/CD

- **Containerization:** `<TODO: Dockerfile / docker-compose.yml notes>`
- **CI Checks:** Lint, typecheck/compile, unit & integration tests, migration check
- **Observability:** `<TODO: structured logs, metrics, tracing, Sentry>`
