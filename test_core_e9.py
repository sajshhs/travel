#!/usr/bin/env python3
"""test_core_e9.py — POC E9 Phase B: Trip/KM & odometer integration.

Memvalidasi:
  - compute_distance: basis odometer (akurat) + fallback OSRM (est) + None (deterministik, no network).
  - checkin(odometer_start) + checkout(odometer_end) -> trip.distance_km = selisih, basis 'odometer',
    dan vehicles.odometer ikut ter-update.
  - GET /api/drivers/{id}/performance -> stats + trips[].
  - GET /api/vehicles/{id}/trips -> totals + trips[].

Run: cd /app && python test_core_e9.py  (backend hidup + DB ter-seed)
"""
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / "backend" / ".env")
except Exception:
    pass
from services.trips import compute_distance  # noqa: E402

API = os.environ.get("API_BASE", "http://localhost:8001")
G, R, X = "\033[92m", "\033[91m", "\033[0m"
passed = failed = 0


def ok(m):
    global passed; passed += 1; print(f"  {G}[PASS]{X} {m}")


def bad(m):
    global failed; failed += 1; print(f"  {R}[FAIL]{X} {m}")


def check(c, m):
    ok(m) if c else bad(m)


def login(email):
    return requests.post(f"{API}/api/auth/login", json={"email": email, "password": "demo12345"}, timeout=20).json().get("token")


def H(t):
    return {"Authorization": f"Bearer {t}"}


def main():
    print("--- compute_distance (unit, tanpa network) ---")
    d, b = compute_distance(80000, 80250)
    check(d == 250.0 and b == "odometer", f"odometer basis: {d} km ({b})")
    d, b = compute_distance(None, None, 137.5)
    check(d == 137.5 and b == "osrm", f"fallback OSRM est: {d} km ({b})")
    d, b = compute_distance(80000, 79000, 50)
    check(d == 50.0 and b == "osrm", "odometer mundur diabaikan -> fallback OSRM")
    d, b = compute_distance(None, None, None)
    check(d is None and b is None, "tanpa data -> (None, None)")

    print("\n--- API: checkin+checkout odometer -> distance + vehicle odometer ---")
    owner, drv = login("owner@demo.local"), login("driver@demo.local")
    check(owner and drv, "login owner/driver")
    tasks = requests.get(f"{API}/api/driver/tasks", headers=H(drv), timeout=20).json()
    standby = next((t for t in tasks if t.get("trip_status") in ("standby", "assigned")), tasks[0] if tasks else None)
    check(standby is not None, f"dapat task untuk diuji ({len(tasks)} task)")
    tid = standby["trip_id"]
    # vehicle id dari trip (via my-trips)
    mytrips = requests.get(f"{API}/api/driver/my-trips", headers=H(drv), timeout=20).json()
    trip0 = next((t for t in mytrips if t.get("id") == tid), None)
    vid = trip0.get("vehicle_id") if trip0 else None
    veh_before = requests.get(f"{API}/api/vehicles/{vid}", headers=H(owner), timeout=20).json() if vid else {}
    odo0 = float(veh_before.get("odometer") or 0)
    start_odo, end_odo = odo0 + 10, odo0 + 260
    r = requests.post(f"{API}/api/driver/checkin", headers=H(drv), json={"trip_id": tid, "odometer_start": start_odo}, timeout=20)
    check(r.status_code == 200, "checkin dgn odometer_start")
    r = requests.post(f"{API}/api/driver/checkout", headers=H(drv), json={"trip_id": tid, "odometer_end": end_odo}, timeout=20)
    tr = r.json() if r.status_code == 200 else {}
    check(r.status_code == 200 and abs(float(tr.get("distance_km") or 0) - 250.0) < 0.5 and tr.get("distance_basis") == "odometer",
          f"checkout -> distance_km={tr.get('distance_km')} basis={tr.get('distance_basis')}")
    veh_after = requests.get(f"{API}/api/vehicles/{vid}", headers=H(owner), timeout=20).json() if vid else {}
    check(float(veh_after.get("odometer") or 0) >= end_odo, f"vehicles.odometer ter-update -> {veh_after.get('odometer')}")

    print("\n--- API: driver performance + vehicle trips ---")
    drivers = requests.get(f"{API}/api/drivers", headers=H(owner), timeout=20).json()
    did = (next((d for d in drivers if "Satu" in (d.get("name") or "")), drivers[0]) or {}).get("id")
    r = requests.get(f"{API}/api/drivers/{did}/performance", headers=H(owner), timeout=20)
    perf = r.json() if r.status_code == 200 else {}
    st = perf.get("stats", {})
    check(r.status_code == 200 and all(k in st for k in ("total_trips", "completed", "completion_rate", "total_km", "total_revenue")),
          f"GET /drivers/{{id}}/performance stats (trips={st.get('total_trips')}, km={st.get('total_km')})")
    check(isinstance(perf.get("trips"), list), "performance.trips berupa list riwayat")
    r = requests.get(f"{API}/api/vehicles/{vid}/trips", headers=H(owner), timeout=20)
    vt = r.json() if r.status_code == 200 else {}
    tot = vt.get("totals", {})
    check(r.status_code == 200 and all(k in tot for k in ("trips", "distance_km", "revenue")),
          f"GET /vehicles/{{id}}/trips totals (trips={tot.get('trips')}, km={tot.get('distance_km')})")
    check(tot.get("distance_km", 0) >= 250.0, "total km armada mencakup trip yang baru diselesaikan")
    check(isinstance(vt.get("trips"), list) and len(vt["trips"]) >= 1, "vehicle.trips berupa list riwayat")

    print(f"\n{'='*56}\n  {G}PASS {passed}{X} | {R}FAIL {failed}{X}\n{'='*56}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
