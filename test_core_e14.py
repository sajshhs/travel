#!/usr/bin/env python3
"""test_core_e14.py — POC E14: Reminder SIM driver otomatis + Guard RBAC terpusat (backend side).

Memvalidasi (B1 — SIM reminder):
  1) event-types catalog memuat 'driver.sim_expiring'.
  2) POST /api/notifications/scan → membuat notifikasi type 'sim_reminder' untuk driver
     dengan sim_expiry ≤ 30 hari (seed: Driver Dua = +20 hari).
  3) event 'driver.sim_expiring' ter-emit (audit/otomasi).
  4) idempotent: scan ulang tidak menduplikasi sim_reminder.

Catatan A1 (guard RBAC terpusat) diverifikasi via browser oleh testing_agent (redirect FE),
tetapi di sini kita pastikan backend tetap menegakkan 403 untuk section terlarang bagi driver.

Run: cd /app && python test_core_e14.py
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


def _list(js):
    return js if isinstance(js, list) else js.get("items", js.get("notifications", js.get("events", [])))


def main():
    owner, drv = login("owner@demo.local"), login("driver@demo.local")
    check(owner and drv, "login owner/driver")

    print("\n--- B1) Event catalog ---")
    et = requests.get(f"{API}/api/automation/event-types", headers=H(owner), timeout=20).json()
    check("driver.sim_expiring" in str(et), "event-types memuat 'driver.sim_expiring'")

    print("\n--- B1) Scan menghasilkan sim_reminder ---")
    sc = requests.post(f"{API}/api/notifications/scan", headers=H(owner), timeout=30)
    check(sc.status_code == 200, f"trigger notifications/scan (status {sc.status_code})")

    notifs = _list(requests.get(f"{API}/api/notifications", headers=H(owner), timeout=20).json())
    sim = [n for n in notifs if n.get("type") == "sim_reminder"]
    check(len(sim) >= 1, f"notifikasi 'sim_reminder' dibuat ({len(sim)})")
    if sim:
        n0 = sim[0]
        check(n0.get("ref_type") == "driver" and n0.get("ref_id"), "sim_reminder rujuk driver (ref_type/ref_id)")
        check("SIM" in (n0.get("title") or ""), f"judul informatif: {n0.get('title')!r}")

    print("\n--- B1) Event driver.sim_expiring ter-emit ---")
    evs = _list(requests.get(f"{API}/api/automation/events?limit=200", headers=H(owner), timeout=20).json())
    sim_ev = [e for e in evs if e.get("type") == "driver.sim_expiring"]
    check(len(sim_ev) >= 1, f"event 'driver.sim_expiring' ({len(sim_ev)})")
    if sim_ev:
        p = sim_ev[0].get("payload") or sim_ev[0].get("data") or {}
        check(any(k in p for k in ("driver_id", "due_date", "days_left")), "payload event punya info SIM")

    print("\n--- B1) Idempotensi ---")
    before = len([n for n in notifs if n.get("type") == "sim_reminder"])
    requests.post(f"{API}/api/notifications/scan", headers=H(owner), timeout=30)
    after_notifs = _list(requests.get(f"{API}/api/notifications", headers=H(owner), timeout=20).json())
    after = len([n for n in after_notifs if n.get("type") == "sim_reminder"])
    check(after == before, f"scan ulang tidak menduplikasi sim_reminder ({before}→{after})")

    print("\n--- A1) Backend tetap 403 utk driver di section terlarang ---")
    check(requests.get(f"{API}/api/customers", headers=H(drv), timeout=20).status_code == 403,
          "driver GET /customers -> 403 (backend guard)")

    print(f"\n{'='*56}\n  {G}PASS {passed}{X} | {R}FAIL {failed}{X}\n{'='*56}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
