"""State adapters: native record (state's own keys, script, units, dates) → canonical bundle.

Each state is described by a YAML field map in config/field_maps/. The adapter never drops the
native record: the canonical bundle keeps a pointer to it and the API returns both.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any

import yaml

from titlivo.services import glossary, units
from titlivo.settings import REPO_ROOT


@dataclass
class CanonicalEvent:
    seq: int
    event_type: str
    native_term: str
    registered_on: date
    from_names: list[str]
    to_names: list[str]
    doc_no: str | None
    amount_inr: int | None
    mutation_no: str | None
    mutation_status: str | None
    basis_ref: str | None


@dataclass
class CanonicalEncumbrance:
    kind: str
    native_term: str
    lender: str
    amount_inr: int
    created_on: date
    released_on: date | None
    mutation_no: str | None

    @property
    def status(self) -> str:
        return "released" if self.released_on else "active"


@dataclass
class CanonicalLitigation:
    case_no: str
    court: str
    status: str
    filed_on: date


@dataclass
class CanonicalBundle:
    state_code: str
    record_type: str
    system_name: str
    village_id: str
    survey_no: str
    area_m2: Decimal
    native_area: str
    native_unit: str
    tenure_class: str
    tenure_native: str
    land_class: str
    holders: list[str]
    remarks: str
    events: list[CanonicalEvent] = field(default_factory=list)
    encumbrances: list[CanonicalEncumbrance] = field(default_factory=list)
    litigation: list[CanonicalLitigation] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


@lru_cache
def load_field_map(name: str) -> dict[str, Any]:
    with open(REPO_ROOT / "config" / "field_maps" / f"{name}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_amount(text: str | None) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^0-9]", "", units.ascii_digits(text))
    return int(digits) if digits else None


class StateAdapter:
    field_map_name: str = ""

    def __init__(self) -> None:
        self.fm = load_field_map(self.field_map_name)
        self.state = self.fm["state_code"]

    def _date(self, text: str | None) -> date | None:
        if not text:
            return None
        return datetime.strptime(units.ascii_digits(text).strip(), self.fm["date_format"]).date()

    def _term(self, domain: str, term: str, issues: list[str]) -> str:
        code, _ = glossary.map_term(domain, self.state, term)
        if code is None:
            issues.append(f"unknown {domain} term: {term!r}")
            return term  # unknown terms pass through, logged as ingest issues
        return code

    def to_canonical(self, native: dict[str, Any]) -> CanonicalBundle:
        fm, p, issues = self.fm, self.fm["parcel"], []
        area_text = native[p["area"]]
        bundle = CanonicalBundle(
            state_code=self.state,
            record_type=fm["record_type"],
            system_name=fm["system_name"],
            village_id=native[p["village_code"]],
            survey_no=units.ascii_digits(native[p["survey_no"]]),
            area_m2=units.to_sqm(area_text, fm["area_unit"]),
            native_area=area_text,
            native_unit=fm["area_unit"],
            tenure_class=self._term("tenure_class", native[p["tenure"]], issues),
            tenure_native=native[p["tenure"]],
            land_class=self._term("land_class", native[p["land_class"]], issues),
            holders=list(native.get(p["holders"], [])),
            remarks=native.get(p["remarks"], ""),
            issues=issues,
        )
        e = fm["events"]
        for i, ev in enumerate(native.get(e["list"], []), start=1):
            bundle.events.append(
                CanonicalEvent(
                    seq=i,
                    event_type=self._term("event_type", ev[e["type"]], issues),
                    native_term=ev[e["type"]],
                    registered_on=self._date(ev[e["date"]]),  # type: ignore[arg-type]
                    from_names=list(ev.get(e["from"], [])),
                    to_names=list(ev.get(e["to"], [])),
                    doc_no=ev.get(e["doc_no"]) and units.ascii_digits(ev[e["doc_no"]]),
                    amount_inr=parse_amount(ev.get(e["amount"])),
                    mutation_no=units.ascii_digits(str(ev[e["entry_no"]])),
                    mutation_status=self._term("mutation_status", ev[e["status"]], issues),
                    basis_ref=ev.get(e["basis"]) or None,
                )
            )
        m = fm["encumbrances"]
        for enc in native.get(m["list"], []):
            bundle.encumbrances.append(
                CanonicalEncumbrance(
                    kind=self._term("encumbrance_kind", enc[m["kind"]], issues),
                    native_term=enc[m["kind"]],
                    lender=enc[m["lender"]],
                    amount_inr=parse_amount(enc[m["amount"]]) or 0,
                    created_on=self._date(enc[m["date"]]),  # type: ignore[arg-type]
                    released_on=self._date(enc.get(m["released"])),
                    mutation_no=enc.get(m["mutation_no"]) and units.ascii_digits(str(enc[m["mutation_no"]])),
                )
            )
        lit = fm["litigation"]
        for case in native.get(lit["list"], []):
            bundle.litigation.append(
                CanonicalLitigation(
                    case_no=units.ascii_digits(case[lit["case_no"]]),
                    court=case[lit["court"]],
                    status=self._term("litigation_status", case[lit["status"]], issues),
                    filed_on=self._date(case[lit["date"]]),  # type: ignore[arg-type]
                )
            )
        return bundle

    # The generator uses the same field map in reverse, so native and canonical can never drift.
    def native_key(self, section: str, name: str) -> str:
        return self.fm[section][name]
