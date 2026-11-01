"""Parcel service: the one place REST, MCP and the Ask agent get parcel facts from (rule 8)."""

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from titlivo.auth import Caller
from titlivo.constants import COVERAGE, DATA_DISCLAIMER, NO_FLAGS_TEXT, STATES
from titlivo.db.pool import fetch_all, fetch_one, pool
from titlivo.services import flags as flag_service
from titlivo.services import glossary, translit, units


class NotFound(Exception):
    pass


def _name(row: dict[str, Any], caller: Caller) -> dict[str, Any]:
    if caller.can_see_names:
        return {"id": row["id"], "name": row["name"], "name_local": row["name_local"], "masked": False}
    return {"id": row["id"], "name": translit.mask(row["name"]), "name_local": None, "masked": True}


def search(q: str, caller: Caller, limit: int = 20) -> list[dict[str, Any]]:
    q = q.strip()
    ascii_q = units.ascii_digits(q)
    survey = ascii_q if re.fullmatch(r"[0-9]+(/[0-9A-Za-z]+)*", ascii_q) else ""
    key = "" if survey else translit.name_key(q)
    rows = fetch_all("search", {"q_survey": survey, "q_key": key, "q_text": q.lower(), "lim": limit})
    return [
        {
            "id": r["id"],
            "survey_no": r["survey_no"],
            "state": STATES[r["state_code"]]["code"],
            "village": r["village"],
            "village_local": r["village_local"],
            "district": r["district"],
            "flag_count": r["flag_count"],
            "max_severity": {3: "high", 2: "medium", 1: "info"}.get(r["max_severity"]),
        }
        for r in rows
    ]


def get_flags(parcel_id: str, lang: str = "en", check: bool = True) -> list[dict[str, Any]]:
    if check:
        _require(parcel_id)
    return [flag_service.present({**f, "flag_id": f["flag_id"]}, lang) for f in fetch_all("parcel_flags", {"parcel_id": parcel_id})]


def _require(parcel_id: str) -> dict[str, Any]:
    p = fetch_one("parcel", {"parcel_id": parcel_id})
    if p is None:
        raise NotFound(parcel_id)
    return p


def title_chain(parcel_id: str, caller: Caller, since_year: int = 1900, check: bool = True) -> list[dict[str, Any]]:
    if check:
        _require(parcel_id)
    chain = fetch_all("title_chain", {"parcel_id": parcel_id})
    ids = sorted({x for e in chain for x in (e["from_parties"] + e["to_parties"])})
    names = {r["id"]: _name(r, caller) for r in fetch_all("parties", {"ids": ids})}
    gloss = {e["local_term"]: e["en"] for e in glossary.entries() if e["domain"] == "event_type"}
    out = []
    for e in chain:
        if e["registered_on"].year < since_year:
            continue
        out.append(
            {
                "position": e["position"],
                "event_type": e["event_type"],
                "native_term": e["native_term"],
                "native_term_en": gloss.get(e["native_term"]),
                "registered_on": e["registered_on"].isoformat(),
                "from": [names[x] for x in e["from_parties"]],
                "to": [names[x] for x in e["to_parties"]],
                "consistent": e["consistent"],
                "doc_no": e["doc_no"],
                "amount_inr": e["amount_inr"],
                "mutation_no": e["mutation_no"],
                "mutation_status": e["mutation_status"],
                "basis_ref": e["basis_ref"],
                "gap_days": e["gap_days"],
                "injected": e["injected"],
                "source_record_id": e["source_record_id"],
            }
        )
    return out


def dossier(parcel_id: str, caller: Caller, lang: str = "en") -> dict[str, Any]:
    p = _require(parcel_id)
    state = STATES[p["state_code"]]
    # Independent reads run in parallel: the database may be a long round trip away.
    args = {"parcel_id": parcel_id}
    with ThreadPoolExecutor(max_workers=5) as ex:
        f_holders = ex.submit(fetch_all, "holders", args)
        f_flags = ex.submit(get_flags, parcel_id, lang, False)
        f_chain = ex.submit(title_chain, parcel_id, caller, 1900, False)
        f_enc = ex.submit(fetch_all, "encumbrances", args)
        f_lit = ex.submit(fetch_all, "litigation", args)
    holders, flags = f_holders.result(), f_flags.result()
    tenure_term = next((e for e in glossary.entries() if e["domain"] == "tenure_class" and e["canonical"] == p["tenure_class"]), None)
    coverage = {**COVERAGE, "parcel_sources": [p["system_name"]]}
    native = p["native"]
    if not caller.can_see_names:
        native = _mask_native(native, p["record_type"])
    return {
        "id": p["id"],
        "ulpin": p["id"],
        "synthetic": True,
        "version": p["version"],
        "canonical": {
            "state": state["name"],
            "state_code": p["state_code"],
            "state_record": state["record"],
            "district": p["district"],
            "taluk": p["taluk"],
            "village": p["village"],
            "village_local": p["village_local"],
            "village_id": p["village_id"],
            "survey_no": p["survey_no"],
            "area_m2": float(p["area_m2"]),
            "mapped_area_m2": float(p["mapped_area_m2"]),
            "area_native": {"value": p["native_area"], "unit": p["native_unit"]},
            "tenure_class": p["tenure_class"],
            "tenure_en": tenure_term["en"] if tenure_term else p["tenure_class"],
            "tenure_restricted": bool(tenure_term and tenure_term["restricted"]),
            "land_class": p["land_class"],
            "holders": [{**_name(h, caller), "share": float(h["share"])} for h in holders],
            "centroid": {"lat": p["lat"], "lon": p["lon"]},
        },
        "native": {"record_type": p["record_type"], "system": p["system_name"], "as_of": p["as_of"].isoformat(), "record": native},
        "geometry": p["geometry"],
        "title_chain": f_chain.result(),
        "encumbrances": [_enc(e) for e in f_enc.result()],
        "litigation": [{**r, "filed_on": r["filed_on"].isoformat()} for r in f_lit.result()],
        "flags": flags,
        "summary": _summary(flags, coverage),
        "coverage": coverage,
        "names_masked": not caller.can_see_names,
        "source_record_id": p["source_record_id"],
        "disclaimer": DATA_DISCLAIMER,
    }


def _enc(e: dict[str, Any]) -> dict[str, Any]:
    return {**e, "created_on": e["created_on"].isoformat(), "released_on": e["released_on"] and e["released_on"].isoformat()}


def _summary(flags: list[dict[str, Any]], coverage: dict[str, Any]) -> str:
    if not flags:
        return NO_FLAGS_TEXT.format(coverage=", ".join(coverage["sources"]) + f", as of {coverage['as_of']}")
    high = sum(1 for f in flags if f["severity"] == "high")
    return f"{len(flags)} red flag(s) found ({high} high severity) in the records available to Titlivo. Review each one with its source record."


def _mask_native(native: dict[str, Any], record_type: str) -> dict[str, Any]:
    """Masks names inside the native record for callers without parcels:pii."""
    from titlivo.adapters import ADAPTERS

    fm = ADAPTERS[record_type].fm
    out = dict(native)
    hk = fm["parcel"]["holders"]
    out[hk] = [_mask_local(n) for n in native.get(hk, [])]
    ek = fm["events"]
    out[ek["list"]] = [
        {**ev, ek["from"]: [_mask_local(n) for n in ev.get(ek["from"], [])], ek["to"]: [_mask_local(n) for n in ev.get(ek["to"], [])]}
        for ev in native.get(ek["list"], [])
    ]
    return out


def _mask_local(name: str) -> str:
    parts = name.split()
    return " ".join(p[0] + "…" for p in parts[:-1]) + (" " if len(parts) > 1 else "") + parts[-1][0] + "****"


def map_layer() -> dict[str, Any]:
    with pool().connection() as conn:
        parcels = conn.execute(open_sql("parcels_geojson")).fetchone()["fc"]
        villages = conn.execute(open_sql("villages_geojson")).fetchone()["fc"]
    return {"parcels": parcels, "villages": villages}


def open_sql(name: str) -> str:
    from titlivo.db.pool import sql

    return sql(name)


def coverage() -> dict[str, Any]:
    rows = fetch_all("coverage")
    return {**COVERAGE, "by_state": [{**r, "code": STATES[r["state_code"]]["code"]} for r in rows]}
