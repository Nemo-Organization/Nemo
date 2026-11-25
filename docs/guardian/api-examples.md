# Guardian API integration examples

All paths below are relative to the public frontend origin. The browser uses same-origin credentials. UUIDs are returned from the current sandbox; samples are illustrative. Mutation headers contain the CSRF token returned for the appropriate cookie. Never store provider credentials in the frontend. OpenAPI revision 1.1 adds optional nullable dossier responses; all request bodies and endpoints remain unchanged. These examples specify future behavior, not currently implemented business endpoints.

## Start and select an actor

`POST /api/v1/demo/sessions`

```json
{"scenario": "MAIN_REFUND"}
```

The 201 response contains sandbox_id, actors, current_actor, controller_csrf_token and actor_csrf_token. Set-Cookie establishes the opaque guardian_demo and guardian_session credentials. Obtain sender account from `GET /api/v1/me`, recipients from `GET /api/v1/recipients`, and official refund facts from `GET /api/v1/orders`.

For `POST /api/v1/demo/actors/select`, send `{"actor_id": "<returned UUID>"}` and controller CSRF. Update the actor CSRF token and invalidate cached actor data from the returned Me response.

## Draft and assess

`POST /api/v1/transfers` with actor CSRF returns 201.

```json
{
  "client_request_id": "148fd5b9-f93e-4cbb-9aba-e9a0066c780a",
  "sender_account_id": "819f08b2-fe70-4504-8a9a-6f2099b6c729",
  "recipient_account_id": "6a269b62-19df-4512-954a-2c65c0e311f8",
  "amount_vnd": 20000
}
```

Replay identical data and key returns 200 with replayed true. Reusing the key for 30000 returns 409. A new draft changes no balance.

`POST /api/v1/transfers/<id>/assess` returns a RiskAssessment. Illustrative recipient-only result follows.

```json
{
  "id": "44ac27d0-af42-43aa-9053-5eaa5d1bf03a",
  "transfer_id": "49d4bcd6-9914-4219-b260-35220b633d22",
  "decision": "HOLD",
  "behavior_signal": "NORMAL",
  "recipient_signal": "HOLD",
  "reasons": [{
    "code": "RECIPIENT_HOLD",
    "message": "This recipient requires additional review based on verified reports.",
    "restriction_id": "9264b339-339f-4938-b7e9-06c50b912f05"
  }],
  "policy_version": "guardian-rules-v1",
  "assessed_at": "2026-11-23T03:00:00Z",
  "expires_at": "2026-11-23T03:05:00Z"
}
```

## Confirm, hold and cancel

`POST /api/v1/transfers/<id>/confirm` with `{}` re-evaluates risk. For HOLD, 200 returns a Transfer with status RISK_HELD, reserved_amount_vnd 20000 and the actual server deadline. The customer screen refreshes Me to display the new available balance. A 200 response here does not always mean payment succeeded; inspect status.

For WARN, obtain the current assessment and send its ID.

```json
{"acknowledged_assessment_id": "44ac27d0-af42-43aa-9053-5eaa5d1bf03a"}
```

A stale warning acknowledgement returns the structured 409 response below. Show the fresh reasons before allowing another acknowledgement.

```json
{
  "error": {
    "code": "ACKNOWLEDGEMENT_REQUIRED",
    "message": "Review the current assessment before continuing.",
    "request_id": "request-7e21"
  }
}
```

The actual conflict includes `error.assessment` when there is a new assessment and can include `error.current_transfer` when state changed. If an active HOLD now applies, return the held Transfer instead of accepting the old acknowledgement. `POST /transfers/<id>/cancel` releases reserved funds and returns CANCELED. Refresh Me.

## Analyze and report

`POST /api/v1/analyses` uses multipart/form-data with client_request_id, transfer_id, order_id and image and/or text. Let the browser generate the multipart Content-Type boundary. The analysis ID can be polled using `GET /analyses/<id>` if a replay returns PENDING. Retrieve original image only through the authorized evidence endpoint.

The Analysis response has model evidence, finding and official_facts as separate fields. An extract might be:

```json
{
  "transcription": "Chi ung giup em 20k phi thu hoi, ben kho moi tra 500k don SHOP-4502. Ma tra soat A-017.",
  "requested_action": "PAY_FEE",
  "claimed_purpose": "Receive the pending order refund",
  "quotes": [{
    "source": "IMAGE_TRANSCRIPTION",
    "text": "ung giup em 20k phi thu hoi, ben kho moi tra 500k don SHOP-4502",
    "report_id": null
  }],
  "extracted_references": ["A-017"],
  "missing_information": []
}
```

Complete synthetic response fixtures, including the 1.1 dossier, are available for FE mocks:

- [Analysis with customer-safe sources](fixtures/analysis-dossier.json): ModelEvidence, official facts, one completed get_customer_context receipt and a source-linked contradiction. No internal batch/access sources.
- [Ops investigation with trace evidence](fixtures/investigation-dossier.json): existing related_reports fields plus a dossier with exact reference/access records, unresolved attribution and completed activity. Empty related_reports is valid; do not invent matches to fill a card.

Resolve each finding's source_ids against dossier.sources. Render source text safely and open resources only through existing authorized routes; a source ID is not an access credential. No public tool-execution route is added. No SSE or live activity endpoint is implied. Accept absent/null dossier in legacy fixtures and pending/error responses. On a failure, partial sources/activity may be shown without presenting a successful definitive verdict. The Ops top-level citation_warnings must include the union of grouping and dossier-validation warnings.

`POST /api/v1/reports` creates the review item. The same recipient must match the linked transfer.

```json
{
  "client_request_id": "9f146a47-26e4-4aa5-bd1b-9a0c65c8b0e2",
  "recipient_account_id": "6a269b62-19df-4512-954a-2c65c0e311f8",
  "transfer_id": "49d4bcd6-9914-4219-b260-35220b633d22",
  "analysis_id": "db2ebcf6-290b-4cfc-8521-efbffaf69ce7",
  "narrative": "I canceled after being asked to advance a fee to receive my refund."
}
```

## Operator actions

Select OPS using the demo controller first. All following actions use the new actor cookie/CSRF.

1. `GET /api/v1/ops/reports/<id>` returns report, analysis and trace.
2. `POST /ops/reports/<id>/investigate` with a new client_request_id starts bounded read-only investigation: related reports plus an optional validated dossier. Internal tool calls are not FE endpoints.
3. `GET /ops/reports/<id>/trace` performs exact lookup and returns MATCHED_SCOPE, NO_MATCH or NO_REFERENCE.
4. `PATCH /ops/reports/<id>` with status RESOLVED and a reason records review.
5. `GET /ops/reports/<id>/notice-preview?batch_id=<id>` lists the server-derived scope.
6. `POST /ops/reports/<id>/notices` with batch_id, title and body publishes the reviewed notice.

To create a recipient decision, `POST /ops/recipient-restrictions` requires recipient_account_id, action WARN or HOLD, reason, at least one evidence_report_id and expires_at within sandbox lifetime. Existing effective restriction returns 409. Revoke using `/ops/recipient-restrictions/<id>/revoke` with a reason.

To clear one held transfer, `POST /ops/transfers/<id>/review` with decision APPROVE and reason returns READY. Select the customer again and confirm the transfer. To reject, use REJECT; reservation is released.

## Stable error codes

| HTTP | Code | Client behavior |
| --- | --- | --- |
| 400 | BAD_REQUEST | Show malformed-request feedback |
| 401 | SESSION_EXPIRED | Offer a new demo session |
| 403 | FORBIDDEN / CSRF_FAILED / ORIGIN_DENIED | Refetch identity or stop the unauthorized action |
| 404 | NOT_FOUND | Treat missing and inaccessible resources equivalently |
| 409 | IDEMPOTENCY_CONFLICT | Generate a new logical request key after user intent changes |
| 409 | ACKNOWLEDGEMENT_REQUIRED | Show the fresh assessment before confirmation |
| 409 | INSUFFICIENT_FUNDS | Refresh balance and show available funds |
| 409 | STATE_CONFLICT / ACTIVE_RESTRICTION_EXISTS | Refetch current resource and ask for an applicable action |
| 422 | VALIDATION_ERROR / UNSUPPORTED_EVIDENCE | Correct form or upload |
| 429 | RATE_LIMITED / MODEL_QUOTA_EXCEEDED | Show retry guidance; normal transfer remains available |
| 500/503 | INTERNAL_ERROR / SERVICE_UNAVAILABLE | Preserve known state, allow refresh and never show a successful payment without confirmation |

Provider failure inside an accepted analysis returns its persisted FAILED/TIMED_OUT state and UNCERTAIN finding. Invalid HTTP input and quota rejection use the error envelope. FastAPI's default validation errors must be mapped into this shared format.
