#!/usr/bin/env python3
"""test_core_e3.py — POC E3 (Dispatch & Komunikasi Operasi).

Membuktikan INTI E3 (tanpa HTTP), bagian paling berisiko/novel:
  1. Geocoding tujuan via OSM Nominatim (perbaiki G1) — nyata + cache.
  2. Trigger WA driver->customer untuk event BARU (trip.assigned, booking.departure_confirmed,
     trip.enroute, trip.arrived) lewat Event Bus + Automation Engine (provider MOCK).
  3. Idempotensi event (dedupe_key) — satu event tak diproses ganda.

Jalankan: cd /app && python test_core_e3.py
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
from core_utils import new_id, now_iso  # noqa: E402
from services import events  # noqa: E402
from services.automation import default_rules  # noqa: E402
from services.geocode import geocode  # noqa: E402
try:
    from services.identity import normalize_phone as _norm_phone  # noqa: E402
except Exception:
    def _norm_phone(p):
        return p

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "app_db")
G, R, Y, X = "\033[92m", "\033[91m", "\033[93m", "\033[0m"
passed = failed = 0
TAG = "__poc_e3__"
PHONE = "081200000333"
NEW_EVENTS = ["trip.assigned", "booking.departure_confirmed", "trip.enroute", "trip.arrived"]


def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  {G}[PASS]{X} {label}")
    else:
        failed += 1
        print(f"  {R}[FAIL]{X} {label} {Y}{detail}{X}")


async def cleanup(db):
    norm = _norm_phone(PHONE)
    await db.automation_rules.delete_many({"test_tag": TAG})
    await db.automation_runs.delete_many({"rule_name": {"$regex": "^__poc"}})
    convs = await db.conversations.find(
        {"contact_phone": {"$in": [PHONE, norm]}}, {"_id": 0, "id": 1}).to_list(50)
    ids = [c["id"] for c in convs]
    if ids:
        await db.messages.delete_many({"conversation_id": {"$in": ids}})
    await db.conversations.delete_many({"contact_phone": {"$in": [PHONE, norm]}})
    await db.events.delete_many({"dedupe_key": {"$regex": "^__poc_e3__"}})


async def seed_rules(db):
    """Sisipkan rule AKTIF utk event BARU (bertanda test_tag agar bisa dibersihkan)."""
    wanted = {r["event_type"]: r for r in default_rules() if r["event_type"] in NEW_EVENTS}
    for et, r in wanted.items():
        r = dict(r)
        r["id"] = new_id("aur")
        r["name"] = f"__poc {et}"
        r["enabled"] = True
        r["test_tag"] = TAG
        await db.automation_rules.insert_one(r)
    return len(wanted)


async def conv_for(db):
    norm = _norm_phone(PHONE)
    return await db.conversations.find_one(
        {"contact_phone": {"$in": [PHONE, norm]}}, {"_id": 0})


async def main():
    print(f"\n{'='*60}\n  POC E3 — Dispatch & Komunikasi Operasi\n{'='*60}")
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    await cleanup(db)

    # --- 1. GEOCODING (Nominatim live) ---
    print(f"\n{Y}[1] Geocoding tujuan via Nominatim (perbaiki G1){X}")
    geo = await geocode(db, "Gunung Bromo, Probolinggo, Jawa Timur")
    ok_geo = bool(geo) and geo.get("lat") is not None and geo.get("lng") is not None
    check("geocode 'Bromo' mengembalikan koordinat", ok_geo, detail=str(geo))
    if ok_geo:
        in_id = -11.5 <= geo["lat"] <= 6.5 and 94.0 <= geo["lng"] <= 141.5
        check("koordinat berada di wilayah Indonesia", in_id,
              detail=f"lat={geo['lat']} lng={geo['lng']}")
        cached = await db.geocode_cache.find_one({"q": {"$exists": True}}, {"_id": 0})
        check("hasil geocode tersimpan di cache", cached is not None)
        geo2 = await geocode(db, "Gunung Bromo, Probolinggo, Jawa Timur")
        check("pemanggilan ke-2 (cache) konsisten", geo2 and geo2.get("lat") == geo["lat"])
    geo_bali = await geocode(db, "Kuta, Bali")
    check("geocode 'Kuta, Bali' juga berhasil", bool(geo_bali) and geo_bali.get("lat") is not None,
          detail=str(geo_bali))

    # --- 2. TRIGGER WA UNTUK EVENT BARU (mock) ---
    print(f"\n{Y}[2] Trigger WA driver->customer (event baru) via Automation Engine{X}")
    n_rules = await seed_rules(db)
    check("4 aturan otomasi event-baru aktif disiapkan", n_rules == 4, detail=f"n={n_rules}")

    base_payload = {
        "customer_name": "Pelanggan POC", "phone": PHONE, "code": "BK-POC1",
        "destination": "Bromo", "origin": "Bandung", "pickup": "Bandung",
        "start_datetime": "2026-07-10T07:00:00+00:00", "vehicle_name": "Hiace Premio 01",
        "driver_name": "Budi", "driver_phone": "081299990001", "company": "Travel Demo",
    }
    for i, et in enumerate(NEW_EVENTS):
        ev = await events.emit(db, et, base_payload, source="poc", ref_type="booking",
                               ref_id="bk_poc", dedupe_key=f"{TAG}:{et}")
        ok_run = ev is not None and (ev.get("runs_created", 0) >= 1)
        check(f"event '{et}' memicu aksi otomasi (run>=1)", ok_run,
              detail=f"runs={ev.get('runs_created') if ev else 'None'}")

    conv = await conv_for(db)
    check("percakapan WhatsApp (mock) ke pelanggan terbentuk", conv is not None)
    if conv:
        msgs = await db.messages.count_documents({"conversation_id": conv["id"]})
        check("≥4 pesan WA terkirim (assigned/confirm/enroute/arrived)", msgs >= 4,
              detail=f"messages={msgs}")
        check("biaya WA (cost tracking) > 0", float(conv.get("total_cost") or 0) > 0,
              detail=f"cost={conv.get('total_cost')}")

    # --- 3. IDEMPOTENSI ---
    print(f"\n{Y}[3] Idempotensi event (dedupe_key){X}")
    dup = await events.emit(db, "trip.assigned", base_payload, source="poc",
                            ref_type="booking", ref_id="bk_poc", dedupe_key=f"{TAG}:trip.assigned")
    check("event duplikat (dedupe sama) tidak diproses ulang", dup is None)

    await cleanup(db)
    print(f"\n{'='*60}")
    total = passed + failed
    color = G if failed == 0 else R
    print(f"  {color}HASIL: {passed}/{total} PASS, {failed} FAIL{X}")
    print(f"{'='*60}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
