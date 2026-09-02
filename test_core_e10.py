#!/usr/bin/env python3
"""test_core_e10.py — POC E10 Phase A: Service Types configurable + riwayat service per-armada.

Memvalidasi:
  - CRUD /api/service-types + RBAC + cegah duplikat/builtin.
  - maintenance create menerima jenis service custom (type == key terdaftar).
  - GET /api/vehicles/{id}/maintenance -> totals + records (riwayat service per armada).

Run: cd /app && python test_core_e10.py  (backend hidup + DB ter-seed)
"""
import os
import sys
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / "backend" / ".env")
except Exception:
    pass

API = os.environ.get("API_BASE", "http://localhost:8001")
G, R, X = "\033[92m", "\033[91m", "\033[0m"
passed = failed = 0


def ok(m):
    global passed; passed += 1; print(f"  {G}[PASS]{X} {m}")


def bad(m):
    global failed; failed += 1; print(f"  {R}[FAIL]{X} {m}")


def check(c, m):
    ok(m) if c else bad(m)


def login(e):
    return requests.post(f"{API}/api/auth/login", json={"email": e, "password": "demo12345"}, timeout=20).json().get("token")


def H(t):
    return {"Authorization": f"Bearer {t}"}


def main():
    owner, drv = login("owner@demo.local"), login("driver@demo.local")
    check(owner and drv, "login owner/driver")

    print("\n--- Master Jenis Service ---")
    r = requests.get(f"{API}/api/service-types", headers=H(owner), timeout=20)
    lst = r.json() if r.status_code == 200 else []
    check(r.status_code == 200 and len(lst) >= 3, f"GET /service-types ({len(lst)} item)")
    check(all(str(s.get("id", "")).startswith("svt_") and s.get("key") for s in lst), "service_types id svt_ + punya key")
    r = requests.post(f"{API}/api/service-types", headers=H(owner),
                      json={"name": "Ganti Filter POC", "default_interval_km": 20000, "default_interval_days": 365}, timeout=20)
    new = r.json() if r.status_code == 200 else {}
    check(r.status_code == 200 and new.get("key") == "ganti_filter_poc", f"POST create (key slug={new.get('key')})")
    tid, tkey = new.get("id"), new.get("key")
    r = requests.post(f"{API}/api/service-types", headers=H(owner), json={"name": "Ganti Filter POC"}, timeout=20)
    check(r.status_code == 400, "duplikat nama/kunci -> 400")
    r = requests.post(f"{API}/api/service-types", headers=H(owner), json={"name": "Servis"}, timeout=20)
    check(r.status_code == 400, "bentrok dgn builtin (servis) -> 400")
    r = requests.post(f"{API}/api/service-types", headers=H(drv), json={"name": "X"}, timeout=20)
    check(r.status_code == 403, "RBAC driver create -> 403")
    r = requests.patch(f"{API}/api/service-types/{tid}", headers=H(owner), json={"active": False}, timeout=20)
    check(r.status_code == 200 and r.json().get("active") is False, "PATCH active=false")
    # aktifkan lagi agar valid untuk maintenance
    requests.patch(f"{API}/api/service-types/{tid}", headers=H(owner), json={"active": True}, timeout=20)

    print("\n--- Maintenance pakai jenis custom ---")
    veh = requests.get(f"{API}/api/vehicles", headers=H(owner), timeout=20).json()
    vid = veh[0]["id"]
    r = requests.post(f"{API}/api/maintenance", headers=H(owner),
                      json={"vehicle_id": vid, "type": tkey, "title": "Ganti filter via POC"}, timeout=20)
    check(r.status_code == 200 and r.json().get("type") == tkey, f"maintenance create type custom diterima ({r.json().get('type')})")

    print("\n--- Riwayat service per-armada ---")
    r = requests.get(f"{API}/api/vehicles/{vid}/maintenance", headers=H(owner), timeout=20)
    data = r.json() if r.status_code == 200 else {}
    tot = data.get("totals", {})
    check(r.status_code == 200 and "count" in tot and "total_cost" in tot, f"GET /vehicles/{{id}}/maintenance totals (count={tot.get('count')})")
    check(isinstance(data.get("records"), list) and len(data["records"]) >= 1, "records riwayat service berupa list")
    r = requests.get(f"{API}/api/vehicles/veh_tidakada/maintenance", headers=H(owner), timeout=20)
    check(r.status_code == 404, "vehicle tak ada -> 404")

    # cleanup
    requests.delete(f"{API}/api/service-types/{tid}", headers=H(owner), timeout=20)

    print(f"\n{'='*56}\n  {G}PASS {passed}{X} | {R}FAIL {failed}{X}\n{'='*56}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
