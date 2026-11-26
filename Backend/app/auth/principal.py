"""Server-resolved identities. Services authorize from these, never from client-supplied IDs."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

Role = Literal["CUSTOMER", "OPERATOR"]


@dataclass(frozen=True, slots=True)
class Principal:
    """A customer or operator resolved from a valid, unrevoked actor session cookie."""

    sandbox_id: UUID
    actor_id: UUID
    role: Role
    request_id: str


@dataclass(frozen=True, slots=True)
class DemoPrincipal:
    """The sandbox demo controller: actor selection and synthetic demo controls only."""

    sandbox_id: UUID
    request_id: str


@dataclass(frozen=True, slots=True)
class SystemPrincipal:
    """Audited server-side maintenance acting inside one sandbox (no HTTP credential)."""

    sandbox_id: UUID
    request_id: str
