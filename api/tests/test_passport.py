import base64
import json

from titlivo.services import status_list


def _payload(jwt):
    p = jwt.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))


def test_bitstring_round_trip():
    bits = bytes(16384)
    for i in (0, 7, 8, 131071):
        bits = status_list.with_bit(bits, i, True)
        assert status_list.get_bit(status_list.decode(status_list.encode(bits)), i)
    assert not status_list.get_bit(bits, 1)


def test_issue_verify_tamper_suspend_reset(client, demo, admin_headers, dev_headers):
    hero = demo["hero"]
    p = client.post(f"/v1/parcels/{hero}/passports").json()
    jwt = p["jwt"]
    cred = _payload(jwt)
    holders = client.get(f"/v1/parcels/{hero}", headers=dev_headers).json()["canonical"]["holders"]
    assert all(h["name"] not in json.dumps(cred) and h["name_local"] not in json.dumps(cred, ensure_ascii=False) for h in holders)
    assert cred["credentialSubject"]["owners"]["count"] == len(holders)
    assert client.post("/v1/passports/verify", json={"jwt": jwt}).json()["status"] == "LIVE"

    h, _, sig = jwt.split(".")
    cred["credentialSubject"]["summary"]["flags"] = 0
    forged = h + "." + base64.urlsafe_b64encode(json.dumps(cred).encode()).rstrip(b"=").decode() + "." + sig
    assert client.post("/v1/passports/verify", json={"jwt": forged}).json()["status"] == "INVALID_SIGNATURE"

    assert client.post("/v1/admin/events", json={"parcel_id": hero, "preset": "heir_impersonation"}).status_code == 401
    r = client.post("/v1/admin/events", json={"parcel_id": hero, "preset": "heir_impersonation"}, headers=admin_headers).json()
    assert r["new_material_flags"] == ["F12"] and p["id"] in r["suspended_passports"]
    assert client.post("/v1/passports/verify", json={"jwt": jwt}).json()["status"] == "SUSPENDED"

    client.post("/v1/admin/demo/reset", json={"parcel_id": hero}, headers=admin_headers)
    assert client.post("/v1/passports/verify", json={"jwt": jwt}).json()["status"] == "LIVE"
    assert client.get(f"/v1/parcels/{hero}").json()["flags"] == []


def test_status_list_is_signed_and_cacheable(client):
    r = client.get("/status/1")
    assert r.headers["content-type"].startswith("application/vc+jwt") and "max-age=60" in r.headers["cache-control"]
    assert client.get("/status/1", headers={"If-None-Match": r.headers["etag"]}).status_code == 304
