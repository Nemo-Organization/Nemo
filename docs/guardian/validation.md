# Specification validation record

Validated locally on 23 November 2026 against the inspected Nemo dev checkout. This record covers the delivery documents and executable schema/contract. Application acceptance tests are assigned in the implementation plan and require the application to be built.

| Check | Result |
| --- | --- |
| OpenAPI 3.1 validation | Passed with openapi-spec-validator 0.9.0 |
| Unique operation IDs | 32 operations across 28 paths, all unique |
| JSON schema references | Resolved during OpenAPI validation |
| Concrete API examples | Seven JSON examples validated against their contract schemas |
| PostgreSQL DDL | Applied successfully to a fresh isolated PostgreSQL 18.6 database; 19 tables created |
| Constraint checks | Eight negative insertion/update checks passed |
| Nullable merchant fee | Missing fee accepted; fee 0 without provenance rejected |
| SQL/API transfer, report and refund states | Checked for enum consistency |
| Markdown links | All relative links resolve |
| Whitespace | No trailing whitespace in delivery files |
| Field-level DB specification | All 19 table sections and 161 column rows match SQL names, order, types, nullability and defaults |
| Per-field key annotations | Dedicated Key type and Key definition / reference columns identify PK, UQ and FK directly, including composite groups and partial unique indexes; checked against DDL |
| Cloud runbook examples | All five Bash command blocks pass shell syntax validation; cloud commands were not executed |
| Cloud design consistency | Architecture, delivery tasks and agent prompts now specify a public Next frontend and IAM-authenticated private FastAPI backend |

The eight negative checks exercised cross-sandbox transfer FKs, account over-reservation, verified fee provenance, duplicate draft request keys, hold-without-reservation, terminal-transfer timestamps, duplicate active recipient restrictions and duplicate debit entries. Test changes were rolled back. The isolated temporary PostgreSQL instance was stopped after validation.

The proposed database compatibility floor is PostgreSQL 16. The available local binary was PostgreSQL 18.6, so run the migration again on the selected production database version in Task 2. The DDL uses features available in PostgreSQL 16, but that target-version run is still a delivery check.

Remaining runtime checks include cookie/proxy integration, live model access, concurrency, strict frontend build, exact evidence interpretation and hosted end-to-end behavior. Actual provider credentials, cloud credit eligibility and deploy cost have not been verified by document validation.

The cloud runbook proposes Cloud SQL PostgreSQL 16 as the initial database and a route proxy with Google service identity. Provisioning requires the team's actual project, IAM permissions, secrets and verified provider configuration. The public deployment, migration job, scheduled execution and rollback checks remain implementation tasks.

## Backend skeleton implementation

Implemented on branch `feat/guardian-backend-skeleton` in incremental commits. The available runtime now includes the FastAPI application factory, liveness, safe JSON errors, request IDs, validated settings, lazy PostgreSQL engines, request-scoped sessions, Alembic scaffolding and a non-root Docker entry point.

| Check | Observed result |
| --- | --- |
| Backend behavior tests | 22 passed, including two real PostgreSQL 16 integration checks |
| Ruff lint and formatting | Passed |
| Dependency lock | `uv lock --check` passed |
| Migration scaffold | `alembic heads`, online upgrade and offline SQL generation ran successfully with no domain revisions yet |
| Linux image | Docker build completed with Python 3.12 and locked production dependencies |
| Container smoke | Health and JSON 404 served over HTTP using custom PORT 8123; runtime UID 10001 |
| Independent code review | No blocking findings; nonstandard HTTP-status fallback fixed with a RED-to-GREEN regression test |

The domain packages are initial boundaries. Product auth, transfers, the 19-table model/migration, live AI and cloud deployment remain subsequent milestones. Generated runtime OpenAPI currently describes the implemented health route; the full planned contract continues to define the future endpoints.
