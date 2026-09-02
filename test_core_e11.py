#!/usr/bin/env python3
"""test_core_e11.py — POC E11 Phase C: Driver Payroll / HR Lite.

Memvalidasi:
  - GET/PATCH /api/drivers/{id}/compensation + RBAC (driver 403).
  - POST /api/payroll/payouts/generate → akrual dari trip SELESAI (komisi/trip, %revenue, uang jalan/km, gaji pokok).
  - Cegah duplikat periode (400).
  - PATCH bonus/potongan (baris manual) → total dihitung ulang.
  - approve → status approved + expense Finance (kategori gaji_driver) dibuat (akrual → P&L).
  - pay → status paid + expense ditandai lunas (kas).
  - slip PDF + Excel (200).
  - RBAC driver 403; delete draft ok, delete approved 400; summary.

Run: cd /app && python test_core_e11.py  (backend hidup + DB ter-seed)
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

WIDE_START, WIDE_END = "2019-01-01", "2035-12-31"
ALT_START, ALT_END = "2018-01-01", "2018-12-31"


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


async def cleanup(driver_id):
    """Idempotensi: hapus payout test driver + expense gaji_driver terkait (DB langsung)."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        db = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]
        payouts = await db.driver_payouts.find({"driver_id": driver_id}, {"_id": 0, "id": 1, "expense_id": 1}).to_list(200)
        exp_ids = [p["expense_id"] for p in payouts if p.get("expense_id")]
        await db.driver_payouts.delete_many({"driver_id": driver_id})
        if exp_ids:
            await db.expenses.delete_many({"id": {"$in": exp_ids}})
    except Exception as e:
        print(f"  (cleanup skip: {e})")


def main():
    owner, drv_user = login("owner@demo.local"), login("driver@demo.local")
    check(owner and drv_user, "login owner/driver")

    drivers = requests.get(f"{API}/api/drivers", headers=H(owner), timeout=20).json()
    check(isinstance(drivers, list) and len(drivers) >= 1, f"GET drivers ({len(drivers)})")
    did = drivers[0]["id"]
    asyncio.run(cleanup(did))

    print("\n--- Kompensasi per driver ---")
    r = requests.patch(f"{API}/api/drivers/{did}/compensation", headers=H(owner), json={
        "base_salary_monthly": 3000000, "commission_per_trip": 100000,
        "commission_pct_revenue": 10, "allowance_per_km": 1000, "revenue_base": "trip",
        "enable_base": True, "enable_commission_trip": True,
        "enable_commission_pct": True, "enable_allowance_km": True}, timeout=20)
    comp = r.json().get("comp", {}) if r.status_code == 200 else {}
    check(r.status_code == 200 and comp.get("base_salary_monthly") == 3000000, "PATCH compensation owner")
    r = requests.get(f"{API}/api/drivers/{did}/compensation", headers=H(owner), timeout=20)
    check(r.status_code == 200 and r.json().get("comp", {}).get("commission_per_trip") == 100000, "GET compensation")
    r = requests.patch(f"{API}/api/drivers/{did}/compensation", headers=H(drv_user), json={"base_salary_monthly": 1}, timeout=20)
    check(r.status_code == 403, "RBAC driver PATCH compensation -> 403")

    print("\n--- Generate payout (akrual) ---")
    r = requests.post(f"{API}/api/payroll/payouts/generate", headers=H(owner), json={
        "driver_id": did, "period_type": "monthly", "period_start": WIDE_START, "period_end": WIDE_END}, timeout=20)
    p = r.json() if r.status_code == 200 else {}
    check(r.status_code == 200 and str(p.get("id", "")).startswith("dpo_"), f"generate payout (id={p.get('id')})")
    pid = p.get("id")
    tc = p.get("trips_count", 0)
    check(p.get("base_salary") == 3000000, f"gaji pokok bulanan = 3.000.000 (got {p.get('base_salary')})")
    check(p.get("commission_trip") == 100000 * tc, f"komisi/trip = 100.000 x {tc} (got {p.get('commission_trip')})")
    expected_pct = round(float(p.get("total_revenue") or 0) * 10 / 100, 2)
    check(abs(float(p.get("commission_pct") or 0) - expected_pct) < 0.5, f"komisi %revenue = 10% x {p.get('total_revenue')} (got {p.get('commission_pct')})")
    expected_km = round(float(p.get("total_km") or 0) * 1000, 2)
    check(abs(float(p.get("allowance_km") or 0) - expected_km) < 0.5, f"uang jalan/km = 1.000 x {p.get('total_km')} km (got {p.get('allowance_km')})")
    expected_gross = round(p.get("base_salary", 0) + p.get("commission_trip", 0) + p.get("commission_pct", 0) + p.get("allowance_km", 0), 2)
    check(abs(float(p.get("gross") or 0) - expected_gross) < 0.5, f"gross = Σ komponen ({p.get('gross')})")
    check(p.get("total") == p.get("gross"), "total == gross (belum ada bonus/potongan)")

    r = requests.post(f"{API}/api/payroll/payouts/generate", headers=H(owner), json={
        "driver_id": did, "period_type": "monthly", "period_start": WIDE_START, "period_end": WIDE_END}, timeout=20)
    check(r.status_code == 400, "duplikat periode -> 400")

    r = requests.post(f"{API}/api/payroll/payouts/generate", headers=H(drv_user), json={
        "driver_id": did, "period_type": "monthly", "period_start": ALT_START, "period_end": ALT_END}, timeout=20)
    check(r.status_code == 403, "RBAC driver generate -> 403")

    print("\n--- Bonus/potongan (baris manual) ---")
    r = requests.patch(f"{API}/api/payroll/payouts/{pid}", headers=H(owner), json={
        "bonuses": [{"label": "Bonus kinerja", "amount": 250000}],
        "deductions": [{"label": "Kasbon", "amount": 50000}], "notes": "uji"}, timeout=20)
    pu = r.json() if r.status_code == 200 else {}
    check(r.status_code == 200 and pu.get("bonus_total") == 250000 and pu.get("deduction_total") == 50000, "PATCH bonus/potongan")
    check(pu.get("total") == round(expected_gross + 250000 - 50000, 2), f"total = gross + bonus - potongan (got {pu.get('total')})")
    total_final = pu.get("total")

    print("\n--- Approve → expense Finance (akrual) ---")
    r = requests.post(f"{API}/api/payroll/payouts/{pid}/approve", headers=H(owner), timeout=20)
    pa = r.json() if r.status_code == 200 else {}
    check(r.status_code == 200 and pa.get("status") == "approved" and pa.get("expense_id"), f"approve (expense_id={pa.get('expense_id')})")
    exps = requests.get(f"{API}/api/expenses", headers=H(owner), timeout=20).json()
    pexp = next((e for e in exps if e.get("id") == pa.get("expense_id")), None)
    check(pexp and pexp.get("category") == "gaji_driver" and abs(float(pexp.get("amount")) - total_final) < 0.5, "expense gaji_driver dibuat = total payout")
    r = requests.get(f"{API}/api/payroll/payouts/{pid}", headers=H(owner), timeout=20)
    r2 = requests.post(f"{API}/api/payroll/payouts/{pid}/approve", headers=H(owner), timeout=20)
    check(r2.status_code == 400, "approve ulang (bukan draft) -> 400")

    print("\n--- P&L memuat kategori gaji_driver ---")
    from datetime import datetime, timezone
    per = datetime.now(timezone.utc).strftime("%Y-%m")
    pl = requests.get(f"{API}/api/finance/pl-full?period={per}", headers=H(owner), timeout=20).json()
    cats = {c["category"]: c["amount"] for c in pl.get("expense_by_category", [])}
    check("gaji_driver" in cats and cats["gaji_driver"] >= total_final - 0.5, f"P&L kategori gaji_driver = {cats.get('gaji_driver')}")

    print("\n--- Pay → expense lunas (kas) ---")
    r = requests.post(f"{API}/api/payroll/payouts/{pid}/pay", headers=H(owner), timeout=20)
    pp = r.json() if r.status_code == 200 else {}
    check(r.status_code == 200 and pp.get("status") == "paid" and pp.get("paid_at"), "pay -> status paid")
    exps = requests.get(f"{API}/api/expenses", headers=H(owner), timeout=20).json()
    pexp = next((e for e in exps if e.get("id") == pa.get("expense_id")), None)
    check(pexp and pexp.get("paid") is True, "expense payout ditandai lunas (paid=true)")
    r = requests.post(f"{API}/api/payroll/payouts/{pid}/pay", headers=H(owner), timeout=20)
    check(r.status_code == 400, "pay ulang / bukan approved -> 400")

    print("\n--- Slip PDF + Excel ---")
    r = requests.get(f"{API}/api/payroll/payouts/{pid}/slip?format=pdf", headers=H(owner), timeout=20)
    check(r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf") and len(r.content) > 800, "slip PDF")
    r = requests.get(f"{API}/api/payroll/payouts/{pid}/slip?format=excel", headers=H(owner), timeout=20)
    check(r.status_code == 200 and "spreadsheet" in r.headers.get("content-type", "") and len(r.content) > 800, "slip Excel")

    print("\n--- Delete draft vs approved/paid ---")
    r = requests.post(f"{API}/api/payroll/payouts/generate", headers=H(owner), json={
        "driver_id": did, "period_type": "weekly", "period_start": ALT_START, "period_end": ALT_END}, timeout=20)
    draft2 = r.json().get("id") if r.status_code == 200 else None
    r = requests.delete(f"{API}/api/payroll/payouts/{draft2}", headers=H(owner), timeout=20)
    check(r.status_code == 200, "delete payout draft -> 200")
    r = requests.delete(f"{API}/api/payroll/payouts/{pid}", headers=H(owner), timeout=20)
    check(r.status_code == 400, "delete payout paid -> 400 (terkunci)")

    print("\n--- Summary ---")
    r = requests.get(f"{API}/api/payroll/summary", headers=H(owner), timeout=20)
    sm = r.json() if r.status_code == 200 else {}
    check(r.status_code == 200 and "by_status" in sm and sm.get("paid_total", 0) >= total_final - 0.5, f"summary (paid_total={sm.get('paid_total')})")
    r = requests.get(f"{API}/api/payroll/payouts", headers=H(drv_user), timeout=20)
    check(r.status_code == 403, "RBAC driver list payouts -> 403")

    print(f"\n{'='*56}\n  {G}PASS {passed}{X} | {R}FAIL {failed}{X}\n{'='*56}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
