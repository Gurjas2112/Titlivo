"""Grade the flag rules against the defects planted by the generator (CI gate, spec §7).

Recall must be 100 % and precision at least 98 % for every rule, or the exit code is 1.
Run: uv run python -m titlivo.tools.check_defects
"""

import csv
import sys

from titlivo.db.pool import pool
from titlivo.settings import REPO_ROOT


def run() -> tuple[bool, list[dict[str, object]]]:
    with open(REPO_ROOT / "data" / "truth" / "defects.csv", encoding="utf-8") as f:
        truth_rows = list(csv.DictReader(f))
    with pool().connection() as conn:
        ids = {(r["village_id"], r["survey_no"]): r["id"] for r in conn.execute("select id, village_id, survey_no from titlivo.parcels")}
        detected = {
            (r["parcel_id"], r["flag_id"])
            for r in conn.execute(
                "select distinct parcel_id, flag_id from titlivo.parcel_flags where parcel_id in (select parcel_id from titlivo.parcel_flags)"
            )
        }
        injected = {
            r["parcel_id"]
            for r in conn.execute(
                "select distinct parcel_id from titlivo.title_events where injected union select parcel_id from titlivo.encumbrances where injected"
            )
        }
    planted = {(ids[(r["village_id"], r["survey_no"])], r["flag_id"]) for r in truth_rows}
    detected = {d for d in detected if d[0] not in injected}  # ignore live-demo injections
    ok, report = True, []
    for flag in sorted({f for _, f in planted | detected}):
        p = {x for x in planted if x[1] == flag}
        d = {x for x in detected if x[1] == flag}
        tp = len(p & d)
        recall = tp / len(p) if p else 1.0
        precision = tp / len(d) if d else 1.0
        passed = recall == 1.0 and precision >= 0.98
        ok &= passed
        report.append({"flag": flag, "planted": len(p), "detected": len(d), "recall": recall, "precision": precision, "pass": passed})
    return ok, report


def main() -> None:
    ok, report = run()
    print(f"{'flag':5} {'planted':>7} {'detected':>8} {'recall':>7} {'precision':>9}  result")
    for r in report:
        print(
            f"{r['flag']:5} {r['planted']:>7} {r['detected']:>8} {r['recall']:>7.0%} {r['precision']:>9.0%}  {'PASS' if r['pass'] else 'FAIL'}"
        )
    print("ALL PASS" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
