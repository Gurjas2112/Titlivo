def test_health(client):
    assert client.get("/healthz").json()["status"] == "ok"
    assert client.get("/healthz/db").json()["parcels"] == 270


def test_masking_anon_vs_key(client, demo, dev_headers):
    anon = client.get(f"/v1/parcels/{demo['hero']}").json()
    dev = client.get(f"/v1/parcels/{demo['hero']}", headers=dev_headers).json()
    assert anon["names_masked"] and all(h["masked"] and "****" in h["name"] for h in anon["canonical"]["holders"])
    assert not dev["names_masked"] and all(not h["masked"] for h in dev["canonical"]["holders"])
    for ev in anon["title_chain"]:
        assert all(p["masked"] for p in ev["from"] + ev["to"])


def test_never_says_safe(client, demo):
    d = client.get(f"/v1/parcels/{demo['hero']}").json()
    assert d["flags"] == [] and "No red flags found in the records available to Titlivo" in d["summary"]
    assert "safe" not in d["summary"].lower()


def test_canonical_and_native_both_returned(client, demo):
    d = client.get(f"/v1/parcels/{demo['hero']}").json()
    assert d["canonical"]["survey_no"] == "214/2" and d["native"]["record"]["भूमापन क्रमांक"] == "२१४/२"


def test_problem_json_and_coverage_header(client):
    r = client.get("/v1/parcels/DOES-NOT-EXIST")
    assert r.status_code == 404 and r.headers["content-type"] == "application/problem+json"
    assert "synthetic=true" in r.headers["x-coverage"]


def test_cross_script_search(client):
    latin = client.get("/v1/parcels/search", params={"q": "Nitin Bhosale"}).json()["results"]
    deva = client.get("/v1/parcels/search", params={"q": "नितीन भोसले"}).json()["results"]
    assert latin and deva and latin[0]["id"] == deva[0]["id"]


def test_ask_is_grounded(client, demo):
    r = client.post("/v1/ask", json={"parcel_id": demo["F02"], "question": "Is there a loan on this land?"}).json()
    assert r["grounded"] and "active mortgage" in r["text"]


def test_grounding_allows_disclaimers_but_not_claims():
    from titlivo.services.ask import grounding_check

    facts = '{"survey_no": "214/2", "as_of": "2026-11-01"}'
    assert grounding_check("No red flags found for 214/2. This is not a legal opinion.", facts) == []
    assert grounding_check("This land is safe to buy.", facts) == ["banned wording: safe"]
    assert grounding_check("A loan of ₹3,00,000 is recorded.", facts) == ["number not in records: 300000"]
