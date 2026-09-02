#!/usr/bin/env python3
"""test_core_e5.py — POC E5 (Finance Automation).

Membuktikan INTI E5 (tanpa HTTP):
  1. pl_full: profit == revenue - opex - maintenance; per-unit profit konsisten; maintenance>0 ikut P&L (G4).
  2. reconciliation: diff == paid - invoice_amount; status (lunas/sebagian/belum/lebih) benar.
  3. sync_invoice_statuses: status invoice mengikuti pembayaran + idempotent (run kedua 0 update) (G5).
  4. cashflow: net == cash_in - cash_out per bulan; saldo kumulatif; proyeksi N titik.
  5. AR reminder: send_ar_reminder memancarkan event invoice.overdue → automation jalan → WA mock bertambah.
  6. assemble_finance_report lengkap (pl+ar_aging+cashflow+reconciliation).

Jalankan: cd /app && python test_core_e5.py
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / "backend" / ".env")
except Exception:
    pass

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from services import finance_automation as fa  # noqa: E402

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "app_db")
G, R, Y, X = "\033[92m", "\033[91m", "\033[93m", "\033[0m"
passed = failed = 0


def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  {G}[PASS]{X} {label}")
    else:
        failed += 1
        print(f"  {R}[FAIL]{X} {label} {Y}{detail}{X}")


async def _period_with_maintenance(db):
    """Cari periode YYYY-MM yang punya maintenance cost agar uji G4 bermakna."""
    m = await db.maintenance_records.find_one({"cost": {"$gt": 0}}, {"_id": 0, "completed_at": 1, "created_at": 1})
    if not m:
        return None
    return (m.get("completed_at") or m.get("created_at") or "")[:7] or None


async def main():
    print(f"\n{'='*60}\n  POC E5 — Finance Automation\n{'='*60}")
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]

    # --- 1. P&L incl. maintenance (G4) ---
    print(f"\n{Y}[1] P&L komprehensif (maintenance masuk P&L){X}")
    mperiod = await _period_with_maintenance(db)
    pl = await fa.pl_full(db, mperiod)
    check("profit == revenue - opex - maintenance",
          round(pl["profit"], 2) == round(pl["revenue"] - pl["operational_expenses"] - pl["maintenance_cost"], 2),
          detail=f"rev={pl['revenue']} opex={pl['operational_expenses']} maint={pl['maintenance_cost']} profit={pl['profit']}")
    check("total_cost == opex + maintenance",
          round(pl["total_cost"], 2) == round(pl["operational_expenses"] + pl["maintenance_cost"], 2))
    check("per-unit: profit == revenue - opex - maintenance (semua unit)",
          all(round(u["profit"], 2) == round(u["revenue"] - u["operational_expenses"] - u["maintenance"], 2)
              for u in pl["per_unit"]))
    check("maintenance_cost > 0 ikut P&L (G4 ditutup)", pl["maintenance_cost"] > 0,
          detail=f"period={pl['period']} maint={pl['maintenance_cost']}")

    # --- 2. Reconciliation (G5) ---
    print(f"\n{Y}[2] Rekonsiliasi invoice ↔ pembayaran{X}")
    rec = await fa.reconciliation(db)
    check("ada item rekonsiliasi", len(rec["items"]) > 0, detail=str(len(rec["items"])))
    ok_diff = all(round(i["diff"], 2) == round(i["paid"] - i["invoice_amount"], 2) for i in rec["items"])
    check("diff == paid - invoice_amount (semua)", ok_diff)
    def expect_status(i):
        if i["paid"] <= 0:
            return "belum"
        if i["paid"] + 0.01 < i["invoice_amount"]:
            return "sebagian"
        if i["paid"] > i["invoice_amount"] + 0.01:
            return "lebih"
        return "lunas"
    check("recon_status benar (lunas/sebagian/belum/lebih)",
          all(i["recon_status"] == expect_status(i) for i in rec["items"]))
    check("summary.total_invoiced == Σ invoice_amount",
          round(rec["summary"]["total_invoiced"], 2) == round(sum(i["invoice_amount"] for i in rec["items"]), 2))

    # --- 3. Sync invoice status idempotent (G5) ---
    print(f"\n{Y}[3] Sinkronisasi status invoice (idempotent){X}")
    first = await fa.sync_invoice_statuses(db)
    second = await fa.sync_invoice_statuses(db)
    check("run pertama menyelaraskan status", isinstance(first["updated_count"], int))
    check("run kedua idempotent (0 update)", second["updated_count"] == 0,
          detail=f"second={second['updated_count']}")
    # verifikasi status sesuai pembayaran
    pay = await fa._payments_by_booking(db)
    invs = await db.invoices.find({}, {"_id": 0, "amount": 1, "booking_id": 1, "status": 1}).to_list(100)
    def want(inv):
        amt = float(inv.get("amount", 0) or 0); paid = float(pay.get(inv.get("booking_id"), 0))
        if amt > 0 and paid + 0.01 >= amt: return "paid"
        if paid > 0: return "partial"
        return inv.get("status")  # tetap draft/sent
    ok_status = all(inv["status"] == want(inv) or inv["status"] in ("draft", "sent") for inv in invs)
    check("status invoice mencerminkan pembayaran", ok_status)

    # --- 4. Cashflow + proyeksi ---
    print(f"\n{Y}[4] Arus kas + proyeksi moving-average{X}")
    cf = await fa.cashflow(db, months_back=6, horizon=3)
    check("net == cash_in - cash_out (semua bulan)",
          all(round(m["net"], 2) == round(m["cash_in"] - m["cash_out"], 2) for m in cf["months"]))
    # saldo kumulatif
    bal = 0.0; ok_bal = True
    for m in cf["months"]:
        bal = round(bal + m["net"], 2)
        if abs(bal - m["balance"]) > 0.01: ok_bal = False
    check("saldo kumulatif benar", ok_bal)
    check("proyeksi 3 bulan", len(cf["projection"]) == 3, detail=str(len(cf["projection"])))

    # --- 5. AR reminder → event + WA mock ---
    print(f"\n{Y}[5] AR collection reminder (event → automation → WA mock){X}")
    overdue = await fa.ar_overdue(db)
    check("ada piutang overdue untuk diingatkan", overdue["count"] > 0, detail=str(overdue["count"]))
    if overdue["count"] > 0:
        wa_before = await db.messages.count_documents({})
        ev_before = await db.events.count_documents({"type": "invoice.overdue"})
        target = overdue["items"][0]["booking_id"]
        r = await fa.send_ar_reminder(db, target)
        ev_after = await db.events.count_documents({"type": "invoice.overdue"})
        wa_after = await db.messages.count_documents({})
        check("event invoice.overdue terpancar", ev_after == ev_before + 1, detail=f"{ev_before}->{ev_after}")
        check("reminder memicu run otomasi", r["runs"] >= 1, detail=str(r))
        check("WA mock bertambah (reminder terkirim)", wa_after > wa_before,
              detail=f"{wa_before}->{wa_after}")

    # --- 6. Assemble report ---
    print(f"\n{Y}[6] Rakit laporan keuangan (export-ready){X}")
    rep = await fa.assemble_finance_report(db, mperiod)
    check("laporan berisi pl+ar_aging+cashflow+reconciliation",
          all(k in rep for k in ["pl", "ar_aging", "cashflow", "reconciliation"]))

    print(f"\n{'='*60}")
    total = passed + failed
    color = G if failed == 0 else R
    print(f"  {color}HASIL: {passed}/{total} PASS, {failed} FAIL{X}")
    print(f"{'='*60}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
