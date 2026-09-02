# 🔧 SSOT MASTER REPAIR PLAN — Rahaza Travel & Fleet (Definitif, Zero-Assumption)

**Dokumen perbaikan tunggal & menyeluruh untuk cacat state-machine, integritas uang, concurrency, dan linkage di SELURUH sistem.**

> **Versi 1 (Deep-Dive + Empiris).** Setiap temuan ditelusuri **sampai akar logika** dan diverifikasi lintas **5 dimensi**: (D1) Data DB nyata, (D2) Kode backend baris-per-baris, (D3) Frontend pemakai, (D4) Linkage/idempotency/FK, (D5) Semantik (bug nyata vs false-positive vs dorman).
>
> - **Status:** RENCANA. **BELUM ADA perubahan kode produksi.** (Reproduksi bug memakai objek uji 2027 + auto-cleanup → DB tetap baseline.)
> - **Basis bukti:** `backend/routers/*.py` & `services/*.py` (dibaca), DB `test_database` (41 koleksi, count nyata), `scripts/forensic_repro.py` (7/7 bug TERBUKTI), `SSOT_FORENSIC_RAW_TRAVEL.json`.
> - **Untuk siapa:** Agent/sesi berikutnya. Dirancang agar **tidak perlu menebak apa pun**. Item tanpa jawaban pasti ditandai **⚠ STOP-VERIFY**.
> - **Dokumen pendamping (WAJIB baca):** `FORENSIC_00_EXECUTIVE_SUMMARY.md`, `FORENSIC_01_INVENTORY_BASELINE.md`, `FORENSIC_12_CURRENT_STATE_AUDIT.md`.

---

# BAGIAN 0 — GOLDEN RULES (Konstitusi. Langgar = rusak lagi)

1. **JANGAN mengubah `.env`.** `MONGO_URL` (backend) & `REACT_APP_BACKEND_URL` (frontend) haram disentuh.
2. **JANGAN re-seed.** Data sudah ada. Uji dengan objek sintetis + cleanup, atau clean-seed di lingkungan terpisah.
3. **"200 / RUNNING" BUKAN bukti benar.** Selalu cek **efek samping DB** (status armada, booking, trip, expense) & **invarian**, bukan cuma HTTP code.
4. **Uji jalur menyimpang, bukan hanya happy-path.** cancel-tanpa-lunas, jalur status alternatif, pembayaran paralel, periode overlap, bentrok driver.
5. **Satu RC = satu perubahan kecil & reversibel.** Uji tiap RC (repro gagal→hijau) SEBELUM lanjut RC berikutnya.
6. **Metode wajib per RC:** `bekukan → tulis test repro (harus GAGAL dulu) → fix minimal → curl+DB verify → testing_agent → catat CHANGELOG`.
7. **State-machine = SSOT tunggal.** Satu transisi status entitas harus lewat **satu** fungsi. Jangan biarkan 2 jalur (mis. `driver/checkout` vs `trips/status`) memutasikan hal sama secara berbeda.
8. **Mutasi uang harus atomik.** Gunakan operasi DB atomik (`$inc`, `find_one_and_update` dengan filter kondisi, atau guard versi) — bukan read-modify-write terpisah.
9. **Jangan mengarang data.** Koleksi DORMANT (`geocode_cache`, `partner_settlements`, `user_onboarding`, `sequence_enrollments`) dibiarkan terisi natural. Jangan buat angka palsu.
10. **Jangan refactor yang sehat.** RBAC, bcrypt, event-bus, INV-4 single-thread SUDAH benar — jangan diubah tanpa alasan.

---

# BAGIAN 1 — SSOT CANONICAL REGISTRY (Tabel Kebenaran Tunggal)

Nama koleksi kanonik + status. Detail count di `FORENSIC_01_INVENTORY_BASELINE.md`. **Tidak ada koleksi phantom** — sistem ini konsisten dalam penamaan (berbeda dari referensi DAterbaru).

### 1A. State-machine entity (paling rawan — fokus RC)
| Entity | Koleksi | Field status | Nilai sah | Transisi via |
|---|---|---|---|---|
| Booking | `bookings` | `status` | `confirmed, ongoing, completed, cancelled` | bookings.py + driver.py + dispatch.py |
| Booking | `bookings` | `payment_status` | `belum_bayar, dp, lunas, selesai` | `services/finance.py::derive_payment_status` |
| Trip | `trips` | `status` | `standby, to_pickup, on_trip, completed` | driver.py::checkout **DAN** trips.py::update_trip_status ⚠ (split-brain) |
| Vehicle | `vehicles` | `status` | `available, on_trip, maintenance` | dispatch/driver/maintenance |
| Driver | `drivers` | `status` | `online, offline` | driver.py |
| Payout | `driver_payouts` | `status` | `draft, approved, paid` | payroll.py |
| Invoice | `invoices` | `status` | `draft, sent, partial, paid` | invoices.py |

### 1B. Uang / Finance
| Konsep | Koleksi | Field kunci |
|---|---|---|
| Pembayaran booking | `payments` | `booking_id, amount, type, paid_at` |
| Pengeluaran | `expenses` | `booking_id, trip_id, category, amount, paid, created_at` |
| Invoice | `invoices` | `booking_id, number, amount, status, due_at` |
| Nomor atomik | `counters` | `_id(namespace), seq` (via `$inc`) |

### 1C. Invarian domain (dijaga `verify_data_integrity.py`)
INV-1 total=base+Σaddons · INV-2 paid≤total & =Σpayments · INV-3 payment_status konsisten · INV-4 anti double-booking armada · INV-5 profit=revenue−Σexpenses · INV-24 payroll akrual/kas sinkron.

> **Catatan:** INV-2, INV-3, INV-4 benar untuk **single-thread happy-path**, tetapi **bocor** pada race (RC-01), complete-tanpa-lunas (RC-02), dan bentrok driver (RC-07). RC di bawah menutup celah tsb.

---

# BAGIAN 2 — REPAIR CARDS (RC-01 s/d RC-07: TERBUKTI EMPIRIS)

Format: `ID | Prioritas | Dampak | File:baris | AKAR | FIX | VERIFIKASI | ROLLBACK | RISIKO | DO-NOT`.

---

## 🔴 RC-01 — Race Overpayment (`POST /payments` TOCTOU)
- **Prioritas:** P0 (uang). **Dampak:** `paid_amount` bisa melampaui `total_amount`; kas over-record; INV-2 bocor.
- **Bukti (D1):** 4× Rp800rb paralel utk tagihan Rp1jt → semua 200 → total Rp3,2jt. (`scripts/forensic_repro.py` BUG-G).
- **File:baris (D2):** `routers/payments.py:37-51` (`total → sum_payments → validasi → insert_one`, non-atomik).
- **AKAR (D5):** read-modify-write terpisah. Antar-request membaca `paid_before` basi sebelum ada yang menulis.
- **FIX (opsi, pilih A):**
  - **A (disarankan, atomik bersyarat):** ganti insert polos menjadi transaksi logis:
    1. `find_one_and_update` pada `bookings` dengan filter `{"id":bk, "status":{"$nin":["cancelled","completed"]}}` dan guard `$expr` bahwa `paid_amount + amount <= total_amount`, lalu `$inc paid_amount`. Bila `None` → 400 (bentrok/melebihi). **Baru** insert `payments` + set `payment_status`.
    2. Ini menjadikan cek-sisa + penambahan **satu operasi atomik** (MongoDB document-level atomic).
  - **B (jika ingin minimal):** gunakan lock per-booking (mis. koleksi `counters`/`$inc` sebagai mutex) — kurang bersih dari A.
- **VERIFIKASI:** jalankan ulang BUG-G → hanya **satu** 200 (sisanya 400), total ≤ tagihan. Lalu `testing_agent`.
- **ROLLBACK:** kembalikan blok insert lama. **RISIKO:** Sedang (jalur uang inti). **DO-NOT:** jangan hanya menambah `if` cek ulang (tetap TOCTOU); harus atomik.

---

## 🔴 RC-02 — `complete` Memberi Sinyal Finansial KONTRADIKTIF (status "selesai" vs AR)
- **⚠ KOREKSI EMPIRIS (penting, jangan salah framing):** klaim awal "hilang dari AR" **KELIRU**. `accounts_receivable` berbasis **`outstanding = total − paid > 0`**, jadi booking completed-belum-lunas **TETAP MUNCUL** di `/finance/ar` (diverifikasi: outstanding=Rp2jt tetap tampil). **Bug sebenarnya = KONTRADIKSI SINYAL:** booking yang sama menampilkan `payment_status='selesai'` (di daftar booking/dashboard) **sekaligus** utang Rp2jt di AR. INV-3 (konsistensi payment_status) dilanggar secara semantik.
- **Prioritas:** P0 (integritas pelaporan). **Dampak:** operator melihat "selesai/lunas" di list booking padahal masih berpiutang → salah ambil keputusan; angka `payment_status` tak bisa dipercaya.
- **Bukti (D1):** booking Rp2jt, dibayar Rp0, complete → `payment_status='selesai'`, `status='completed'`, **AR outstanding=Rp2jt (tetap muncul)** (BUG-C, diverifikasi 2×).
- **File:baris (D2):** `services/finance.py:13-20` (`if status=="completed": return "selesai"`) + `routers/bookings.py:239-244` (`complete_booking` paksa `payment_status='selesai'`) + `driver.py:167`/`checkout` (idem).
- **AKAR (D5):** status "selesai" mencampur **selesai operasional** dengan **lunas finansial**. `derive_payment_status` mengabaikan `paid` saat completed.
- **FIX:**
  1. `derive_payment_status(paid,total,status)`: bila `completed` **dan** `paid >= total` → `lunas`; bila `completed` **dan** `paid < total` → **tetap `dp`/`belum_bayar`** (sinyal finansial jujur). Status operasional tetap di field `status` (`completed`).
  2. `complete_booking` & `checkout`: JANGAN paksa `payment_status='selesai'`; panggil `recompute_booking_payment` agar derivasi konsisten dengan Σpayments.
  3. FE (`Bookings.jsx`, dashboard): peta label — "selesai" operasional dari `status`, "lunas/dp/belum" finansial dari `payment_status`. Hindari drift.
- **VERIFIKASI:** complete booking belum lunas → `payment_status ∈ {dp,belum_bayar}` **DAN** tetap di `/finance/ar` (konsisten); dibayar penuh → `lunas`. `testing_agent`.
- **ROLLBACK:** kembalikan `derive_payment_status`. **RISIKO:** Sedang (label FE). **DO-NOT:** jangan hapus makna "selesai" tanpa memetakan ke `status=completed` + `payment_status=lunas`.

---

## 🔴 RC-03 — Split-Brain Status Trip (`/trips/{id}/status` vs `driver/checkout`)
- **Prioritas:** P0. **Dampak:** trip "completed" via jalur generik TIDAK membebaskan armada, TIDAK menyelesaikan booking, TIDAK menghitung KM → payroll & laporan salah.
- **Bukti (D1):** BUG-D — `vehicle=on_trip`, `booking=confirmed`, `distance_km=0` setelah `/trips/status completed`.
- **File:baris (D2):** `routers/trips.py:88-110` (`update_trip_status` — hanya set status/end_at) vs `routers/driver.py:132-174` (`checkout` — lengkap). FE `features/app/DriverCheckin.jsx:82` memakai jalur generik.
- **AKAR (D5):** dua state-machine untuk transisi trip→completed. Golden Rule #7 dilanggar.
- **FIX (opsi):**
  - **A (disarankan):** jadikan `update_trip_status` mendelegasikan efek samping ke fungsi bersama. Ekstrak `_finalize_trip_completion(db, trip)` (bebaskan armada + hitung KM + selesaikan booking + emit) yang dipakai **baik** `checkout` **maupun** `update_trip_status` saat `status==completed`. Untuk `to_pickup`/`on_trip` set status armada/driver yang sesuai.
  - **B (jika ingin cepat & aman):** batasi `/trips/{id}/status` agar **tidak menerima** `completed` (arahkan FE ke `/driver/checkout`), dan perbaiki FE `DriverCheckin.jsx` memakai checkout. Kurang ideal (mengurangi kapabilitas) tapi menutup split-brain.
- **VERIFIKASI:** ulang BUG-D → armada `available`, booking `completed`, `distance_km` terisi (dari odometer/est). `testing_agent`.
- **ROLLBACK:** kembalikan handler. **RISIKO:** Sedang. **DO-NOT:** jangan biarkan 2 jalur completed aktif dengan efek berbeda.

---

## 🔴 RC-04 — Cancel/Confirm Tak Menyinkron Sumber Daya (armada terkunci + trip yatim)
- **Prioritas:** P0. **Dampak:** batal booking ter-assign → armada `on_trip` selamanya (tak bisa dibooking) + trip `standby` yatim mencemari dispatch/laporan.
- **Bukti (D1):** BUG-A — `vehicle=on_trip`, `trip=standby` pasca-cancel.
- **File:baris (D2):** `routers/bookings.py:231-244` (`cancel_booking`/`complete_booking` hanya set booking.status). Assign membuat `vehicles.status='on_trip'` (`dispatch.py:167`) & trip (`dispatch.py:158-165`) tanpa jalur balik.
- **AKAR (D5):** transisi booking tak "membereskan" entitas turunan (vehicle/trip).
- **FIX:**
  1. `cancel_booking`: bila ada trip terkait belum berjalan → set `trips.status='cancelled'`; bila `vehicles` sedang `on_trip` karena booking ini & tak ada trip aktif lain → kembalikan `vehicles.status='available'`; driver → `offline` bila tak ada tugas lain.
  2. `complete_booking`: pastikan armada dibebaskan (delegasi ke `_finalize_trip_completion` RC-03) — hindari duplikasi logika.
  3. Idempotent & defensif (cek trip aktif lain sebelum membebaskan armada).
- **VERIFIKASI:** ulang BUG-A → armada `available`, trip `cancelled`. Cek tak ada armada bebas ber-status `on_trip`. `testing_agent`.
- **ROLLBACK:** kembalikan handler. **RISIKO:** Sedang. **DO-NOT:** jangan set armada `available` tanpa cek trip aktif lain (bisa membebaskan yang sedang jalan).

---

## 🟠 RC-05 — Pembayaran Diterima untuk Booking `cancelled`/`completed`-invalid
- **Prioritas:** P1. **Dampak:** kas & AR tercemar; pembayaran nyasar ke booking batal.
- **Bukti (D1):** BUG-B — `POST /payments` ke booking cancelled → 200.
- **File:baris (D2):** `routers/payments.py:32-44` (tanpa cek `booking.status`).
- **AKAR (D5):** validasi hanya sisa-tagihan, bukan kelayakan status.
- **FIX:** tolak (400) bila `booking.status == 'cancelled'`. (Opsional: izinkan pelunasan booking `completed` yang belum lunas — sejalan RC-02.)
- **VERIFIKASI:** ulang BUG-B → 400 "Booking dibatalkan". `testing_agent`.
- **ROLLBACK:** hapus guard. **RISIKO:** Rendah. **DO-NOT:** jangan blokir pelunasan booking `completed`-belum-lunas (justru diperlukan).

---

## 🟠 RC-06 — Payroll Dobel-Hitung Lintas Periode
- **Prioritas:** P1 (uang). **Dampak:** trip sama masuk 2 payout overlap → 2 expense `gaji_driver` → beban ganda P&L.
- **Bukti (D1):** BUG-E — payout(02..02) & payout(01..02) keduanya trips=1 (trip sama).
- **File:baris (D2):** `routers/payroll.py:80-83`, `services/payroll.py:180-184` (guard hanya `period_start==X AND period_end==Y`).
- **AKAR (D5):** deteksi duplikat berbasis kecocokan periode **persis**, bukan **overlap**, dan tak ada penanda trip "sudah dibayar".
- **FIX (opsi, disarankan gabungan):**
  1. **Guard overlap:** saat generate, tolak bila ada payout non-`draft`-dibatalkan untuk driver dengan periode **tumpang-tindih** (`existing.start <= new.end AND new.start <= existing.end`).
  2. **Idempotency trip:** saat approve/generate, tandai trip yang sudah masuk payout (mis. `trips.payout_id`) dan **kecualikan** dari akrual payout lain. Ini SSOT anti dobel-hitung sejati.
- **VERIFIKASI:** ulang BUG-E → payout kedua ditolak/trip tak dihitung ulang. Approve → hanya 1 expense. `testing_agent`.
- **ROLLBACK:** kembalikan guard exact-match. **RISIKO:** Sedang. **DO-NOT:** jangan izinkan approve payout overlap tanpa idempotency trip.

---

## 🟠 RC-07 — Driver Double-Assign (bentrok sopir tak dicek)
- **Prioritas:** P1. **Dampak:** 1 sopir di-assign ke 2 trip tumpang-tindih waktu → jadwal mustahil, payroll/laporan rancu.
- **Bukti (D1):** BUG-F — assign driver D ke 2 booking overlap (armada beda) → keduanya 200.
- **File:baris (D2):** `routers/dispatch.py:108-126` + `services/availability.py` (hanya cek armada, INV-4). `POST /bookings` (`bookings.py:99`) juga tak cek driver.
- **AKAR (D5):** anti-konflik hanya 1 dimensi (vehicle). Dimensi driver hilang.
- **FIX:** tambah `find_driver_conflicts(db, driver_id, start, end, exclude_booking_id)` (analog `find_conflicts`, filter `driver_id` + status aktif) dan panggil di **assign** (dispatch) & **create/confirm booking**. Tolak 400 bila bentrok.
- **VERIFIKASI:** ulang BUG-F → assign kedua 400 "Driver bentrok". `testing_agent`.
- **ROLLBACK:** hapus cek driver. **RISIKO:** Rendah-sedang. **DO-NOT:** jangan blokir assign ulang ke booking yang sama (gunakan `exclude`).

---

# BAGIAN 3 — REPAIR CARDS TAMBAHAN (RC-08 s/d RC-11: HYGIENE / P2-P3)

## 🟡 RC-08 — CORS `allow_origins="*"` + `allow_credentials=True` (misconfig)
- **File:** `server.py:122-128`. Kombinasi wildcard + credentials tidak sah menurut spec CORS (browser menolak kredensial dengan `*`). Saat ini app pakai Bearer header (bukan cookie) jadi dampak nyata rendah, **tapi** konfigurasi menyesatkan.
- **FIX:** set `CORS_ORIGINS` env ke origin frontend spesifik (JANGAN ubah `REACT_APP_BACKEND_URL`); atau matikan `allow_credentials` bila memang hanya Bearer. **RISIKO:** Rendah. ⚠ STOP-VERIFY: konfirmasi FE tidak mengandalkan cookie.

## 🟡 RC-09 — Session cleanup & rotation
- **File:** `dependencies.py:36-38` — sesi kedaluwarsa hanya dihapus saat diakses; tak ada TTL index / logout-all. `sessions` bisa menumpuk.
- **FIX:** tambah TTL index pada `sessions.expires_at` (Mongo TTL) + endpoint logout-all (opsional). **RISIKO:** Rendah. **DO-NOT:** jangan ubah skema token (`sess_`).

## ✅ RC-10 — Rate-limit login in-memory (tidak persisten/terdistribusi) — SELESAI (2026-07-03)
- **File:** `services/ratelimit.py` + `auth.py:38`. Counter reset saat restart; tak lintas-worker. Cukup untuk 1 worker, lemah bila diskalakan.
- **FIX (DONE):** dipindah ke store persisten koleksi Mongo `login_failures` + TTL index (dibuat di `server.py` startup). Fungsi baru `note_failure_db/failure_count_db/clear_failures_db`. Ambang 8 gagal per (ip+email)/5 menit → ke-9 = 429; login sukses membersihkan budget (per-key isolation).
- **VERIFIKASI:** curl 8×401→429, owner tetap 200; `testing_agent` iter 51 PASS. **Bertahan lintas restart.**

## ✅ RC-11 — Money sebagai `float` → INTEGER rupiah — SELESAI (2026-07-03)
- **Observasi:** nilai uang disimpan `float` + `round(...,2)`. Untuk IDR (tanpa sen) risiko rendah, tapi akumulasi float bisa menyimpang.
- **FIX (DONE):** helper `core_utils.money()` (int rupiah) diterapkan di semua titik tulis uang (bookings/payments/expenses/invoices/payroll). Skrip migrasi `scripts/migrate_money_to_int.py` di-wire ke `seed_reset.sh` (23 dok dinormalisasi). Invarian baru **INV-11 (money-integral)** di `verify_data_integrity.py`.
- **VERIFIKASI:** base_price=1234567 + addon 50000.5 → total/paid/payment/expense/invoice semua whole integer; `testing_agent` iter 51 PASS.

---

# BAGIAN 4 — FALSE-POSITIVE & DORMANT REGISTRY (agar tidak "diperbaiki" keliru)

| Item | Verdict | Alasan |
|---|---|---|
| `geocode_cache`, `partner_settlements`, `user_onboarding` | **DORMANT** | writer+reader ada; terisi saat fitur dipakai. Bukan phantom. |
| `sequence_enrollments` (count 0) | **DORMANT** | belum ada enrollment; index sudah disiapkan. |
| `counters` "write-only" | **BY-DESIGN** | `find_one_and_update($inc)` = read+write atomik dalam 1 op. |
| `articles`/`packages`/`promos` "DB-only" | **FALSE-POSITIVE** | diakses `get_db().<coll>` (scanner `db.` awal melewatkan). Dipakai `public.py`/`content.py`. |
| 36 route "tak dipakai FE" | **MAYORITAS FALSE-POSITIVE** | path dinamis (`/bookings/${id}/${action}`) atau eksternal (`wa/webhook`,`gps/webhook`). |
| 4xx pada endpoint sweep | **EKSPEKTASI** | ID dummy → 404 wajar. |
| Warning N+1 `verify_architecture` | **BACKLOG (WARN)** | tech-debt performa, bukan bug korektif. |

---

# BAGIAN 5 — GATE BARU (mencegah kambuh) — WAJIB ditambah saat fix

> Bug di atas **lolos** gate lama karena gate menguji clean-seed+single-thread+happy-path. Tambahkan:

1. **`verify_state_machine.py`** (usulan): setelah `cancel` → armada tak `on_trip` & trip terkait `cancelled`; setelah `complete` tanpa lunas → `payment_status` ∈ {`dp`,`belum_bayar`} & muncul di AR; `/trips/status completed` menghasilkan efek identik dengan `checkout`.
2. **`verify_concurrency.py`** (usulan): N pembayaran paralel → Σ ≤ total (INV-2 di bawah balapan).
3. **`verify_cross_entity.py`** (usulan): tak ada driver ter-assign ke 2 trip overlap; tak ada payout overlap untuk driver sama.
4. Integrasikan ke `scripts/gate.sh` sebagai gate runtime baru.

---

# BAGIAN 6 — ROADMAP EKSEKUSI (urut prioritas + gerbang aman)

| Urutan | RC | Prioritas | Est. | Gate verifikasi |
|---|---|---|---|---|
| 1 | RC-01 Race payment | P0 | S | repro BUG-G + testing_agent |
| 2 | RC-02 AR selesai/lunas | P0 | S | repro BUG-C + AR check + testing_agent |
| 3 | RC-03 Split-brain trip | P0 | M | repro BUG-D + testing_agent |
| 4 | RC-04 Cancel sumber daya | P0 | M | repro BUG-A + testing_agent |
| 5 | RC-05 Pay ke cancelled | P1 | S | repro BUG-B + testing_agent |
| 6 | RC-06 Payroll overlap | P1 | M | repro BUG-E + INV-24 + testing_agent |
| 7 | RC-07 Driver double-assign | P1 | S | repro BUG-F + testing_agent |
| 8 | RC-08..11 Hygiene | P2/P3 | — | sesuai kartu |
| 9 | Gate baru (BAGIAN 5) | — | M | jalankan `gate.sh` |

**Aturan penutup per RC:** tidak boleh lanjut ke RC berikut sebelum RC saat ini **hijau di testing_agent** dan **repro-nya berubah dari TERBUKTI → TIDAK TERBUKTI**.

---

# APPENDIX A — Perintah Verifikasi Cepat

```bash
# Dump DB + endpoint + code-access (read-only)
cd /app/backend && python /app/scripts/forensic_dump.py

# Reproduksi 7 bug (auto-cleanup ke baseline)
cd /app && python scripts/forensic_repro.py

# Gate bawaan
cd /app && bash scripts/gate.sh              # orkestrator (receipt di memory/GATE_RECEIPT.md)
python scripts/verify_data_integrity.py      # 32 invarian (clean-seed)
python scripts/audit_endpoint_sweep.py       # sweep GET → cek 5xx

# Kredensial uji
owner@demo.local / ops@demo.local / driver@demo.local  (password: demo12345)
```

---

**➡ Rangkuman:** 7 cacat state-machine/uang/concurrency TERBUKTI empiris (RC-01..07, P0/P1) + 4 hygiene (RC-08..11). **STATUS EKSEKUSI (2026-07-03): RC-01..RC-11 SELESAI & TERVERIFIKASI (SELURUH REPAIR PLAN TUNTAS)** — `forensic_repro.py` 7×TIDAK TERBUKTI, `gate.sh` HIJAU (13/13, termasuk verify_state_machine/concurrency/cross_entity), testing_agent iter 51 = Backend 100% (52/52) + Frontend 100%, 0 bug. RC-10 (ratelimit persisten via Mongo `login_failures`+TTL) & RC-11 (money→integer rupiah + migrasi + INV-11) kini SELESAI. Regresi RC-01 (race) yang ditemukan `verify_concurrency` juga sudah diperbaiki (atomic $inc = SSOT paid_amount).
