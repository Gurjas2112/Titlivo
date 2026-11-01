"""W3C Bitstring Status List v1.0: one bit per passport, published as a signed credential.

Bit order: index 0 is the most significant bit of the first byte. encodedList is the multibase
base64url ("u" prefix) of the GZIP-compressed bitstring. This is the only module that encodes
or decodes the bitstring (rule 12).
"""

import base64
import gzip
import hashlib
import json
import secrets
from datetime import UTC, datetime
from typing import Any

import psycopg
from joserfc import jws

from titlivo.db.pool import pool
from titlivo.services import did
from titlivo.settings import get_settings

SUSPENSION, REVOCATION = 1, 2


def get_bit(bits: bytes, index: int) -> bool:
    return bool(bits[index // 8] & (0x80 >> (index % 8)))


def with_bit(bits: bytes, index: int, value: bool) -> bytes:
    b = bytearray(bits)
    if value:
        b[index // 8] |= 0x80 >> (index % 8)
    else:
        b[index // 8] &= ~(0x80 >> (index % 8)) & 0xFF
    return bytes(b)


def encode(bits: bytes) -> str:
    return "u" + base64.urlsafe_b64encode(gzip.compress(bits, mtime=0)).rstrip(b"=").decode()


def decode(encoded: str) -> bytes:
    if not encoded.startswith("u"):
        raise ValueError("encodedList must be multibase base64url (prefix 'u')")
    data = encoded[1:]
    return gzip.decompress(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)))


def set_bit(conn: psycopg.Connection, list_id: int, index: int, value: bool) -> None:
    """Change one bit inside the caller's transaction (row-locked)."""
    row = conn.execute("select bits from titlivo.status_lists where id = %s for update", (list_id,)).fetchone()
    bits = row["bits"] if isinstance(row, dict) else row[0]
    conn.execute(
        "update titlivo.status_lists set bits = %s, updated_at = now() where id = %s",
        (with_bit(bytes(bits), index, value), list_id),
    )


def allocate(conn: psycopg.Connection, list_id: int) -> int:
    """A random unused index, so neighbouring indexes reveal nothing about issue order."""
    size = get_settings().status_list_size
    col = "suspension_index" if list_id == SUSPENSION else "revocation_index"
    for _ in range(50):
        i = secrets.randbelow(size)
        if conn.execute(f"select 1 from titlivo.passports where {col} = %s", (i,)).fetchone() is None:
            return i
    raise RuntimeError("status list is full")


def list_url(list_id: int) -> str:
    return f"{get_settings().public_api_base}/status/{list_id}"


def credential_jwt(list_id: int) -> tuple[str, str]:
    """Signed BitstringStatusListCredential (vc+jwt) and an ETag for HTTP caching."""
    with pool().connection() as conn:
        row = conn.execute("select purpose, bits, updated_at from titlivo.status_lists where id = %s", (list_id,)).fetchone()
    if row is None:
        raise KeyError(list_id)
    bits = bytes(row["bits"])
    etag = hashlib.sha256(bits).hexdigest()[:32]
    payload: dict[str, Any] = {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": list_url(list_id),
        "type": ["VerifiableCredential", "BitstringStatusListCredential"],
        "issuer": did.issuer(),
        "validFrom": row["updated_at"].astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "credentialSubject": {
            "id": f"{list_url(list_id)}#list",
            "type": "BitstringStatusList",
            "statusPurpose": row["purpose"],
            "encodedList": encode(bits),
        },
    }
    header = {"alg": did.ALG, "typ": "vc+jwt", "kid": did.kid()}
    token = jws.serialize_compact(header, json.dumps(payload, separators=(",", ":")).encode(), did.signing_key(), algorithms=[did.ALG])
    return token, etag


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
