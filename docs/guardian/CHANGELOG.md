# Guardian specification changes

## 25 November 2026 — API contract 1.1, bounded AI investigation

Scope: documentation and executable API specification only. No business API, model adapter, migration, billing change or cloud deployment is implemented by this revision.

- Added a [team brief](team-brief.md) and [bounded AI design](ai-investigation.md).
- Retained 32 operations on 28 paths, existing request bodies/auth/status responses and all previous response fields. Added optional nullable dossier to Analysis and Investigation, plus four shared dossier schemas.
- Defined separate customer/Ops read-only tool registries, initial root context, private per-claim support validation and server-generated activity. Tools cannot mutate money/policy/notices.
- Defined a shared 20-second, three-model-request, four-tool budget, logical-vs-provider quotas, pre-admission vs accepted-run failures and canonical replay.
- Preserved exact reference/batch/access tracing, forwarding uncertainty, independent trace availability and human-reviewed actions. Clarified preview before report resolution versus publication after resolution.
- Retained 19 tables/161 physical columns, key/type definitions and executable SQL unchanged. Documented versioned ai_runs JSON projection and private execution receipts.
- Updated customer/Ops UI guidance, FE adapters, safe error/PENDING recovery and complete synthetic JSON fixtures. No general chat or streaming added.
- Aligned architecture/deployment to private Neon S3 evidence storage alongside Neon PostgreSQL and Cloud Run; provider choice remains configurable and unverified until a live smoke.
- Updated both plans, prompts, scenarios, evaluation and setup guidance. Added no training/fine-tuning, real-money settlement or automatic provider rotation to core.

Validation: see [the validation record](validation.md). Schema/example/syntax checks do not validate runtime behavior, model quality, provider quota or live deployment.
