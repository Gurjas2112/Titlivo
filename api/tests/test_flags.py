from titlivo.tools import check_defects


def test_planted_defects_recall_100_precision_98(client):
    ok, report = check_defects.run()
    assert ok, report
    assert {r["flag"] for r in report} == {"F01", "F02", "F03", "F04", "F05", "F06", "F11", "F12", "F16"}


def test_flag_text_comes_from_evidence(client, demo):
    flags = client.get(f"/v1/parcels/{demo['F12']}/flags").json()["flags"]
    f12 = next(f for f in flags if f["id"] == "F12")
    assert f12["evidence"]["succession"]["mutation_no"] in f12["text"]
    assert f12["source_record_id"].startswith("DEMO-SR-")
