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

Contract 1.2 replaces this table with ordered rules and adds requested_action definitions; see [Contract 1.2 amendment](#contract-12-amendment). The table above is kept as the 1.1 record.

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

Use a simple keyword baseline that flags co-occurrence of refund/return terms and fee/advance terms. Publish its exact vocabulary in the evaluation results. Contract 1.2 fixes that vocabulary and its decision order; see [Contract 1.2 amendment](#contract-12-amendment). Grouping baseline uses exact issued references and image content hashes; it may miss paraphrases. Neither baseline changes the reviewed recipient truth labels.

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

## Contract 1.2 amendment

Applied 25 November 2026. This section supersedes the composition table in Provider contract and fixes the keyword baseline. Earlier text above remains as the 1.1 record. Contract 1.2 adds optional `ModelEvidence.additional_actions` and a nullable `InvestigationFinding.signal`.

### Requested action definitions

| Code | Assign when the message asks the customer to |
| --- | --- |
| PAY_FEE | Pay a fee, deposit or advance as a condition for receiving money or a benefit: a refund, loan disbursement, prize, or unlocking an order/account |
| PAY_PURCHASE | Pay for goods or services the customer is buying, including the shipping fee or deposit of that new order |
| CONFIRM_TRANSFER | Send money for a purpose that is neither a purchase nor a fee-to-receive, for example returning a "mistaken" transfer or moving money to a "safe account" |
| SHARE_SECRET | Provide an OTP, password, PIN, CVV or verification code |
| CONFIRM_LOGIN | Approve a new login or device |
| OTHER | Do something readable that is outside the codes above, including messages that only inform, such as a delivery time |
| UNKNOWN | The request cannot be read or understood |

A shipping fee for a new order is PAY_PURCHASE, not PAY_FEE. When a message makes several requests, requested_action takes the first applicable code in this order: SHARE_SECRET, CONFIRM_LOGIN, PAY_FEE, CONFIRM_TRANSFER, PAY_PURCHASE, OTHER. The remaining concrete requests go to additional_actions: at most three, no duplicates, never UNKNOWN and never the primary code.

### Finding composition

Apply the rules in order. The first matching rule decides.

| Order | Condition | Composed finding |
| --- | --- | --- |
| 1 | The message says the transfer it asks for will bring money to the customer, while the linked transfer is OUTGOING | MISMATCH |
| 2 | PAY_FEE is in requested_action or additional_actions, a supported quote ties the payment to receiving a refund, and the linked order's authoritative return_fee_vnd is 0 | MISMATCH |
| 3 | requested_action is PAY_PURCHASE for an explicit new purchase, with no identified contradiction in the provided scope | CONSISTENT |
| 4 | Every other case | UNCERTAIN for the unresolved question |

Rule 1 does not apply when a message mentions an earlier refund to the customer while asking for a separate new payment. Rule 4 covers a missing, unknown or positive fee; no linked order; unreadable or unclear evidence; SHARE_SECRET, CONFIRM_LOGIN, CONFIRM_TRANSFER, OTHER and UNKNOWN without a rule 1 contradiction; provider errors and invalid results.

Open item before backend Task 9: ModelEvidence has no structured field that carries the rule 1 claim that the requested transfer is incoming. Decide how the provider expresses that claim, for example a typed claimed-direction field, before implementing rule 1.

When requested_action or additional_actions contains SHARE_SECRET or CONFIRM_LOGIN, the customer UI shows a fixed localized safety message. It is display copy keyed on the validated action, not a finding, transfer state or restriction. Because rule 2 also reads additional_actions, adding a secret request to a fee demand does not weaken a supported MISMATCH.

Prompt-injection text is evidence. Label such a case as if the injected instruction were absent. It passes when the composed finding is unchanged and no internal data is disclosed.

### Message signals

A signal tags a message-level warning sign that requested_action does not already express.

| Signal | Tag when the message | Do not tag when |
| --- | --- | --- |
| CLAIMS_OFFICIAL_ROLE | Claims to be staff of a marketplace, warehouse, shop, bank or government body | It only names the shop the customer bought from, without claiming to act for it |
| URGENCY_PRESSURE | Sets an urgent deadline or threatens loss, an account lock or a cancelled refund unless the customer acts now | It states an ordinary timeframe, such as delivery within three days |
| OFF_PLATFORM_CHANNEL | Moves the conversation to Zalo, Telegram, a phone number, or a link/app outside the official channel | It points to the official app the customer already uses |
| PAYEE_DIFFERS_FROM_SENDER | Claims to represent an organization but asks for payment to an account held by a different individual | A small shop owner introduces themselves and receives payment in their own name |
| USES_ORDER_DETAILS | Cites an order number, trace code or exact amount to appear legitimate | It refers to "your order" without specifics |
| DISCOURAGES_VERIFICATION | Tells the customer not to call support, not to tell the shop, to keep it secret, or to "do it through me" | It only reports a delay, such as busy support lines |
| OTHER | Shows a clear warning sign outside this catalog; the finding statement names it | Not applicable |

- A tagged finding needs at least one literal quote from CUSTOMER_TEXT, IMAGE_TRANSCRIPTION or REPORT text. PAYEE_DIFFERS_FROM_SENDER also needs a FactSupport for the linked transfer's recipient_display_name.
- signal is null for findings about official or system data, such as a trace match.
- Uncertainty uses relation UNRESOLVED, so the catalog has no UNKNOWN code. USES_ORDER_DETAILS is neutral by itself because legitimate shops also cite orders; it is usually UNRESOLVED.
- Signals never change the composed finding, a transfer state or a restriction.
- A quote binding does not prove the tag is correct. Signal accuracy is evaluated against BA labels.
- The UI renders signals neutrally. No green/check styling. An absent signal is not counter-evidence or a safety indication.

### Keyword baseline

The baseline reads the same text the model interprets: the customer text, or the model's image transcription for image cases. This isolates interpretation. The baseline therefore inherits transcription errors, including on unreadable codes.

Normalize to lowercase, remove Vietnamese diacritics (đ becomes d), split on whitespace and punctuation, and match whole syllable sequences. Never match raw substrings.

| Group | Terms |
| --- | --- |
| A: refund/return | hoan tien, hoan lai, hoan tra, hoan don, tien hoan, don hoan, tra hang, tra lai, thu hoi, refund |
| B: fee/advance/deposit | phi, le phi, ung, ung truoc, ung trc, dat coc, tien coc, ky quy, chuyen truoc, chuyen trc, ck truoc, ck trc, fee, deposit |
| C: new purchase | don moi, dat hang, dat mua, mua them, mua moi, thanh toan don |
| D: customer receives money | nhan tien, nhan lai tien, nhan hoan, tien ve, chuyen ve, hoan ve |

Baseline finding, first match wins:

1. D matches and the linked transfer is OUTGOING: MISMATCH.
2. A and B both match: MISMATCH when the linked order's return_fee_vnd is 0, otherwise UNCERTAIN.
3. C matches: CONSISTENT.
4. Otherwise: UNCERTAIN.

Baseline requested_action is PAY_FEE when A and B match, otherwise PAY_PURCHASE when C matches, otherwise UNKNOWN. Baseline references are case-insensitive matches of `\b[A-Z]-\d{3}\b` in the unnormalized input, reported in uppercase.

The lists were drafted before any held-out case existed. BA may add terms, but not remove them, before authoring held-out cases. The lists are then frozen and published verbatim with the results.

### Labels, metrics and checks

Each held-out case label records requested_action, additional_actions, the expected finding, the expected reference string or abstention, the expected trace outcome, related reports, expected signals and the permissible customer/operator outcome. Use N/A where a flow does not apply. Keep held-out cases and labels outside the repository until prompts are frozen.

| Metric | Measurement |
| --- | --- |
| Additional actions | Exact additional_actions set matches / labeled cases |
| Signal tagging | Per signal: correct, missed and extra tags against BA labels, reported as counts |

Additional required checks:

- Message demands a refund fee and an OTP, with linked fee 0: requested_action SHARE_SECRET, PAY_FEE in additional_actions, MISMATCH retained and the fixed secret warning shown.
- Legitimate new purchase mentions an earlier refund to the customer: rule 1 does not fire and no MISMATCH comes from that mention.
