"""Append-only audit events for state changes. The helper only adds rows and never commits.

`append_audit` derives the actor from the server-resolved principal: a customer or operator
Principal records its role and actor ID, the demo controller records DEMO_CONTROL, and server-side
reconciliation records SYSTEM; the latter two have no actor ID. The request ID always comes from
the principal, so every event correlates with the request that caused it.

Details are sanitized before persistence: keys that look like credentials are dropped, UUIDs and
timestamps become strings, text is truncated, and any other value type is a programming error.
"""

import math
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app import models
from app.auth.principal import DemoPrincipal, Principal, SystemPrincipal

AuditPrincipal = Principal | DemoPrincipal | SystemPrincipal

MAX_TEXT_LENGTH = 500
_SECRET_MARKERS = ("token", "csrf", "secret", "password", "cookie", "authorization", "api_key")


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in _SECRET_MARKERS)


def sanitize_details(value: Any) -> Any:
    """A JSON-safe copy of `value` without credential-like keys."""
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Audit details cannot contain non-finite numbers.")
        return value
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else str(value)
    if isinstance(value, str):
        return value[:MAX_TEXT_LENGTH]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("Audit timestamps must be timezone-aware.")
        return value.astimezone(UTC).isoformat()
    if isinstance(value, Mapping):
        return {
            str(key): sanitize_details(item)
            for key, item in value.items()
            if not _is_secret_key(str(key))
        }
    if isinstance(value, list | tuple):
        return [sanitize_details(item) for item in value]
    raise TypeError(f"Unsupported audit detail type: {type(value).__name__}")


def append_audit(
    session: Session,
    principal: AuditPrincipal,
    event_type: str,
    target_type: str,
    target_id: UUID | None,
    details: Mapping[str, Any],
) -> None:
    if isinstance(principal, Principal):
        actor_kind, actor_id = principal.role, principal.actor_id
    elif isinstance(principal, DemoPrincipal):
        actor_kind, actor_id = "DEMO_CONTROL", None
    else:
        actor_kind, actor_id = "SYSTEM", None
    session.add(
        models.AuditEvent(
            sandbox_id=principal.sandbox_id,
            actor_id=actor_id,
            actor_kind=actor_kind,
            event_type=event_type,
            target_type=target_type,
            target_id=target_id,
            request_id=principal.request_id,
            details=sanitize_details(dict(details)),
        )
    )
