#!/usr/bin/env python3
"""test_core_conflict.py — POC ISOLASI: kelas "bentrok" mana yang NYATA terjadi?

Konteks (titik henti sesi lalu): banner bentrok di Kalender Keberangkatan tidak muncul
(`CONFLICT BANNER: False`, `CONFLICT-MARKED CHIPS: 0`). Hipotesis: bukan bug UI, tapi
memang TIDAK ADA data bentrok karena backend sudah mengunci INV-4 di semua jalur tulis.

Script ini membuktikan lewat API NYATA (bukan mock) kelas bentrok mana yang:
  A. Sudah dicegah backend (400)        -> aman, banner memang harus 0
  B. LOLOS / bisa terjadi (GAP)         -> sumber data bentrok yang nyata & wajib ditampilkan

Kelas yang diuji:
  1. Armada dobel via POST /bookings (status aktif)                  -> harus 400
  2. Armada dobel via POST /bookings/{id}/reschedule                  -> harus 400
  3. Perawatan (maintenance) menabrak keberangkatan aktif             -> ? (INV-21)
  4. Booking `pending` dari publik (tanpa armada) — 2x tumpang-tindih -> pending menumpuk
  5. Driver dobel pada booking pending (PATCH driver)                 -> ?
  6. Keberangkatan aktif TANPA driver (risiko operasional)            -> hitung
  7. Booking `completed` overlap booking aktif (potensi false-positive UI)

Jalankan: python /app/test_core_conflict.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

BASE = os.environ.get("POC_BASE", "http://localhost:8001/api")
OWNER = ("owner@demo.local", "demo12345")

G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; C = "\033[96m"; B = "\033[1m"; X = "\033[0m"
results = []


def head(t):
    print(f"\n{C}{B}{'=' * 72}\n  {t}\n{'=' * 72}{X}")


def ok(msg):
    print(f"  {G}[OK]{X} {msg}")
    results.append(("OK", msg))


def gap(msg):
    print(f"  {Y}[GAP]{X} {msg}")
    results.append(("GAP", msg))


def bad(msg):
    print(f"  {R}[FAIL]{X} {msg}")
    results.append(("FAIL", msg))


def info(msg):
    print(f"       {msg}")


def parse(dt):
    if not dt:
        return None
    try:
        return datetime.fromisoformat(str(dt).replace("Z", "+00:00"))
    except ValueError:
        return None


def overlaps(a1, a2, b1, b2):
    a1, a2, b1, b2 = parse(a1), parse(a2), parse(b1), parse(b2)
    if not all([a1, a2, b1, b2]):
        return False
    return a1 < b2 and b1 < a2


def login():
    r = requests.post(f"{BASE}/auth/login", json={"email": OWNER[0], "password": OWNER[1]}, timeout=20)
    r.raise_for_status()
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, f"token tidak ada: {r.text[:200]}"
    return {"Authorization": f"Bearer {tok}"}


def main():
    head("LOGIN + SNAPSHOT DATA")
    H = login()
    ok("login owner berhasil")
    bookings = requests.get(f"{BASE}/bookings?limit=1000", headers=H, timeout=30).json()
    vehicles = requests.get(f"{BASE}/vehicles", headers=H, timeout=30).json()
    drivers = requests.get(f"{BASE}/drivers", headers=H, timeout=30).json()
    customers = requests.get(f"{BASE}/customers", headers=H, timeout=30).json()
    info(f"bookings={len(bookings)} vehicles={len(vehicles)} drivers={len(drivers)} customers={len(customers)}")

    ACTIVE = {"hold", "confirmed", "ongoing"}
    by_status = {}
    for b in bookings:
        by_status[b.get("status")] = by_status.get(b.get("status"), 0) + 1
    info(f"sebaran status: {by_status}")

    # ---- Kelas 7 + baseline: hitung overlap yang ADA di data sekarang -------------
    head("BASELINE — overlap yang benar-benar ADA di data saat ini")
    def pairs(pred):
        out = []
        byv = {}
        for b in bookings:
            if b.get("vehicle_id"):
                byv.setdefault(b["vehicle_id"], []).append(b)
        for vid, lst in byv.items():
            for i in range(len(lst)):
                for j in range(i + 1, len(lst)):
                    a, c = lst[i], lst[j]
                    if pred(a, c) and overlaps(a.get("start_datetime"), a.get("end_datetime"),
                                               c.get("start_datetime"), c.get("end_datetime")):
                        out.append((vid, a.get("code"), a.get("status"), c.get("code"), c.get("status")))
        return out

    active_pairs = pairs(lambda a, c: a.get("status") in ACTIVE and c.get("status") in ACTIVE)
    any_pairs = pairs(lambda a, c: a.get("status") != "cancelled" and c.get("status") != "cancelled")
    info(f"overlap armada antar status AKTIF   : {len(active_pairs)} {active_pairs[:3]}")
    info(f"overlap armada semua status (non-cancel): {len(any_pairs)} {any_pairs[:3]}")
    if not active_pairs:
        ok("tidak ada bentrok armada aktif -> banner 0 pada data seed = BENAR (bukan bug UI)")
    else:
        gap(f"ADA {len(active_pairs)} bentrok armada aktif di data")

    # driver overlap
    byd = {}
    for b in bookings:
        if b.get("driver_id") and b.get("status") != "cancelled":
            byd.setdefault(b["driver_id"], []).append(b)
    dpairs = []
    for did, lst in byd.items():
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                if overlaps(lst[i].get("start_datetime"), lst[i].get("end_datetime"),
                            lst[j].get("start_datetime"), lst[j].get("end_datetime")):
                    dpairs.append((did, lst[i].get("code"), lst[j].get("code")))
    info(f"overlap DRIVER (non-cancel): {len(dpairs)} {dpairs[:3]}")

    # kelas 6: aktif tanpa driver
    no_driver = [b for b in bookings if b.get("status") in ACTIVE and not b.get("driver_id")]
    info(f"keberangkatan AKTIF tanpa driver: {len(no_driver)} -> {[b.get('code') for b in no_driver][:6]}")
    if no_driver:
        gap(f"{len(no_driver)} keberangkatan aktif BELUM punya driver (risiko ops nyata, tidak ditampilkan di kalender)")

    pending = [b for b in bookings if b.get("status") == "pending"]
    info(f"permintaan pending: {len(pending)} (vehicle_id kosong: {sum(1 for b in pending if not b.get('vehicle_id'))})")

    # ---- Kelas 1: POST /bookings overlap armada aktif -----------------------------
    head("KELAS 1 — POST /bookings pada slot armada aktif (harus DITOLAK)")
    anchor = next((b for b in bookings if b.get("status") in ACTIVE and b.get("vehicle_id")
                   and b.get("start_datetime") and b.get("end_datetime")), None)
    if not anchor:
        bad("tidak ada booking aktif sebagai acuan")
        return finish()
    info(f"acuan: {anchor['code']} veh={anchor.get('vehicle_name')} {anchor['start_datetime'][:16]} -> {anchor['end_datetime'][:16]}")
    s = parse(anchor["start_datetime"]) + timedelta(minutes=30)
    e = parse(anchor["end_datetime"]) + timedelta(minutes=30)
    cust = customers[0]["id"]
    payload = {"customer_id": cust, "vehicle_id": anchor["vehicle_id"], "origin": "POC",
               "destination": "POC", "start_datetime": s.isoformat(), "end_datetime": e.isoformat(),
               "base_price": 1000000}
    r = requests.post(f"{BASE}/bookings", json=payload, headers=H, timeout=30)
    if r.status_code == 400 and "bentrok" in r.text.lower():
        ok(f"ditolak 400: {r.json().get('detail')[:80]}")
    else:
        gap(f"LOLOS ({r.status_code}) -> bisa jadi sumber bentrok nyata: {r.text[:160]}")
        created_id = r.json().get("id") if r.status_code < 300 else None
        if created_id:
            requests.post(f"{BASE}/bookings/{created_id}/cancel", json={"reason": "poc cleanup"}, headers=H, timeout=20)

    # ---- Kelas 2: reschedule ke slot bentrok --------------------------------------
    head("KELAS 2 — reschedule ke slot armada yang sudah terisi (harus DITOLAK)")
    other = next((b for b in bookings if b.get("status") in ACTIVE and b.get("vehicle_id")
                  and b["id"] != anchor["id"]), None)
    if other:
        r = requests.post(f"{BASE}/bookings/{other['id']}/reschedule",
                          json={"start_datetime": anchor["start_datetime"], "end_datetime": anchor["end_datetime"],
                                "vehicle_id": anchor["vehicle_id"], "reason": "poc"}, headers=H, timeout=30)
        if r.status_code == 400:
            ok(f"ditolak 400: {str(r.json().get('detail'))[:80]}")
        else:
            gap(f"LOLOS ({r.status_code}) -> reschedule bisa membuat bentrok: {r.text[:160]}")
    else:
        info("hanya 1 booking aktif — kelas 2 dilewati")

    # ---- Kelas 3: maintenance menabrak keberangkatan aktif ------------------------
    head("KELAS 3 — POST /maintenance pada window keberangkatan aktif (INV-21)")
    mpay = {"vehicle_id": anchor["vehicle_id"], "type": "perbaikan", "title": "POC cek INV-21",
            "start_date": anchor["start_datetime"][:10], "end_date": anchor["end_datetime"][:10],
            "status": "scheduled", "cost": 0}
    r = requests.post(f"{BASE}/maintenance", json=mpay, headers=H, timeout=30)
    if r.status_code == 400:
        ok(f"ditolak 400: {str(r.json().get('detail'))[:100]}")
    elif r.status_code < 300:
        mid = r.json().get("id")
        gap("LOLOS — perawatan bisa dibuat menabrak keberangkatan AKTIF "
            f"(melanggar INV-21). id={mid} -> kelas bentrok NYATA untuk kalender")
        if mid:
            d = requests.delete(f"{BASE}/maintenance/{mid}", headers=H, timeout=20)
            info(f"cleanup maintenance: {d.status_code}")
    else:
        bad(f"respon tak terduga {r.status_code}: {r.text[:160]}")

    # ---- Kelas 4: 2 permintaan publik tumpang-tindih ------------------------------
    head("KELAS 4 — 2 permintaan publik tumpang-tindih (pending, tanpa armada)")
    base_dt = datetime.now(timezone.utc) + timedelta(days=9)
    made = []
    for i, nm in enumerate(["POC Uji Bentrok A", "POC Uji Bentrok B"]):
        pay = {"name": nm, "phone": f"08111000{i}99", "origin": "Jakarta", "destination": "Bandung",
               "start_datetime": (base_dt + timedelta(hours=i)).isoformat(),
               "end_datetime": (base_dt + timedelta(hours=8 + i)).isoformat(), "pax": 30,
               "vehicle_type": "bus_besar", "message": "poc"}
        r = requests.post(f"{BASE}/public/booking", json=pay, timeout=30)
        if r.status_code < 300:
            made.append(r.json())
            info(f"pending dibuat: {r.json().get('code')}")
        else:
            info(f"gagal ({r.status_code}): {r.text[:120]}")
    if len(made) == 2:
        ok("2 permintaan pending tumpang-tindih diterima (memang tidak mereservasi armada)")
        gap("pending TANPA armada -> deteksi bentrok kalender (yang berbasis vehicle_name) TIDAK akan melihatnya; "
            "ops butuh sinyal 'permintaan menunggu diproses' di kalender")

    # ---- Kelas 5: driver dobel pada booking pending -------------------------------
    head("KELAS 5 — PATCH driver ke booking pending yang bentrok jadwal driver")
    drv_active = next((b for b in bookings if b.get("status") in ACTIVE and b.get("driver_id")), None)
    if drv_active and made:
        pid = made[0]["id"]
        # samakan jadwal pending ke jadwal booking driver agar pasti overlap -> tak bisa via API
        # (pending tak bisa reschedule? coba), jadi cukup uji PATCH driver saja.
        r = requests.patch(f"{BASE}/bookings/{pid}", json={"driver_id": drv_active["driver_id"]},
                           headers=H, timeout=30)
        info(f"PATCH driver ke pending: {r.status_code} {str(r.text)[:120]}")
        if r.status_code < 300:
            gap("driver bisa ditugaskan ke booking pending (tanpa cek bentrok terhadap pending lain) "
                "-> kelas bentrok driver bisa muncul saat banyak pending")
        else:
            ok("PATCH driver pada pending divalidasi backend")
    else:
        info("tidak ada booking aktif berdriver / pending — kelas 5 dilewati")

    # cleanup pending POC
    for m in made:
        rc = requests.post(f"{BASE}/bookings/{m['id']}/reject", headers=H, timeout=20)
        info(f"cleanup pending {m.get('code')}: {rc.status_code}")

    finish()


def finish():
    head("RINGKASAN")
    n_ok = sum(1 for k, _ in results if k == "OK")
    n_gap = sum(1 for k, _ in results if k == "GAP")
    n_bad = sum(1 for k, _ in results if k == "FAIL")
    for k, m in results:
        col = G if k == "OK" else (Y if k == "GAP" else R)
        print(f"  {col}{k:4}{X} {m}")
    print(f"\n  {G}OK={n_ok}{X}  {Y}GAP={n_gap}{X}  {R}FAIL={n_bad}{X}\n")
    sys.exit(1 if n_bad else 0)


if __name__ == "__main__":
    main()
