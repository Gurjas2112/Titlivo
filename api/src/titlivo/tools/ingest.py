"""Ingest: native state records → adapters → canonical tables. Rebuilds the demo data from scratch.

Run: uv run python -m titlivo.tools.ingest [--url postgresql://…]
"""

import argparse
import hashlib
import json
from collections import Counter
from typing import Any

import psycopg
from shapely.geometry import shape

from titlivo.adapters import ADAPTERS
from titlivo.services import translit
from titlivo.services.ulpin import demo_ulpin
from titlivo.settings import REPO_ROOT, get_settings

SYN = REPO_ROOT / "data" / "synth"


def _id(prefix: str, *parts: str) -> str:
    return f"{prefix}-" + hashlib.sha1("|".join(parts).encode()).hexdigest()[:10].upper()


def run(url: str) -> dict[str, Any]:
    villages = json.loads((SYN / "villages.json").read_text(encoding="utf-8"))
    cadastral = {(c["village_id"], c["survey_no"]): c for c in json.loads((SYN / "cadastral.json").read_text())}
    issues: Counter[str] = Counter()
    stats: Counter[str] = Counter()

    # Pipeline mode sends statements without waiting for each reply: fast even to a distant database.
    with psycopg.connect(url, prepare_threshold=None) as conn, conn.transaction(), conn.pipeline():
        conn.execute(
            "truncate titlivo.passport_events, titlivo.passports, titlivo.parcel_flags, titlivo.litigation, "
            "titlivo.encumbrances, titlivo.title_events, titlivo.holdings, titlivo.parcels, titlivo.parties, "
            "titlivo.source_records, titlivo.villages cascade"
        )
        conn.execute("update titlivo.status_lists set bits = decode(repeat('00', size_bits / 8), 'hex'), next_free = 0")
        for v in villages:
            conn.execute(
                "insert into titlivo.villages (id, state_code, state, district, taluk, name, name_local, geom) "
                "values (%s,%s,%s,%s,%s,%s,%s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)))",
                (
                    v["id"],
                    v["state_code"],
                    {"27": "Maharashtra", "29": "Karnataka", "24": "Gujarat"}[v["state_code"]],
                    v["district"],
                    v["taluk"],
                    v["name"],
                    v["name_local"],
                    json.dumps(v["geometry"]),
                ),
            )
        parties: dict[str, str] = {}

        def party(state: str, local_name: str) -> str:
            pid = _id("DEMO-PTY", state, local_name)
            if pid not in parties:
                parties[pid] = local_name
                conn.execute(
                    "insert into titlivo.parties (id, name, name_local, name_key) values (%s,%s,%s,%s)",
                    (pid, translit.to_latin(local_name), local_name, translit.name_key(local_name)),
                )
            return pid

        for rtype, adapter in ADAPTERS.items():
            for f in sorted((SYN / "native" / rtype).glob("*.json")):
                native = json.loads(f.read_text(encoding="utf-8"))
                b = adapter.to_canonical(native)
                issues.update(b.issues)
                geo = shape(cadastral[(b.village_id, b.survey_no)]["geometry"])
                c = geo.centroid
                pid = demo_ulpin(b.state_code, c.y, c.x)
                sr = _id("DEMO-SR", rtype, b.village_id, b.survey_no)
                conn.execute(
                    "insert into titlivo.source_records (id, state_code, record_type, system_name, native, as_of) "
                    "values (%s,%s,%s,%s,%s,'2026-11-01')",
                    (sr, b.state_code, b.record_type, b.system_name, json.dumps(native, ensure_ascii=False)),
                )
                conn.execute(
                    "insert into titlivo.parcels (id, state_code, village_id, survey_no, area_m2, native_area, native_unit, "
                    "tenure_class, land_class, geom, source_record_id) values (%s,%s,%s,%s,%s,%s,%s,%s,%s, "
                    "ST_SetSRID(ST_GeomFromGeoJSON(%s),4326), %s)",
                    (
                        pid,
                        b.state_code,
                        b.village_id,
                        b.survey_no,
                        b.area_m2,
                        b.native_area,
                        b.native_unit,
                        b.tenure_class,
                        b.land_class,
                        json.dumps(cadastral[(b.village_id, b.survey_no)]["geometry"]),
                        sr,
                    ),
                )
                holders = [party(b.state_code, n) for n in b.holders]
                for h in holders:
                    conn.execute(
                        "insert into titlivo.holdings (parcel_id, party_id, share) values (%s,%s,%s)",
                        (pid, h, round(1 / len(holders), 4)),
                    )
                for ev in b.events:
                    conn.execute(
                        "insert into titlivo.title_events (id, parcel_id, seq, event_type, native_term, registered_on, "
                        "from_parties, to_parties, doc_no, amount_inr, mutation_no, mutation_status, basis_ref, remarks, "
                        "source_record_id) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (
                            _id("DEMO-EV", pid, str(ev.seq)),
                            pid,
                            ev.seq,
                            ev.event_type,
                            ev.native_term,
                            ev.registered_on,
                            [party(b.state_code, n) for n in ev.from_names],
                            [party(b.state_code, n) for n in ev.to_names],
                            ev.doc_no,
                            ev.amount_inr,
                            ev.mutation_no,
                            ev.mutation_status,
                            ev.basis_ref,
                            None,
                            sr,
                        ),
                    )
                for i, en in enumerate(b.encumbrances):
                    conn.execute(
                        "insert into titlivo.encumbrances (id, parcel_id, kind, native_term, lender, amount_inr, created_on, "
                        "released_on, status, mutation_no, source_record_id) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (
                            _id("DEMO-ENC", pid, str(i)),
                            pid,
                            en.kind,
                            en.native_term,
                            en.lender,
                            en.amount_inr,
                            en.created_on,
                            en.released_on,
                            en.status,
                            en.mutation_no,
                            sr,
                        ),
                    )
                for i, lc in enumerate(b.litigation):
                    conn.execute(
                        "insert into titlivo.litigation (id, parcel_id, case_no, court, status, filed_on, source_record_id) "
                        "values (%s,%s,%s,%s,%s,%s,%s)",
                        (_id("DEMO-LIT", pid, str(i)), pid, lc.case_no, lc.court, lc.status, lc.filed_on, sr),
                    )
                stats["parcels"] += 1
                stats["events"] += len(b.events)
        stats["parties"] = len(parties)
        demo = json.loads((SYN / "demo_parcels.json").read_text(encoding="utf-8"))
        conn.execute("delete from titlivo.demo_parcels")
        for key, ref in demo.items():
            conn.execute(
                "insert into titlivo.demo_parcels (key, parcel_id) select %s, id from titlivo.parcels "
                "where village_id = %s and survey_no = %s",
                (key, ref["village_id"], ref["survey_no"]),
            )
    return {"stats": dict(stats), "ingest_issues": dict(issues)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None)
    a = ap.parse_args()
    out = run(a.url or get_settings().database_url)
    from titlivo.services import flags

    out["flags"] = flags.recompute_all(a.url or get_settings().database_url)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
