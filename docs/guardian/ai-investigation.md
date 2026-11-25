# Guardian bounded AI investigation

Revision: 25 November 2026. Approved direction: evidence verification with read-only function calling and exact-reference tracing. This document specifies future implementation; the current backend still exposes only health. It supplements [product requirements](product-requirements.md), [OpenAPI](openapi.yaml) and [transaction rules](data-model.md).

## Product scope and AI contribution

Guardian is a synthetic-wallet anti-fraud application with a customer evidence-check panel and an operator case-investigation panel. The customer may upload an image or paste text, optionally linked to an owned transfer and order. An operator investigates a submitted report. Both experiences return a source-linked result rather than a free-form chat session.

The AI interprets the requested action and claimed purpose, selects permitted verification steps, considers supporting and counter-evidence, and proposes findings with sources and remaining questions. Backend code authenticates, scopes queries, matches issued references exactly, computes money and enforces policy. Function calling is an implementation technique, not an originality claim or an authorization mechanism.

The core hypothesis is measurable: the same transfer can require different evidence interpretations when a message describes a refund fee, a legitimate new purchase or insufficient context. A matched reference can expose a candidate investigation scope without proving who leaked information. Evaluate both correct concerns and false suspicions.

Core excludes general chat, persisted conversations, token streaming/SSE, automatic money/policy tools, broad autonomous incident response, trained transaction-pattern models and real payment settlement. These require a separate scope decision. The 19 tables and 32 existing API operations remain the baseline.

## Customer experience

1. On the transfer screen, choose **Check suspicious message**. Reuse `ScreenshotAnalysis`; attach the current draft automatically when present. Do not require an explanation for every ordinary payment.
2. Upload PNG/JPEG/WebP <= 5 MiB, paste <= 12,000 characters, or provide both. An owned order is optional. Without a linked order, no order fee/refund is invented.
3. POST `/api/v1/analyses` using the existing multipart contract. Backend resolves identity and validates linked ownership before starting the run.
4. During the synchronous request show a neutral loading state. No fake timed investigation steps. The core API returns completed activity after processing; it does not stream live progress.
5. Display finding, original evidence, official facts and the optional dossier. Distinguish a contradiction from a proven fraud accusation. CONSISTENT is not a verified-safe sender; UNCERTAIN and provider failure remain usable results.
6. Customer chooses an existing authorized action: return to transfer, cancel an applicable draft/hold, or submit a report. AI output never bypasses a restriction. Ordinary payment remains possible without supplying evidence.

Changing text/image/order/transfer invalidates the displayed result for that form. Re-check with a new client request key. A replay of an unchanged key returns the original run/snapshot and does not re-invoke the model. The UI may load that saved result without another provider call.

## Operator experience

1. Select a report and view its original evidence and linked analysis. The operator principal is resolved independently of the customer who submitted it.
2. For an explicitly new investigation, POST `/api/v1/ops/reports/{id}/investigate` with a new client request key. Keep that key scoped to actor/sandbox/root report. After network loss or a PENDING replay, retry the same POST/key with bounded backoff; do not create another run. Core has no GET-investigation-by-run-ID endpoint. Clear saved keys on actor/sandbox changes; an explicit rerun gets a new key.
3. The model may inspect the root case, find a bounded set of related reports, look up a cited reference, and inspect access events for a batch established by that lookup.
4. Return existing related_reports plus a dossier: source-linked findings, counter-evidence/unresolved points, completed activity, recommended checks and limitations.
5. Ops opens underlying sources, reviews the report, and separately invokes the existing restriction/hold/notice endpoints. None of those mutations is an AI tool.

The separate GET `/ops/reports/{id}/trace` remains an exact backend query and works without a model. It returns MATCHED_SCOPE, NO_MATCH or NO_REFERENCE. The investigation tool calls the same scoped trace service rather than implementing another matching algorithm.

## Identity and tool registry

`InvestigationContext` contains server-resolved principal, root analysis/report, linked owned resource IDs, a run-local source catalog and deadline. Model messages and tool arguments cannot override actor_id, sandbox_id, role, DB URL, bucket or endpoint. The gateway owns the principal, checks permissions on every call and returns minimized data.

Admission preloads a bounded permitted root message/report excerpt and its source handle into the first model turn. This is authenticated initial context, not a fictional read_case tool receipt. read_case remains available when the model needs additional permitted root details. The successful trace example uses three model requests: request 1 calls lookup_reference using the initial excerpt, request 2 calls get_batch_access_events using the matched batch, request 3 produces the final output. A retry consumes one of those same requests; budget exhaustion may prevent a complete trace.

| Tool | Role and input | Allowed result | Checks |
| --- | --- | --- | --- |
| `get_customer_context` | CUSTOMER; no model-chosen resource IDs | Facts from the run's explicitly linked owned draft/order/refund, with source IDs | Linked resources must belong to the authenticated customer; missing links remain unknown; no internal trace/access data |
| `read_case` | OPERATOR; no model-chosen root report | Selected report, permitted text/transcription and linked analysis/facts | Same sandbox; no unrelated customer history or secrets |
| `search_related_reports` | OPERATOR; query <= 240 characters, limit 1-19 | Root plus at most 19 distinct same-sandbox candidate reports, with bounded excerpts and source IDs | Parameterized queries; no raw SQL; exclude foreign records; similarity is a hypothesis, not common-attacker attribution |
| `lookup_reference` | OPERATOR; code and source_id | Exact issued reference, order/batch/partner metadata permitted for review | Code must occur literally in a permitted source; no guessing unreadable digits or creating issuance records; no fuzzy reference matches |
| `get_batch_access_events` | OPERATOR; batch_id | Bounded READ/EXPORT events with timestamps and source IDs | Batch must have been established by a successful reference lookup in this run; scope checked again; legitimate access is not proof of leakage |

The CUSTOMER registry exposes only `get_customer_context`. It never advertises operator tools. An operator registry cannot be selected by a client role header. Unknown/disallowed tools are rejected without execution. Foreign or inaccessible object IDs receive a generic unavailable/not-found result that does not reveal whether the object exists.

Tool responses are schema-checked, carry server-issued source IDs, and contain no raw session tokens, complete bank identifiers, arbitrary logs or credentials. Source IDs are run-local citation handles, not credentials or arbitrary URL/file paths. Resource routes independently re-check ownership when the UI opens a source.

## Runtime bounds and state

| Control | Core default |
| --- | --- |
| Shared investigation deadline | 20 seconds, including model requests, tool work and any retry |
| Model requests | At most 3 per logical run, including retry/final formatting |
| Tool executions | At most 4 per logical run, counted individually even if proposed in parallel |
| Provider transient retries | At most 1, only within the same remaining deadline and request budget |
| Related reports | At most 20 including the root, fewer when context limits require |
| Serialized result size | At most 6,000 UTF-8 bytes per tool result; at most 16,000 bytes across tool results |
| Final findings | At most 8; every retained finding cites at least one verified source |
| Recommended checks | At most 5 |
| Displayed tool activity | At most 4 completed receipts; no raw arguments or internal reasoning |
| Model response output cap | Start with 1,600 tokens per request; measure truncation/quality before changing |
| Logical runs per sandbox/hour | 20 customer analyses and 5 operator investigations |
| Deployment-wide provider requests/day | 300 initially, including retries and every request in a tool loop |

Proposed new settings are `AI_MAX_MODEL_REQUESTS=3`, `AI_MAX_TOOL_CALLS=4`, `AI_MAX_OUTPUT_TOKENS=1600`. They are not implemented in the current Settings class. Existing GROUP_SANDBOX_HOURLY_LIMIT is retained for compatibility and now budgets the operator investigation endpoint, including its related-report work.

Persist PENDING and canonical input digest in a short transaction. Release the transaction before model/object-store network calls. Tool queries use short-lived scoped DB sessions, query timeouts and no money/account locks. Provider requests, tool receipts and outcomes are finalized in short transactions; do not hold one transaction across the agent loop.

Count each outbound model attempt before dispatch under a deployment-wide quota lock and append a sanitized `AI_MODEL_REQUEST_RESERVED` audit event. Hourly logical-run limits and actual provider-request limits are different counters. A request reserved before a process crash remains conservatively consumed; do not silently retry a PENDING run under the same client key. Configuring the SDK with automatic unbounded retries is prohibited.

If the model requests more work than the budget permits, do not invent a completed finding. Return a persisted FAILED/UNCERTAIN run with error_code `AI_BUDGET_EXCEEDED` and permitted partial sources/activity. Other safe codes include `MODEL_UNAVAILABLE`, `MODEL_RATE_LIMITED`, `MODEL_INVALID_OUTPUT`, `MODEL_TIMEOUT` and `TOOL_UNAVAILABLE`. Use TIMED_OUT when the total deadline expires. Already verified facts and deterministic transfer/cancel/trace remain available. No partial result can claim SUCCEEDED.

Wire distinction: Analysis exposes finding and nullable error_code; Investigation has no top-level error_code/finding. For a failed Ops run, expose its existing status, safe missing_information and optional dossier.limitations; persist the execution code internally. Reject before admission with HTTP 429 when logical/actual-call quota is unavailable. If an admitted run loses the remaining global allowance before another dispatch, finalize FAILED without another reservation/call and replay that stored outcome. Provider 429 after admission is MODEL_RATE_LIMITED internally, not a successful response or unlimited retry. All SDK retries are disabled or explicitly accounted for by the runner.

Do not expose raw provider exceptions or model chain-of-thought. `activity` is a server-generated record of completed operations, not private reasoning and not a trusted copy of a model's claimed actions.

## Dossier and source validation

Guardian API contract v1.1 (OpenAPI 3.1) adds optional nullable `dossier` to Analysis and Investigation. All existing fields, operation IDs, request bodies and endpoints remain. New implementations should include dossier=null when none is available. FE must also accept an omitted dossier while integrating legacy fixtures.

| Schema | Required fields and meaning |
| --- | --- |
| `InvestigationSource` | id, kind, resource_id (nullable UUID), label, excerpt, observed_at (nullable time). A permitted source or canonical fact snapshot, never an unrestricted retrieval instruction. |
| `InvestigationFinding` | id, statement, relation, source_ids. relation is SUPPORTS_CONCERN, COUNTERS_CONCERN or UNRESOLVED. At least one retained source ID is required. |
| `InvestigationActivity` | step, tool, status, summary. Tool is one of the five allowlisted names; status is SUCCEEDED, NOT_FOUND, DENIED or UNAVAILABLE. Summary is generated/redacted by the server. |
| `InvestigationDossier` | version, sources, findings, activity, recommended_checks, limitations, citation_warnings. version is guardian-dossier-v1. |

Source kinds: CUSTOMER_TEXT, IMAGE_TRANSCRIPTION, TRANSFER, ORDER, REFUND, REPORT, TRACE_REFERENCE, ACCESS_EVENT. Customers can receive only CUSTOMER_TEXT, IMAGE_TRANSCRIPTION, TRANSFER, ORDER and REFUND for their own context. TRANSFER sources describe an explicitly linked owned instruction snapshot; the gateway verifies sender ownership and must not disguise a transfer as an ORDER source. Ops may receive the other types within the root sandbox. A source ID supplied by the model must have been issued to that run. A new or guessed ID is dropped with citation_warnings. Public source projection preserves safe masking and scopes; persistence of internal execution metadata is not a permission to return it.

Require literal quotes from customer text/report excerpts and exact canonical values for official facts.

### Private per-claim support contract

The provider proposes `FindingProposal(id, statement, relation, supports)`, where supports is a nonempty list of typed `QuoteSupport(source_id, exact_quote)` or `FactSupport(source_id, whitelisted_field, typed_value)`. QuoteSupport applies to permitted message/transcription/report snapshots and must match a literal span. FactSupport applies to a server-issued structured fact snapshot; the field is allowlisted for that tool and its JSON scalar value must equal the canonical value with the correct type. Source IDs alone are insufficient claim support. Contract 1.2 adds a signal to FindingProposal and extends the TRANSFER allowlist; see [Contract 1.2 amendment](#contract-12-amendment).

The gateway owns the source catalog and canonical fact maps. Model output cannot create official sources, timestamps or completed tool receipts. Validate private support bindings before projection, drop unsupported proposals, and derive public source_ids from retained supports. Compose/check decisive amount/direction/fee comparisons server-side. Persist bounded validated support bindings in private _execution for evaluation, without chain-of-thought. Public InvestigationFinding retains statement/relation/source_ids.

Literal quote/value checks establish a source binding, not semantic entailment of arbitrary prose. Semantic accuracy still requires evaluation and human review; overclaims remain unresolved or are dropped. The fee verdict example must quote the clause linking payment to receiving the refund; an unrelated linked refund cannot establish that purpose by itself.

### Image transcription caveat

An image transcription remains model-derived and can be wrong; identify its source kind and show the original for review. Matching a model-generated transcription alone does not independently verify OCR accuracy. A proposed code must be visible in the permitted textual evidence before lookup; unclear codes remain unresolved.

Reject source references to another run or actor. Drop any finding with unsupported source IDs/quotes and record the warning. If necessary evidence for a verdict is invalid or absent, the overall customer finding must remain UNCERTAIN; do not silently retain a definitive verdict after its only support was removed.

Customer finding remains gated by verified facts: PAY_FEE tied to a refund with authoritative fee zero can support MISMATCH. Missing fee remains unknown; an explicit new purchase must not become a fee scam merely because the message mentions a refund. Contract 1.2 makes composition follow the ordered rules in [evaluation](evaluation.md#contract-12-amendment) and also reads additional_actions. A model's recommendation never becomes a transfer state, restriction, publication or proof of a perpetrator.

## Exact tracing and exposure scope

1. Use supported extracted references from the submitted evidence; retain source provenance.
2. Query trace_references -> data_batches -> partner records using exact code and sandbox.
3. Query actual partner_access_events for that matched batch.
4. Derive distinct candidate customers through trace_references -> orders -> customer_actor_id.
5. Return references, access events and explicit limitations. A copied/forwarded image and a legitimate partner read remain plausible explanations.
6. Preview notices for a matched batch; publication additionally requires a RESOLVED source report and operator approval. An unrelated customer is excluded. No automatic partner suspension or arbitrary recipient list.

This traces information provenance within the application. It does not follow real funds across banks, infer private external logs, or detect an unknown intrusion from no telemetry. Demo issuance/access records are synthetic and visibly disclosed; querying/enforcement must be real when implemented.

## Persistence without new tables

Keep the 19-table, 161-column baseline unchanged. Use existing ai_runs kind IMAGE_ANALYSIS/TEXT_ANALYSIS for customer runs and REPORT_GROUPING for the bounded operator investigation (the historical enum name is retained). Reports link the source analysis; operator grouping runs are linked to a root report in their canonical input snapshot.

`ai_runs.output` is a versioned JSON envelope: output_version, public_result, dossier and `_execution`. public_result contains the existing Analysis/Investigation payload without recursive storage of itself. dossier contains the validated public dossier. `_execution` holds bounded request/tool counts, run-local source receipts and usage metadata for internal recovery/evaluation; never serialize it wholesale to FE. Store no API key, cookie, raw authorization header or chain-of-thought. Provider/model/prompt_version use existing columns; status/error/timestamps use existing lifecycle columns.

input_digest remains SHA-256 of canonical client input and original image bytes; it does not include later live DB/model outputs. input_text stores the canonical permitted text/root-report and source snapshot, not an unconstrained query. Replays re-use the original sources/decision rather than re-evaluating changing data. A new intent/evidence investigation uses a new client request key.

## Provider and hosting decision

Implement one `ReasoningModel` adapter boundary and one bounded runner first. Candidate Groq Qwen `qwen/qwen3.8-27b` supports image/text/tool use but is Preview; verify account availability, quality and rate limits before release. Gemini through google-genai is a configurable alternative if selected and authorized. GPT-OSS 120B on Groq is text-only and requires a separately validated image-extraction step for image input; never send it an unsupported image payload or hide OCR uncertainty.

Provider selection, enabling billing and purchasing credits remain team decisions. No live key/model is established by these docs. API credits, coding-agent credits and GCP promotional credits are distinct. Prefer a measured small API budget over building a rotation system solely to evade free limits. Core has no automatic provider rotation; preserve an adapter so an explicitly configured replacement does not change FE payloads. [Groq models](https://console.groq.com/docs/models) / [limits](https://console.groq.com/docs/rate-limits) / [Gemini limits](https://aistudio.google.com/docs/rate-limits).

Groq Structured Outputs currently cannot be combined with tool use in the same request. Use tool-call requests and a separate no-tools schema-finalization request when needed, all within the three-request/20-second budget. Pydantic validates shape; source checks validate support. JSON schema conformance never proves truth. [Groq structured output](https://console.groq.com/docs/structured-outputs).

Evidence storage target is a private Neon Object Storage bucket via an S3 adapter (boto3, endpoint, region, scoped access keys and path-style addressing). Cloud Run hosts FastAPI/Next; PostgreSQL stores rows and object keys. Never expose the bucket credentials or make evidence public to let a model fetch it; send permitted image bytes through the configured adapter. [Neon S3 compatibility](https://neon.com/docs/storage/s3-compatibility).

## Frontend contract and states

Keep existing endpoints and components. Extend ScreenshotAnalysis with source-linked result cards and optional collapsed completed activity. Add an **Investigate with AI** action and dossier view to operator report detail. Explain a finding separately from the deterministic transaction status/restriction. Recommended checks are plain text suggestions, not executable model-generated buttons or URLs.

Required states: idle, submitting, pending, succeeded, inconclusive, failed, timed_out, quota_rejected. Unknown/error paths keep official facts and allowed cancel/report navigation visible. A loaded report or available balance is not replaced with fabricated optimistic AI state. Read dossier defensively when absent/null; a successful run may validly have no findings and explain missing information. Render model text as text, never HTML.

## Required proof before claiming AI value

- Preserve 12-16 independently labeled held-out cases: fee scam, legitimate purchase, missing facts, unreadable/cropped image, no/unknown code, forwarded evidence, misleading related reports and prompt injection.
- Compare OCR/text + keyword + exact-ID baseline against LLM with fixed supplied context and against the bounded tool runner on the same permitted facts. Report errors and token/call cost; tool use is not automatically better.
- Test a customer attempting Ops tools/foreign IDs; no private data returned. Test invented sources, literal quote mismatch, huge tool outputs, repeated same tool, invalid arguments, budget exhaustion, rate limit and process death.
- Trace A-017 -> BATCH_A with actual stored READ record and three candidate customers; Mai excluded. Test NO_REFERENCE and NO_MATCH and preserve forwarding uncertainty.
- Prove no AI tool can transfer/cancel/restrict/publish or alter issued records. All mutations remain separately authenticated API commands.
- Live-smoke the actual model and private storage with synthetic data. A fake adapter test is not evidence that provider quota, Vietnamese OCR or deployment works.

## Contract 1.2 amendment

Applied 25 November 2026. Earlier sections remain as the 1.1 record; where they conflict, this section applies. The 1.1 contract file is archived in [archive](archive/README.md).

Contract v1.2 adds two optional fields and no endpoint, request body or table: `ModelEvidence.additional_actions` and a nullable `InvestigationFinding.signal` from the `InvestigationSignal` catalog. New implementations emit an empty array and null respectively when nothing applies; FE accepts their absence. Action definitions, precedence, finding rules and the signal catalog are in [evaluation](evaluation.md#contract-12-amendment).

The provider now proposes `FindingProposal(id, statement, relation, signal, supports)`, where signal is an `InvestigationSignal` code or null. A proposal with a non-null signal must include at least one QuoteSupport from CUSTOMER_TEXT, IMAGE_TRANSCRIPTION or REPORT text. PAYEE_DIFFERS_FROM_SENDER also requires a FactSupport for `recipient_display_name` from the linked TRANSFER snapshot. A proposal missing the required support is dropped with a citation warning. Finding composition never reads signals.

`get_customer_context` includes the linked draft recipient's verified display name in the TRANSFER snapshot, and `recipient_display_name` joins that snapshot's FactSupport allowlist.

Customer finding composition reads PAY_FEE from requested_action or additional_actions. Every case outside the two MISMATCH rules and the one CONSISTENT rule is UNCERTAIN.

UI: render finding signals as neutral labels, never green/check styling. When requested_action or additional_actions contains SHARE_SECRET or CONFIRM_LOGIN, show a fixed localized safety message; it does not change the finding or transfer state.

Additional required proof:

- A fee demand combined with an OTP request keeps MISMATCH through additional_actions and shows the secret warning.
- A signal proposal without its required quote/fact support is dropped with a warning.

## Contract 1.3 amendment

Applied 26 November 2026. Earlier sections remain as the record; where they conflict, this section applies. The 1.2 contract file is archived in [archive](archive/README.md).

Contract v1.3 adds optional `ModelEvidence.claimed_transfer_direction` (INCOMING, OUTGOING or UNKNOWN) and no endpoint, request body or table. The provider reports what the message claims the requested transfer does for the customer. Finding rule 1 reads this claim, requires a validated quote for it, and compares it with the linked transfer's actual direction from the TRANSFER snapshot. Definitions are in [evaluation](evaluation.md#contract-13-amendment).
