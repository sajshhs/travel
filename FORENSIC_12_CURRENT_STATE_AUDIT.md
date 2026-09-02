# 🔬 FORENSIC 12 — CURRENT STATE AUDIT (Koreksi Empiris / Bukti Live)

> **Bagian terpenting.** Ini adalah hasil **Pass Pendalaman**: login nyata → panggil endpoint → cek DB → cleanup. Beberapa hal yang "kelihatan aman" dari baca kode **PECAH saat alur nyata**. Semua di bawah **REPRODUCIBLE** via `python scripts/forensic_repro.py` (idempotent, auto-cleanup ke baseline).

**Konteks:** server `today = 2026-07-02`. Uji memakai tanggal **2027** (jauh dari seed) + cleanup total. Kredensial: `owner@demo.local` / `demo12345`.

---

## 12.1 Ringkasan Verdict (7/7 TERBUKTI)

```
[TERBUKTI] BUG-A cancel-tak-bebaskan-armada/trip   → RC-04 (P0)
[TERBUKTI] BUG-B pembayaran-ke-booking-cancelled   → RC-05 (P1)
[TERBUKTI] BUG-C selesai-menutupi-tunggakan        → RC-02 (P0)
[TERBUKTI] BUG-D jalur-status-generik-split-brain  → RC-03 (P0)
[TERBUKTI] BUG-E payroll-overlap-dobel-hitung      → RC-06 (P1)
[TERBUKTI] BUG-F driver-double-assign              → RC-07 (P1)
[TERBUKTI] BUG-G race-overpayment                  → RC-01 (P0)
```

---

## 12.2 Bukti Mentah per Bug

### BUG-G / RC-01 — Race overpayment (TOCTOU pada INV-2)
```
4 request paralel Rp800.000 utk tagihan Rp1.000.000:
  HTTP = [200, 200, 200, 200]
  total tercatat di payments = Rp3.200.000  >  total_amount = Rp1.000.000
```
**Akar:** `routers/payments.py:37-51` — pola *read* `sum_payments` lalu *validasi* lalu *insert* **tidak atomik**. Di bawah balapan, keempat request membaca `paid_before` yang sama (0) sebelum salah satu menulis.
**Semantik:** INV-2 (`paid <= total`) benar untuk single-thread, **dilanggar** saat konkuren. Kelas: **TOCTOU**.

### BUG-C / RC-02 — `complete` beri sinyal finansial kontradiktif
```
Booking total=Rp2.000.000, dibayar=Rp0 → POST /bookings/{id}/complete
  → payment_status = 'selesai'  (paid=0 < total=2jt)
  → /finance/ar : booking TETAP MUNCUL, outstanding = Rp2.000.000   ← diverifikasi 2×
```
**⚠ KOREKSI EMPIRIS:** AR **outstanding-based**, jadi piutang **TIDAK hilang** (klaim "under-report AR" keliru). Bug sebenarnya = **KONTRADIKSI SINYAL**: daftar booking/dashboard menandai `payment_status='selesai'` sementara AR menunjukkan utang Rp2jt. INV-3 dilanggar secara semantik.
**Akar:** `services/finance.py:13-20` `derive_payment_status`: `if status=="completed": return "selesai"` **tanpa** memeriksa `paid`. `routers/bookings.py:241` `complete_booking` memaksa `payment_status='selesai'`.
**Dampak:** operator membaca "selesai/lunas" padahal berpiutang → keputusan salah; `payment_status` tak reliabel.

### BUG-D / RC-03 — Split-brain status trip
```
Assign → POST /trips/{id}/status {status:'completed'}
  trip.status = completed  ✅
  vehicle.status = on_trip ❌ (tak dibebaskan)
  booking.status = confirmed ❌ (tak diselesaikan)
  trip.distance_km = 0 ❌ (KM/odometer tak dihitung)
```
**Akar:** DUA state-machine paralel untuk "selesai trip":
- `routers/driver.py::checkout` (lengkap: bebaskan armada, selesaikan booking, hitung KM).
- `routers/trips.py::update_trip_status` (`:88-110`) hanya set `status`/`end_at` — **tak melakukan efek samping**.
FE `features/app/DriverCheckin.jsx:82` memakai jalur generik → cabang rusak.

### BUG-A / RC-04 — Cancel tak membebaskan sumber daya
```
Assign booking (armada→on_trip, trip standby dibuat) → POST /bookings/{id}/cancel
  vehicle.status = on_trip ❌ (tetap terkunci)
  trip.status = standby ❌ (trip yatim tetap hidup)
```
**Akar:** `routers/bookings.py:231-236` `cancel_booking` hanya set `status='cancelled'`. Tidak menyentuh `vehicles.status`, tidak membatalkan `trips` terkait. `confirm`/`complete` juga tak sinkron ke status armada.
**Dampak:** armada "hantu terkunci" → tak bisa dibooking meski bebas; trip yatim mencemari dispatch/laporan.

### BUG-B / RC-05 — Pembayaran ke booking cancelled
```
POST /payments {booking_id: <cancelled>} → HTTP 200
  booking cancelled kini punya paid=Rp500.000, payment_status='dp'
```
**Akar:** `routers/payments.py:32-44` tak memeriksa `booking.status`. Menerima pembayaran untuk booking `cancelled`/`completed`.

### BUG-E / RC-06 — Payroll dobel-hitung lintas periode
```
payout1 (2026-07-02 .. 2026-07-02) trips=1
payout2 (2026-07-01 .. 2026-07-02) trips=1   ← trip yang SAMA
```
**Akar:** `routers/payroll.py:80-83` & `services/payroll.py:180` — guard duplikat hanya cek `period_start == X AND period_end == Y` (**persis sama**). Periode **overlap** lolos → trip sama dihitung 2×. Saat approve → **2 expense** `gaji_driver` (beban ganda ke Finance/P&L).

### BUG-F / RC-07 — Driver double-assign
```
Assign driver D ke booking#1 (armada A, 10 Apr 08-11) → 200
Assign driver D ke booking#2 (armada B, 10 Apr 09-07) → 200  ← tumpang-tindih
```
**Akar:** `routers/dispatch.py:108-126` & `services/availability.py` — `find_conflicts` hanya cek **armada** (INV-4). **Tidak ada** cek bentrok **driver**. Satu sopir bisa "mengemudi 2 mobil" bersamaan.

---

## 12.3 Yang Diverifikasi SEHAT (jangan diutak-atik)

| Uji live | Hasil |
|---|---|
| driver → `/finance/profit-loss`, `/payroll/summary`, `/users`, `/reports/summary`, `/audit-logs`, `POST /maintenance`, `POST /vehicles`, `/dispatch/today` | **403 semua** ✅ |
| ops_admin → `/users`, `/settings`, `/audit-logs` (owner-only) | **403 semua** ✅ |
| tanpa token → `/vehicles` | **401** ✅ |
| Endpoint sweep 130 GET | **0×5xx** ✅ |
| `verify_data_integrity.py` (clean-seed) | **32/32 PASS** ✅ |
| datetime naif di router/service | **0 temuan** ✅ |

---

## 12.4 Mengapa Guardrail Bawaan "Hijau" tapi Bug Nyata Ada?

Gate saat ini menguji: **DB bersih** + **single-thread** + **happy-path** (create→bayar penuh→selesai). Bug di atas hanya muncul pada:
- **transisi menyimpang** (cancel/complete tanpa lunas, jalur status alternatif),
- **konkurensi** (pembayaran paralel),
- **lintas-periode** (payroll overlap),
- **dimensi entitas lain** (bentrok driver, bukan armada).

→ **Rekomendasi:** tambah **gate state-machine + gate concurrency + gate cross-entity** (detail di `SSOT_MASTER_REPAIR_PLAN.md → BAGIAN 5`). Tanpa itu, bug kelas ini akan **kambuh senyap**.

---

## 12.5 Re-run Bukti

```bash
cd /app && python scripts/forensic_repro.py
# Membuat objek uji 2027, mereproduksi 7 bug, lalu CLEANUP total → DB kembali ke baseline.
# Verifikasi baseline: bookings=6, payments=5, trips=4, driver_payouts=2, invoices=2.
```
