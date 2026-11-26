# Guardian fixtures, walkthrough and three-minute video

## Fixture rules

Generate fresh UUIDs for every sandbox. Refer to symbolic names below only in fixture construction and tests. A scenario must be created from server-held fixtures; browser data cannot mark a report reviewed or set an active restriction. Dates are relative to sandbox creation so history remains in the last 30 days. All source messages, images and organizations are synthetic and visibly labeled.

| Symbol | Fixture |
| --- | --- |
| LINH, AN, BINH, MAI | Four CUSTOMER actors, each with a distinct wallet |
| OPS | One OPERATOR actor |
| CAFE | Familiar, unrestricted recipient |
| RISK_RECIPIENT | External recipient with a pre-existing verified HOLD restriction |
| NEW_RECIPIENT | External recipient without a restriction |
| PARTNER_A, PARTNER_B | Two synthetic refund-support partners |
| BATCH_A | Issued to A; references A-017, A-018, A-019 belong to Linh, An and Binh orders |
| BATCH_B | Issued to B; reference B-001 belongs to Mai's order |

Linh's five historical outgoing settled transfers are VND 100,000, 200,000, 300,000, 400,000 and 500,000 over the last ten days. Median is 300,000. CAFE appears in that history. Opening funds of VND 11,500,000 and the historical debits leave a current posted balance of VND 10,000,000. All credits/debits have matching ledger entries. Other customer accounts get sufficient opening funds for their tests.

Provide three selectable QR fixture cards. Each supplies a synthetic recipient ID and amount, validated server-side. Also allow a typed amount and a recipient selected from same-sandbox fixtures. Camera scanning is optional post-contest work. Card labels describe the scenario and never pre-populate the AI answer.

## MAIN_REFUND

Linh has order SHOP-4502, original amount/refund VND 500,000, refund APPROVED, and official return fee VND 0. The fee source is a labeled synthetic merchant confirmation issued before analysis. A screenshot reads “Chi ung giup em 20k phi thu hoi, ben kho moi tra 500k don SHOP-4502. Ma tra soat A-017.” A clean Vietnamese-accented variant must also be included.

Two independently authored near-miss reports already concern RISK_RECIPIENT. OPS has reviewed both as RESOLVED and created its HOLD restriction. They demonstrate existing evidence, not a requirement that an earlier customer lose money. This provenance must be visible before the customer transfer. Do not claim the recipient was detected from Linh's amount alone.

PARTNER_A has a READ event for BATCH_A at a time after issuance and before Linh's screenshot report. The event is a legitimate access record. A forwarding explanation remains possible. The trace reveals a candidate exposure scope, not a proven perpetrator. PARTNER_B has a READ of BATCH_B only.

### Judge walkthrough

1. Create MAIN_REFUND and select Linh. Confirm a normal VND 20,000 transfer to CAFE. Posted balance becomes 9,980,000.
2. Create VND 20,000 to RISK_RECIPIENT, assess, then attempt confirmation. The API returns RISK_HELD. Posted balance stays 9,980,000; reserved is 20,000; available is 9,960,000. The reason is an active verified recipient restriction.
3. Analyze the supplied screenshot with this draft and Linh's order. The UI shows source quotation, outgoing 20,000, approved refund 500,000 and verified fee 0. Requested action is PAY_FEE; backend finding is MISMATCH.
4. Cancel the hold. Reserved becomes zero and available becomes 9,980,000. Submit a near-miss report with the analysis ID and original draft ID. Canceled drafts remain valid report evidence.
5. Select OPS. Open that exact report. Run bounded related-report analysis. Inspect original source images/quotes rather than accepting a generated verdict.
6. Open trace. A-017 resolves to BATCH_A and A's access event. Preview recipients Linh, An and Binh. Mai is outside the batch. Mark the report RESOLVED with a reason that separates recipient evidence from source uncertainty.
7. Publish a precautionary notice to BATCH_A. Select An and see it. Select Mai and verify none exists. Repeated publication does not duplicate notices.
8. Settle Linh's pre-approved refund through the labeled demo toolbar. Its posted balance becomes 10,480,000. Repeat settlement and verify it stays 10,480,000.

## Additional live acceptance cases

| Case | Input | Required result |
| --- | --- | --- |
| Behavioral warning | New sandbox, Linh sends 8,000,000 to NEW_RECIPIENT | WARN, ANOMALOUS and recipient NONE. After current acknowledgement, succeeds once. |
| Below threshold | Linh sends 20,000 to NEW_RECIPIENT | No additional warning. Do not imply the receiver is verified safe. |
| Sparse history | An has only two historical settled outgoing payments | INSUFFICIENT_HISTORY. Still evaluate any recipient restriction. |
| Legitimate reorder | Image says old order is refunding; 20,000 pays for a new purchase | Requested action PAY_PURCHASE; no refund-fee mismatch finding. Independent recipient HOLD remains applicable if chosen. |
| Unknown fee | INSUFFICIENT_EVIDENCE has return_fee_vnd NULL | Show UNKNOWN fee and UNCERTAIN fee verification. Outgoing direction remains known. |
| No code | Suspicious message has no issued reference | NO_REFERENCE and no candidate exposure notice publication. User can still cancel/report. |
| Copied evidence | Fifteen reports include the same image | Show common-source evidence; no automatic restriction based on count. |
| New recipient report | Customer reports NEW_RECIPIENT; OPS resolves and creates WARN | Subsequent same-sandbox transfer to that recipient warns, even for 20,000. |
| Policy changed | Customer assesses ALLOW; OPS adds HOLD before confirm | Confirmation returns RISK_HELD. A cached assessment cannot bypass the decision. |
| Model unavailable | Provider times out or quota reached | Facts and cancellation remain available; finding UNCERTAIN; no invented trace link. |

## FALSE_POSITIVE

Seed a separate recipient SHOP_REAL with a mistaken active HOLD restriction, explicitly labeled as a test of correcting an earlier operational decision. A buyer disputes the restriction; the operator sees that the supporting image was forwarded and does not establish SHOP_REAL as the requested receiver. The operator revokes the restriction with a reason.

Create two held transfers to test both correction paths. On one, cancellation releases money immediately. On the other, OPS approves the individual hold to READY and the customer reconfirms. Revoking a restriction alone never sends a held transfer. Another optional test waits for the original deadline: transfer becomes EXPIRED and releases the reservation. Automated tests can configure the hold duration to one second; the production demo UI retains the displayed real deadline and never pretends time elapsed.

## Three-minute primary video

| Time | Show | Claim supported |
| --- | --- | --- |
| 0–25 s | Familiar CAFE payment succeeds; same amount to RISK_RECIPIENT is held | Recipient evidence can matter even for an ordinary amount |
| 25–65 s | Load screenshot, show quotation plus official facts, cancel and report | Evidence interpretation gives a concrete explanation; first customer in this story keeps the payment |
| 65–125 s | OPS opens report, grouped source excerpts and exact trace | Customer report becomes a verifiable internal investigation |
| 125–160 s | Notice preview and publish; An sees warning | Review can protect others within an evidenced scope |
| 160–180 s | Approved refund settles; display measured held-out AI results | Legitimate credit continues and measured AI value is explicit |

Use preloaded fixtures to save typing time while still calling the live backend and model. Record actual latency. If a full model call consumes the video budget, trim navigation and explanatory speech; the live product retains arbitrary text/image input for judging. The video duration limits the submitted recording; the judge can continue exploring the live app afterward.

## AI evidence variants and bounded investigation — 25 November

Keep the original balance/reservation/refund checkpoints and all three scenario names. The pre-existing recipient HOLD protects Linh independently of AI; explain that provenance rather than attributing the hold to the model.

For the same amount/recipient, provide three separately authored evidence variants: (1) fee demanded to receive the refund with verified fee zero; (2) a clearly separate new purchase mentioning the old refund; (3) cropped/ambiguous evidence or unknown fee. AI must return supported MISMATCH, no invented fee-scam contradiction for the purchase, and UNCERTAIN where evidence is missing. An independent recipient HOLD remains effective in all variants.

The live guide repeats the three variants on a VND 20,000 draft from Linh to NEW_RECIPIENT, linked to SHOP-4502. No restriction applies to that recipient, so the analysis result is the only warning on screen. The three-minute video keeps the RISK_RECIPIENT story; during 25–65 s the narration states that the HOLD comes from earlier reviewed reports and that the analysis result is separate. Demo images given to developers must not reuse the wording of held-out evaluation cases.

The Ops investigate action returns a completed source-linked dossier. Show a quoted claim, a corroborating or countervailing fact, the exact reference lookup if supported, and limitations. Demonstrate NO_REFERENCE/NO_MATCH as valid outcomes. A-017 maps to the stored BATCH_A and READ event; this narrows investigation scope without proving partner culpability.

The submitted recording remains at most three minutes. Use existing navigation and preloaded synthetic input to avoid typing, but run actual APIs/model; do not fake progress or hard-code verdicts. The broader live guide/evaluation covers variants that cannot fit in the recording. No chatbot or streaming is required. Candidate numbers/results are not measured findings until saved in the evaluation results.
