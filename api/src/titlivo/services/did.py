"""Issuer identity: did:web document and the Ed25519 signing key (spec §6.10, rule 12).

Signing uses joserfc only. Algorithm name: "Ed25519" (RFC 9864 fully-specified name; the older
"EdDSA" name is deprecated). Same key type and signature as EdDSA over Ed25519.
"""

import json
from functools import lru_cache
from urllib.parse import unquote

from joserfc.jwk import OKPKey

from titlivo.settings import get_settings

ALG = "Ed25519"
KEY_ID_SUFFIX = "key-2026-11"


@lru_cache
def signing_key() -> OKPKey:
    raw = get_settings().passport_signing_jwk
    if not raw:
        raise RuntimeError("PASSPORT_SIGNING_JWK is not set. Run: uv run python -m titlivo.tools.keys")
    return OKPKey.import_key(json.loads(raw))


def issuer() -> str:
    return get_settings().issuer_did


def kid() -> str:
    return f"{issuer()}#{KEY_ID_SUFFIX}"


def document() -> dict:
    pub = signing_key().as_dict(private=False)
    pub.pop("kid", None)
    vm = {"id": kid(), "type": "JsonWebKey", "controller": issuer(), "publicKeyJwk": pub}
    return {
        "@context": ["https://www.w3.org/ns/did/v1", "https://w3id.org/security/jwk/v1"],
        "id": issuer(),
        "verificationMethod": [vm],
        "assertionMethod": [vm["id"]],
    }


def did_web_url(did: str) -> str:
    """did:web:host%3Aport[:path] → URL of its did.json (http only for localhost)."""
    if not did.startswith("did:web:"):
        raise ValueError("only did:web issuers are supported")
    parts = [unquote(p) for p in did[len("did:web:") :].split(":")]
    host, path = parts[0], parts[1:]
    scheme = "http" if host.startswith(("localhost", "127.0.0.1")) else "https"
    return f"{scheme}://{host}/" + ("/".join(path) + "/did.json" if path else ".well-known/did.json")
