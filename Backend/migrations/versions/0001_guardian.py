"""Guardian initial schema.

Frozen copy of docs/guardian/schema.sql (19 tables, 161 columns). Released migrations never read
mutable docs at runtime; tests compare this revision with schema.sql instead.

Revision ID: 0001_guardian
Revises:
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_guardian"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_STATEMENTS: tuple[str, ...] = (
    """
CREATE EXTENSION IF NOT EXISTS pgcrypto
    """,
    """
CREATE TABLE sandboxes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario text NOT NULL CHECK (scenario IN ('MAIN_REFUND', 'FALSE_POSITIVE', 'INSUFFICIENT_EVIDENCE')),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL DEFAULT now() + interval '24 hours'
)
    """,
    """
CREATE TABLE actors (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('CUSTOMER', 'OPERATOR')),
    display_name text NOT NULL,
    UNIQUE (sandbox_id, id)
)
    """,
    """
CREATE TABLE auth_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    actor_id uuid,
    kind text NOT NULL CHECK (kind IN ('DEMO_CONTROL', 'ACTOR')),
    token_hash text NOT NULL UNIQUE,
    csrf_hash text NOT NULL,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    CHECK ((kind = 'ACTOR' AND actor_id IS NOT NULL) OR (kind = 'DEMO_CONTROL' AND actor_id IS NULL)),
    FOREIGN KEY (sandbox_id, actor_id) REFERENCES actors(sandbox_id, id)
)
    """,
    """
CREATE TABLE accounts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    owner_actor_id uuid,
    bank_code text NOT NULL,
    account_identifier text NOT NULL,
    display_name text NOT NULL,
    balance_vnd bigint NOT NULL DEFAULT 0 CHECK (balance_vnd >= 0),
    reserved_vnd bigint NOT NULL DEFAULT 0 CHECK (reserved_vnd >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (reserved_vnd <= balance_vnd),
    UNIQUE (sandbox_id, id),
    UNIQUE (sandbox_id, bank_code, account_identifier),
    FOREIGN KEY (sandbox_id, owner_actor_id) REFERENCES actors(sandbox_id, id)
)
    """,
    """
CREATE TABLE orders (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    customer_actor_id uuid NOT NULL,
    order_reference text NOT NULL,
    merchant_name text NOT NULL,
    original_amount_vnd bigint NOT NULL CHECK (original_amount_vnd > 0),
    return_fee_vnd bigint CHECK (return_fee_vnd >= 0),
    fee_source text,
    fee_verified_at timestamptz,
    CHECK (return_fee_vnd IS NULL OR (fee_source IS NOT NULL AND fee_verified_at IS NOT NULL)),
    UNIQUE (sandbox_id, id),
    UNIQUE (sandbox_id, order_reference),
    FOREIGN KEY (sandbox_id, customer_actor_id) REFERENCES actors(sandbox_id, id)
)
    """,
    """
CREATE TABLE refunds (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    order_id uuid NOT NULL,
    account_id uuid NOT NULL,
    amount_vnd bigint NOT NULL CHECK (amount_vnd > 0),
    status text NOT NULL DEFAULT 'APPROVED' CHECK (status IN ('APPROVED', 'SETTLED')),
    settled_at timestamptz,
    CHECK ((status = 'SETTLED') = (settled_at IS NOT NULL)),
    UNIQUE (sandbox_id, id),
    UNIQUE (sandbox_id, order_id),
    FOREIGN KEY (sandbox_id, order_id) REFERENCES orders(sandbox_id, id),
    FOREIGN KEY (sandbox_id, account_id) REFERENCES accounts(sandbox_id, id)
)
    """,
    """
CREATE TABLE transfers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    sender_account_id uuid NOT NULL,
    recipient_account_id uuid NOT NULL,
    client_request_id uuid NOT NULL,
    amount_vnd bigint NOT NULL CHECK (amount_vnd > 0 AND amount_vnd <= 1000000000),
    status text NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'RISK_HELD', 'READY', 'SUCCEEDED', 'CANCELED', 'REJECTED', 'EXPIRED')),
    reserved_amount_vnd bigint NOT NULL DEFAULT 0 CHECK (reserved_amount_vnd >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL DEFAULT now() + interval '30 minutes',
    held_at timestamptz,
    reviewed_by uuid,
    review_reason text,
    cleared_restriction_id uuid,
    completed_at timestamptz,
    CHECK (sender_account_id <> recipient_account_id),
    CHECK ((status IN ('RISK_HELD', 'READY') AND reserved_amount_vnd = amount_vnd)
        OR (status NOT IN ('RISK_HELD', 'READY') AND reserved_amount_vnd = 0)),
    CHECK (status <> 'READY' OR (reviewed_by IS NOT NULL AND review_reason IS NOT NULL AND cleared_restriction_id IS NOT NULL)),
    CHECK ((status IN ('SUCCEEDED', 'CANCELED', 'REJECTED', 'EXPIRED')) = (completed_at IS NOT NULL)),
    UNIQUE (sandbox_id, id),
    UNIQUE (sandbox_id, sender_account_id, client_request_id),
    FOREIGN KEY (sandbox_id, sender_account_id) REFERENCES accounts(sandbox_id, id),
    FOREIGN KEY (sandbox_id, recipient_account_id) REFERENCES accounts(sandbox_id, id),
    FOREIGN KEY (sandbox_id, reviewed_by) REFERENCES actors(sandbox_id, id)
)
    """,
    """
CREATE TABLE ledger_entries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    account_id uuid NOT NULL,
    transfer_id uuid,
    refund_id uuid,
    kind text NOT NULL CHECK (kind IN ('OPENING', 'TRANSFER_DEBIT', 'TRANSFER_CREDIT', 'REFUND_CREDIT')),
    amount_vnd bigint NOT NULL CHECK (amount_vnd <> 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (
        (kind = 'OPENING' AND transfer_id IS NULL AND refund_id IS NULL AND amount_vnd > 0)
        OR (kind = 'TRANSFER_DEBIT' AND transfer_id IS NOT NULL AND refund_id IS NULL AND amount_vnd < 0)
        OR (kind = 'TRANSFER_CREDIT' AND transfer_id IS NOT NULL AND refund_id IS NULL AND amount_vnd > 0)
        OR (kind = 'REFUND_CREDIT' AND refund_id IS NOT NULL AND transfer_id IS NULL AND amount_vnd > 0)
    ),
    FOREIGN KEY (sandbox_id, account_id) REFERENCES accounts(sandbox_id, id),
    FOREIGN KEY (sandbox_id, transfer_id) REFERENCES transfers(sandbox_id, id),
    FOREIGN KEY (sandbox_id, refund_id) REFERENCES refunds(sandbox_id, id),
    UNIQUE (sandbox_id, transfer_id, kind),
    UNIQUE (sandbox_id, refund_id)
)
    """,
    """
CREATE UNIQUE INDEX one_opening_per_account ON ledger_entries(sandbox_id, account_id) WHERE kind = 'OPENING'
    """,
    """
CREATE TABLE risk_assessments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    transfer_id uuid NOT NULL,
    decision text NOT NULL CHECK (decision IN ('ALLOW', 'WARN', 'HOLD')),
    behavior_signal text NOT NULL CHECK (behavior_signal IN ('NORMAL', 'ANOMALOUS', 'INSUFFICIENT_HISTORY')),
    recipient_signal text NOT NULL CHECK (recipient_signal IN ('NONE', 'WARN', 'HOLD')),
    policy_version text NOT NULL,
    facts_fingerprint text NOT NULL,
    reasons jsonb NOT NULL CHECK (jsonb_typeof(reasons) = 'array'),
    facts jsonb NOT NULL CHECK (jsonb_typeof(facts) = 'object'),
    assessed_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL DEFAULT now() + interval '5 minutes',
    UNIQUE (sandbox_id, id),
    FOREIGN KEY (sandbox_id, transfer_id) REFERENCES transfers(sandbox_id, id)
)
    """,
    """
CREATE TABLE ai_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    owner_actor_id uuid NOT NULL,
    client_request_id uuid NOT NULL,
    kind text NOT NULL CHECK (kind IN ('IMAGE_ANALYSIS', 'TEXT_ANALYSIS', 'REPORT_GROUPING')),
    transfer_id uuid,
    order_id uuid,
    input_text text,
    input_digest text NOT NULL,
    evidence_object_key text,
    evidence_mime text,
    status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'SUCCEEDED', 'FAILED', 'TIMED_OUT')),
    output jsonb,
    provider text,
    model text,
    prompt_version text NOT NULL,
    error_code text,
    created_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    CHECK (status <> 'SUCCEEDED' OR output IS NOT NULL),
    UNIQUE (sandbox_id, id),
    UNIQUE (sandbox_id, owner_actor_id, client_request_id),
    FOREIGN KEY (sandbox_id, owner_actor_id) REFERENCES actors(sandbox_id, id),
    FOREIGN KEY (sandbox_id, transfer_id) REFERENCES transfers(sandbox_id, id),
    FOREIGN KEY (sandbox_id, order_id) REFERENCES orders(sandbox_id, id)
)
    """,
    """
CREATE TABLE reports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    reporter_actor_id uuid NOT NULL,
    client_request_id uuid NOT NULL,
    recipient_account_id uuid NOT NULL,
    transfer_id uuid,
    analysis_id uuid,
    narrative text NOT NULL,
    status text NOT NULL DEFAULT 'RECEIVED' CHECK (status IN ('RECEIVED', 'IN_REVIEW', 'RESOLVED', 'DISMISSED')),
    reviewed_by uuid,
    resolution_reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (sandbox_id, id),
    UNIQUE (sandbox_id, reporter_actor_id, client_request_id),
    FOREIGN KEY (sandbox_id, reporter_actor_id) REFERENCES actors(sandbox_id, id),
    FOREIGN KEY (sandbox_id, recipient_account_id) REFERENCES accounts(sandbox_id, id),
    FOREIGN KEY (sandbox_id, transfer_id) REFERENCES transfers(sandbox_id, id),
    FOREIGN KEY (sandbox_id, analysis_id) REFERENCES ai_runs(sandbox_id, id),
    FOREIGN KEY (sandbox_id, reviewed_by) REFERENCES actors(sandbox_id, id)
)
    """,
    """
CREATE TABLE partners (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    name text NOT NULL,
    UNIQUE (sandbox_id, id),
    UNIQUE (sandbox_id, name)
)
    """,
    """
CREATE TABLE data_batches (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    partner_id uuid NOT NULL,
    label text NOT NULL,
    issued_at timestamptz NOT NULL,
    UNIQUE (sandbox_id, id),
    FOREIGN KEY (sandbox_id, partner_id) REFERENCES partners(sandbox_id, id)
)
    """,
    """
CREATE TABLE trace_references (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    batch_id uuid NOT NULL,
    order_id uuid NOT NULL,
    code text NOT NULL,
    UNIQUE (sandbox_id, code),
    UNIQUE (sandbox_id, id),
    FOREIGN KEY (sandbox_id, batch_id) REFERENCES data_batches(sandbox_id, id),
    FOREIGN KEY (sandbox_id, order_id) REFERENCES orders(sandbox_id, id)
)
    """,
    """
CREATE TABLE partner_access_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    partner_id uuid NOT NULL,
    batch_id uuid NOT NULL,
    action text NOT NULL CHECK (action IN ('READ', 'EXPORT')),
    occurred_at timestamptz NOT NULL,
    UNIQUE (sandbox_id, id),
    FOREIGN KEY (sandbox_id, partner_id) REFERENCES partners(sandbox_id, id),
    FOREIGN KEY (sandbox_id, batch_id) REFERENCES data_batches(sandbox_id, id)
)
    """,
    """
CREATE TABLE recipient_restrictions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    recipient_account_id uuid NOT NULL,
    action text NOT NULL CHECK (action IN ('WARN', 'HOLD')),
    status text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'REVOKED', 'EXPIRED')),
    reason text NOT NULL,
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_by uuid,
    revoked_at timestamptz,
    revocation_reason text,
    CHECK (expires_at > created_at),
    CHECK (status <> 'REVOKED' OR (revoked_by IS NOT NULL AND revoked_at IS NOT NULL AND revocation_reason IS NOT NULL)),
    UNIQUE (sandbox_id, id),
    FOREIGN KEY (sandbox_id, recipient_account_id) REFERENCES accounts(sandbox_id, id),
    FOREIGN KEY (sandbox_id, created_by) REFERENCES actors(sandbox_id, id),
    FOREIGN KEY (sandbox_id, revoked_by) REFERENCES actors(sandbox_id, id)
)
    """,
    """
CREATE UNIQUE INDEX one_active_restriction ON recipient_restrictions(sandbox_id, recipient_account_id) WHERE status = 'ACTIVE'
    """,
    """
CREATE TABLE restriction_reports (
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    restriction_id uuid NOT NULL,
    report_id uuid NOT NULL,
    PRIMARY KEY (sandbox_id, restriction_id, report_id),
    FOREIGN KEY (sandbox_id, restriction_id) REFERENCES recipient_restrictions(sandbox_id, id),
    FOREIGN KEY (sandbox_id, report_id) REFERENCES reports(sandbox_id, id)
)
    """,
    """
ALTER TABLE transfers ADD CONSTRAINT cleared_restriction_scope_fk
    FOREIGN KEY (sandbox_id, cleared_restriction_id) REFERENCES recipient_restrictions(sandbox_id, id)
    """,
    """
CREATE TABLE notifications (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    recipient_actor_id uuid NOT NULL,
    batch_id uuid NOT NULL,
    source_report_id uuid NOT NULL,
    title text NOT NULL,
    body text NOT NULL,
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    read_at timestamptz,
    UNIQUE (sandbox_id, id),
    UNIQUE (sandbox_id, source_report_id, batch_id, recipient_actor_id),
    FOREIGN KEY (sandbox_id, recipient_actor_id) REFERENCES actors(sandbox_id, id),
    FOREIGN KEY (sandbox_id, batch_id) REFERENCES data_batches(sandbox_id, id),
    FOREIGN KEY (sandbox_id, source_report_id) REFERENCES reports(sandbox_id, id),
    FOREIGN KEY (sandbox_id, created_by) REFERENCES actors(sandbox_id, id)
)
    """,
    """
CREATE TABLE audit_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id uuid NOT NULL REFERENCES sandboxes(id) ON DELETE CASCADE,
    actor_id uuid,
    actor_kind text NOT NULL CHECK (actor_kind IN ('CUSTOMER', 'OPERATOR', 'SYSTEM', 'DEMO_CONTROL')),
    event_type text NOT NULL,
    target_type text NOT NULL,
    target_id uuid,
    request_id text NOT NULL,
    details jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(details) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (sandbox_id, actor_id) REFERENCES actors(sandbox_id, id)
)
    """,
    """
CREATE INDEX transfers_sender_history ON transfers(sandbox_id, sender_account_id, created_at DESC) WHERE status = 'SUCCEEDED'
    """,
    """
CREATE INDEX transfers_due_expiry ON transfers(expires_at) WHERE status IN ('DRAFT', 'RISK_HELD', 'READY')
    """,
    """
CREATE INDEX risk_assessments_transfer ON risk_assessments(sandbox_id, transfer_id, assessed_at DESC)
    """,
    """
CREATE INDEX reports_queue ON reports(sandbox_id, status, created_at)
    """,
    """
CREATE INDEX reports_recipient ON reports(sandbox_id, recipient_account_id)
    """,
    """
CREATE INDEX ai_runs_actor ON ai_runs(sandbox_id, owner_actor_id, created_at DESC)
    """,
    """
CREATE INDEX trace_references_batch ON trace_references(sandbox_id, batch_id)
    """,
    """
CREATE INDEX access_batch_time ON partner_access_events(sandbox_id, batch_id, occurred_at)
    """,
    """
CREATE INDEX notifications_customer ON notifications(sandbox_id, recipient_actor_id, created_at DESC)
    """,
    """
CREATE INDEX audit_events_timeline ON audit_events(sandbox_id, created_at DESC)
    """,
)

# Reverse creation order. The cross-table FK is dropped first so tables drop cleanly.
DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "ALTER TABLE transfers DROP CONSTRAINT cleared_restriction_scope_fk",
    "DROP TABLE audit_events",
    "DROP TABLE notifications",
    "DROP TABLE restriction_reports",
    "DROP TABLE recipient_restrictions",
    "DROP TABLE partner_access_events",
    "DROP TABLE trace_references",
    "DROP TABLE data_batches",
    "DROP TABLE partners",
    "DROP TABLE reports",
    "DROP TABLE ai_runs",
    "DROP TABLE risk_assessments",
    "DROP TABLE ledger_entries",
    "DROP TABLE transfers",
    "DROP TABLE refunds",
    "DROP TABLE orders",
    "DROP TABLE accounts",
    "DROP TABLE auth_sessions",
    "DROP TABLE actors",
    "DROP TABLE sandboxes",
)


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
