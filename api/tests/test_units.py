import random
from decimal import Decimal

import pytest

from titlivo.services import units


@pytest.mark.parametrize(
    "value,unit,expected",
    [
        ("1.25", "hectare_are", Decimal(12500)),
        ("१.२५", "hectare_are", Decimal(12500)),  # Devanagari digits
        ("2-15", "acre_gunta", Decimal("9611.28")),
        ("1-20-35", "hectare_are_sqm", Decimal(12035)),
    ],
)
def test_to_sqm(value, unit, expected):
    assert units.to_sqm(value, unit) == expected


@pytest.mark.parametrize("unit,tolerance", [("hectare_are", 50), ("acre_gunta", 51), ("hectare_are_sqm", 0.5)])
def test_round_trip(unit, tolerance):
    r = random.Random(7)
    for _ in range(500):
        sqm = r.uniform(50, 200_000)
        assert abs(float(units.to_sqm(units.from_sqm(sqm, unit), unit)) - sqm) <= tolerance
