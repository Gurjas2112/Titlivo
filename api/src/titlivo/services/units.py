"""Area units used by Indian state land records, converted to and from square metres."""

from decimal import ROUND_HALF_UP, Decimal

SQM_PER_HECTARE = Decimal(10000)
SQM_PER_ARE = Decimal(100)
SQM_PER_ACRE = Decimal("4046.8564224")
GUNTAS_PER_ACRE = 40
SQM_PER_GUNTA = SQM_PER_ACRE / GUNTAS_PER_ACRE

_DIGITS = str.maketrans(
    "०१२३४५६७८९೦೧೨೩೪೫೬೭೮೯૦૧૨૩૪૫૬૭૮૯",
    "0123456789" * 3,
)


def ascii_digits(text: str) -> str:
    """Convert Devanagari, Kannada and Gujarati digits to ASCII digits."""
    return text.translate(_DIGITS)


def to_sqm(value: str, unit: str) -> Decimal:
    """Parse a native area string, e.g. "1.25" (ha.are), "2-15" (acre-gunta), "1-20-35"."""
    v = ascii_digits(value).strip()
    if unit == "hectare_are":
        ha, _, are = v.partition(".")
        return Decimal(int(ha or 0)) * SQM_PER_HECTARE + Decimal(int(are or 0)) * SQM_PER_ARE
    if unit == "acre_gunta":
        acre, _, gunta = v.partition("-")
        return (Decimal(int(acre or 0)) * SQM_PER_ACRE + Decimal(gunta or 0) * SQM_PER_GUNTA).quantize(Decimal("0.01"), ROUND_HALF_UP)
    if unit == "hectare_are_sqm":
        ha, are, sqm = (v.split("-") + ["0", "0"])[:3]
        return Decimal(int(ha)) * SQM_PER_HECTARE + Decimal(int(are)) * SQM_PER_ARE + Decimal(int(sqm))
    if unit == "sq_m":
        return Decimal(v)
    raise ValueError(f"unknown unit: {unit}")


def from_sqm(sqm: float | Decimal, unit: str) -> str:
    """Write square metres the way a state record would (used by the synthetic generator)."""
    s = Decimal(str(sqm))
    if unit == "hectare_are":
        total_are = int((s / SQM_PER_ARE).to_integral_value(ROUND_HALF_UP))
        return f"{total_are // 100}.{total_are % 100:02d}"
    if unit == "acre_gunta":
        total_g = int((s / SQM_PER_GUNTA).to_integral_value(ROUND_HALF_UP))
        return f"{total_g // GUNTAS_PER_ACRE}-{total_g % GUNTAS_PER_ACRE:02d}"
    if unit == "hectare_are_sqm":
        total = int(s.to_integral_value(ROUND_HALF_UP))
        return f"{total // 10000}-{(total % 10000) // 100:02d}-{total % 100:02d}"
    raise ValueError(f"unknown unit: {unit}")


def to_local_digits(text: str, script: str) -> str:
    base = {"devanagari": 0x0966, "kannada": 0x0CE6, "gujarati": 0x0AE6}[script]
    return "".join(chr(base + int(c)) if c.isdigit() and c.isascii() else c for c in text)
