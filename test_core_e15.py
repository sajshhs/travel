"""test_core_e15.py — POC inti E15 (GPS Dual-Source: device fisik via Traccar).

Menguji langsung backend live (localhost:8001):
  1. Auth owner + assign IMEI ke armada.
  2. Webhook Traccar → ingest device (konversi knot→km/j, power/ignition tersimpan).
  3. /gps/live menampilkan source=device + telemetri.
  4. FAILOVER: device fresh diprioritaskan atas phone (kebutuhan backup).
  5. Alarm powerCut → notifikasi gps_alarm dibuat.
  6. IMEI tak dikenal → diabaikan (ignored/imei_unmapped).
  7. Auth webhook: token salah → 401.
  8. /gps/devices & /gps/summary konsisten.

Exit code 0 = semua PASS.
"""
import os
import sys
import json
import urllib.request
import urllib.error

BASE = "http://localhost:8001/api"
SECRET = "c5ec694b7067a93fcf056bebc1ec8a547e6aefec07da7b85"
IMEI = "POC864000123456789"
UNKNOWN_IMEI = "POC000000000000000"

results = []


def _req(method, path, body=None, headers=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)}


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return cond


def traccar_payload(imei, lat, lng, speed_knot, alarm=None, power=12.8, ignition=True):
    attrs = {"ignition": ignition, "motion": speed_knot > 1, "power": power,
             "battery": 4.1, "batteryLevel": 95, "sat": 12, "blocked": False}
    if alarm:
        attrs["alarm"] = alarm
    return {
        "position": {
            "id": 1, "deviceId": 1, "protocol": "teltonika",
            "fixTime": "2026-07-01T18:00:00.000+00:00", "valid": True,
            "latitude": lat, "longitude": lng, "speed": speed_knot, "course": 90.0,
            "attributes": attrs,
        },
        "device": {"id": 1, "uniqueId": imei, "name": "POC-Teltonika"},
    }


def main():
    print("== E15 GPS Dual-Source POC ==")

    # 1) Login owner
    st, r = _req("POST", "/auth/login", {"email": "owner@demo.local", "password": "demo12345"})
    token = r.get("token")
    if not check("Login owner", st == 200 and token, f"status={st}"):
        return finish()

    # Pilih armada pertama
    st, vehicles = _req("GET", "/vehicles", token=token)
    if not check("List vehicles", st == 200 and isinstance(vehicles, list) and vehicles, f"status={st}"):
        return finish()
    veh = vehicles[0]
    vid = veh["id"]
    print(f"    -> pakai armada {veh.get('code')} {veh.get('name')} ({vid})")

    # 2) Assign IMEI
    st, r = _req("POST", f"/gps/devices/{vid}/assign", {"imei": IMEI, "enabled": True, "note": "POC"}, token=token)
    check("Assign IMEI ke armada", st == 200 and r.get("ok"), f"status={st} {r.get('detail','')}")

    # 3) Webhook ingest (27 knot ~ 50 km/j)
    st, r = _req("POST", "/gps/webhook", traccar_payload(IMEI, -6.2000, 106.8000, 27.0),
                 headers={"X-Gps-Token": SECRET})
    check("Webhook device diterima", st == 200 and r.get("status") == "ok", f"status={st} {r}")
    check("Mapping IMEI→armada benar", r.get("vehicle_id") == vid, f"vid={r.get('vehicle_id')}")
    check("Konversi knot→km/j (27kn≈50)", abs((r.get("speed_kmh") or 0) - 50.0) < 0.2, f"speed_kmh={r.get('speed_kmh')}")

    # 4) /gps/live source=device + telemetri
    st, live = _req("GET", "/gps/live", token=token)
    row = next((x for x in live if x.get("vehicle_id") == vid), None) if isinstance(live, list) else None
    check("Live menampilkan armada", row is not None, f"status={st}")
    if row:
        check("Live source = device", row.get("source") == "device", f"source={row.get('source')}")
        check("Live speed ≈ 50 km/j", abs((row.get("speed") or 0) - 50.0) < 0.2, f"speed={row.get('speed')}")
        check("Live power_v = 12.8", abs((row.get("power_v") or 0) - 12.8) < 0.01, f"power_v={row.get('power_v')}")
        check("Live ignition = True", row.get("ignition") is True, f"ignition={row.get('ignition')}")
        check("Live has_device = True", row.get("has_device") is True, "")

    # 5) FAILOVER: kirim titik phone (lebih baru) → device tetap diprioritaskan
    st, r = _req("POST", "/locations", {"vehicle_id": vid, "lat": -6.3, "lng": 106.9, "speed": 10}, token=token)
    check("Ingest phone (utk uji failover)", st == 200, f"status={st}")
    # kirim ulang device fresh agar jelas device masih aktif
    _req("POST", "/gps/webhook", traccar_payload(IMEI, -6.2100, 106.8100, 30.0), headers={"X-Gps-Token": SECRET})
    st, live = _req("GET", "/gps/live", token=token)
    row = next((x for x in live if x.get("vehicle_id") == vid), None) if isinstance(live, list) else None
    if row:
        check("FAILOVER: device diprioritaskan atas phone", row.get("source") == "device",
              f"source={row.get('source')} has_phone={row.get('has_phone')}")
        check("FAILOVER: has_phone terdeteksi juga", row.get("has_phone") is True, "")

    # 6) Alarm powerCut → notifikasi gps_alarm
    st, r = _req("POST", "/gps/webhook", traccar_payload(IMEI, -6.2100, 106.8100, 0.0, alarm="powerCut"),
                 headers={"X-Gps-Token": SECRET})
    alarm = (r or {}).get("alarm") or {}
    check("Webhook alarm powerCut diproses", st == 200 and alarm.get("alarm") == "powerCut", f"{alarm}")
    st, notifs = _req("GET", "/notifications", token=token)
    has_alarm = isinstance(notifs, list) and any(n.get("type") == "gps_alarm" for n in notifs)
    check("Notifikasi gps_alarm dibuat & terlihat owner", has_alarm, f"n={len(notifs) if isinstance(notifs, list) else '?'}")

    # 7) IMEI tak dikenal → diabaikan
    st, r = _req("POST", "/gps/webhook", traccar_payload(UNKNOWN_IMEI, -6.2, 106.8, 5.0),
                 headers={"X-Gps-Token": SECRET})
    check("IMEI tak dikenal → ignored", st == 200 and r.get("status") == "ignored"
          and r.get("reason") == "imei_unmapped", f"{r}")

    # 8) Auth webhook: token salah → 401
    st, r = _req("POST", "/gps/webhook", traccar_payload(IMEI, -6.2, 106.8, 5.0),
                 headers={"X-Gps-Token": "SALAH"})
    check("Webhook token salah → 401", st == 401, f"status={st}")
    # tanpa token juga 401
    st, r = _req("POST", "/gps/webhook", traccar_payload(IMEI, -6.2, 106.8, 5.0))
    check("Webhook tanpa token → 401", st == 401, f"status={st}")

    # 9) devices & summary
    st, devices = _req("GET", "/gps/devices", token=token)
    dev_row = next((d for d in devices if d.get("vehicle_id") == vid), None) if isinstance(devices, list) else None
    check("Devices: armada tampil dgn IMEI", dev_row is not None and dev_row.get("imei") == IMEI,
          f"imei={dev_row.get('imei') if dev_row else None}")
    if dev_row:
        check("Devices: online = True", dev_row.get("online") is True, f"online={dev_row.get('online')}")
    st, summ = _req("GET", "/gps/summary", token=token)
    check("Summary: with_device≥1 & online≥1", (summ.get("with_device", 0) >= 1)
          and (summ.get("online", 0) >= 1), f"{summ}")

    return finish()


def finish():
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n== HASIL: {passed}/{total} PASS ==")
    if passed != total:
        print("GAGAL:")
        for n, ok, d in results:
            if not ok:
                print(f"  - {n} :: {d}")
        sys.exit(1)
    print("SEMUA POC E15 HIJAU ✅")
    sys.exit(0)


if __name__ == "__main__":
    main()
