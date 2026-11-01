"""Strings that must stay identical everywhere they appear (spec rules R4, 11)."""

PASSPORT_DISCLAIMER = (
    "Titlivo Title Passport: attests only to the records available to Titlivo on the issue date "
    "(synthetic demonstration data). Not a guarantee, certificate of title, legal digital "
    "signature or legal opinion."
)

DATA_DISCLAIMER = "Synthetic demonstration data. Not a legal opinion or a certified record."

NO_FLAGS_TEXT = "No red flags found in the records available to Titlivo (coverage: {coverage})."

STATES = {
    "27": {"code": "MH", "name": "Maharashtra", "record": "7/12 (Satbara)"},
    "29": {"code": "KA", "name": "Karnataka", "record": "RTC (Pahani)"},
    "24": {"code": "GJ", "name": "Gujarat", "record": "7/12 + 8-A"},
}

COVERAGE = {
    "states": ["MH", "KA", "GJ"],
    "sources": ["revenue record (7/12, RTC)", "mutation register", "encumbrances", "court cases"],
    "as_of": "2026-11-01",
    "synthetic": True,
}


def coverage_header() -> str:
    return "states=MH,KA,GJ; sources=revenue,mutations,encumbrances,courts; as_of=2026-11-01; synthetic=true"
