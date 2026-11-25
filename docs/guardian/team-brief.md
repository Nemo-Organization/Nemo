# Guardian team brief

Updated 25 November 2026. Share this page first; follow the linked specifications for implementation. Status: agreed documentation direction, not completed business APIs. Backend currently exposes health; FE uses mock business data.

## What we are building

Guardian is an anti-fraud web application inside a synthetic wallet experience. Customers can transfer test money, receive risk interventions, check suspicious messages/images and report evidence. Operators investigate reports, review held transfers, apply reviewed recipient restrictions and send scoped precautionary notices.

The primary contest theme is Anti-Fraud. Exact-reference/access-record tracing supports security investigation. We are not claiming to detect every scam, operate a real-money wallet, or prove a partner leaked data from a single matched reference.

## Two screens, one connected case

| Customer | Operator |
| --- | --- |
| Balance, recipient/amount, transfer status and deadline | Report and held-transfer queues |
| Optional image/text check linked to the current draft/order | Investigate one report with AI |
| AI result with evidence, official facts, uncertainty and source-linked dossier | Review findings, counter-evidence, related reports and exact trace |
| Cancel an applicable payment or submit report | Separately review/approve/reject, restrict/revoke, preview/publish notices |

No general chatbot or token streaming is needed. Input evidence is optional for ordinary transfers. Loading indicators do not invent progress. Every customer/Ops action goes through server authentication and permission checks.

## What AI contributes

AI interprets what someone is asking the customer to do, chooses permitted verification steps and returns source-linked findings. It should distinguish a demanded refund fee, a legitimate new purchase and incomplete evidence even when amounts/words overlap. It can propose related reports and further checks; invalid citations are removed and uncertainty remains visible.

Function calls are backend-controlled read-only functions. Customer tools see only explicitly linked owned facts. Ops tools may read the selected case, search bounded related reports, look up an evidenced code exactly and retrieve access events for a matched batch. No tool can transfer/cancel money, change policy, publish a notice, execute SQL or run shell commands.

Default run bounds: 20 seconds shared, at most three model requests and four tool executions. SDK retries/final formatting count inside the model budget. A provider outage leaves deterministic payment controls available. Sources and activity are validated/redacted by the backend; schema-valid JSON alone does not prove correctness.

## What the wallet actually means

Money, bank identifiers, people, merchants and access history are synthetic fixtures. The future backend must actually persist state, lock accounts, reserve/release money, enforce retries and record ledger/audit entries. A UI animation is not a completed transaction. Customers choose seeded recipients; arbitrary real-bank account verification and signup/KYC are not in scope.

Posted balance, reserved balance and available balance are distinct. Operator approval changes a held transfer to READY, not SUCCEEDED. Customer reconfirmation is required. The original hold deadline remains. Independent active restrictions still apply after an AI result.

## Main demo and honest attribution

1. Linh makes a normal 20,000 payment successfully.
2. Another 20,000 transfer to a recipient with a pre-existing reviewed HOLD reserves funds. This intervention is policy-based, not a newly discovered AI fraud.
3. Linh checks a suspicious message. AI interprets the request and verifies available official context. Customer sees a specific contradiction or uncertainty, then can cancel and report.
4. Ops investigates that report. Supported code A-017 can map to BATCH_A and a real stored READ event. Show source links and forwarding/access limitations.
5. Ops reviews the report and previews notices for Linh, An and Binh. Mai is outside scope. Publishing twice creates no duplicate notice.
6. The approved 500,000 refund settles once; legitimate incoming credit continues.

Show AI value using changed-evidence variants and held-out evaluation. A pre-existing HOLD, an exact SQL match or function calling alone is not proof of AI novelty. No case requires an earlier victim to lose money.

## What changed in this revision

| Area | Change |
| --- | --- |
| Requirements | Bounded model-selected read-only verification, source validation, source-linked dossier, safe failure and run budgets |
| API | Version 1.1; all 32 operations/28 paths and request bodies retained. Analysis and Investigation gain optional nullable dossier; related_reports and existing fields remain |
| DB | Still 19 tables/161 columns. Dossier and private execution metadata use existing ai_runs.output; physical keys/types remain unchanged |
| Tracing | Already in scope; now explicitly reused by permitted investigation tools, with exact-match and no-attribution limitations |
| Storage | Private Neon Object Storage via S3 adapter, alongside Neon Postgres; Cloud Run still hosts the app |
| Provider | Configurable adapter. Groq Qwen is an initial candidate, Gemini an alternative; selection/billing/live access still require team configuration and measurement |
| FE | Keep existing screens; map wire DTOs, add result/source cards and investigate action. No chat pages or live activity stream |

## Scope boundary

Core: demo identity/isolation, synthetic ledger/transfers/refunds, rule-based amount anomaly warning, reviewed recipient WARN/HOLD, cancellation/expiry/READY reconfirmation, AI evidence verification, bounded investigation, exact trace, targeted notices and audit.

Deferred: general chat/history, SSE, automatic provider rotation, training/fine-tuning/graph ML, real bank transfer/settlement, native chat interception, automatic partner suspension and broad security operations. Provider API keys remain server-side; buying an API is not training a model.

## Ownership and immediate sequence

| Owner | Work |
| --- | --- |
| Backend dev | Schema/migration, sessions, DTOs, ledger/risk/holds, tool gateway, exact trace, Ops mutations, storage/runtime wiring |
| Frontend dev | Contract-shaped mock fixtures, DTO adapters, current-actor state, customer/Ops panels, source navigation, structured errors; coordinate one editor for any shared AI backend module |
| BA | Independently labeled legitimate/suspicious/inconclusive evidence, original/forwarded-source checks, source-grounded copy, evaluation and walkthrough |

Implementation sequence: (A) DB/session/discovery; (B) money lifecycle; (C) evidence/model/tools; (D) Ops/trace/notices; (E) hosted integration/evaluation. Test model access and a small evidence set early alongside foundation work. Do not postpone that uncertainty until all endpoints are built.

Deadline is 3 December 2026, 23:59:59 Asia/Bangkok. The detailed 15-task plan describes work, not a guarantee of completion within the remaining calendar. Re-estimate each gate, protect money/authorization tests, and reduce optional grouping/polish before adding new scope.

## Documents to use

- [Requirements](product-requirements.md) and [AI investigation](ai-investigation.md): product behavior and tool boundaries.
- [OpenAPI](openapi.yaml) and [API examples](api-examples.md): wire agreement.
- [FE handoff](frontend-integration-notes.md): mock differences and panel behavior.
- [Database specification](database-specification.md), [schema](schema.sql) and [transaction rules](data-model.md): physical fields/keys and invariants.
- [Architecture](architecture.md), [backend plan](../superpowers/plans/2026-11-24-guardian-backend-api.md) and [agent prompts](agent-prompts.md): implementation.
- [Evaluation](evaluation.md), [scenarios](scenarios.md), [cloud runbook](cloud-deployment.md), [validation record](validation.md): evidence and release gates.
