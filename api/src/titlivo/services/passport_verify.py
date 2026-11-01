"""Verify a Title Passport using only published documents: the issuer's did.json and the signed
status lists (spec §6.10). Never reads the passports table. The browser verifier
(web/src/lib/verifyPassport.ts) implements the same steps and passes the same test vectors.

Result: LIVE | SUSPENDED | REVOKED | EXPIRED | INVALID_SIGNATURE (+ reasons), or UNVERIFIED when
the signature is valid but a status list could not be fetched (never shown as LIVE).
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from joserfc import jws
from joserfc.errors import JoseError
from joserfc.jwk import OKPKey

from titlivo.services import did, status_list

Fetch = Callable[[str], str]  # URL → response body


def _b64json(part: str) -> dict[str, Any]:
    import base64

    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def _key_for(kid: str, fetch: Fetch) -> OKPKey:
    issuer = kid.split("#")[0]
    doc = json.loads(fetch(did.did_web_url(issuer)))
    for vm in doc.get("verificationMethod", []):
        if vm["id"] == kid:
            return OKPKey.import_key(vm["publicKeyJwk"])
    raise KeyError(kid)


def _verify_jws(token: str, fetch: Fetch) -> dict[str, Any]:
    header = _b64json(token.split(".")[0])
    if header.get("typ") != "vc+jwt" or header.get("alg") != did.ALG:
        raise ValueError("unexpected header")
    key = _key_for(header["kid"], fetch)
    payload = json.loads(jws.deserialize_compact(token, key, algorithms=[did.ALG]).payload)
    if payload.get("issuer") != header["kid"].split("#")[0]:
        raise ValueError("issuer does not match the signing key")
    return payload


def verify(token: str, fetch: Fetch, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    token = token.strip()
    try:
        cred = _verify_jws(token, fetch)
    except (JoseError, ValueError, KeyError, IndexError, json.JSONDecodeError) as e:
        return {"status": "INVALID_SIGNATURE", "reasons": [f"signature or issuer check failed: {type(e).__name__}"]}

    reasons: list[str] = []
    result = {
        "status": "LIVE",
        "signature": "valid",
        "issuer": cred["issuer"],
        "credential": cred,
        "checked_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reasons": reasons,
    }
    if datetime.fromisoformat(cred["validUntil"]) < now:
        result["status"] = "EXPIRED"
        reasons.append(f"expired on {cred['validUntil']}")
    for entry in cred.get("credentialStatus", []):
        try:
            sl = _verify_jws(fetch(entry["statusListCredential"]), fetch)
            if sl["credentialSubject"]["statusPurpose"] != entry["statusPurpose"]:
                raise ValueError("status purpose mismatch")
            bits = status_list.decode(sl["credentialSubject"]["encodedList"])
            if status_list.get_bit(bits, int(entry["statusListIndex"])):
                if entry["statusPurpose"] == "revocation":
                    result["status"] = "REVOKED"
                    reasons.append("revoked by the issuer")
                elif result["status"] == "LIVE":
                    result["status"] = "SUSPENDED"
                    reasons.append("suspended: a material change was detected in the records")
        except Exception as e:  # noqa: BLE001 — a status list that cannot be checked must not read as LIVE
            result["status"] = "UNVERIFIED" if result["status"] == "LIVE" else result["status"]
            reasons.append(f"status list check failed: {type(e).__name__}")
    return result
