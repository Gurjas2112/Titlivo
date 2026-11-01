"""Living monitoring (spec §6.12, rule 13): a registry event arrives → rules re-run → any new
material flag suspends every live passport for the parcel. All of it commits in ONE transaction;
status-change notifications are published only after the commit.

Presets power the admin "Inject registry event" panel for the live-revocation demo.
"""

import asyncio
import hashlib
import random
from datetime import date, timedelta
from typing import Any

import psycopg

from titlivo.db.pool import fetch_all, tx
from titlivo.services import flags as flag_service
from titlivo.services import status_list, translit
from titlivo.services.parcels import NotFound
from titlivo.tools.synth import COURT, GIVEN, LENDERS, SURNAMES, term

PRESETS = {
    "heir_impersonation": "Sale by newly added heirs, no death record (Fraud Sentinel F12)",
    "double_sale": "Same owners sell the parcel twice (Fraud Sentinel F11)",
    "new_mortgage": "New mortgage registered, not released (F02)",
    "court_case": "Civil suit filed against the parcel (F03)",
}


# ---------- in-process pub/sub for the verifier page (Server-Sent Events) ----------
class Broker:
    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None
        self.subs: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}

    def subscribe(self, key: str) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.subs.setdefault(key, set()).add(q)
        return q

    def unsubscribe(self, key: str, q: asyncio.Queue[dict[str, Any]]) -> None:
        self.subs.get(key, set()).discard(q)

    def publish(self, key: str, message: dict[str, Any]) -> None:
        if self.loop is None:
            return
        for q in list(self.subs.get(key, ())):
            self.loop.call_soon_threadsafe(q.put_nowait, message)


broker = Broker()


def _party(conn: psycopg.Connection, state: str, local_name: str) -> str:
    pid = "DEMO-PTY-" + hashlib.sha1(f"{state}|{local_name}".encode()).hexdigest()[:10].upper()
    conn.execute(
        "insert into titlivo.parties (id, name, name_local, name_key) values (%s,%s,%s,%s) on conflict (id) do nothing",
        (pid, translit.to_latin(local_name), local_name, translit.name_key(local_name)),
    )
    return pid


def _add_event(
    conn: psycopg.Connection,
    p: dict[str, Any],
    code: str,
    on: date,
    frm: list[str],
    to: list[str],
    amount: int | None = None,
    basis: str | None = None,
) -> None:
    seq = conn.execute("select coalesce(max(seq), 0) + 1 as n from titlivo.title_events where parcel_id = %s", (p["id"],)).fetchone()["n"]
    mut = conn.execute(
        "select coalesce(max(mutation_no::int), 1000) + 7 as n from titlivo.title_events where parcel_id = %s", (p["id"],)
    ).fetchone()["n"]
    conn.execute(
        "insert into titlivo.title_events (id, parcel_id, seq, event_type, native_term, registered_on, from_parties, to_parties, "
        "doc_no, amount_inr, mutation_no, mutation_status, basis_ref, source_record_id, injected) "
        "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending',%s,%s,true)",
        (
            f"DEMO-EV-INJ-{p['id'][-6:]}-{seq}",
            p["id"],
            seq,
            code,
            term("event_type", p["state_code"], code),
            on,
            frm,
            to,
            f"{random.randint(1000, 9999)}/{on.year}" if code == "sale" else None,
            amount,
            str(mut),
            basis,
            p["source_record_id"],
        ),
    )


def inject(parcel_id: str, preset: str, today: date | None = None) -> dict[str, Any]:
    if preset not in PRESETS:
        raise ValueError(f"unknown preset; use one of {sorted(PRESETS)}")
    today = today or date.today()
    r = random.Random()
    suspended: list[str] = []
    with tx() as conn:
        p = conn.execute("select * from titlivo.parcels where id = %s for update", (parcel_id,)).fetchone()
        if p is None:
            raise NotFound(parcel_id)
        st = p["state_code"]
        before = {f["flag_id"] for f in fetch_all("parcel_flags", {"parcel_id": parcel_id}, conn)}
        holders = [h["id"] for h in fetch_all("holders", {"parcel_id": parcel_id}, conn)]
        name = lambda: _party(conn, st, f"{r.choice(GIVEN[st])} {r.choice(SURNAMES[st])}")
        price = int(float(p["area_m2"]) / 10000 * 3_500_000)
        if preset == "heir_impersonation":
            dead, heirs, buyer = holders[0], [name(), name()], name()
            _add_event(conn, p, "succession", today - timedelta(days=45), [dead], heirs, basis=None)
            _add_event(conn, p, "sale", today, heirs, [buyer], amount=price)
            new_holders = [h for h in holders if h != dead] + [buyer]
        elif preset == "double_sale":
            b1, b2 = name(), name()
            _add_event(conn, p, "sale", today - timedelta(days=30), holders, [b1], amount=price)
            _add_event(conn, p, "sale", today, holders, [b2], amount=price)
            new_holders = [b2]
        elif preset == "new_mortgage":
            conn.execute(
                "insert into titlivo.encumbrances (id, parcel_id, kind, native_term, lender, amount_inr, created_on, status, "
                "mutation_no, source_record_id, injected) values (%s,%s,'mortgage',%s,%s,%s,%s,'active',%s,%s,true)",
                (
                    f"DEMO-ENC-INJ-{r.randint(10**5, 10**6)}",
                    parcel_id,
                    term("encumbrance_kind", st, "mortgage"),
                    r.choice(LENDERS[st]),
                    int(round(price * 0.5, -4)),
                    today,
                    str(r.randint(2000, 2999)),
                    p["source_record_id"],
                ),
            )
            new_holders = holders
        else:
            conn.execute(
                "insert into titlivo.litigation (id, parcel_id, case_no, court, status, filed_on, source_record_id) "
                "values (%s,%s,%s,%s,'pending',%s,%s)",
                (
                    f"DEMO-LIT-INJ-{r.randint(10**5, 10**6)}",
                    parcel_id,
                    f"RCS/{r.randint(10, 999)}/{today.year}",
                    COURT[st],
                    today,
                    p["source_record_id"],
                ),
            )
            new_holders = holders
        if new_holders != holders:
            conn.execute("delete from titlivo.holdings where parcel_id = %s", (parcel_id,))
            for h in new_holders:
                conn.execute("insert into titlivo.holdings values (%s,%s,%s)", (parcel_id, h, round(1 / len(new_holders), 4)))
        conn.execute("update titlivo.parcels set version = version + 1 where id = %s", (parcel_id,))
        after = flag_service.recompute(conn, parcel_id)
        catalogue = flag_service.catalogue()
        new_material = sorted({f["flag_id"] for f in after if catalogue[f["flag_id"]]["material"]} - before)
        if new_material:
            reason = "; ".join(f"{f} {catalogue[f]['title']}" for f in new_material)
            for pp in conn.execute(
                "select id, suspension_index from titlivo.passports where parcel_id = %s and superseded_by is null", (parcel_id,)
            ).fetchall():
                status_list.set_bit(conn, status_list.SUSPENSION, pp["suspension_index"], True)
                conn.execute(
                    "insert into titlivo.passport_events (passport_id, kind, reason, flag_ids) values (%s,'suspended',%s,%s)",
                    (pp["id"], reason, new_material),
                )
                suspended.append(str(pp["id"]))
    # Published only after the transaction committed.
    for pid in suspended:
        broker.publish(pid, {"event": "status", "status": "SUSPENDED", "flags": new_material})
    broker.publish(f"parcel:{parcel_id}", {"event": "changed", "flags": [f["flag_id"] for f in after]})
    return {
        "parcel_id": parcel_id,
        "preset": preset,
        "new_material_flags": new_material,
        "suspended_passports": suspended,
        "flags": [flag_service.present(f) for f in after],
    }


def reset(parcel_id: str) -> dict[str, Any]:
    """Undo demo injections for a parcel and reinstate its passports (so the demo can be re-run)."""
    reinstated: list[str] = []
    with tx() as conn:
        if conn.execute("select 1 from titlivo.parcels where id = %s for update", (parcel_id,)).fetchone() is None:
            raise NotFound(parcel_id)
        conn.execute("delete from titlivo.title_events where parcel_id = %s and injected", (parcel_id,))
        conn.execute("delete from titlivo.encumbrances where parcel_id = %s and injected", (parcel_id,))
        conn.execute("delete from titlivo.litigation where parcel_id = %s and id like 'DEMO-LIT-INJ-%%'", (parcel_id,))
        # Rebuild current holders from the chain.
        chain = fetch_all("title_chain", {"parcel_id": parcel_id}, conn)
        holders = chain[-1]["holders_after"] if chain else []
        conn.execute("delete from titlivo.holdings where parcel_id = %s", (parcel_id,))
        for h in holders:
            conn.execute("insert into titlivo.holdings values (%s,%s,%s)", (parcel_id, h, round(1 / len(holders), 4)))
        conn.execute("update titlivo.parcels set version = version + 1 where id = %s", (parcel_id,))
        after = flag_service.recompute(conn, parcel_id)
        for pp in conn.execute(
            "select id, suspension_index from titlivo.passports where parcel_id = %s and superseded_by is null", (parcel_id,)
        ).fetchall():
            status_list.set_bit(conn, status_list.SUSPENSION, pp["suspension_index"], False)
            conn.execute(
                "insert into titlivo.passport_events (passport_id, kind, reason) values (%s,'reinstated','demo reset')", (pp["id"],)
            )
            reinstated.append(str(pp["id"]))
    for pid in reinstated:
        broker.publish(pid, {"event": "status", "status": "LIVE"})
    broker.publish(f"parcel:{parcel_id}", {"event": "changed", "flags": [f["flag_id"] for f in after]})
    return {"parcel_id": parcel_id, "reinstated_passports": reinstated, "flags": [flag_service.present(f) for f in after]}
