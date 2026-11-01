import json

import pytest

from titlivo.adapters import ADAPTERS
from titlivo.settings import REPO_ROOT

NATIVE = REPO_ROOT / "data" / "synth" / "native"


@pytest.mark.parametrize("rtype", ["mh_712", "ka_rtc", "gj_712"])
def test_every_record_maps_without_unknown_terms(rtype):
    files = sorted((NATIVE / rtype).glob("*.json"))
    assert len(files) == 90
    for f in files:
        b = ADAPTERS[rtype].to_canonical(json.loads(f.read_text(encoding="utf-8")))
        assert b.issues == [], (f.name, b.issues)
        assert b.area_m2 > 0 and b.survey_no.replace("/", "").isascii()
        assert all(e.registered_on.year >= 1990 for e in b.events)


def test_marathi_record_is_harmonised():
    native = json.loads((NATIVE / "mh_712" / "DEMO-V-27-01_214-2.json").read_text(encoding="utf-8"))
    b = ADAPTERS["mh_712"].to_canonical(native)
    assert native["भूमापन क्रमांक"] == "२१४/२" and b.survey_no == "214/2"
    assert b.native_unit == "hectare_are" and b.events[0].event_type == "grant"
    assert {e.event_type for e in b.events} <= {"grant", "sale", "gift", "succession"}
