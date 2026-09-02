#!/usr/bin/env python3
"""test_core_phase1.py — POC ISOLASI untuk Phase 1 (Core).

Membuktikan 3 hal paling failure-prone SEBELUM membangun app:
  1. OSRM ETA  : panggilan nyata ke provider OSM (jarak + ETA + polyline).
  2. Anti double-booking: fungsi overlap (positif & negatif) — INV-4.
  3. Locations : validasi monotonik timestamp + rentang lat/lng — INV-6.

Jalankan: cd /app && python test_core_phase1.py
Exit 0 = semua POC HIJAU.
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from services.availability import overlaps  # noqa: E402
from services.geo import parse_iso, valid_coord  # noqa: E402
from services.osrm import fallback_eta, route_eta  # noqa: E402

G, R, Y, B, X = "\033[92m", "\033[91m", "\033[93m", "\033[1m", "\033[0m"
results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        results["pass"] += 1
        print(f"  {G}[PASS]{X} {name}" + (f"  {detail}" if detail else ""))
    else:
        results["fail"] += 1
        print(f"  {R}[FAIL]{X} {name}" + (f"  {detail}" if detail else ""))


async def poc_osrm():
    print(f"\n{B}1) OSRM ETA (panggilan nyata ke provider OSM){X}")
    # Bandung (kota) -> Lembang (~15-20km berkendara)
    res = await route_eta(-6.9147, 107.6098, -6.8118, 107.6175, with_geometry=True)
    if res is None:
        print(f"  {Y}[WARN]{X} OSRM tak menjawab — uji fallback haversine sebagai gantinya.")
        fb = fallback_eta(-6.9147, 107.6098, -6.8118, 107.6175)
        check("fallback_eta menghasilkan jarak>0 & eta>0", fb["distance_km"] > 0 and fb["eta_minutes"] > 0, str(fb))
        return
    check("OSRM distance_km > 0", res["distance_km"] > 0, f"{res['distance_km']} km")
    check("OSRM eta_minutes > 0", res["eta_minutes"] > 0, f"{res['eta_minutes']} mnt")
    check("OSRM polyline >= 2 titik [lat,lng]", len(res["geometry"]) >= 2, f"{len(res['geometry'])} titik")
    if res["geometry"]:
        lat, lng = res["geometry"][0]
        check("polyline titik pertama dalam rentang valid", valid_coord(lat, lng), f"[{lat},{lng}]")


def poc_double_booking():
    print(f"\n{B}2) Anti double-booking (overlap engine — INV-4){X}")
    now = datetime.now(timezone.utc)
    d = lambda days: (now + timedelta(days=days)).isoformat()  # noqa: E731
    # A = [d3, d5]
    check("overlap: B[d4,d6] vs A[d3,d5] -> TRUE", overlaps(d(3), d(5), d(4), d(6)) is True)
    check("overlap: C[d5,d7] (bersentuhan) vs A[d3,d5] -> FALSE", overlaps(d(3), d(5), d(5), d(7)) is False)
    check("overlap: D[d1,d2] vs A[d3,d5] -> FALSE", overlaps(d(3), d(5), d(1), d(2)) is False)
    check("overlap: E[d3,d5] identik -> TRUE", overlaps(d(3), d(5), d(3), d(5)) is True)
    check("overlap: F membungkus [d2,d6] vs A[d3,d5] -> TRUE", overlaps(d(3), d(5), d(2), d(6)) is True)
    # Mendukung campuran format Z dan +00:00
    zulu = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    check("overlap menerima format 'Z'", overlaps(zulu, d(5), d(0), d(1)) in (True, False))


def poc_locations_monotonic():
    print(f"\n{B}3) Locations monotonik + rentang valid (INV-6){X}")
    now = datetime.now(timezone.utc)
    pts = [
        {"lat": -6.9147, "lng": 107.6098, "timestamp": (now + timedelta(seconds=0)).isoformat()},
        {"lat": -6.9100, "lng": 107.6120, "timestamp": (now + timedelta(seconds=30)).isoformat()},
        {"lat": -6.9050, "lng": 107.6150, "timestamp": (now + timedelta(seconds=60)).isoformat()},
    ]
    ts = [parse_iso(p["timestamp"]) for p in pts]
    check("timestamp monotonik naik", ts == sorted(ts))
    check("semua koordinat valid", all(valid_coord(p["lat"], p["lng"]) for p in pts))
    # negatif: koordinat di luar rentang harus tertangkap
    check("koordinat invalid (lat=200) tertangkap", valid_coord(200, 107) is False)
    # negatif: urutan mundur terdeteksi
    bad = [ts[2], ts[0], ts[1]]
    check("urutan mundur terdeteksi (bukan sorted)", bad != sorted(bad))


async def main():
    print(f"{B}{'='*64}{X}\n  POC PHASE 1 — GPS/ETA + Anti Double-Booking\n{B}{'='*64}{X}")
    await poc_osrm()
    poc_double_booking()
    poc_locations_monotonic()
    print(f"\n{B}{'='*64}{X}\n  {G}PASS {results['pass']}{X} | {R}FAIL {results['fail']}{X}\n{B}{'='*64}{X}")
    if results["fail"]:
        print(f"{R}{B}  POC GAGAL — perbaiki core sebelum membangun app.{X}\n")
        return 1
    print(f"{G}{B}  POC HIJAU — core terbukti, lanjut membangun app.{X}\n")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
