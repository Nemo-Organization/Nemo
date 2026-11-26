# Guardian specification changes

## 26 November 2026 — API contract 1.3, claimed transfer direction

Scope: documentation and executable API specification only.

- Added optional `ModelEvidence.claimed_transfer_direction` (INCOMING, OUTGOING, UNKNOWN). Operations, paths, request bodies and required fields are unchanged.
- Resolved the rule 1 open item from 1.2: finding rule 1 reads this field with a validated quote and compares it with the linked transfer's direction. Added it to held-out labels, metrics and required checks.
- Archived OpenAPI 1.2.0 and the 1.2.0 fixtures byte-for-byte. Added dated "Contract 1.3 amendment" sections; the 1.2 text stays in place.

## 25 November 2026 — API contract 1.2, evaluation labels and baseline

Scope: documentation and executable API specification only. No runtime code, migration or deployment changes.

- Added optional `ModelEvidence.additional_actions` and a nullable `InvestigationFinding.signal`, plus the `InvestigationSignal` schema. Operations, paths, request bodies and required fields are unchanged.
- Defined the seven requested_action codes, their precedence for multi-request messages, ordered finding rules (two MISMATCH, one CONSISTENT, UNCERTAIN otherwise) and a fixed UI safety message for secret/login requests.
- Defined six message signals plus OTHER, their support requirements and neutral display. Added `recipient_display_name` to the TRANSFER fact allowlist.
- Specified the keyword baseline: input text, normalization, four term groups, decision order, reference pattern and freeze rule.
- Recorded the NEW_RECIPIENT live-guide variant, held-out case handling outside the repository, the plain-Python runner decision and the open rule 1 direction field.
- Added the new rules as dated "Contract 1.2 amendment" sections in evaluation.md and ai-investigation.md. The 1.1 text stays in place with pointers to the amendment.
- Archived OpenAPI 1.0.0 and 1.1.0 and the 1.1.0 fixtures byte-for-byte in [archive](archive/README.md).
- Updated the two fixtures and added notes to FE integration, team brief, architecture, API examples, the BA prompt, AGENTS.md and the backend README.

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
