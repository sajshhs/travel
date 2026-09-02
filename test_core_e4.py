#!/usr/bin/env python3
"""test_core_e4.py — POC E4 (BI & Management Cockpit).

Membuktikan INTI E4 (tanpa HTTP) — agregasi analytics read-only + invarian:
  1. summary KPI + delta vs periode sebelumnya (revenue/profit/leads/conversion).
  2. funnel cohort lead monotonic (lead >= contacted >= quotation >= won).
  3. channel ROI/ROAS/CPL/CAC dengan ad-spend manual (matematika benar).
  4. AR aging buckets menjumlah TEPAT ke total outstanding (konsisten accounts_receivable).
  5. fleet ROI: profit == revenue - expenses per unit.
  6. retention rate ∈ [0,1]; forecast = historis + N titik moving-average.
  7. set/get marketing_spend (settings) idempotent.

Jalankan: cd /app && python test_core_e4.py
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
from services import analytics  # noqa: E402
from services.finance import accounts_receivable  # noqa: E402

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


async def main():
    print(f"\n{'='*60}\n  POC E4 — BI & Management Cockpit\n{'='*60}")
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    # Rentang lebar agar mencakup data seed (1 tahun).
    rng = analytics.parse_range(days=365)

    # --- 1. SUMMARY KPI + delta ---
    print(f"\n{Y}[1] Exec KPI + delta periode sebelumnya{X}")
    summ = await analytics.summary_kpis(db, rng)
    m = summ["metrics"]
    check("summary mengembalikan metrik utama", all(k in m for k in
          ["revenue", "profit", "leads", "conversion_rate", "outstanding_ar"]))
    check("setiap metrik punya value/prev/delta_pct",
          all("value" in m[k] and "delta_pct" in m[k] for k in ["revenue", "profit", "leads"]))
    check("revenue >= 0 dan profit = revenue - expenses (range)",
          m["revenue"]["value"] >= 0 and
          round(m["profit"]["value"], 2) == round(m["revenue"]["value"] - m["expenses"]["value"], 2),
          detail=f"rev={m['revenue']['value']} exp={m['expenses']['value']} profit={m['profit']['value']}")

    # --- 2. FUNNEL monotonic ---
    print(f"\n{Y}[2] Sales funnel cohort lead (monotonic){X}")
    fn = await analytics.funnel(db, rng)
    counts = [s["count"] for s in fn["stages"]]
    check("funnel 4 tahap (lead/contacted/quotation/won)", len(fn["stages"]) == 4, detail=str(counts))
    check("counts monotonic turun (lead>=contacted>=quotation>=won)",
          counts == sorted(counts, reverse=True), detail=str(counts))
    check("overall_conversion dalam 0..100", 0 <= fn["overall_conversion"] <= 100,
          detail=str(fn["overall_conversion"]))

    # --- 3. CHANNELS ROI/ROAS ---
    print(f"\n{Y}[3] Channel mix + ROAS/CPL/CAC (ad-spend manual){X}")
    # ambil source nyata dari data, beri spend supaya math teruji
    chan0 = await analytics.channels_roi(db, rng, spend_map={})
    first_src = chan0["channels"][0]["channel"] if chan0["channels"] else "website"
    spend_map = {first_src: 1000.0}
    chan = await analytics.channels_roi(db, rng, spend_map=spend_map)
    row = next((c for c in chan["channels"] if c["channel"] == first_src), None)
    check("channel teridentifikasi dengan spend", row is not None and row["spend"] == 1000.0,
          detail=str(row))
    if row:
        exp_cpl = round(1000.0 / row["leads"], 2) if row["leads"] > 0 else None
        exp_roas = round(row["revenue"] / 1000.0, 2)
        check("CPL = spend/leads benar", row["cpl"] == exp_cpl, detail=f"cpl={row['cpl']} exp={exp_cpl}")
        check("ROAS = revenue/spend benar", row["roas"] == exp_roas, detail=f"roas={row['roas']} exp={exp_roas}")
    check("totals.spend == jumlah spend channel", chan["totals"]["spend"] == 1000.0,
          detail=str(chan["totals"]))

    # --- 4. AR AGING == outstanding ---
    print(f"\n{Y}[4] AR aging buckets == total outstanding{X}")
    ar = await accounts_receivable(db)
    aging = await analytics.ar_aging(db)
    bsum = round(sum(b["amount"] for b in aging["buckets"]), 2)
    check("Σ bucket == total_outstanding (accounts_receivable)",
          bsum == round(ar["total_outstanding"], 2),
          detail=f"buckets={bsum} ar={ar['total_outstanding']}")
    check("jumlah count bucket == count AR",
          sum(b["count"] for b in aging["buckets"]) == ar["count"])

    # --- 5. FLEET ROI ---
    print(f"\n{Y}[5] Fleet ROI: profit == revenue - expenses/unit{X}")
    fleet = await analytics.fleet_roi(db, rng)
    ok_fleet = all(round(v["profit"], 2) == round(v["revenue"] - v["expenses"], 2)
                   for v in fleet["vehicles"])
    check("profit per unit konsisten", ok_fleet)
    check("active+idle == total armada",
          fleet["active_units"] + fleet["idle_units"] == len(fleet["vehicles"]))

    # --- 6. RETENTION + FORECAST ---
    print(f"\n{Y}[6] Retention rate ∈ [0,1] + forecast moving-average{X}")
    ret = await analytics.retention(db, rng)
    check("repeat_rate dalam [0,1]", 0.0 <= ret["repeat_rate"] <= 1.0, detail=str(ret["repeat_rate"]))
    check("one_time + returning == total customers",
          ret["one_time_customers"] + ret["returning_customers"] == ret["total_customers"])
    fc = await analytics.forecast(db, months_back=6, horizon=3, metric="revenue")
    check("forecast: 6 historis + 3 prediksi",
          len(fc["history"]) == 6 and len(fc["forecast"]) == 3, detail=str(len(fc["forecast"])))
    check("forecast nilai numerik non-negatif",
          all(isinstance(p["value"], (int, float)) and p["value"] >= 0 for p in fc["forecast"]))

    # --- 7. AD-SPEND settings ---
    print(f"\n{Y}[7] Set/Get marketing_spend (settings){X}")
    saved = await analytics.set_marketing_spend(
        db, [{"channel": "meta_ads", "amount": 500}, {"channel": "website", "amount": 0}], note="poc")
    check("set marketing_spend tersimpan & ter-normalisasi",
          saved["spend_map"].get("meta_ads") == 500.0, detail=str(saved["spend_map"]))
    got = await analytics.get_marketing_spend(db)
    check("get marketing_spend konsisten", got["spend_map"].get("meta_ads") == 500.0)

    print(f"\n{'='*60}")
    total = passed + failed
    color = G if failed == 0 else R
    print(f"  {color}HASIL: {passed}/{total} PASS, {failed} FAIL{X}")
    print(f"{'='*60}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
