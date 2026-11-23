# Guardian decisions, boundaries and expansion

## Recorded choices

| Choice | Rationale and consequence |
| --- | --- |
| Anti-Fraud is the primary contest theme | Customer intervention and operator-reviewed evidence form one product. Trace functionality supports security investigation. |
| Two independent risk signals | Behavioral unusualness and verified recipient risk both matter. Warning wording identifies the actual reason. |
| WARN for behavioral anomalies | Legitimate high-value payments remain possible after acknowledgement. |
| Operator-created WARN or HOLD restrictions | Community reports create evidence, with explicit human accountability for a public-facing restriction. |
| 15-minute hold, 30-minute draft, five-minute assessment | Concrete defaults for implementation and tests. They are design proposals, configurable and measurable during usability testing. |
| Customer reconfirmation after clearance | The customer remains in control of whether a delayed transfer should still happen. |
| Reference-based tracing | Seeded issuance and access records permit a falsifiable investigation. A code and legitimate read do not establish the perpetrator. |
| Private image storage | Evidence survives container restarts and remains available for scoped review. |
| Next.js and FastAPI services | Matches the repository's actual frontend runtime; no static-export assumption. |
| Neon PostgreSQL, with Supabase as an alternative | Follows the team's preference for affordable hosted PostgreSQL. Separate development/demo data, retain TLS, and verify plan quotas and connection limits before deployment. |
| Public frontend and IAM-authenticated private API | The Next route proxy attaches its service identity and forwards actor cookies. FastAPI retains application authorization. The cloud-deployment document defines the release steps. |
| Synchronous bounded AI calls | Keeps the first implementation comprehensible. Persisted runs support future workers. |
| No automatic partner suspension in core | Investigation-to-customer-protection is sufficient for the primary journey; suspension adds a distinct permission lifecycle and operational impact model. |

## Dependencies to verify on Day 1

- Frontend dependency install, strict namespace generation, type check and production build succeed with the committed lockfile. Record targeted fixes if a dependency/config is unavailable.
- An authorized vision/text provider responds from the hosting environment. Confirm actual account access and billing eligibility. AWS, GCP and coding-agent credits are separate from runtime model access.
- Managed PostgreSQL and private object storage are reachable with TLS and scoped service credentials.
- Next-to-FastAPI proxy forwards cookies and no-store semantics correctly and attaches a valid service identity to the private API. Session creation/selection works in an ordinary browser.
- Both developers agree on OpenAPI fields before replacing domain mocks. BA agrees the primary scenario starts with a pre-existing verified recipient restriction.

## Extension roadmap

| Stage | Capability | Existing boundary reused | New requirement before implementation |
| --- | --- | --- | --- |
| After core passes | More refund impersonation variants and report grouping | ModelEvidence, reports, ai_runs | More independently labeled cases and review UX |
| Merchant pilot | Real merchant order/refund facts | orders/refunds source metadata | Partner authentication, consent/retention terms, field-level access, data reconciliation |
| Real payment pilot | Live hold and final settlement | transfer lifecycle and payment service | Authorized provider API, durable dispatch IDs, outbox, UNKNOWN reconciliation, provider guarantees and licensing review |
| Security response | Suspend one partner's reads; compare policy impact | partners, batches, access events, audit | Integration identities, scoped API permissions, policy history and event-replay model |
| Additional scam types | Purchase impersonation, investment/task scam evidence | requested action, reports, recipient signals | Distinct evidence sources, labels and intervention criteria for each type |
| Better behavioral detection | Statistical/ML personalization | risk evaluator and assessment facts | Representative historical data, temporal train/test split, bias/false-positive review, calibration |
| Higher throughput | Background OCR/grouping and callbacks | persistent ai_runs and adapters | Durable jobs, worker identity, per-run idempotency, retry/dead-letter policy |
| Multi-organization | Tenant-owned production data | scoped entity boundaries | Explicit organization/tenant tables and membership; separate sandbox expiration from production ownership |
| Mobile / trusted channels | In-app image sharing and payment intervention | API contract and principal model | Authorized platform integrations, device-specific UX and privacy design |

## Data evolution rules

- Add versioned migrations, with backwards-compatible fields before switching callers. Keep existing sandbox records readable after upgrades.
- Extend a risk reason additively and version the evaluator. Persist original assessment facts for review. Update frontend labels and API enums together.
- Keep external identifiers separate from internal UUIDs. Include source system and verification time when introducing authoritative live data.
- Preserve decision history and source evidence. Use explicit status transitions and compensating ledger entries for corrections.
- Add separate tables when records have an independent lifecycle, permission or retry history. Avoid a universal JSON table for money, policy and evidence.
- Introduce external settlement only with a separate provider-state model. Local atomic database commits cannot make a network payment atomic.

## Claims the evidence currently supports

The product combines reviewed-recipient interventions, rule-based anomaly warnings, image evidence interpretation and exact-reference investigation. Existing wallets and security/payment providers already publish recipient warnings, anomaly detection, reporting and policy tooling. The contest's originality claim should focus on the measured behavior of this combined workflow and on avoiding false attribution/false restrictions. A claim that the product is the first in Vietnam requires a separate competitive study.

The initial behavioral dataset and financial balances are synthetic. The primary screenshot and trace records are synthetic. Runtime AI interpretation and database enforcement must be demonstrated through the live product. Customer protection for a completely unseen ordinary transfer without contextual evidence remains limited.

## Credit and availability plan

The team reported roughly USD 200 GCP, USD 20 AWS and organizer coding-tool credits. Treat those as reported balances, not verified runtime budgets. Prefer existing credits for hosting after checking eligibility. Set Cloud Run maximum instances and DB pool sizes to match measured load, add provider quotas, and cap image size/calls before sharing the public URL. Keep a text/sample-image path when a judge's upload is unreadable. Disclose provider errors visibly and keep deterministic transfer controls usable.

## Scope reduction order

If the integrated journey slips, first defer automatic multi-report grouping, then nonessential charts and polished analytics. Preserve recipient and behavioral branches, live screenshot interpretation, exact tracing, reviewed restrictions, cancel/expiry behavior and isolation between sandboxes. Keep targeted batch notices because they close the primary demo. Preserve the false-positive correction test even if its UI becomes a simple operator action.
