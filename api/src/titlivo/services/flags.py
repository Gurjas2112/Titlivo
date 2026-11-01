"""Red-flag rules: run the SQL files, render plain-language text from the evidence only."""

import json
import re
from functools import lru_cache
from typing import Any

import psycopg
from psycopg.rows import dict_row

from titlivo.db.pool import QUERIES, pool, sql
from titlivo.services import glossary
from titlivo.settings import REPO_ROOT

SEVERITY_ORDER = {"high": 3, "medium": 2, "info": 1}


@lru_cache
def catalogue() -> dict[str, dict[str, Any]]:
    import yaml

    with open(REPO_ROOT / "config" / "flags.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def rule_sql(flag_id: str) -> str:
    text = (QUERIES / "flags" / f"{flag_id}.sql").read_text(encoding="utf-8")
    chain = sql("title_chain").rstrip().removesuffix("order by parcel_id, rn")
    return text.replace("{{title_chain}}", chain)


def _lookup(evidence: dict[str, Any], dotted: str) -> Any:
    cur: Any = evidence
    for part in dotted.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
    return cur


def _fmt(v: Any) -> str:
    if isinstance(v, int) and not isinstance(v, bool) and v >= 1000:
        return f"{v:,}"
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    if v is None:
        return "none"
    return str(v).replace("_", " ") if isinstance(v, str) and re.fullmatch(r"[a-z_0-9]+", v) else str(v)


def render(flag_id: str, evidence: dict[str, Any], lang: str = "en") -> str:
    tpl = catalogue()[flag_id]["template"].get(lang) or catalogue()[flag_id]["template"]["en"]
    return re.sub(r"\{([a-z_.]+)\}", lambda m: _fmt(_lookup(evidence, m.group(1))), tpl)


def evaluate(conn: psycopg.Connection, parcel_id: str | None) -> list[dict[str, Any]]:
    params = {"parcel_id": parcel_id, "restricted": sorted(glossary.restricted_tenures())}
    out = []
    for flag_id, meta in catalogue().items():
        with conn.cursor(row_factory=dict_row) as cur:
            for row in cur.execute(rule_sql(flag_id), params).fetchall():
                ev = row["evidence"] if isinstance(row["evidence"], dict) else json.loads(row["evidence"])
                out.append(
                    {
                        "parcel_id": row["parcel_id"],
                        "flag_id": flag_id,
                        "severity": meta["severity"],
                        "evidence": json.loads(json.dumps(ev, default=str)),
                        "source_record_id": row["source_record_id"],
                    }
                )
    return out


def store(conn: psycopg.Connection, parcel_id: str | None, flags: list[dict[str, Any]]) -> None:
    if parcel_id is None:
        conn.execute("delete from titlivo.parcel_flags")
    else:
        conn.execute("delete from titlivo.parcel_flags where parcel_id = %s", (parcel_id,))
    with conn.cursor() as cur:
        cur.executemany(
            "insert into titlivo.parcel_flags (parcel_id, flag_id, severity, evidence, source_record_id) values (%s,%s,%s,%s,%s)",
            [(f["parcel_id"], f["flag_id"], f["severity"], json.dumps(f["evidence"]), f["source_record_id"]) for f in flags],
        )


def recompute(conn: psycopg.Connection, parcel_id: str) -> list[dict[str, Any]]:
    flags = evaluate(conn, parcel_id)
    store(conn, parcel_id, flags)
    return flags


def recompute_all(url: str | None = None) -> dict[str, int]:
    def go(conn: psycopg.Connection) -> dict[str, int]:
        flags = evaluate(conn, None)
        store(conn, None, flags)
        counts: dict[str, int] = {}
        for f in flags:
            counts[f["flag_id"]] = counts.get(f["flag_id"], 0) + 1
        return dict(sorted(counts.items()))

    if url:
        with psycopg.connect(url, prepare_threshold=None) as conn, conn.transaction():
            return go(conn)
    with pool().connection() as conn, conn.transaction():
        return go(conn)


def present(flag: dict[str, Any], lang: str = "en") -> dict[str, Any]:
    """API shape for one flag: id, severity, title, plain text, evidence, source."""
    meta = catalogue()[flag["flag_id"]]
    return {
        "id": flag["flag_id"],
        "title": meta["title"],
        "severity": flag["severity"],
        "material": meta["material"],
        "text": render(flag["flag_id"], flag["evidence"], lang),
        "basis": meta["basis"],
        "evidence": flag["evidence"],
        "source_record_id": flag["source_record_id"],
    }
