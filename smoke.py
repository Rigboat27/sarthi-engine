"""Smoke test against a running engine: assert the whole surface is healthy.

Run after `python run.py`:  python smoke.py
Exits 0 when everything responds, 1 otherwise.
"""

import sys

import httpx

BASE = "http://127.0.0.1:8787"


def main() -> None:
    c = httpx.Client(base_url=BASE, timeout=15)

    h = c.get("/health").json()
    assert h["ok"], h
    print(f"health  v{h['data']['version']}  mock={h['data']['mockMode']}")

    consent = c.post("/aa/consent", json={"aggregatorId": "onemoney", "scopes": ["bank", "demat"]}).json()
    cid = consent["data"]["consentId"]
    assert c.post("/aa/verify", json={"consentId": cid}).json()["ok"]
    fetched = c.post("/aa/fetch", json={"consentId": cid}).json()
    assert fetched["ok"]
    print(f"aa      {len(fetched['data']['fips'])} FIPs")

    m = c.post("/docs/match", json={"a": "Ramesh Sharma", "b": "Ramesh Sharm"}).json()
    assert m["ok"]
    print(f"match   score={m['data']['score']}")

    assert c.get("/data/rules").json()["ok"]
    assert c.get("/data/brokers", params={"name": "groww"}).json()["ok"]
    assert c.get("/data/nodal", params={"company": "Infosys"}).json()["ok"]
    print("data    rules / brokers / nodal ok")

    # extension-compatible proxy routes (mock mode)
    stt = c.post("/stt").json()
    assert "detectedLang" in stt, stt
    tts = c.post("/tts", json={"text": "hi", "language_code": "en-IN"}).json()
    assert "audios" in tts, tts
    g = c.post("/gemini/gemini-3.5-flash-lite:generateContent", json={}).json()
    assert "candidates" in g, g
    print("proxy   /stt /tts /gemini ok")

    print("\nall green")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print("FAIL:", e)
        sys.exit(1)
