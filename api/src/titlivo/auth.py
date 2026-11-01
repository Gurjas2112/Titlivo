"""Who is calling, and what they may see (spec §12, rule 5: mask by default).

Prototype keys come from settings: `DEMO_API_KEY` (developer key with parcels:pii, ask, mcp) and
`ADMIN_API_KEY` (adds admin). Anonymous callers get masked names on every surface.
"""

import hmac
from dataclasses import dataclass, field

from fastapi import Request

from titlivo.settings import get_settings


@dataclass(frozen=True)
class Caller:
    role: str = "anon"  # anon | developer | admin
    scopes: frozenset[str] = field(default_factory=frozenset)

    @property
    def can_see_names(self) -> bool:
        return "parcels:pii" in self.scopes

    @property
    def is_admin(self) -> bool:
        return "admin" in self.scopes


ANON = Caller()
DEVELOPER_SCOPES = frozenset({"parcels:read", "parcels:pii", "ask", "mcp"})


def caller_from_token(token: str | None) -> Caller:
    s = get_settings()
    if not token:
        return ANON
    if hmac.compare_digest(token, s.admin_api_key):
        return Caller("admin", DEVELOPER_SCOPES | {"admin"})
    if hmac.compare_digest(token, s.demo_api_key):
        return Caller("developer", DEVELOPER_SCOPES)
    return ANON


def token_from_headers(headers: dict[str, str] | object) -> str | None:
    get = headers.get  # type: ignore[attr-defined]
    auth = get("authorization") or get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return get("x-api-key") or get("X-API-Key")


def get_caller(request: Request) -> Caller:
    return caller_from_token(token_from_headers(request.headers))
