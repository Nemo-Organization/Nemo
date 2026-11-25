# Guardian frontend integration notes

Prepared on 24 November 2026 against `dev` commit `6f96e51`. This note records differences between the current UI mocks and the agreed API. It does not change the API contract or claim that business endpoints are implemented.

## Contract and ownership

Use [openapi.yaml](openapi.yaml) for wire fields, request bodies, response schemas, cookies, CSRF and status codes. Use [product-requirements.md](product-requirements.md) for business behavior. The detailed [backend implementation plan](../superpowers/plans/2026-11-24-guardian-backend-api.md) defines delivery dependencies.

Frontend components may keep camelCase view models. Translate snake_case DTOs once in feature services/adapters. Do not invent missing backend fields or infer money outcomes from a local animation. Until a route is ready, use a fixture satisfying its exact response schema. The current runtime implements only `GET /api/v1/health`.

## Required mock corrections

| Area | Current frontend assumption | Agreed behavior and integration action |
| --- | --- | --- |
| Behavioral risk | `evaluate-risk.ts` warns at 5,000,000 and holds at 20,000,000, including an 80%-of-balance signal | Initial rule: last 30 days of settled outgoing history; at least five observations; amount >= 3 x median AND >= 2,000,000 produces WARN. Below five observations is INSUFFICIENT_HISTORY. Do not create extra business rules in FE. |
| Recipient risk | Flags mapped into a local decision | Use `recipient_signal` NONE/WARN/HOLD and `reasons` from the assessment. A currently active, Ops-verified HOLD can hold even 20,000. A new community report alone never creates a restriction. |
| Combined risk | Amount threshold decides HOLD | Display `decision` from BE. Keep `behavior_signal` and `recipient_signal` independent. Anomaly alone does not produce HOLD. |
| Transfer status | awaiting_decision / held / completed / cancelled | Wire enum: DRAFT / RISK_HELD / READY / SUCCEEDED / CANCELED / REJECTED / EXPIRED. Awaiting warning acknowledgement is a UI state while the transfer remains DRAFT or READY. |
| Deadline | Mock hold deadline is 24 hours | Draft TTL is 30 minutes; first hold TTL is 15 minutes. Render server `expires_at`; refresh canonical state after expiry/actions. A READY clearance retains the original hold deadline. |
| Hold approval | pending / approved / rejected can imply payment completion | APPROVE returns READY and preserves the reservation; only a fresh customer confirmation can produce SUCCEEDED. REJECT returns REJECTED and releases reserved funds. |
| Balance | balance and available only | Map `balance_vnd`, `reserved_vnd`, `available_vnd` from `/me`. Re-fetch after confirm/cancel/review/refund. Holding changes reserved/available, not posted balance. |
| IDs | TRF-Date.now and symbolic fixture IDs | UUIDs come from bootstrap/list/create responses. Do not submit display labels or compiled mock IDs as resource IDs. |
| Recipient | name / accountNumber / flags | DTO has id / display_name / bank_code / masked_identifier. Obtain risk from assessment; never send a client risk verdict. |
| Reports | new / inReview / resolved / dismissed | Map RECEIVED / IN_REVIEW / RESOLVED / DISMISSED. Final states are terminal; a conflicting repeat returns 409. |
| Report type, priority and summary | Mock-specific fields | Not API fields in the current contract. Use truthful presentation defaults, narrative and timestamps; propose an explicit contract change if server-assigned type/priority is required. |
| Refund | pending / approved / completed / rejected | Core DTO supports APPROVED / SETTLED only. Missing fee is unknown; a verified fee of zero must display as zero. |
| Trace | partial matches and generic record IDs | Exact issued references only; result status MATCHED_SCOPE / NO_MATCH / NO_REFERENCE. Show references and access records plus `limitations`. A match does not prove a partner leaked data. |
| Notice audience | transferredRecently / hasDraft | Preview derives distinct customers owning orders in the traced batch. UI cannot supply an arbitrary recipient list. An unrelated customer must be excluded. |
| Restriction | level and creation time only | Use action WARN/HOLD, status ACTIVE/REVOKED/EXPIRED, evidence report IDs, expiry and reason. A report count is evidence for review, not an automatic decision. |
| Notice copy | Local i18n key only | Display server-provided title/body safely as plain text; do not treat generated strings as translation keys or HTML. |

Observed source files: `Frontend/src/features/transfer/types/transfer.types.ts`, `lib/evaluate-risk.ts`, `services/transfer.service.ts`, `Frontend/src/features/operator/types/operator.types.ts` and operator mock consumers. This is an integration review, not a frontend build verification.

## API client behavior

1. Bootstrap via `POST /api/v1/demo/sessions`, with one scenario: MAIN_REFUND, FALSE_POSITIVE or INSUFFICIENT_EVIDENCE. Store the returned actors/current actor and both CSRF tokens in the demo UI's session state. They are different credentials.
2. Use actor `X-CSRF-Token` for mutating customer/operator calls; controller CSRF for actor selection and demo refund settlement. Browser Origin must match `PUBLIC_APP_ORIGIN`. The controller cookie is not an operator permission.
3. Cookies are server-issued. Do not send a chosen actor role or sandbox ID as authorization. Restore selected identity via `GET /me`; clear actor-specific query/cache state after selection. Tabs in one browser share cookies.
4. Use relative `/api/v1/...` routes through the planned same-origin Next proxy. The backend is on localhost:8080 during development. Calling it directly from localhost:3000 needs a deliberate credentialed CORS configuration; the current skeleton has no such integration. Never expose DB/storage/provider secrets to browser code.
5. Draft creation uses a client-generated UUID request key. Retry the same logical submission with the same UUID; editing immutable amount/recipient creates a new draft and key. 201 means created, 200 means replay. A reused key with a different body returns 409.
6. WARN continuation sends `acknowledged_assessment_id` from the latest assessment. Do not auto-confirm a newly returned warning. On 409, inspect `error.assessment` / `error.current_transfer`, refresh relevant data and ask for a fresh decision when required.
7. Submit `POST /analyses` as multipart FormData. Do not set the multipart Content-Type header manually. Optional image: PNG/JPEG/WebP, maximum 5 MiB; optional text: at most 12,000 characters. At least one source must be present. An analysis is not a transfer confirmation.
8. AI PENDING/FAILED/TIMED_OUT and UNCERTAIN are real UI states. Keep official facts and cancel/report actions visible. CONSISTENT does not certify the sender as legitimate.
9. Evidence is served through authenticated `/analyses/{id}/evidence`. Do not assume a public object URL. Related-report and trace access remains scoped by BE.
10. Pagination is `items`, `total`, `limit`, `offset`, with default limit 20 and maximum 100. Preserve status, request ID and error message in the API client; disable caching for sessions, money, evidence and Ops data.

## Backend handoff gates

| Gate | FE can integrate | Acceptance proof |
| --- | --- | --- |
| A: database and sessions | Demo toolbar, actor identity, recipients, orders, balances | Two independent sessions remain isolated; current Linh balance is 10,000,000 |
| B: transfers | Draft, assessment, warning continuation, holds, cancellation, refund | Normal 20,000 succeeds; verified risky 20,000 reserves; cancel restores available funds; retry does not debit twice |
| C: cases and AI | Analysis upload/results, reports, queues, reviews, evidence | Real persistence and fake-adapter automated tests; separately recorded live model/storage smoke before claiming full integration |
| D: operations and release | Exact trace, restriction decisions, notice publication, audit | Linh/An/Binh preview, Mai excluded; publication replay creates no duplicates; full API contract checks pass |

No gate is complete merely because a route exists or Swagger lists it. Backend delivery reports must name implemented operations, tests, unresolved external configuration and the commit to integrate.

## 25 November AI amendment — action for FE

Read [bounded AI investigation](ai-investigation.md) and Guardian API contract v1.1 (OpenAPI 3.1). There is no new chat, streaming or public tool-call endpoint. Keep the current upload/evidence/report screens and add result/dossier cards.

| FE area | Required change |
| --- | --- |
| Analysis result | Preserve evidence/finding/official_facts; optionally render dossier sources/findings, limitations and recommended_checks. Accept absent/null dossier in old mocks and pending/error states. |
| Source navigation | Resolve source_ids against returned dossier.sources; link only to an existing authorized resource view. Do not treat model text as a URL, HTML or executable action. |
| Ops investigate | POST existing /ops/reports/{id}/investigate; keep related_reports/citation_warnings and add dossier view. Separate review/hold/restriction/publication buttons from AI suggestions. |
| Activity | Show returned completed tool receipts after the response. Display neutral loading while waiting. No timer-generated fake progress or raw tool arguments/chain-of-thought. |
| Error/uncertainty | Keep verified facts and allowed cancel/report navigation. FAILED/TIMED_OUT do not display a definitive AI verdict. An unavailable dossier does not hide an active financial HOLD. |
| Changed input | Any image/text/order/transfer edit marks the old result stale; re-check uses a new request key. Saved result/replay does not invoke AI again. |

Customer source kinds are limited to CUSTOMER_TEXT, IMAGE_TRANSCRIPTION, TRANSFER, ORDER and REFUND for their owned context. Internal REPORT/TRACE_REFERENCE/ACCESS_EVENT sources belong only to authorized Ops results. Recommended checks are textual review suggestions. Neither a CONSISTENT finding nor an AI suggestion can bypass a server-enforced hold.

API wire names remain snake_case. No new conversation/message table or chat cache is required.

For Ops recovery, keep client_request_id keyed by sandbox/actor/root report and replay the same POST /ops/reports/{id}/investigate after network loss or PENDING, with bounded backoff. There is no GET-investigation-by-run-ID endpoint in core. Generate a fresh key only on an explicit rerun and clear prior actor keys on selection changes. Analysis can use its existing GET once the ID is known. Investigation failures have status/missing_information/dossier.limitations, not an invented top-level error_code; pre-admission 429 is a separate HTTP error. Image parsing, scoped tool execution and model loops belong to BE. All new panels are specified future work; current FE mock components have not been modified by this documentation update.
