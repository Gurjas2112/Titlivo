"""Reject blank or near-blank demo screenshots (spec §16.5) and list what was captured.

Run: uv run python -m titlivo.tools.check_shots
"""

import hashlib
import json
import sys

from PIL import Image, ImageStat

from titlivo.settings import REPO_ROOT

MEDIA = REPO_ROOT / "demo-media"


def main() -> None:
    manifest = json.loads((MEDIA / "manifest.json").read_text(encoding="utf-8"))
    seen: dict[str, str] = {}
    bad = []
    for s in manifest["shots"]:
        path = MEDIA / s["file"]
        img = Image.open(path).convert("L")
        std = ImageStat.Stat(img).stddev[0]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if std < 255 * 0.02:
            bad.append(f"{s['file']}: near-blank (luminance std {std:.1f})")
        if digest in seen:
            bad.append(f"{s['file']}: identical to {seen[digest]}")
        seen[digest] = s["file"]
    print(f"{len(manifest['shots'])} screenshots checked, {len(bad)} problems")
    for b in bad:
        print("  ✗", b)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
