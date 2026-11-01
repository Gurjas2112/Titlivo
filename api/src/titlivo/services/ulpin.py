"""Demo ULPIN: "DEMO-" + 2-digit LGD state code + 12-character geohash of the parcel centroid."""

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def geohash(lat: float, lon: float, precision: int = 12) -> str:
    lat_rng, lon_rng = [-90.0, 90.0], [-180.0, 180.0]
    out, bits, ch, even = [], 0, 0, True
    while len(out) < precision:
        rng, val = (lon_rng, lon) if even else (lat_rng, lat)
        mid = (rng[0] + rng[1]) / 2
        if val >= mid:
            ch = (ch << 1) | 1
            rng[0] = mid
        else:
            ch <<= 1
            rng[1] = mid
        even = not even
        bits += 1
        if bits == 5:
            out.append(_BASE32[ch])
            bits, ch = 0, 0
    return "".join(out)


def demo_ulpin(state_code: str, lat: float, lon: float) -> str:
    return f"DEMO-{state_code}{geohash(lat, lon).upper()}"
