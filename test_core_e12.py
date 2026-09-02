#!/usr/bin/env python3
"""test_core_e12.py — POC E12: Payroll Enhancements.

Memvalidasi:
  1) Rekap Payroll di Laporan: GET /api/reports/payroll (period totals + per_driver + ytd + sdm_vs_revenue),
     /api/reports/summary memuat key 'payroll', export PDF + Excel.
  2) Generate payout MASSAL: POST /api/payroll/payouts/generate-bulk (semua driver, skip existing / idempotent).
  3) Otomasi/pengingat Payroll: POST /api/notifications/scan → notifikasi payroll_reminder + event payroll.payout_pending;
     event-types catalog memuat payroll.period_due & payroll.payout_pending.
  4) RBAC driver 403.

Run: cd /app && python test_core_e12.py
"""
import asyncio
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
B_START, B_END = "2016-05-01", "2016-05-31"


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


async def cleanup_period(start, end):
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        db = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]
        await db.driver_payouts.delete_many({"period_start": start, "period_end": end})
    except Exception as e:
        print(f"  (cleanup skip: {e})")


def main():
    owner, drv = login("owner@demo.local"), login("driver@demo.local")
    check(owner and drv, "login owner/driver")

    print("\n--- 1) Rekap Payroll di Laporan ---")
    r = requests.get(f"{API}/api/reports/payroll", headers=H(owner), timeout=20)
    rep = r.json() if r.status_code == 200 else {}
    check(r.status_code == 200 and "period" in rep, f"GET /reports/payroll (period={rep.get('period')})")
    for k in ("by_status", "total_gross", "total_net", "per_driver", "sdm_vs_revenue"):
        check(k in rep, f"rekap punya field '{k}'")
    sr = rep.get("sdm_vs_revenue", {})
    check("payroll_cost" in sr and "revenue" in sr and "ratio_pct" in sr, "sdm_vs_revenue lengkap (payroll_cost/revenue/ratio)")
    if rep.get("per_driver"):
        d0 = rep["per_driver"][0]
        check(all(k in d0 for k in ("driver_name", "trips", "km", "gross", "total", "ytd", "statuses")), "per_driver row lengkap (+ytd)")

    r = requests.get(f"{API}/api/reports/summary", headers=H(owner), timeout=20)
    check(r.status_code == 200 and "payroll" in r.json(), "/reports/summary memuat key 'payroll'")

    r = requests.get(f"{API}/api/reports/payroll/export?format=excel", headers=H(owner), timeout=25)
    check(r.status_code == 200 and "spreadsheet" in r.headers.get("content-type", "") and len(r.content) > 800, "export Excel rekap payroll")
    r = requests.get(f"{API}/api/reports/payroll/export?format=pdf", headers=H(owner), timeout=25)
    check(r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf") and len(r.content) > 800, "export PDF rekap payroll")

    print("\n--- 2) Generate payout MASSAL ---")
    asyncio.run(cleanup_period(B_START, B_END))
    drivers = requests.get(f"{API}/api/drivers", headers=H(owner), timeout=20).json()
    n_drivers = len(drivers)
    r = requests.post(f"{API}/api/payroll/payouts/generate-bulk", headers=H(owner),
                      json={"period_type": "monthly", "period_start": B_START, "period_end": B_END}, timeout=30)
    res = r.json() if r.status_code == 200 else {}
    check(r.status_code == 200 and res.get("created_count") == n_drivers and res.get("skipped_count") == 0,
          f"bulk generate buat {res.get('created_count')} payout untuk {n_drivers} driver")
    r2 = requests.post(f"{API}/api/payroll/payouts/generate-bulk", headers=H(owner),
                       json={"period_type": "monthly", "period_start": B_START, "period_end": B_END}, timeout=30)
    res2 = r2.json() if r2.status_code == 200 else {}
    check(r2.status_code == 200 and res2.get("created_count") == 0 and res2.get("skipped_count") == n_drivers,
          f"bulk generate idempotent (skip {res2.get('skipped_count')} existing)")
    r = requests.post(f"{API}/api/payroll/payouts/generate-bulk", headers=H(owner),
                      json={"period_type": "monthly", "period_start": "2016-05-31", "period_end": "2016-05-01"}, timeout=20)
    check(r.status_code == 400, "bulk generate periode invalid (end<start) -> 400")

    print("\n--- 3) Otomasi/pengingat Payroll ---")
    et = requests.get(f"{API}/api/automation/event-types", headers=H(owner), timeout=20).json()
    et_str = str(et)
    check("payroll.period_due" in et_str and "payroll.payout_pending" in et_str, "event-types catalog memuat payroll.*")
    sc = requests.post(f"{API}/api/notifications/scan", headers=H(owner), timeout=30)
    check(sc.status_code == 200, f"trigger notifications/scan (status {sc.status_code})")
    notifs = requests.get(f"{API}/api/notifications", headers=H(owner), timeout=20).json()
    notif_list = notifs if isinstance(notifs, list) else notifs.get("items", notifs.get("notifications", []))
    payroll_notifs = [n for n in notif_list if n.get("type") == "payroll_reminder" or n.get("ref_type") == "payroll"]
    check(len(payroll_notifs) >= 1, f"notifikasi payroll_reminder dibuat ({len(payroll_notifs)})")
    evs = requests.get(f"{API}/api/automation/events?limit=200", headers=H(owner), timeout=20).json()
    ev_list = evs if isinstance(evs, list) else evs.get("items", evs.get("events", []))
    pending_ev = [e for e in ev_list if e.get("type") == "payroll.payout_pending"]
    check(len(pending_ev) >= 1, f"event payroll.payout_pending ter-emit ({len(pending_ev)})")

    print("\n--- 4) RBAC driver ---")
    check(requests.get(f"{API}/api/reports/payroll", headers=H(drv), timeout=20).status_code == 403, "driver GET /reports/payroll -> 403")
    check(requests.post(f"{API}/api/payroll/payouts/generate-bulk", headers=H(drv),
                        json={"period_type": "monthly", "period_start": B_START, "period_end": B_END}, timeout=20).status_code == 403,
          "driver generate-bulk -> 403")

    # cleanup test payouts
    asyncio.run(cleanup_period(B_START, B_END))

    print(f"\n{'='*56}\n  {G}PASS {passed}{X} | {R}FAIL {failed}{X}\n{'='*56}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
