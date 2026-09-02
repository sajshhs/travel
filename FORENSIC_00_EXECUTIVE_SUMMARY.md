# 🧭 FORENSIC 00 — EXECUTIVE SUMMARY

**Sistem:** Rahaza Travel & Fleet Management Ecosystem (FARM: FastAPI + React + MongoDB)
**Tanggal audit:** 2026-07-02 · **Auditor:** Neo (AI Full-Stack Engineer)
**Metode:** Audit forensik 5-dimensi + **reproduksi empiris live** (login nyata → panggil endpoint → cek DB → cleanup).
**Basis bukti:** kode dibaca baris-per-baris, DB `test_database` (41 koleksi, count nyata), 265 route FastAPI, 188 file frontend.

> **Prinsip dokumen ini (sama seperti referensi DAterbaru, tapi lebih ketat):** *tidak ada klaim tanpa bukti.* Setiap temuan P0/P1 di-**REPRO** dengan skrip `scripts/forensic_repro.py` (idempotent + auto-cleanup, DB kembali ke baseline). Verdict hanya: **TERBUKTI / TIDAK TERBUKTI / DORMANT / FALSE-POSITIVE**.

---

## 0.1 Verdict Ringkas

| Dimensi | Nilai | Catatan |
|---|---|---|
| **Kesehatan infrastruktur** | 🟢 SEHAT | backend/frontend/mongodb RUNNING; `/api/` 200; login OK; 0 endpoint 5xx (sweep 130 GET). |
| **Integritas data (clean-seed)** | 🟢 32/32 invarian PASS | `verify_data_integrity.py` hijau di DB bersih. |
| **RBAC / Auth** | 🟢 KUAT | bcrypt + migrasi legacy; driver & ops_admin diblokir tepat dari section terlarang (diverifikasi live). |
| **Logika bisnis (runtime, data hidup)** | 🔴 **7 CACAT TERBUKTI** | Semua **lolos** dari gate statik & clean-seed, tapi **PECAH saat alur nyata** (cancel/complete/pay/assign/payroll). |
| **Konsistensi kontrak FE↔BE** | 🟡 SEBAGIAN | Tidak ada 404 senyap nyata; beberapa "temuan" adalah false-positive analisis statis (query-string). |
| **Concurrency / race** | 🔴 **TOCTOU TERBUKTI** | Overpayment saat pembayaran paralel (INV-2 dilanggar di bawah balapan). |

**Kesimpulan utama:** Aplikasi **terlihat 100% hijau** oleh guardrail bawaan karena gate menguji **DB bersih + single-thread + happy-path**. Namun **7 cacat state-machine & 1 race condition** hanya muncul pada **transisi status nyata** (batal, selesai, bayar, assign, payroll lintas-periode). Ini adalah kelas bug **"green-but-broken"** — persis pola yang diperingatkan Golden Rule.

---

## 0.2 Temuan Kritis ( diverifikasi LIVE — bukan asumsi)

| ID | Prioritas | Judul | Bukti empiris (ringkas) |
|---|---|---|---|
| **RC-01** | 🔴 P0 | **Race overpayment** (`POST /payments` TOCTOU) | 4× bayar Rp800rb paralel utk tagihan Rp1jt → **semua 200**, total tercatat **Rp3,2jt > Rp1jt**. INV-2 dilanggar. |
| **RC-02** | 🔴 P0 | **`complete` beri sinyal finansial kontradiktif** | Booking Rp2jt, dibayar Rp0 → `complete` set `payment_status='selesai'`, TAPI AR tetap menunjukkan utang Rp2jt → **sinyal saling bertentangan** (INV-3 semantik dilanggar). |
| **RC-03** | 🔴 P0 | **Split-brain status trip** (`/trips/{id}/status` vs `driver/checkout`) | `status=completed` via jalur generik → trip *completed* TAPI **armada terkunci `on_trip`**, booking **tak selesai**, `distance_km=0` (payroll/KM salah). |
| **RC-04** | 🔴 P0 | **Cancel tak membebaskan sumber daya** | Batal booking ter-assign → **armada tetap `on_trip`**, **trip yatim `standby`** tetap hidup → armada "hantu terkunci" + double-book laten. |
| **RC-05** | 🟠 P1 | **Pembayaran ke booking `cancelled`** | `POST /payments` diterima 200 pada booking yang sudah dibatalkan → kas & AR tercemar. |
| **RC-06** | 🟠 P1 | **Payroll dobel-hitung lintas periode** | Guard duplikat hanya cek periode **persis sama**; periode **overlap** → **trip yang sama dihitung di 2 payout** → beban ganda ke Finance saat approve. |
| **RC-07** | 🟠 P1 | **Driver double-assign** | Dispatch cek bentrok **armada** (INV-4) tapi **tidak** cek bentrok **driver** → 1 sopir di-assign ke 2 trip tumpang-tindih. |

Detail lengkap (file:baris, akar masalah, peta perbaikan, verifikasi, rollback, risiko) ada di **`SSOT_MASTER_REPAIR_PLAN.md`**.

---

## 0.3 Yang TERBUKTI SEHAT (jangan "diperbaiki")

- **RBAC/section-guard:** driver & ops_admin ditolak 403 pada modul terlarang; no-auth 401 (diverifikasi live).
- **Password:** bcrypt + verifikasi legacy SHA256 + rehash transparan (`core_utils.py`). Baik.
- **Datetime:** **tidak ada** `datetime.now()`/`utcnow()` naif di router/service — semua `timezone.utc`. Baik.
- **Anti double-booking single-thread (INV-4):** benar untuk jalur `POST /bookings` (bukan race).
- **Idempotency event bus:** `dedupe_key` unik + index sparse. Baik.
- **GPS webhook:** default aman (secret kosong → tolak semua).

---

## 0.4 Klarifikasi FALSE-POSITIVE / DORMANT (agar agent berikut TIDAK salah perbaiki)

| Item | Status | Penjelasan |
|---|---|---|
| `geocode_cache`, `partner_settlements`, `user_onboarding`, `sequence_enrollments` | **DORMANT (bukan bug)** | Punya writer & reader di kode; koleksi baru terisi saat fitur dipakai/di-seed. `sequence_enrollments` count=0 = belum ada enrollment. **Jangan buat data palsu.** |
| `counters` "write-only" | **BY DESIGN** | Ditulis `find_one_and_update($inc)` untuk nomor atomik; "read" terjadi di operasi yang sama. Bukan orphan. |
| `articles`/`packages`/`promos` "DB-only" | **FALSE-POSITIVE** | Diakses via `get_db().articles...` (scanner attr `db.` awal melewatkannya). Dipakai `routers/public.py` & `content.py`. |
| 36 route "tak dipakai FE" | **MAYORITAS FALSE-POSITIVE** | Dipanggil via path dinamis (`/bookings/${id}/${action}`, `/quotations/${id}/${verb}`) atau eksternal (`wa/webhook`, `gps/webhook`). |
| 4×4xx sweep (`/invoices/{id}` dst.) | **EKSPEKTASI** | Sweeper pakai ID dummy → 404 wajar. Bukan endpoint rusak. |

---

## 0.5 Rekomendasi Eksekusi

1. **Urutan perbaikan:** RC-01 → RC-02 → RC-03 → RC-04 (P0, integritas uang & sumber daya) lalu RC-05/06/07 (P1).
2. **Metode wajib per RC (Golden Rule):** `bekukan → tulis test gagal (repro) → fix minimal & reversibel → curl+DB verify → testing_agent → catat CHANGELOG`.
3. **Tambah gate baru** yang menangkap kelas bug ini (state-machine & concurrency) agar tidak kambuh — lihat `SSOT_MASTER_REPAIR_PLAN.md → BAGIAN 5`.
4. **Jangan** ubah `.env` (`MONGO_URL`, `REACT_APP_BACKEND_URL`). **Jangan** re-seed. **Jangan** refactor file yang sehat.

> **Dokumen terkait:** `SSOT_MASTER_REPAIR_PLAN.md` (master + RC-01..RC-14 + roadmap + gate baru) · `FORENSIC_01_INVENTORY_BASELINE.md` · `FORENSIC_12_CURRENT_STATE_AUDIT.md` (koreksi empiris) · `SSOT_FORENSIC_RAW_TRAVEL.json` (dump mentah).
