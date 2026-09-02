#!/usr/bin/env python3
"""test_core_e13.py — POC E13: Laporan Driver (Leaderboard) + Revenue-per-Trip.

Memvalidasi:
  1) GET /api/reports/drivers → {period, fleet{...}, drivers[...]} dengan field lengkap
     (rank, trips, completed, completion_rate, km, revenue, revenue_per_trip, avg_km_per_trip).
  2) Konsistensi agregat: fleet.trips == Σ drivers.trips; fleet.revenue == Σ drivers.revenue;
     revenue_per_trip == revenue/trips; leaderboard terurut menurun berdasarkan revenue; rank berurut.
  3) /api/reports/summary memuat key 'drivers_report'.
  4) Export Excel + PDF (/api/reports/drivers/export?format=excel|pdf).
  5) Filter periode (period param mempengaruhi hasil).
  6) RBAC: driver 403 di /reports/drivers dan /reports/drivers/export.

Run: cd /app && python test_core_e13.py
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

    print("\n--- 1) GET /reports/drivers struktur ---")
    r = requests.get(f"{API}/api/reports/drivers", headers=H(owner), timeout=20)
    rep = r.json() if r.status_code == 200 else {}
    check(r.status_code == 200 and "period" in rep, f"GET /reports/drivers (period={rep.get('period')})")
    check("fleet" in rep and "drivers" in rep, "punya 'fleet' + 'drivers'")
    fl = rep.get("fleet", {})
    for k in ("trips", "completed", "completion_rate", "km", "revenue", "revenue_per_trip",
              "avg_km_per_trip", "active_drivers"):
        check(k in fl, f"fleet punya field '{k}'")
    drivers = rep.get("drivers", [])
    if drivers:
        d0 = drivers[0]
        for k in ("rank", "driver_id", "driver_name", "trips", "completed", "completion_rate",
                  "km", "revenue", "revenue_per_trip", "avg_km_per_trip"):
            check(k in d0, f"driver row punya field '{k}'")

    print("\n--- 2) Konsistensi agregat & urutan ---")
    if drivers:
        sum_trips = sum(int(d["trips"]) for d in drivers)
        sum_rev = round(sum(float(d["revenue"]) for d in drivers), 2)
        check(sum_trips == fl.get("trips"), f"fleet.trips ({fl.get('trips')}) == Σ drivers.trips ({sum_trips})")
        check(abs(sum_rev - float(fl.get("revenue", 0))) < 1, f"fleet.revenue == Σ drivers.revenue ({sum_rev})")
        exp_rpt = round(float(fl.get("revenue", 0)) / fl.get("trips"), 2) if fl.get("trips") else 0.0
        check(abs(exp_rpt - float(fl.get("revenue_per_trip", 0))) < 1, "fleet.revenue_per_trip == revenue/trips")
        revs = [float(d["revenue"]) for d in drivers]
        check(revs == sorted(revs, reverse=True), "leaderboard terurut revenue menurun")
        check([d["rank"] for d in drivers] == list(range(1, len(drivers) + 1)), "rank berurut 1..N")
        d0 = drivers[0]
        exp = round(float(d0["revenue"]) / int(d0["trips"]), 2) if d0["trips"] else 0.0
        check(abs(exp - float(d0["revenue_per_trip"])) < 1, "revenue_per_trip per-driver benar")
    else:
        print("  (tidak ada trip di periode berjalan — lewati cek konsistensi nilai)")

    print("\n--- 3) /reports/summary memuat drivers_report ---")
    r = requests.get(f"{API}/api/reports/summary", headers=H(owner), timeout=20)
    js = r.json() if r.status_code == 200 else {}
    check(r.status_code == 200 and "drivers_report" in js, "/reports/summary memuat key 'drivers_report'")
    check(isinstance(js.get("drivers_report", {}).get("drivers"), list), "drivers_report.drivers berupa list")

    print("\n--- 4) Export Excel + PDF ---")
    r = requests.get(f"{API}/api/reports/drivers/export?format=excel", headers=H(owner), timeout=25)
    check(r.status_code == 200 and "spreadsheet" in r.headers.get("content-type", "") and len(r.content) > 800,
          "export Excel laporan driver")
    r = requests.get(f"{API}/api/reports/drivers/export?format=pdf", headers=H(owner), timeout=25)
    check(r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf") and len(r.content) > 800,
          "export PDF laporan driver")

    print("\n--- 5) Filter periode ---")
    r = requests.get(f"{API}/api/reports/drivers?period=2020-01", headers=H(owner), timeout=20)
    old = r.json() if r.status_code == 200 else {}
    check(r.status_code == 200 and old.get("period") == "2020-01", "period param dipakai (2020-01)")
    check(old.get("fleet", {}).get("trips", 0) == 0 and old.get("drivers") == [],
          "periode tanpa trip → kosong (fleet.trips=0, drivers=[])")

    print("\n--- 6) RBAC driver ---")
    check(requests.get(f"{API}/api/reports/drivers", headers=H(drv), timeout=20).status_code == 403,
          "driver GET /reports/drivers -> 403")
    check(requests.get(f"{API}/api/reports/drivers/export?format=excel", headers=H(drv), timeout=20).status_code == 403,
          "driver export -> 403")

    print(f"\n{'='*56}\n  {G}PASS {passed}{X} | {R}FAIL {failed}{X}\n{'='*56}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
