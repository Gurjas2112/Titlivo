"""Native-term glossary (config/glossary.yaml): map a state's own word to a canonical code."""

from functools import lru_cache
from typing import Any

import yaml

from titlivo.settings import REPO_ROOT


@lru_cache
def load() -> dict[str, Any]:
    with open(REPO_ROOT / "config" / "glossary.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def map_term(domain: str, state_code: str, term: str) -> tuple[str | None, dict[str, Any]]:
    """Return (canonical_code, entry). Unknown terms return (None, {}) and are logged by ingest."""
    entry = load().get(domain, {}).get(state_code, {}).get(term.strip())
    if entry is None:
        return None, {}
    if isinstance(entry, str):
        return entry, {"code": entry}
    return entry["code"], entry


def entries() -> list[dict[str, Any]]:
    """Flat list for GET /v1/glossary and the UI glossary page."""
    out = []
    for domain, by_state in load().items():
        for state, terms in by_state.items():
            for local, entry in terms.items():
                e = entry if isinstance(entry, dict) else {"code": entry}
                out.append(
                    {
                        "domain": domain,
                        "state_code": state,
                        "local_term": local,
                        "canonical": e["code"],
                        "en": e.get("en", e["code"].replace("_", " ")),
                        "restricted": e.get("restricted", False),
                    }
                )
    return out


def restricted_tenures() -> set[str]:
    return {e["code"] for terms in load()["tenure_class"].values() for e in terms.values() if e.get("restricted")}
