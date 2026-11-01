"""Title Passport issuance (spec §6.10, rule 11): a W3C VC 2.0 secured as vc+jwt, with no names.

The credential carries: parcel identity, owner COUNT + salted commitment (never names), the
result of every rule with a digest of its evidence, coverage, validity, two status entries
(suspension, revocation) and the disclaimer.
"""

import hashlib
import io
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import qrcode
import qrcode.image.svg
from joserfc import jws

from titlivo.constants import COVERAGE, PASSPORT_DISCLAIMER, STATES
from titlivo.db.pool import fetch_all, fetch_one, tx
from titlivo.services import did, status_list, translit
from titlivo.services import flags as flag_service
from titlivo.services.parcels import NotFound
from titlivo.settings import get_settings


def _digest(obj: Any) -> str:
    return "sha256-" + hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def verify_url(passport_id: str) -> str:
    return f"{get_settings().public_web_base}/v/{passport_id}"


def qr_svg(url: str) -> str:
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode()


def issue(parcel_id: str) -> dict[str, Any]:
    s = get_settings()
    with tx() as conn:
        p = fetch_one("parcel", {"parcel_id": parcel_id}, conn)
        if p is None:
            raise NotFound(parcel_id)
        holders = fetch_all("holders", {"parcel_id": parcel_id}, conn)
        flags = flag_service.recompute(conn, parcel_id)
        pid = str(uuid.uuid4())
        now = datetime.now(UTC).replace(microsecond=0)
        until = now + timedelta(days=s.passport_validity_days)
        salt = secrets.token_hex(16)
        commitment = hashlib.sha256((salt + "|" + "|".join(sorted(translit.name_key(h["name"]) for h in holders))).encode()).hexdigest()
        checks = []
        for rule_id, meta in flag_service.catalogue().items():
            hits = [f for f in flags if f["flag_id"] == rule_id]
            check = {"rule": rule_id, "title": meta["title"], "result": "flag" if hits else "clear", "severity": meta["severity"]}
            if hits:
                check["evidenceDigest"] = _digest([h["evidence"] for h in hits])
            checks.append(check)
        s_idx = status_list.allocate(conn, status_list.SUSPENSION)
        r_idx = status_list.allocate(conn, status_list.REVOCATION)
        credential = {
            "@context": ["https://www.w3.org/ns/credentials/v2", "https://titlivo.dev/ns/passport/v1"],
            "id": f"urn:uuid:{pid}",
            "type": ["VerifiableCredential", "TitlePassport"],
            "issuer": did.issuer(),
            "validFrom": _iso(now),
            "validUntil": _iso(until),
            "credentialSubject": {
                "id": f"urn:demo-ulpin:{p['id']}",
                "parcel": {
                    "ulpin": p["id"],
                    "state": STATES[p["state_code"]]["name"],
                    "district": p["district"],
                    "village": p["village"],
                    "surveyNo": p["survey_no"],
                    "recordedAreaM2": float(p["area_m2"]),
                    "recordType": p["system_name"],
                    "recordVersion": p["version"],
                },
                "owners": {"count": len(holders), "commitment": f"sha256-{commitment}"},
                "checks": checks,
                "summary": {"flags": len(flags), "high": sum(1 for f in flags if f["severity"] == "high")},
                "coverage": COVERAGE,
                "synthetic": True,
                "disclaimer": PASSPORT_DISCLAIMER,
            },
            "credentialStatus": [
                {
                    "id": f"{status_list.list_url(1)}#{s_idx}",
                    "type": "BitstringStatusListEntry",
                    "statusPurpose": "suspension",
                    "statusListIndex": str(s_idx),
                    "statusListCredential": status_list.list_url(1),
                },
                {
                    "id": f"{status_list.list_url(2)}#{r_idx}",
                    "type": "BitstringStatusListEntry",
                    "statusPurpose": "revocation",
                    "statusListIndex": str(r_idx),
                    "statusListCredential": status_list.list_url(2),
                },
            ],
        }
        header = {"alg": did.ALG, "typ": "vc+jwt", "kid": did.kid()}
        token = jws.serialize_compact(
            header, json.dumps(credential, separators=(",", ":")).encode(), did.signing_key(), algorithms=[did.ALG]
        )
        conn.execute(
            "insert into titlivo.passports (id, parcel_id, parcel_version, jwt, suspension_list, suspension_index, "
            "revocation_list, revocation_index, issued_at, valid_until) values (%s,%s,%s,%s,1,%s,2,%s,%s,%s)",
            (pid, parcel_id, p["version"], token, s_idx, r_idx, now, until),
        )
        conn.execute("insert into titlivo.passport_events (passport_id, kind, reason) values (%s, 'issued', null)", (pid,))
    return {"id": pid, "jwt": token, "credential": credential, "verify_url": verify_url(pid), "qr_svg": qr_svg(verify_url(pid))}


def get(passport_id: str) -> dict[str, Any]:
    try:
        uuid.UUID(passport_id)
    except ValueError as e:
        raise NotFound(passport_id) from e
    with tx() as conn:
        row = conn.execute("select * from titlivo.passports where id = %s", (passport_id,)).fetchone()
        if row is None:
            raise NotFound(passport_id)
        events = conn.execute(
            "select kind, reason, flag_ids, at from titlivo.passport_events where passport_id = %s order by at", (passport_id,)
        ).fetchall()
    return {
        "id": str(row["id"]),
        "parcel_id": row["parcel_id"],
        "jwt": row["jwt"],
        "issued_at": _iso(row["issued_at"]),
        "valid_until": _iso(row["valid_until"]),
        "verify_url": verify_url(passport_id),
        "qr_svg": qr_svg(verify_url(passport_id)),
        "events": [{**e, "at": _iso(e["at"])} for e in events],
    }


def for_parcel(parcel_id: str) -> list[dict[str, Any]]:
    with tx() as conn:
        rows = conn.execute(
            "select id, issued_at, valid_until from titlivo.passports where parcel_id = %s and superseded_by is null order by issued_at desc",
            (parcel_id,),
        ).fetchall()
    return [
        {
            "id": str(r["id"]),
            "issued_at": _iso(r["issued_at"]),
            "valid_until": _iso(r["valid_until"]),
            "verify_url": verify_url(str(r["id"])),
        }
        for r in rows
    ]
