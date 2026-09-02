#!/usr/bin/env python3
"""fa_5xx_fuzz.py (FORENSIK) — fuzz adversarial LUAS: endpoint TIDAK boleh 5xx pada input buruk.

Enumerasi POST/PATCH/PUT dari `/openapi.json`, kirim payload adversarial (kosong, tipe salah,
markup, negatif, string raksasa, operator Mongo). Assert status < 500. Melengkapi INV-5XX-01
(spesifik) dgn cakupan LUAS otomatis. Jalankan via `scripts/run_forensics.sh` (reseed sesudahnya).
Bukan gate (bisa buat data sampah) — alat bug-hunt.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("GUARD_BASE_URL", "http://127.0.0.1:8001")
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; X = "\033[0m"

SKIP_SUBSTR = ("/auth/logout", "/seed", "/reset", "/wa/webhook", "/gps/webhook")
MISSING = object()
BAD_BODIES = [
    ("empty", {}),
    ("null", None),
    ("array-not-object", []),
    ("string-not-object", "x"),
    ("adversarial", {"a": "<b>&</b>", "amount": -999999, "price": "gratis",
                     "name": "A" * 20000, "qty": -1, "email": {"$ne": None},
                     "criteria": {"$where": "1"}, "lat": "abc", "items": "notalist"}),
    ("mongo-op", {"id": {"$gt": ""}, "filter": {"$ne": None}}),
]


def req(method, full_path, token, body):
    data = None if body is MISSING else json.dumps(body).encode()
    r = urllib.request.Request(BASE + full_path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=25) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:  # noqa: BLE001
        return -1


def login():
    r = urllib.request.Request(BASE + "/api/auth/login",
                               data=json.dumps({"email": "owner@demo.local", "password": "demo12345"}).encode(),
                               method="POST")
    r.add_header("Content-Type", "application/json")
    try:
        return json.loads(urllib.request.urlopen(r, timeout=15).read())["token"]
    except Exception:  # noqa: BLE001
        return None


def openapi_paths():
    try:
        return json.load(urllib.request.urlopen(BASE + "/openapi.json", timeout=15)).get("paths", {})
    except Exception as e:  # noqa: BLE001
        print(f"{R}gagal ambil openapi: {e}{X}")
        return {}


def main() -> int:
    tok = login()
    if not tok:
        print(f"{R}login gagal — backend hidup?{X}")
        return 2
    paths = openapi_paths()
    targets = []
    for p, ops in paths.items():
        if any(s in p for s in SKIP_SUBSTR):
            continue
        for m in ops:
            if m in ("post", "patch", "put"):
                targets.append((m.upper(), p))
    fails = []
    n = 0
    for method, p in targets:
        url = re.sub(r'\{[^}]+\}', 'advtest', p)  # ganti path-param dgn dummy
        for label, body in BAD_BODIES:
            n += 1
            st = req(method, url, tok, MISSING if body is None else body)
            if st >= 500:
                fails.append((method, p, label, st))
    print(f"=== fa_5xx_fuzz: {len(targets)} endpoint × {len(BAD_BODIES)} payload = {n} probe ===")
    if fails:
        print(f"{R}✗ {len(fails)} respons 5xx (BUG — input buruk HARUS 4xx, bukan crash):{X}")
        for method, p, label, st in fails[:50]:
            print(f"   {R}{st}{X} {method} {p}  [{label}]")
        return 1
    print(f"{G}✓ Tidak ada 5xx pada seluruh probe adversarial.{X}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
