# Guardian database specification

This field-level specification accompanies [schema.sql](schema.sql) and [transaction rules](data-model.md). PostgreSQL 16+ is the target. Every table below includes every physical column from the baseline DDL.

## Conventions

- `No` in Nullable means the database rejects NULL. Optional fields can have additional state-dependent requirements.
- `Key type` states PK, UQ or FK directly on each field row. `Key definition / reference` gives the complete key columns and referenced table/columns. A field can participate in more than one key.
- PK means primary key, UQ means unique and FK means foreign key. Composite keys apply to the complete listed tuple. Conditional unique indexes also appear on their member fields with the WHERE condition. Additional indexes are listed below each table.
- `timestamptz` stores an instant; application timestamps are UTC and displayed in the user locale.
- `bigint` money fields use integer VND. JSON transfer amounts are capped at VND 1,000,000,000.
- `text` has no database length limit. API limits, state transitions and cross-record business conditions are specified separately.
- UUIDs do not grant access. Server authentication determines sandbox and actor permissions.
- Each sandbox-bearing child has a direct cascading FK to sandboxes. Other references use PostgreSQL default NO ACTION. Whole-sandbox deletion cascades through all directly owned records.

## Table catalog

| No. | Table | Responsibility |
| --- | --- | --- |
| 1 | `sandboxes` | Owns one isolated judge scenario, its lifetime and all synthetic records. |
| 2 | `actors` | Represents a customer or operator inside a sandbox. |
| 3 | `auth_sessions` | Stores hashed controller/actor session credentials and their CSRF material. |
| 4 | `accounts` | Stores synthetic account identity, posted balance and outstanding reservations. |
| 5 | `orders` | Stores customer-owned order facts and the provenance of any verified return fee. |
| 6 | `refunds` | Stores one pre-approved synthetic incoming refund per order. |
| 7 | `transfers` | Stores an immutable outgoing instruction and its hold/approval/execution lifecycle. |
| 8 | `ledger_entries` | Records append-only posted credits and debits. Reservations remain on transfers/accounts. |
| 9 | `risk_assessments` | Preserves an assessment snapshot and independent recipient/behavior reasons. |
| 10 | `ai_runs` | Preserves inference input identity, private evidence location, model version, status and validated output. |
| 11 | `reports` | Stores a customer complaint or near-miss report for operator review. |
| 12 | `partners` | Identifies synthetic organizations receiving limited refund-support data. |
| 13 | `data_batches` | Records a batch issued to one partner for a specific support purpose. |
| 14 | `trace_references` | Maps an issued reference to a batch and customer order. |
| 15 | `partner_access_events` | Records actual synthetic reads/exports of issued batches. |
| 16 | `recipient_restrictions` | Records operator-approved warning/hold decisions and their revocation history. |
| 17 | `restriction_reports` | Links each recipient decision to the reports used as evidence. |
| 18 | `notifications` | Stores operator-approved precautionary messages for an evidenced customer cohort. |
| 19 | `audit_events` | Retains append-only operational and security events with actor and request correlation. |

## 1. `sandboxes`

Owns one isolated judge scenario, its lifetime and all synthetic records.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK | PK `(id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `scenario` | `text` | — | — | No | — | Fixture selection: MAIN_REFUND, FALSE_POSITIVE or INSUFFICIENT_EVIDENCE. DB check `scenario IN ('MAIN_REFUND', 'FALSE_POSITIVE', 'INSUFFICIENT_EVIDENCE')`. |
| 3 | `created_at` | `timestamptz` | — | — | No | `now()` | Database timestamp when this record was created. |
| 4 | `expires_at` | `timestamptz` | — | — | No | `now() + interval '24 hours'` | Server-enforced deadline. Effective validity is checked against database time. |

## 2. `actors`

Represents a customer or operator inside a sandbox.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK, UQ | PK `(id)`<br>UQ `(sandbox_id, id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | UQ, FK | UQ `(sandbox_id, id)`<br>FK → `sandboxes.id` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `role` | `text` | — | — | No | — | Application permission class: CUSTOMER or OPERATOR. Demo control is a session kind. DB check `role IN ('CUSTOMER', 'OPERATOR')`. |
| 4 | `display_name` | `text` | — | — | No | — | Synthetic human-readable name for actor selection and review. |

## 3. `auth_sessions`

Stores hashed controller/actor session credentials and their CSRF material.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK | PK `(id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | FK | FK → `sandboxes.id`<br>FK → `actors.sandbox_id`<br>Composite `(sandbox_id, actor_id)` → `actors(sandbox_id, id)` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `actor_id` | `uuid` | FK | FK → `actors.id`<br>Composite `(sandbox_id, actor_id)` → `actors(sandbox_id, id)` | Yes | — | Selected actor. Required for ACTOR sessions and absent for DEMO_CONTROL sessions. |
| 4 | `kind` | `text` | — | — | No | — | Credential purpose: DEMO_CONTROL for scenario management or ACTOR for application actions. DB check `kind IN ('DEMO_CONTROL', 'ACTOR')`. |
| 5 | `token_hash` | `text` | UQ | UQ `(token_hash)` | No | — | Hash of the opaque session cookie. The raw credential is never stored here. |
| 6 | `csrf_hash` | `text` | — | — | No | — | Hash of the CSRF token bound to this session. |
| 7 | `expires_at` | `timestamptz` | — | — | No | — | Server-enforced deadline. Effective validity is checked against database time. |
| 8 | `revoked_at` | `timestamptz` | — | — | Yes | — | When this credential was explicitly invalidated; NULL while not revoked. |

**Table checks**

- `CHECK ((kind = 'ACTOR' AND actor_id IS NOT NULL) OR (kind = 'DEMO_CONTROL' AND actor_id IS NULL))`.

## 4. `accounts`

Stores synthetic account identity, posted balance and outstanding reservations.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK, UQ | PK `(id)`<br>UQ `(sandbox_id, id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | UQ, FK | UQ `(sandbox_id, id)`<br>UQ `(sandbox_id, bank_code, account_identifier)`<br>FK → `sandboxes.id`<br>FK → `actors.sandbox_id`<br>Composite `(sandbox_id, owner_actor_id)` → `actors(sandbox_id, id)` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `owner_actor_id` | `uuid` | FK | FK → `actors.id`<br>Composite `(sandbox_id, owner_actor_id)` → `actors(sandbox_id, id)` | Yes | — | Owning customer for a wallet. NULL permits a seeded external recipient account. |
| 4 | `bank_code` | `text` | UQ | UQ `(sandbox_id, bank_code, account_identifier)` | No | — | Source institution code. Together with account_identifier identifies the recipient within the sandbox. |
| 5 | `account_identifier` | `text` | UQ | UQ `(sandbox_id, bank_code, account_identifier)` | No | — | Synthetic account number or wallet identifier. Ordinary API responses mask it. |
| 6 | `display_name` | `text` | — | — | No | — | Verified fixture display name for the recipient or wallet. |
| 7 | `balance_vnd` | `bigint` | — | — | No | `0` | Posted integer-VND balance. Must equal the sum of this account ledger entries. DB check `balance_vnd >= 0`. |
| 8 | `reserved_vnd` | `bigint` | — | — | No | `0` | Total active holds. Available funds are balance_vnd minus reserved_vnd. DB check `reserved_vnd >= 0`. |
| 9 | `created_at` | `timestamptz` | — | — | No | `now()` | Database timestamp when this record was created. |

**Table checks**

- `CHECK (reserved_vnd <= balance_vnd)`.

Balance and reservation aggregates are maintained by the transaction services. Validate ledger equality and concurrent reservation changes with PostgreSQL tests.

## 5. `orders`

Stores customer-owned order facts and the provenance of any verified return fee.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK, UQ | PK `(id)`<br>UQ `(sandbox_id, id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | UQ, FK | UQ `(sandbox_id, id)`<br>UQ `(sandbox_id, order_reference)`<br>FK → `sandboxes.id`<br>FK → `actors.sandbox_id`<br>Composite `(sandbox_id, customer_actor_id)` → `actors(sandbox_id, id)` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `customer_actor_id` | `uuid` | FK | FK → `actors.id`<br>Composite `(sandbox_id, customer_actor_id)` → `actors(sandbox_id, id)` | No | — | Customer authorized to see this order and its official refund facts. |
| 4 | `order_reference` | `text` | UQ | UQ `(sandbox_id, order_reference)` | No | — | Merchant-facing order code, unique within the sandbox. |
| 5 | `merchant_name` | `text` | — | — | No | — | Merchant displayed alongside official order facts. |
| 6 | `original_amount_vnd` | `bigint` | — | — | No | — | Original approved positive order value in integer VND. DB check `original_amount_vnd > 0`. |
| 7 | `return_fee_vnd` | `bigint` | — | — | Yes | — | Authoritatively supplied return fee. NULL means unknown; zero means verified free. DB check `return_fee_vnd >= 0`. |
| 8 | `fee_source` | `text` | — | — | Yes | — | Provenance label of the official merchant or workflow confirmation. |
| 9 | `fee_verified_at` | `timestamptz` | — | — | Yes | — | When the authoritative fee was confirmed. Required whenever a numeric fee is stored. |

**Table checks**

- `CHECK (return_fee_vnd IS NULL OR (fee_source IS NOT NULL AND fee_verified_at IS NOT NULL))`.

## 6. `refunds`

Stores one pre-approved synthetic incoming refund per order.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK, UQ | PK `(id)`<br>UQ `(sandbox_id, id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | UQ, FK | UQ `(sandbox_id, id)`<br>UQ `(sandbox_id, order_id)`<br>FK → `sandboxes.id`<br>FK → `orders.sandbox_id`<br>Composite `(sandbox_id, order_id)` → `orders(sandbox_id, id)`<br>FK → `accounts.sandbox_id`<br>Composite `(sandbox_id, account_id)` → `accounts(sandbox_id, id)` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `order_id` | `uuid` | UQ, FK | UQ `(sandbox_id, order_id)`<br>FK → `orders.id`<br>Composite `(sandbox_id, order_id)` → `orders(sandbox_id, id)` | No | — | Order associated with this record within the same sandbox. |
| 4 | `account_id` | `uuid` | FK | FK → `accounts.id`<br>Composite `(sandbox_id, account_id)` → `accounts(sandbox_id, id)` | No | — | Account associated with this record within the same sandbox. |
| 5 | `amount_vnd` | `bigint` | — | — | No | — | Approved refund amount in integer VND. Service validates it against the original order. DB check `amount_vnd > 0`. |
| 6 | `status` | `text` | — | — | No | `'APPROVED'` | APPROVED before settlement or SETTLED after the unique credit. DB check `status IN ('APPROVED', 'SETTLED')`. |
| 7 | `settled_at` | `timestamptz` | — | — | Yes | — | Settlement timestamp. Present exactly when status is SETTLED. |

**Table checks**

- `CHECK ((status = 'SETTLED') = (settled_at IS NOT NULL))`.

## 7. `transfers`

Stores an immutable outgoing instruction and its hold/approval/execution lifecycle.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK, UQ | PK `(id)`<br>UQ `(sandbox_id, id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | UQ, FK | UQ `(sandbox_id, id)`<br>UQ `(sandbox_id, sender_account_id, client_request_id)`<br>FK → `sandboxes.id`<br>FK → `accounts.sandbox_id`<br>Composite `(sandbox_id, sender_account_id)` → `accounts(sandbox_id, id)`<br>FK → `accounts.sandbox_id`<br>Composite `(sandbox_id, recipient_account_id)` → `accounts(sandbox_id, id)`<br>FK → `actors.sandbox_id`<br>Composite `(sandbox_id, reviewed_by)` → `actors(sandbox_id, id)`<br>FK → `recipient_restrictions.sandbox_id`<br>Composite `(sandbox_id, cleared_restriction_id)` → `recipient_restrictions(sandbox_id, id)` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `sender_account_id` | `uuid` | UQ, FK | UQ `(sandbox_id, sender_account_id, client_request_id)`<br>FK → `accounts.id`<br>Composite `(sandbox_id, sender_account_id)` → `accounts(sandbox_id, id)` | No | — | Customer-owned account being debited; immutable after draft creation. |
| 4 | `recipient_account_id` | `uuid` | FK | FK → `accounts.id`<br>Composite `(sandbox_id, recipient_account_id)` → `accounts(sandbox_id, id)` | No | — | Same-sandbox destination account; immutable after draft creation. |
| 5 | `client_request_id` | `uuid` | UQ | UQ `(sandbox_id, sender_account_id, client_request_id)` | No | — | Client-generated UUID identifying one logical operation. Replays must preserve the original request data. |
| 6 | `amount_vnd` | `bigint` | — | — | No | — | Immutable positive transfer amount, limited to VND 1,000,000,000. DB check `amount_vnd > 0 AND amount_vnd <= 1000000000`. |
| 7 | `status` | `text` | — | — | No | `'DRAFT'` | DRAFT, RISK_HELD, READY, SUCCEEDED, CANCELED, REJECTED or EXPIRED. DB check `status IN ('DRAFT', 'RISK_HELD', 'READY', 'SUCCEEDED', 'CANCELED', 'REJECTED', 'EXPIRED')`. |
| 8 | `reserved_amount_vnd` | `bigint` | — | — | No | `0` | Full amount while RISK_HELD/READY, otherwise zero. Reservation writes are atomic with account totals. DB check `reserved_amount_vnd >= 0`. |
| 9 | `created_at` | `timestamptz` | — | — | No | `now()` | Database timestamp when this record was created. |
| 10 | `expires_at` | `timestamptz` | — | — | No | `now() + interval '30 minutes'` | Server-enforced deadline. Effective validity is checked against database time. |
| 11 | `held_at` | `timestamptz` | — | — | Yes | — | Timestamp of the first hold. It establishes the original review deadline. |
| 12 | `reviewed_by` | `uuid` | FK | FK → `actors.id`<br>Composite `(sandbox_id, reviewed_by)` → `actors(sandbox_id, id)` | Yes | — | Operator actor responsible for the recorded review. |
| 13 | `review_reason` | `text` | — | — | Yes | — | Human-readable explanation of the operator decision. |
| 14 | `cleared_restriction_id` | `uuid` | FK | FK → `recipient_restrictions.id`<br>Composite `(sandbox_id, cleared_restriction_id)` → `recipient_restrictions(sandbox_id, id)` | Yes | — | Exact immutable restriction overridden by operator clearance. A different restriction needs review again. |
| 15 | `completed_at` | `timestamptz` | — | — | Yes | — | Terminal-state timestamp. Required for SUCCEEDED/CANCELED/REJECTED/EXPIRED and absent for active states. |

**Table checks**

- `CHECK (sender_account_id <> recipient_account_id)`.
- `CHECK ((status IN ('RISK_HELD', 'READY') AND reserved_amount_vnd = amount_vnd) OR (status NOT IN ('RISK_HELD', 'READY') AND reserved_amount_vnd = 0))`.
- `CHECK (status <> 'READY' OR (reviewed_by IS NOT NULL AND review_reason IS NOT NULL AND cleared_restriction_id IS NOT NULL))`.
- `CHECK ((status IN ('SUCCEEDED', 'CANCELED', 'REJECTED', 'EXPIRED')) = (completed_at IS NOT NULL))`.

**Additional indexes**

- `transfers_sender_history` on `(sandbox_id, sender_account_id, created_at DESC) WHERE status = 'SUCCEEDED'`.
- `transfers_due_expiry` on `(expires_at) WHERE status IN ('DRAFT', 'RISK_HELD', 'READY')`.

## 8. `ledger_entries`

Records append-only posted credits and debits. Reservations remain on transfers/accounts.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK | PK `(id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | UQ, FK | UQ `(sandbox_id, transfer_id, kind)`<br>UQ `(sandbox_id, refund_id)`<br>FK → `sandboxes.id`<br>FK → `accounts.sandbox_id`<br>Composite `(sandbox_id, account_id)` → `accounts(sandbox_id, id)`<br>FK → `transfers.sandbox_id`<br>Composite `(sandbox_id, transfer_id)` → `transfers(sandbox_id, id)`<br>FK → `refunds.sandbox_id`<br>Composite `(sandbox_id, refund_id)` → `refunds(sandbox_id, id)`<br>UQ `(sandbox_id, account_id)` WHERE `kind = 'OPENING'` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `account_id` | `uuid` | FK, UQ | FK → `accounts.id`<br>Composite `(sandbox_id, account_id)` → `accounts(sandbox_id, id)`<br>UQ `(sandbox_id, account_id)` WHERE `kind = 'OPENING'` | No | — | Account associated with this record within the same sandbox. |
| 4 | `transfer_id` | `uuid` | UQ, FK | UQ `(sandbox_id, transfer_id, kind)`<br>FK → `transfers.id`<br>Composite `(sandbox_id, transfer_id)` → `transfers(sandbox_id, id)` | Yes | — | Transfer associated with this record within the same sandbox. |
| 5 | `refund_id` | `uuid` | UQ, FK | UQ `(sandbox_id, refund_id)`<br>FK → `refunds.id`<br>Composite `(sandbox_id, refund_id)` → `refunds(sandbox_id, id)` | Yes | — | Approved refund that generated this credit; absent for opening and transfer entries. |
| 6 | `kind` | `text` | UQ | UQ `(sandbox_id, transfer_id, kind)` | No | — | OPENING, TRANSFER_DEBIT, TRANSFER_CREDIT or REFUND_CREDIT. DB check `kind IN ('OPENING', 'TRANSFER_DEBIT', 'TRANSFER_CREDIT', 'REFUND_CREDIT')`. |
| 7 | `amount_vnd` | `bigint` | — | — | No | — | Signed posted VND amount. Debit is negative; opening and credits are positive. Zero is rejected. DB check `amount_vnd <> 0`. |
| 8 | `created_at` | `timestamptz` | — | — | No | `now()` | Database timestamp when this record was created. |

**Table checks**

- `CHECK ( (kind = 'OPENING' AND transfer_id IS NULL AND refund_id IS NULL AND amount_vnd > 0) OR (kind = 'TRANSFER_DEBIT' AND transfer_id IS NOT NULL AND refund_id IS NULL AND amount_vnd < 0) OR (kind = 'TRANSFER_CREDIT' AND transfer_id IS NOT NULL AND refund_id IS NULL AND amount_vnd > 0) OR (kind = 'REFUND_CREDIT' AND refund_id IS NOT NULL AND transfer_id IS NULL AND amount_vnd > 0) )`.

**Additional indexes**

- UNIQUE `one_opening_per_account` on `(sandbox_id, account_id) WHERE kind = 'OPENING'`.

## 9. `risk_assessments`

Preserves an assessment snapshot and independent recipient/behavior reasons.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK, UQ | PK `(id)`<br>UQ `(sandbox_id, id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | UQ, FK | UQ `(sandbox_id, id)`<br>FK → `sandboxes.id`<br>FK → `transfers.sandbox_id`<br>Composite `(sandbox_id, transfer_id)` → `transfers(sandbox_id, id)` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `transfer_id` | `uuid` | FK | FK → `transfers.id`<br>Composite `(sandbox_id, transfer_id)` → `transfers(sandbox_id, id)` | No | — | Transfer associated with this record within the same sandbox. |
| 4 | `decision` | `text` | — | — | No | — | Combined intervention: ALLOW, WARN or HOLD. DB check `decision IN ('ALLOW', 'WARN', 'HOLD')`. |
| 5 | `behavior_signal` | `text` | — | — | No | — | Independent history signal: NORMAL, ANOMALOUS or INSUFFICIENT_HISTORY. DB check `behavior_signal IN ('NORMAL', 'ANOMALOUS', 'INSUFFICIENT_HISTORY')`. |
| 6 | `recipient_signal` | `text` | — | — | No | — | Independent effective restriction: NONE, WARN or HOLD. DB check `recipient_signal IN ('NONE', 'WARN', 'HOLD')`. |
| 7 | `policy_version` | `text` | — | — | No | — | Evaluator version used to calculate this snapshot. |
| 8 | `facts_fingerprint` | `text` | — | — | No | — | Digest of relevant immutable instruction, current history, policy version and active recipient restriction. |
| 9 | `reasons` | `jsonb` | — | — | No | — | Array of structured reason codes and explanations used by the frontend. DB check `jsonb_typeof(reasons) = 'array'`. |
| 10 | `facts` | `jsonb` | — | — | No | — | Object containing observed median/sample count/threshold/restriction ID for reproducible review. DB check `jsonb_typeof(facts) = 'object'`. |
| 11 | `assessed_at` | `timestamptz` | — | — | No | `now()` | When the backend evaluated the transaction. |
| 12 | `expires_at` | `timestamptz` | — | — | No | `now() + interval '5 minutes'` | Server-enforced deadline. Effective validity is checked against database time. |

**Additional indexes**

- `risk_assessments_transfer` on `(sandbox_id, transfer_id, assessed_at DESC)`.

## 10. `ai_runs`

Preserves inference input identity, private evidence location, model version, status and validated output.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK, UQ | PK `(id)`<br>UQ `(sandbox_id, id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | UQ, FK | UQ `(sandbox_id, id)`<br>UQ `(sandbox_id, owner_actor_id, client_request_id)`<br>FK → `sandboxes.id`<br>FK → `actors.sandbox_id`<br>Composite `(sandbox_id, owner_actor_id)` → `actors(sandbox_id, id)`<br>FK → `transfers.sandbox_id`<br>Composite `(sandbox_id, transfer_id)` → `transfers(sandbox_id, id)`<br>FK → `orders.sandbox_id`<br>Composite `(sandbox_id, order_id)` → `orders(sandbox_id, id)` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `owner_actor_id` | `uuid` | UQ, FK | UQ `(sandbox_id, owner_actor_id, client_request_id)`<br>FK → `actors.id`<br>Composite `(sandbox_id, owner_actor_id)` → `actors(sandbox_id, id)` | No | — | Actor allowed to retrieve the run, with operator access additionally checked server-side. |
| 4 | `client_request_id` | `uuid` | UQ | UQ `(sandbox_id, owner_actor_id, client_request_id)` | No | — | Client-generated UUID identifying one logical operation. Replays must preserve the original request data. |
| 5 | `kind` | `text` | — | — | No | — | IMAGE_ANALYSIS, TEXT_ANALYSIS or REPORT_GROUPING. DB check `kind IN ('IMAGE_ANALYSIS', 'TEXT_ANALYSIS', 'REPORT_GROUPING')`. |
| 6 | `transfer_id` | `uuid` | FK | FK → `transfers.id`<br>Composite `(sandbox_id, transfer_id)` → `transfers(sandbox_id, id)` | Yes | — | Transfer associated with this record within the same sandbox. |
| 7 | `order_id` | `uuid` | FK | FK → `orders.id`<br>Composite `(sandbox_id, order_id)` → `orders(sandbox_id, id)` | Yes | — | Order associated with this record within the same sandbox. |
| 8 | `input_text` | `text` | — | — | Yes | — | Customer text or canonical grouping input snapshot with source report IDs/excerpts. |
| 9 | `input_digest` | `text` | — | — | No | — | SHA-256 of canonical submitted input, including image bytes or root grouping request identity. |
| 10 | `evidence_object_key` | `text` | — | — | Yes | — | Private storage key for original uploaded evidence; never a publicly readable URL. |
| 11 | `evidence_mime` | `text` | — | — | Yes | — | Verified decoded image media type: image/png, image/jpeg or image/webp. |
| 12 | `status` | `text` | — | — | No | `'PENDING'` | PENDING, SUCCEEDED, FAILED or TIMED_OUT independently of report/transfer state. DB check `status IN ('PENDING', 'SUCCEEDED', 'FAILED', 'TIMED_OUT')`. |
| 13 | `output` | `jsonb` | — | — | Yes | — | Validated ModelEvidence or grouping object plus citation warnings and composed findings. |
| 14 | `provider` | `text` | — | — | Yes | — | Configured inference provider recorded for repeatability and evaluation. |
| 15 | `model` | `text` | — | — | Yes | — | Exact model identifier used by this run. |
| 16 | `prompt_version` | `text` | — | — | No | — | Version of the extraction/grouping prompt and output contract. |
| 17 | `error_code` | `text` | — | — | Yes | — | Stable provider/validation failure code; omit sensitive upstream details. |
| 18 | `created_at` | `timestamptz` | — | — | No | `now()` | Database timestamp when this record was created. |
| 19 | `finished_at` | `timestamptz` | — | — | Yes | — | Timestamp when the run finished or was reconciled as timed out. |

**Table checks**

- `CHECK (status <> 'SUCCEEDED' OR output IS NOT NULL)`.

**Additional indexes**

- `ai_runs_actor` on `(sandbox_id, owner_actor_id, created_at DESC)`.

Validate output against the versioned API model schema. Avoid a database transaction spanning provider inference. Store the logical input identity for replay and the source snapshot for repeatable grouping.

## 11. `reports`

Stores a customer complaint or near-miss report for operator review.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK, UQ | PK `(id)`<br>UQ `(sandbox_id, id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | UQ, FK | UQ `(sandbox_id, id)`<br>UQ `(sandbox_id, reporter_actor_id, client_request_id)`<br>FK → `sandboxes.id`<br>FK → `actors.sandbox_id`<br>Composite `(sandbox_id, reporter_actor_id)` → `actors(sandbox_id, id)`<br>FK → `accounts.sandbox_id`<br>Composite `(sandbox_id, recipient_account_id)` → `accounts(sandbox_id, id)`<br>FK → `transfers.sandbox_id`<br>Composite `(sandbox_id, transfer_id)` → `transfers(sandbox_id, id)`<br>FK → `ai_runs.sandbox_id`<br>Composite `(sandbox_id, analysis_id)` → `ai_runs(sandbox_id, id)`<br>FK → `actors.sandbox_id`<br>Composite `(sandbox_id, reviewed_by)` → `actors(sandbox_id, id)` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `reporter_actor_id` | `uuid` | UQ, FK | UQ `(sandbox_id, reporter_actor_id, client_request_id)`<br>FK → `actors.id`<br>Composite `(sandbox_id, reporter_actor_id)` → `actors(sandbox_id, id)` | No | — | Customer submitting this near-miss or complaint. |
| 4 | `client_request_id` | `uuid` | UQ | UQ `(sandbox_id, reporter_actor_id, client_request_id)` | No | — | Client-generated UUID identifying one logical operation. Replays must preserve the original request data. |
| 5 | `recipient_account_id` | `uuid` | FK | FK → `accounts.id`<br>Composite `(sandbox_id, recipient_account_id)` → `accounts(sandbox_id, id)` | No | — | Reported destination. Must match the linked transfer when one is present. |
| 6 | `transfer_id` | `uuid` | FK | FK → `transfers.id`<br>Composite `(sandbox_id, transfer_id)` → `transfers(sandbox_id, id)` | Yes | — | Transfer associated with this record within the same sandbox. |
| 7 | `analysis_id` | `uuid` | FK | FK → `ai_runs.id`<br>Composite `(sandbox_id, analysis_id)` → `ai_runs(sandbox_id, id)` | Yes | — | Optional owned analysis used as supporting evidence. |
| 8 | `narrative` | `text` | — | — | No | — | Original customer description, treated as untrusted evidence. |
| 9 | `status` | `text` | — | — | No | `'RECEIVED'` | RECEIVED, IN_REVIEW, RESOLVED or DISMISSED. DB check `status IN ('RECEIVED', 'IN_REVIEW', 'RESOLVED', 'DISMISSED')`. |
| 10 | `reviewed_by` | `uuid` | FK | FK → `actors.id`<br>Composite `(sandbox_id, reviewed_by)` → `actors(sandbox_id, id)` | Yes | — | Operator actor responsible for the recorded review. |
| 11 | `resolution_reason` | `text` | — | — | Yes | — | Operator reason supporting review or dismissal; required by service on terminal review. |
| 12 | `created_at` | `timestamptz` | — | — | No | `now()` | Database timestamp when this record was created. |

**Additional indexes**

- `reports_queue` on `(sandbox_id, status, created_at)`.
- `reports_recipient` on `(sandbox_id, recipient_account_id)`.

## 12. `partners`

Identifies synthetic organizations receiving limited refund-support data.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK, UQ | PK `(id)`<br>UQ `(sandbox_id, id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | UQ, FK | UQ `(sandbox_id, id)`<br>UQ `(sandbox_id, name)`<br>FK → `sandboxes.id` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `name` | `text` | UQ | UQ `(sandbox_id, name)` | No | — | Synthetic partner name, unique inside this sandbox. |

## 13. `data_batches`

Records a batch issued to one partner for a specific support purpose.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK, UQ | PK `(id)`<br>UQ `(sandbox_id, id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | UQ, FK | UQ `(sandbox_id, id)`<br>FK → `sandboxes.id`<br>FK → `partners.sandbox_id`<br>Composite `(sandbox_id, partner_id)` → `partners(sandbox_id, id)` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `partner_id` | `uuid` | FK | FK → `partners.id`<br>Composite `(sandbox_id, partner_id)` → `partners(sandbox_id, id)` | No | — | Partner associated with this record within the same sandbox. |
| 4 | `label` | `text` | — | — | No | — | Readable issuance-batch label shown in the trace view. |
| 5 | `issued_at` | `timestamptz` | — | — | No | — | When these records were provided to the associated partner. |

## 14. `trace_references`

Maps an issued reference to a batch and customer order.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK, UQ | PK `(id)`<br>UQ `(sandbox_id, id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | UQ, FK | UQ `(sandbox_id, code)`<br>UQ `(sandbox_id, id)`<br>FK → `sandboxes.id`<br>FK → `data_batches.sandbox_id`<br>Composite `(sandbox_id, batch_id)` → `data_batches(sandbox_id, id)`<br>FK → `orders.sandbox_id`<br>Composite `(sandbox_id, order_id)` → `orders(sandbox_id, id)` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `batch_id` | `uuid` | FK | FK → `data_batches.id`<br>Composite `(sandbox_id, batch_id)` → `data_batches(sandbox_id, id)` | No | — | Issued data batch associated with this record within the same sandbox. |
| 4 | `order_id` | `uuid` | FK | FK → `orders.id`<br>Composite `(sandbox_id, order_id)` → `orders(sandbox_id, id)` | No | — | Order associated with this record within the same sandbox. |
| 5 | `code` | `text` | UQ | UQ `(sandbox_id, code)` | No | — | Exact issued lookup code, such as A-017. It grants no access and does not identify a perpetrator. |

**Additional indexes**

- `trace_references_batch` on `(sandbox_id, batch_id)`.

The issued code is lookup evidence. A forwarded screenshot can contain a valid code. Operator review must preserve uncertainty about the source of disclosure.

## 15. `partner_access_events`

Records actual synthetic reads/exports of issued batches.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK, UQ | PK `(id)`<br>UQ `(sandbox_id, id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | UQ, FK | UQ `(sandbox_id, id)`<br>FK → `sandboxes.id`<br>FK → `partners.sandbox_id`<br>Composite `(sandbox_id, partner_id)` → `partners(sandbox_id, id)`<br>FK → `data_batches.sandbox_id`<br>Composite `(sandbox_id, batch_id)` → `data_batches(sandbox_id, id)` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `partner_id` | `uuid` | FK | FK → `partners.id`<br>Composite `(sandbox_id, partner_id)` → `partners(sandbox_id, id)` | No | — | Partner associated with this record within the same sandbox. |
| 4 | `batch_id` | `uuid` | FK | FK → `data_batches.id`<br>Composite `(sandbox_id, batch_id)` → `data_batches(sandbox_id, id)` | No | — | Issued data batch associated with this record within the same sandbox. |
| 5 | `action` | `text` | — | — | No | — | Recorded READ or EXPORT of the specified batch. DB check `action IN ('READ', 'EXPORT')`. |
| 6 | `occurred_at` | `timestamptz` | — | — | No | — | Time of the recorded access; compare with batch issuance and report timing. |

**Additional indexes**

- `access_batch_time` on `(sandbox_id, batch_id, occurred_at)`.

## 16. `recipient_restrictions`

Records operator-approved warning/hold decisions and their revocation history.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK, UQ | PK `(id)`<br>UQ `(sandbox_id, id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | UQ, FK | UQ `(sandbox_id, id)`<br>FK → `sandboxes.id`<br>FK → `accounts.sandbox_id`<br>Composite `(sandbox_id, recipient_account_id)` → `accounts(sandbox_id, id)`<br>FK → `actors.sandbox_id`<br>Composite `(sandbox_id, created_by)` → `actors(sandbox_id, id)`<br>FK → `actors.sandbox_id`<br>Composite `(sandbox_id, revoked_by)` → `actors(sandbox_id, id)`<br>UQ `(sandbox_id, recipient_account_id)` WHERE `status = 'ACTIVE'` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `recipient_account_id` | `uuid` | FK, UQ | FK → `accounts.id`<br>Composite `(sandbox_id, recipient_account_id)` → `accounts(sandbox_id, id)`<br>UQ `(sandbox_id, recipient_account_id)` WHERE `status = 'ACTIVE'` | No | — | Recipient to which this operator-approved decision applies. |
| 4 | `action` | `text` | — | — | No | — | WARN permits acknowledged continuation; HOLD requires review/cancel/expiry. DB check `action IN ('WARN', 'HOLD')`. |
| 5 | `status` | `text` | — | — | No | `'ACTIVE'` | ACTIVE, REVOKED or EXPIRED. Effective activity also requires a future expires_at. DB check `status IN ('ACTIVE', 'REVOKED', 'EXPIRED')`. |
| 6 | `reason` | `text` | — | — | No | — | Operator explanation linking evidence to the chosen intervention. |
| 7 | `created_by` | `uuid` | FK | FK → `actors.id`<br>Composite `(sandbox_id, created_by)` → `actors(sandbox_id, id)` | No | — | Operator actor that approved creation of this record. |
| 8 | `created_at` | `timestamptz` | — | — | No | `now()` | Database timestamp when this record was created. |
| 9 | `expires_at` | `timestamptz` | — | — | No | — | Server-enforced deadline. Effective validity is checked against database time. |
| 10 | `revoked_by` | `uuid` | FK | FK → `actors.id`<br>Composite `(sandbox_id, revoked_by)` → `actors(sandbox_id, id)` | Yes | — | Operator who withdrew this decision, retained for accountability. |
| 11 | `revoked_at` | `timestamptz` | — | — | Yes | — | When revocation was recorded. |
| 12 | `revocation_reason` | `text` | — | — | Yes | — | Why this decision was withdrawn or corrected. |

**Table checks**

- `CHECK (expires_at > created_at)`.
- `CHECK (status <> 'REVOKED' OR (revoked_by IS NOT NULL AND revoked_at IS NOT NULL AND revocation_reason IS NOT NULL))`.

**Additional indexes**

- UNIQUE `one_active_restriction` on `(sandbox_id, recipient_account_id) WHERE status = 'ACTIVE'`.

The partial unique index limits rows whose stored status is ACTIVE. Creation first expires time-expired rows. Queries also check expires_at. A transaction-specific clearance does not revoke this decision.

## 17. `restriction_reports`

Links each recipient decision to the reports used as evidence.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `sandbox_id` | `uuid` | PK, FK | PK `(sandbox_id, restriction_id, report_id)`<br>FK → `sandboxes.id`<br>FK → `recipient_restrictions.sandbox_id`<br>Composite `(sandbox_id, restriction_id)` → `recipient_restrictions(sandbox_id, id)`<br>FK → `reports.sandbox_id`<br>Composite `(sandbox_id, report_id)` → `reports(sandbox_id, id)` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 2 | `restriction_id` | `uuid` | PK, FK | PK `(sandbox_id, restriction_id, report_id)`<br>FK → `recipient_restrictions.id`<br>Composite `(sandbox_id, restriction_id)` → `recipient_restrictions(sandbox_id, id)` | No | — | Recipient restriction supported by this evidence link. |
| 3 | `report_id` | `uuid` | PK, FK | PK `(sandbox_id, restriction_id, report_id)`<br>FK → `reports.id`<br>Composite `(sandbox_id, report_id)` → `reports(sandbox_id, id)` | No | — | Reviewed RESOLVED report about the same recipient, checked by the service. |

## 18. `notifications`

Stores operator-approved precautionary messages for an evidenced customer cohort.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK, UQ | PK `(id)`<br>UQ `(sandbox_id, id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | UQ, FK | UQ `(sandbox_id, id)`<br>UQ `(sandbox_id, source_report_id, batch_id, recipient_actor_id)`<br>FK → `sandboxes.id`<br>FK → `actors.sandbox_id`<br>Composite `(sandbox_id, recipient_actor_id)` → `actors(sandbox_id, id)`<br>FK → `data_batches.sandbox_id`<br>Composite `(sandbox_id, batch_id)` → `data_batches(sandbox_id, id)`<br>FK → `reports.sandbox_id`<br>Composite `(sandbox_id, source_report_id)` → `reports(sandbox_id, id)`<br>FK → `actors.sandbox_id`<br>Composite `(sandbox_id, created_by)` → `actors(sandbox_id, id)` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `recipient_actor_id` | `uuid` | UQ, FK | UQ `(sandbox_id, source_report_id, batch_id, recipient_actor_id)`<br>FK → `actors.id`<br>Composite `(sandbox_id, recipient_actor_id)` → `actors(sandbox_id, id)` | No | — | Customer derived from the evidenced batch membership; caller cannot choose arbitrary customers. |
| 4 | `batch_id` | `uuid` | UQ, FK | UQ `(sandbox_id, source_report_id, batch_id, recipient_actor_id)`<br>FK → `data_batches.id`<br>Composite `(sandbox_id, batch_id)` → `data_batches(sandbox_id, id)` | No | — | Issued data batch associated with this record within the same sandbox. |
| 5 | `source_report_id` | `uuid` | UQ, FK | UQ `(sandbox_id, source_report_id, batch_id, recipient_actor_id)`<br>FK → `reports.id`<br>Composite `(sandbox_id, source_report_id)` → `reports(sandbox_id, id)` | No | — | Reviewed report whose trace supports this precautionary notice. |
| 6 | `title` | `text` | — | — | No | — | Operator-approved notice title, at most 120 characters through API validation. |
| 7 | `body` | `text` | — | — | No | — | Operator-approved notice text, at most 1,000 characters through API validation. |
| 8 | `created_by` | `uuid` | FK | FK → `actors.id`<br>Composite `(sandbox_id, created_by)` → `actors(sandbox_id, id)` | No | — | Operator actor that approved creation of this record. |
| 9 | `created_at` | `timestamptz` | — | — | No | `now()` | Database timestamp when this record was created. |
| 10 | `read_at` | `timestamptz` | — | — | Yes | — | Optional timestamp when acknowledged as read; future read-tracking UI can populate it. |

**Additional indexes**

- `notifications_customer` on `(sandbox_id, recipient_actor_id, created_at DESC)`.

## 19. `audit_events`

Retains append-only operational and security events with actor and request correlation.

| No. | Field | PostgreSQL type | Key type | Key definition / reference | Nullable | Default | Meaning and validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | PK | PK `(id)` | No | `gen_random_uuid()` | Server-generated identifier for this record. |
| 2 | `sandbox_id` | `uuid` | FK | FK → `sandboxes.id`<br>FK → `actors.sandbox_id`<br>Composite `(sandbox_id, actor_id)` → `actors(sandbox_id, id)` | No | — | Owning isolated demo environment. The server resolves this scope from the authenticated session. |
| 3 | `actor_id` | `uuid` | FK | FK → `actors.id`<br>Composite `(sandbox_id, actor_id)` → `actors(sandbox_id, id)` | Yes | — | Acting human actor, NULL for a system or controller event when appropriate. |
| 4 | `actor_kind` | `text` | — | — | No | — | CUSTOMER, OPERATOR, SYSTEM or DEMO_CONTROL, resolved by server. DB check `actor_kind IN ('CUSTOMER', 'OPERATOR', 'SYSTEM', 'DEMO_CONTROL')`. |
| 5 | `event_type` | `text` | — | — | No | — | Stable operation label, for example TRANSFER_HELD or RESTRICTION_REVOKED. |
| 6 | `target_type` | `text` | — | — | No | — | Resource category affected by the event. |
| 7 | `target_id` | `uuid` | — | — | Yes | — | Resource UUID when an event addresses a specific entity. |
| 8 | `request_id` | `text` | — | — | No | — | Server request-correlation value for troubleshooting and review. |
| 9 | `details` | `jsonb` | — | — | No | `'{}'::jsonb` | Structured redacted event metadata, reason and evidence references. No secrets or raw private screenshots. DB check `jsonb_typeof(details) = 'object'`. |
| 10 | `created_at` | `timestamptz` | — | — | No | `now()` | Database timestamp when this record was created. |

**Additional indexes**

- `audit_events_timeline` on `(sandbox_id, created_at DESC)`.

## Implementation agreement

Copy every column, key and DB check into the initial Alembic migration and SQLAlchemy metadata. Retain the SQL file as the reviewable baseline. Update this specification when a migration changes storage. [data-model.md](data-model.md) defines authorization, locking, deadlines and ledger aggregates that span multiple rows.
