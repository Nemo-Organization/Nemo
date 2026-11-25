# Guardian AI and system evaluation

## AI hypothesis

Given customer evidence or an Ops root report, a bounded model runner interprets requested action/purpose, chooses permitted read-only verification tools, and produces a source-linked dossier of findings, counter-evidence, missing information and recommended checks. The backend validates sources and composes customer findings with official facts. Exact-reference tracing is deterministic support. The model never determines authorization or changes money/restrictions/notices. See [AI investigation](ai-investigation.md).

OCR alone produces a candidate transcription that must be checked against the original. A useful model must distinguish a fee demanded to receive a refund from a legitimate purchase despite overlapping words, amounts and order references. If a keyword baseline performs similarly on the held-out cases, report that outcome and reconsider the AI-value claim before submission.

## Provider contract

`ModelEvidence` in OpenAPI is the validated extraction schema. Required output is transcription, requested_action, claimed_purpose, source quotations, extracted references and missing information. The provider cannot emit a receiver warning action or a transfer state. The final customer finding is composed by server logic using permitted official facts.

| Condition | Composed finding |
| --- | --- |
| PAY_FEE linked to a refund and an authoritative fee of zero | MISMATCH |
| Claimed incoming refund conflicts with the actual outgoing transfer | MISMATCH |
| Explicit new purchase, with no identified contradiction in the provided scope | CONSISTENT |
| Missing fee, unreadable message, unclear intent, provider error, invalid result | UNCERTAIN for the unresolved question |

A fee greater than zero does not by itself verify the external receiver, the claim or the requested amount. A CONSISTENT result means the checked evidence is consistent within its scope. Display independent recipient/behavior findings alongside it. AI-extracted amounts/identifiers never overwrite immutable transfer or account fields.

Group input contains this report and up to 19 other same-sandbox reports, their permitted text/transcription excerpts and report IDs. Output contains proposed report IDs, rationale, source quotations and missing information. The related-report tool gets only bounded permitted excerpts. A separate authorized Ops lookup/access tool may return minimized records for an evidenced batch; customers never receive internal access logs. Backend exact tracing remains independently callable without AI.

## Baselines and held-out evaluation

BA owns labels and preserves 12–16 cases before prompt tuning. Keep development examples separate. Include at least these classes, with two different wordings per class where practical.

1. Fee-to-receive-refund, including slang and amounts written in words.
2. Legitimate reorder/new purchase mentioning an old refund.
3. Unknown official fee or ambiguous message.
4. Image with unclear reference digits and a cropped sender.
5. Forwarded same image appearing in different reports.
6. Related scam messages with different order numbers.
7. Similar benign messages about pickup, deliveries or corrected invoices.
8. Prompt-injection text asking to reveal logs or classify everything as safe.

Use a simple keyword baseline that flags co-occurrence of refund/return terms and fee/advance terms. Publish its exact vocabulary in the evaluation results. Grouping baseline uses exact issued references and image content hashes; it may miss paraphrases. Neither baseline changes the reviewed recipient truth labels.

| Metric | Measurement |
| --- | --- |
| Action interpretation | Correct requested_action / total labeled cases |
| Missed dangerous instructions | False negatives / labeled suspicious instructions |
| False mismatch warnings | Benign cases incorrectly reported MISMATCH / benign cases |
| Missing-evidence handling | Ambiguous cases correctly marked UNCERTAIN / ambiguous cases |
| Trace extraction | Correct reference strings, including abstention on unreadable codes |
| Grouping quality | Pairwise precision and recall of related-report proposals |
| Citation validity | Valid source IDs and supporting quotations / all proposed citations |
| Operator burden | Median case review time with evidence view, measured in a small user walkthrough |
| Runtime | p50/p95 measured model latency, errors, request count and observed provider cost |

Always show case counts with percentages. A 16-case evaluation supports a bounded demonstration, not production fraud-reduction claims. Save a reproducible JSON/CSV result artifact during implementation containing prompt/model version, input case ID, baseline result, model result, label, latency and error. Include disagreements in the slides. Never place raw real personal data in the evaluation.

## Required model failure checks

- Provider returns invalid JSON or an unsupported action → bounded validation/repair within deadline, otherwise FAILED/UNCERTAIN.
- Provider cites another sandbox's report → drop link, record citation warning, no downstream scope decision.
- Image contains commands to change policy → treat as text evidence; no policy tool exists.
- Provider times out after transaction facts are read → return those facts with TIMED_OUT.
- User replays the same analysis key → existing logical run; changed bytes/fields with same key → 409.
- No model quota remains → transfer/cancel/review operations still work; analysis request returns a quota error with clear UI recovery.

## Required application checks

Use PostgreSQL for transactional tests. SQLite does not verify the relevant row/advisory lock behavior.

| Test group | Required proof |
| --- | --- |
| Identity | Cross-sandbox IDs denied; customer cannot call operator routes; role header cannot elevate; source images scoped |
| Financial | Concurrent confirm creates one debit/credit pair; competing transfers cannot overspend; held funds are not spendable |
| Holds | Cancel/expire/reject releases once; clearance does not execute; new restriction invalidates clearance; timeout cannot send funds |
| Policy | Behavior and recipient signals work independently; stale warning acknowledgement cannot bypass a newly added HOLD |
| False positives | Revoke a mistaken restriction and complete an approved individual hold after customer confirmation |
| Trace | Code lookup and access records are real DB reads; missing code remains unresolved; forwarded-code ambiguity stays visible |
| Notices | Publish requires matched batch and reviewed report; recipients derived by server; unrelated customer excluded; replay does not duplicate |
| Refund | APPROVED refund credits once even with an active hold; second settlement unchanged |
| Hosted end-to-end | Main scenario on the deployed URL with two independent browser contexts and an actual provider response |

The three-minute video uses the main scenario. The live guide links normal/anomaly/false-positive/inconclusive scenarios so judges can verify behavior beyond the recording.

## Bounded-runner evaluation amendment

Compare three configurations on the same permitted facts: OCR/text + keyword/exact-ID baseline; LLM with fixed supplied context; bounded tool runner. Do not weaken the baseline or withhold facts just to make tools look better. Keep independent labels hidden during prompt tuning. Report whether the runner actually improves outcomes; negative/no-improvement results are valid findings.

Add per-case model/prompt/output version, actual model request count, tool count, source coverage, valid/invalid finding citations, abstention correctness and provider token cost. Count response-shape validation separately from factual correctness. A 12-16-case result is a bounded demonstration, not a production fraud-reduction or unseen-attack discovery claim.

Required cases: customer attempts Ops tool; foreign source IDs; invented quotes; valid forwarded code; too many tool calls; oversized output; SDK retry inflation; provider 429; total deadline exceeded; process death after PENDING; safe partial dossier and canonical replay. Unsupported findings are dropped with warnings; if remaining evidence cannot support a definitive verdict, require UNCERTAIN. Activity must come from executed server receipts, never model assertions.

No training/fine-tuning experiment is added to core. The behavioral median rule must be disclosed as a rule; do not present it as learned anomaly detection. The MAIN_REFUND pre-existing HOLD is also not an AI detection result.
