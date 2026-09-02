#!/usr/bin/env python3
"""fa_rbac_matrix.py (FORENSIK) — matriks RBAC runtime: peran `driver` TAK BOLEH akses modul manajemen.

Enumerasi GET (tanpa path-param) dari `/openapi.json` yang path-nya mengandung modul sensitif.
- driver → HARUS 401/403 (bukan 200 = kebocoran; bukan 5xx = crash).
- owner  → HARUS bukan 401/403 & bukan 5xx (boleh 200/2xx).
Melengkapi INV-RBAC (statik) dgn BUKTI runtime. Jalankan via `scripts/run_forensics.sh`.
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("GUARD_BASE_URL", "http://127.0.0.1:8001")
API = BASE + "/api"
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; X = "\033[0m"

SENSITIVE = ("settings", "finance", "invoice", "payroll", "expense", "audit",
             "report", "/crm", "content", "partner", "analytic", "/users", "broadcast")


def req(path, token):
    r = urllib.request.Request(BASE + path, method="GET")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:  # noqa: BLE001
        return -1


def login(email):
    r = urllib.request.Request(API + "/auth/login",
                               data=json.dumps({"email": email, "password": "demo12345"}).encode(),
                               method="POST")
    r.add_header("Content-Type", "application/json")
    try:
        return json.loads(urllib.request.urlopen(r, timeout=15).read())["token"]
    except Exception:  # noqa: BLE001
        return None


def openapi_paths():
    try:
        return json.load(urllib.request.urlopen(BASE + "/openapi.json", timeout=15)).get("paths", {})
    except Exception as e:  # noqa: BLE001
        print(f"{R}gagal ambil openapi: {e}{X}")
        return {}


def main() -> int:
    owner = login("owner@demo.local")
    driver = login("driver@demo.local")
    if not owner or not driver:
        print(f"{R}login owner/driver gagal — backend hidup?{X}")
        return 2
    paths = openapi_paths()
    targets = [p for p, ops in paths.items()
               if "get" in ops and "{" not in p and any(s in p for s in SENSITIVE)]
    leaks = []
    crashes = []
    owner_blocked = []
    for p in sorted(targets):
        ds = req(p, driver)
        if ds >= 500:
            crashes.append(("driver", p, ds))
        elif ds not in (401, 403):
            leaks.append((p, ds))  # driver TIDAK diblokir = kebocoran
        os_ = req(p, owner)
        if os_ >= 500:
            crashes.append(("owner", p, os_))
        elif os_ in (401, 403):
            owner_blocked.append((p, os_))  # owner malah diblokir = false-positive RBAC
    print(f"=== fa_rbac_matrix: {len(targets)} endpoint sensitif (GET no-param) × (driver, owner) ===")
    bad = 0
    if leaks:
        bad += len(leaks)
        print(f"{R}✗ {len(leaks)} KEBOCORAN — driver mengakses modul manajemen (harus 401/403):{X}")
        for p, st in leaks[:40]:
            print(f"   {R}driver {st}{X} {p}")
    if crashes:
        bad += len(crashes)
        print(f"{R}✗ {len(crashes)} CRASH 5xx pada cek RBAC:{X}")
        for role, p, st in crashes[:40]:
            print(f"   {R}{role} {st}{X} {p}")
    if owner_blocked:
        print(f"{Y}⚠ {len(owner_blocked)} endpoint memblokir OWNER (cek apakah wajar / butuh query):{X}")
        for p, st in owner_blocked[:20]:
            print(f"   {Y}owner {st}{X} {p}")
    if bad == 0:
        print(f"{G}✓ RBAC runtime aman: driver diblokir di semua modul manajemen, owner tak crash.{X}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
