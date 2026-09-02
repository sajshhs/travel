#!/usr/bin/env python3
"""test_core_e8.py — POC E8: Driver Workspace + Fleet Preventive + Master Vendor/Bengkel.

Memvalidasi inti backend SEBELUM membangun UI:
  - Workshops CRUD + RBAC (driver tak boleh mutasi).
  - Servis preventif: status overdue/due_soon dari interval seed + jadwalkan otomatis.
  - Maintenance create dgn workshop_id → nama bengkel ter-resolve.
  - Driver Workspace: summary/tasks + ack/arrived/pod + scoping kepemilikan (403/404).

Run: cd /app && python test_core_e8.py  (backend hidup + DB ter-seed)
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
    global passed
    passed += 1
    print(f"  {G}[PASS]{X} {m}")


def bad(m):
    global failed
    failed += 1
    print(f"  {R}[FAIL]{X} {m}")


def check(cond, m):
    ok(m) if cond else bad(m)


def login(email):
    r = requests.post(f"{API}/api/auth/login",
                      json={"email": email, "password": "demo12345"}, timeout=20)
    return r.json().get("token")


def H(t):
    return {"Authorization": f"Bearer {t}"}


def main():
    owner, ops, drv = login("owner@demo.local"), login("ops@demo.local"), login("driver@demo.local")
    check(all([owner, ops, drv]), "Login owner/ops/driver")

    print("\n--- Master Vendor/Bengkel (workshops) ---")
    r = requests.get(f"{API}/api/workshops", headers=H(owner), timeout=20)
    ws = r.json() if r.status_code == 200 else []
    check(r.status_code == 200 and isinstance(ws, list) and len(ws) >= 3, f"GET /workshops ({len(ws)} item)")
    check(all(str(w.get("id", "")).startswith("wsh_") for w in ws), "id workshops berprefiks wsh_")
    r = requests.post(f"{API}/api/workshops", headers=H(owner),
                      json={"name": "Bengkel POC", "city": "Bandung", "specialties": ["servis"]}, timeout=20)
    wid = r.json().get("id") if r.status_code == 200 else None
    check(r.status_code == 200 and str(wid).startswith("wsh_"), "POST /workshops (create)")
    r = requests.patch(f"{API}/api/workshops/{wid}", headers=H(owner), json={"active": False}, timeout=20)
    check(r.status_code == 200 and r.json().get("active") is False, "PATCH /workshops active=false")
    r = requests.post(f"{API}/api/workshops", headers=H(drv), json={"name": "X"}, timeout=20)
    check(r.status_code == 403, "RBAC: driver create workshop → 403")
    r = requests.delete(f"{API}/api/workshops/{wid}", headers=H(owner), timeout=20)
    check(r.status_code == 200 and r.json().get("deleted"), "DELETE /workshops")

    print("\n--- Servis Preventif Terjadwal ---")
    r = requests.get(f"{API}/api/maintenance/preventive", headers=H(owner), timeout=20)
    pv = r.json() if r.status_code == 200 else {}
    items = pv.get("items", []) if isinstance(pv, dict) else []
    check(r.status_code == 200 and len(items) >= 1, f"GET /maintenance/preventive ({len(items)} armada)")
    check(any(i["status"] == "overdue" for i in items), "ada armada OVERDUE (seed veh01 km habis)")
    check(any(i["status"] == "due_soon" for i in items), "ada armada DUE_SOON (seed veh02 sisa ~1000km)")
    sample = items[0] if items else {}
    check(bool(sample.get("status")) and (sample.get("km") or sample.get("date")), "item preventif punya basis km/waktu + status")
    summ = pv.get("summary", {})
    check(summ.get("total") == len(items), "summary.total konsisten dgn items")
    r = requests.get(f"{API}/api/maintenance/preventive", headers=H(drv), timeout=20)
    check(r.status_code == 200, "driver baca preventif (read-only) → 200")
    vid = next((i["vehicle_id"] for i in items if i["status"] in ("overdue", "due_soon")), items[0]["vehicle_id"])
    r = requests.post(f"{API}/api/maintenance/preventive/{vid}/schedule", headers=H(owner), timeout=20)
    check(r.status_code == 200 and r.json().get("type") == "servis" and r.json().get("status") == "scheduled",
          "POST preventive/{id}/schedule → maintenance servis 'scheduled'")
    r = requests.post(f"{API}/api/maintenance/preventive/{vid}/schedule", headers=H(drv), timeout=20)
    check(r.status_code == 403, "RBAC: driver schedule preventive → 403")

    print("\n--- Maintenance + workshop_id ---")
    auto = next((w for w in requests.get(f"{API}/api/workshops", headers=H(owner), timeout=20).json()
                 if "Auto2000" in w.get("name", "")), None)
    if auto:
        r = requests.post(f"{API}/api/maintenance", headers=H(owner),
                          json={"vehicle_id": vid, "type": "servis", "title": "Servis POC",
                                "workshop_id": auto["id"]}, timeout=20)
        check(r.status_code == 200 and r.json().get("workshop") == auto["name"]
              and r.json().get("workshop_id") == auto["id"], "create maintenance workshop_id → nama ter-resolve")

    print("\n--- Driver Workspace ---")
    r = requests.get(f"{API}/api/driver/summary", headers=H(drv), timeout=20)
    s = r.json() if r.status_code == 200 else {}
    check(r.status_code == 200 and s.get("is_driver") is True and "total" in s, f"GET /driver/summary (total={s.get('total')})")
    r = requests.get(f"{API}/api/driver/tasks", headers=H(drv), timeout=20)
    tasks = r.json() if r.status_code == 200 else []
    check(r.status_code == 200 and isinstance(tasks, list) and len(tasks) >= 1, f"GET /driver/tasks ({len(tasks)} tugas)")
    t0 = tasks[0] if tasks else {}
    check(all(k in t0 for k in ("trip_id", "destination", "trip_status", "acknowledged")),
          "task punya trip_id/destination/trip_status/acknowledged")
    tid = t0.get("trip_id")
    r = requests.post(f"{API}/api/driver/tasks/{tid}/ack", headers=H(drv), timeout=20)
    check(r.status_code == 200 and r.json().get("driver_ack_at"), "POST driver ack → driver_ack_at terisi")
    r = requests.post(f"{API}/api/driver/tasks/{tid}/arrived", headers=H(drv), timeout=20)
    check(r.status_code == 200 and r.json().get("arrived_at"), "POST driver arrived → arrived_at terisi")
    r = requests.post(f"{API}/api/driver/tasks/{tid}/pod", headers=H(drv),
                      data={"recipient_name": "Pak Budi", "note": "Diterima di lobi"}, timeout=20)
    check(r.status_code == 200 and r.json().get("pod"), "POST driver pod (catatan) → pod tersimpan")

    print("\n--- Scoping / RBAC kepemilikan ---")
    r = requests.get(f"{API}/api/driver/tasks", headers=H(owner), timeout=20)
    check(r.status_code == 200 and r.json() == [], "owner (bukan driver) → tasks kosong")
    r = requests.post(f"{API}/api/driver/tasks/trp_tidakada/ack", headers=H(drv), timeout=20)
    check(r.status_code == 404, "driver ack trip tak ada → 404")
    r = requests.post(f"{API}/api/driver/tasks/{tid}/ack", headers=H(owner), timeout=20)
    check(r.status_code == 403, "non-driver ack → 403")
    # trip milik driver lain (via dispatch/today) → 403 kepemilikan
    disp = requests.get(f"{API}/api/dispatch/today", headers=H(owner), timeout=20).json()
    other = next((d.get("trip_id") for d in disp.get("departures", [])
                  if d.get("trip_id") and d.get("trip_id") != tid and d.get("driver_id")), None)
    if other:
        r = requests.post(f"{API}/api/driver/tasks/{other}/ack", headers=H(drv), timeout=20)
        check(r.status_code == 403, "driver ack trip milik driver lain → 403 (kepemilikan)")

    print(f"\n{'='*56}\n  {G}PASS {passed}{X} | {R}FAIL {failed}{X}\n{'='*56}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
