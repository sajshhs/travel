# 🚀 ENHANCEMENT PLAN — DAMPAK BISNIS NYATA (Rahaza Travel & Fleet)

**Dibuat:** 2026-07-02 · **Penyusun:** Neo · **Status:** RENCANA (belum ada kode) · **Bahasa:** Indonesia
**Konteks bisnis:** Rental Toyota Hiace Premio premium (Bandung), melayani **wisata Jawa–Bali + korporat**. Model bisnis: aset (armada) + jasa (driver) → **utilisasi armada** & **arus kas** adalah nyawa bisnis.

> **Prinsip dokumen ini:** setiap enhancement diikat ke **tuas bisnis (business lever)** + **hipotesis dampak terukur** + **KPI** + **skor RICE**. Angka dampak adalah **HIPOTESIS untuk divalidasi** (bukan klaim), memakai asumsi konservatif industri rental — bukan data finansial nyata (belum tersedia).
>
> Dokumen ini melengkapi `memory/ENHANCEMENT_BACKLOG.md` (E16–E21) dengan **framing ROI + prioritas**, dan mengintegrasikan **nilai perbaikan bug** dari `SSOT_MASTER_REPAIR_PLAN.md` (mencegah kebocoran uang).

---

## 1. NORTH-STAR & TUAS BISNIS

**North-star metric:** **Laba bersih per armada per bulan** (net profit / vehicle / month).
Ini menyatukan 3 hal: pendapatan naik, biaya turun, dan aset bekerja maksimal.

| # | Tuas Bisnis | Metrik Pendorong | Kondisi saat ini |
|---|---|---|---|
| L1 | **Utilisasi Armada** | % hari armada menghasilkan uang; idle days | Belum diukur/ditampilkan |
| L2 | **Konversi (Lead→Booking)** | conversion rate, waktu respon, waktu ke penawaran | CRM ada, self-service booking belum |
| L3 | **Nilai per Transaksi** | rata-rata nilai booking, attach-rate add-on, harga musiman | Pricing engine ada, upsell/dynamic belum optimal |
| L4 | **Kecepatan Kas (Cash Conversion)** | % DP tepat waktu, umur piutang (AR days), bad debt | Pencatatan ada; DP-gate & penagihan otomatis belum |
| L5 | **Retensi & LTV** | repeat rate, kontrak korporat, winback | CRM/winback ada; program loyalitas/korporat belum |
| L6 | **Efisiensi Biaya Operasional** | biaya BBM/km, biaya maintenance, produktivitas driver | Data mentah ada; analitik biaya belum tajam |
| L7 | **Keandalan Sistem (anti-kebocoran)** | overpayment, piutang hilang, double-assign | **7 bug TERBUKTI** (lihat SSOT plan) |

---

## 2. RINGKASAN EKSEKUTIF — 3 Gelombang

| Gelombang | Fokus | Tujuan bisnis | Durasi estimasi |
|---|---|---|---|
| **W0 — Stop the Leak** | Perbaikan bug P0/P1 (RC-01..07) | Hentikan kebocoran uang & data yang sudah TERBUKTI | 1 sprint |
| **W1 — Quick Wins ROI** | Utilisasi dashboard, DP-gate, penagihan AR otomatis, upsell add-on | Kas lebih cepat + revenue naik, effort rendah | 2–3 sprint |
| **W2 — Strategic Bets** | Sub-charter (E16), booking self-service, dynamic pricing, portal korporat, payment gateway | Kapasitas & pendapatan skala besar | 4–8 sprint |

---

## 3. KATALOG ENHANCEMENT (per item: masalah → solusi → dampak → KPI)

> Format tiap kartu: **Tuas · Masalah bisnis · Solusi · Hipotesis dampak · KPI ukur · Effort · Ketergantungan · Risiko.**

---

### 🟥 W0 — STOP THE LEAK (prasyarat, dari SSOT_MASTER_REPAIR_PLAN)

**EN-00 — Perbaiki 7 bug integritas (RC-01..RC-07)**
- **Tuas:** L7 (+ L4). **Masalah:** overpayment race (RC-01), piutang bersinyal "selesai" (RC-02), armada "hantu terkunci" (RC-04), payroll dobel-bayar (RC-06), double-assign (RC-07) → **kebocoran uang & kapasitas nyata**.
- **Solusi:** eksekusi Repair Cards (atomik payment, derive status jujur, SSOT completion, sinkron cancel, guard driver/periode).
- **Hipotesis dampak:** hilangkan **100% overpayment** & **double-pay payroll**; pulihkan **kapasitas armada** yang salah-terkunci; piutang tercatat akurat.
- **KPI:** 0 kasus paid>total; 0 payout overlap; 0 armada available ber-status on_trip; repro `forensic_repro.py` → 7×TIDAK TERBUKTI.
- **Effort:** M · **Ketergantungan:** — · **Risiko:** Sedang (jalur uang). **Wajib testing_agent.**

---

### 🟩 W1 — QUICK WINS (impact tinggi, effort rendah–sedang)

**EN-01 — Dashboard Utilisasi Armada & "Idle Money"**
- **Tuas:** L1. **Masalah:** owner tak tahu armada mana yang "nganggur membakar biaya". Idle = rugi tersembunyi.
- **Solusi:** metrik utilisasi per armada (hari terpakai / hari tersedia), revenue/idle-days, heatmap kalender, alert unit <X% utilisasi. Data sudah ada (`bookings`, `trips`, `vehicles`).
- **Hipotesis dampak:** menaikkan utilisasi **3–8 poin %** via keputusan reposisi/promo unit sepi → langsung ke laba/armada.
- **KPI:** utilization %, idle-days/bulan, revenue/vehicle. **Effort:** S–M · **Ketergantungan:** EN-00 (RC-04 agar status armada akurat) · **Risiko:** Rendah.

**EN-02 — DP-Gate + Auto-expire "Hold" (E18)**
- **Tuas:** L4 (+ L1). **Masalah:** booking `confirmed` tanpa DP mengunci armada tapi berisiko batal → kas seret + kapasitas terbuang.
- **Solusi:** status `hold` (pending DP) → `confirmed` otomatis saat DP masuk; auto-expire hold (lepas blok armada) bila DP telat; reminder DP via WA.
- **Hipotesis dampak:** **DP tepat waktu +15–30%**, no-show/booking hangus turun, armada tidak terkunci sia-sia.
- **KPI:** % DP on-time, hold-expiry rate, armada re-released. **Effort:** M · **Ketergantungan:** EN-00 (RC-01/04) · **Risiko:** Sedang (state-machine).

**EN-03 — Penagihan Piutang (AR) Otomatis + Aging**
- **Tuas:** L4. **Masalah:** piutang menua tanpa penagihan sistematis → arus kas & bad debt.
- **Solusi:** aging bucket (0–7/8–30/30+), reminder WA berjenjang otomatis (`invoice.overdue` sudah ada — perkuat + jadwal), dashboard AR days. (Sebagian infrastruktur `finance_automation` sudah ada.)
- **Hipotesis dampak:** **AR days turun 20–35%**; bad debt turun.
- **KPI:** rata-rata AR days, % tertagih ≤30 hari, nilai overdue. **Effort:** S–M · **Ketergantungan:** EN-00 (RC-02 agar piutang akurat) · **Risiko:** Rendah.

**EN-04 — Upsell Add-on & Attach-rate (Nilai per Transaksi)**
- **Tuas:** L3. **Masalah:** add-on (driver tambahan, overtime, tol/parkir, hotel, dekorasi) belum di-upsell sistematis.
- **Solusi:** katalog add-on terstruktur + saran otomatis saat buat booking/penawaran; laporan attach-rate.
- **Hipotesis dampak:** **nilai rata-rata booking +5–12%** via attach-rate.
- **KPI:** attach-rate, add-on revenue, avg booking value. **Effort:** S–M · **Ketergantungan:** — · **Risiko:** Rendah.

**EN-05 — Reschedule Booking + Penutupan Celah WA (E17)**
- **Tuas:** L2/L5. **Masalah:** tak ada reschedule aman (re-cek ketersediaan); pelanggan tak diberi tahu saat batal/ubah jadwal (celah G1/G2 di backlog).
- **Solusi:** endpoint reschedule (re-cek availability) + event `booking.cancelled`/`booking.rescheduled` → WA; samakan POD→`trip.completed`.
- **Hipotesis dampak:** kurangi pembatalan jadi reschedule (**selamatkan 5–10% booking** yang tadinya batal); CX naik.
- **KPI:** reschedule-vs-cancel ratio, WA delivery, CSAT. **Effort:** M · **Ketergantungan:** EN-00 (RC-03/04) · **Risiko:** Sedang.

---

### 🟦 W2 — STRATEGIC BETS (impact besar, effort besar)

**EN-06 — Partner Sourcing / Sub-charter (E16)** ⭐ *fitur inti diminta user*
- **Tuas:** L1/L3. **Masalah:** saat semua unit sendiri penuh/bentrok/maintenance → booking DITOLAK = revenue hilang.
- **Solusi:** master `partners` + unit `ownership=partner` + sub-charter order + biaya partner masuk **COGS/AP** (P&L per booking akurat) + saran otomatis saat bentrok + WA ke partner.
- **Hipotesis dampak:** **tangkap revenue yang tadinya ditolak** (peak season bisa **+10–20% booking terpenuhi**); margin tetap terukur.
- **KPI:** booking terselamatkan via partner, margin sub-charter, AP partner. **Effort:** L · **Ketergantungan:** EN-00 (INV-4/RC), availability engine · **Risiko:** Sedang-tinggi. *(Sudah dirancang detail di backlog B2.)*

**EN-07 — Booking Publik Self-Service (E19)**
- **Tuas:** L2. **Masalah:** semua booking manual via ops → bottleneck + jam malam hilang.
- **Solusi:** form pesan di situs → booking `pending` → approval ops + WA ke pelanggan. Bangun di atas trip-estimate & pricing engine yang sudah ada.
- **Hipotesis dampak:** **konversi lead→booking +10–25%**, ops lebih ringan, capture 24/7.
- **KPI:** self-serve booking %, konversi, waktu-ke-konfirmasi. **Effort:** M–L · **Ketergantungan:** EN-02 (DP-gate), EN-00 · **Risiko:** Sedang.

**EN-08 — Dynamic / Seasonal Pricing**
- **Tuas:** L3. **Masalah:** harga statis → kehilangan margin peak & kalah saing low season.
- **Solusi:** aturan harga per musim/hari libur/utilisasi (pricing engine `settings.pricing_rules` sudah mendukung surcharge; perluas ke demand-based).
- **Hipotesis dampak:** **revenue/booking +5–15%** di peak; utilisasi naik di low.
- **KPI:** revPAR (revenue per available vehicle), margin musiman. **Effort:** M · **Ketergantungan:** EN-01 (data utilisasi) · **Risiko:** Sedang (butuh guardrail agar tak overprice).

**EN-09 — Portal & Kontrak Korporat (B2B) + Loyalty**
- **Tuas:** L5. **Masalah:** klien korporat = pendapatan berulang bernilai tinggi, belum ada portal/kontrak/harga khusus.
- **Solusi:** akun korporat (multi-user), harga kontrak, invoice bulanan terkonsolidasi, share-link tracking (sudah ada), laporan pemakaian; loyalty poin untuk retail.
- **Hipotesis dampak:** **repeat rate & LTV naik**; pendapatan berulang (recurring) lebih stabil.
- **KPI:** % revenue korporat, repeat rate, LTV. **Effort:** L · **Ketergantungan:** EN-03 (AR), invoice · **Risiko:** Sedang.

**EN-10 — Payment Gateway (DP Online)** *(DITUNDA user — surface ulang karena impact tinggi)*
- **Tuas:** L4. **Masalah:** DP manual/transfer → friksi + verifikasi lambat + DP telat.
- **Solusi:** Midtrans/Xendit untuk DP/pelunasan online (butuh persetujuan + kredensial user; via integration agent).
- **Hipotesis dampak:** **DP on-time & konversi naik signifikan**, verifikasi otomatis, kas lebih cepat.
- **KPI:** % DP online, waktu verifikasi, konversi. **Effort:** M–L · **Ketergantungan:** EN-02 (DP-gate) · **Risiko:** Sedang. **CATATAN: sebelumnya DITUNDA — perlu keputusan ulang user.**

**EN-11 — Analitik Biaya Operasional (BBM/km, Predictive Maintenance, Produktivitas Driver)**
- **Tuas:** L6. **Masalah:** biaya BBM & maintenance tidak dianalisis per unit/km → kebocoran margin.
- **Solusi:** biaya/ km per armada, tren maintenance, prediksi servis dari odometer/interval (`service_types` sudah ada), leaderboard produktivitas driver (sudah ada di Reports E13 — perluas ke cost).
- **Hipotesis dampak:** **biaya operasional −3–8%** via deteksi unit boros/maintenance mahal.
- **KPI:** cost/km, maintenance cost/vehicle, revenue/driver. **Effort:** M · **Ketergantungan:** — · **Risiko:** Rendah.

---

## 4. PRIORITISASI RICE (Reach × Impact × Confidence ÷ Effort)

> Skala: Reach 1–5 (seberapa sering transaksi menyentuhnya), Impact 1–3, Confidence 0.5–1.0, Effort 1–5 (makin besar makin mahal). **Skor = R×I×C / E** (indikatif untuk urutan, bukan absolut).

| ID | Enhancement | R | I | C | E | **RICE** | Gelombang |
|---|---|:-:|:-:|:-:|:-:|:-:|---|
| EN-00 | Fix 7 bug integritas | 5 | 3 | 1.0 | 2 | **7.5** | W0 |
| EN-03 | AR otomatis + aging | 4 | 3 | 0.9 | 2 | **5.4** | W1 |
| EN-01 | Dashboard utilisasi | 5 | 2 | 0.9 | 2 | **4.5** | W1 |
| EN-02 | DP-gate + auto-expire | 4 | 3 | 0.8 | 2 | **4.8** | W1 |
| EN-04 | Upsell add-on | 4 | 2 | 0.8 | 2 | **3.2** | W1 |
| EN-06 | Sub-charter (E16) | 3 | 3 | 0.8 | 4 | **1.8** | W2 |
| EN-08 | Dynamic pricing | 4 | 3 | 0.6 | 3 | **2.4** | W2 |
| EN-07 | Booking self-service | 4 | 3 | 0.7 | 4 | **2.1** | W2 |
| EN-10 | Payment gateway | 4 | 3 | 0.7 | 3 | **2.8** | W2 |
| EN-05 | Reschedule + WA gap | 3 | 2 | 0.8 | 3 | **1.6** | W1/W2 |
| EN-11 | Analitik biaya ops | 3 | 2 | 0.8 | 3 | **1.6** | W2 |
| EN-09 | Portal korporat + loyalty | 3 | 3 | 0.6 | 5 | **1.1** | W2 |

**Urutan disarankan:** EN-00 → EN-03 → EN-02 → EN-01 → EN-04 → (EN-10/EN-08/EN-06 sesuai keputusan strategis) → EN-07 → EN-11 → EN-05 → EN-09.

---

## 5. ROADMAP BERGELOMBANG

```
W0 (Stop Leak)     : EN-00 (RC-01..07)  ── prasyarat integritas
        │
W1 (Quick Wins)    : EN-03 AR → EN-02 DP-gate → EN-01 Utilisasi → EN-04 Upsell → EN-05 Reschedule
        │             (kas lebih cepat + revenue/booking naik + kapasitas terpakai)
        ▼
W2 (Strategic)     : EN-10 Payment GW / EN-08 Dynamic Pricing / EN-06 Sub-charter
                     → EN-07 Self-service → EN-11 Cost Analytics → EN-09 Portal Korporat
```

**Metode tiap enhancement (konsisten dgn guardrail proyek):**
`POC → build (BE+FE) → gate.sh HIJAU → testing_agent_v3 → update docs/manifest`.

---

## 6. RENCANA PENGUKURAN (agar dampak "nyata", bukan asumsi)

Sebelum & sesudah tiap enhancement, ukur baseline:
1. **Utilisasi:** hari-armada terpakai / tersedia (dari `bookings`/`trips`).
2. **Kas:** rata-rata AR days, % DP on-time (dari `payments`/`invoices`).
3. **Revenue:** avg booking value, attach-rate add-on.
4. **Konversi:** lead→booking (dari `leads`/`bookings`).
5. **Biaya:** cost/km, maintenance/vehicle (dari `expenses`/`maintenance_records`).
6. **Keandalan:** hasil `forensic_repro.py` (harus tetap 0 bug).

> **Rekomendasi:** bangun **EN-01 (dashboard utilisasi)** lebih awal karena ia juga menjadi **instrumen ukur** untuk enhancement lain.

---

## 7. RISIKO & GUARDRAIL

- **Dynamic pricing (EN-08):** pasang batas atas/bawah + approval agar tak overprice/undercut.
- **Sub-charter (EN-06):** margin & AP partner wajib akurat — bangun di atas fix RC (INV-4).
- **Payment gateway (EN-10):** butuh kredensial user + integration agent; jangan hardcode secret.
- **Self-service (EN-07):** butuh DP-gate (EN-02) & anti-spam (rate-limit sudah ada di publik).
- **Semua:** jangan ubah `.env`; jangan re-seed; tiap fase wajib `testing_agent` + gate hijau.

---

## 8. KEPUTUSAN YANG DIBUTUHKAN DARI USER

1. Setuju urutan **W0 → W1 → W2**? (atau ada prioritas bisnis lain, mis. peak season mendekat → dahulukan EN-06 sub-charter?)
2. **Payment Gateway (EN-10)** sebelumnya DITUNDA — apakah dibuka kembali? (impact kas tinggi)
3. Untuk **Sub-charter (EN-06)**: unit partner masuk master permanen (opsi a) atau ad-hoc per booking (opsi b)? Perlu modul AP/settlement partner sekarang atau nanti?
4. Apakah ada **target metrik** spesifik (mis. "AR days < 21 hari", "utilisasi > 70%") yang ingin dikejar lebih dulu?

---

**Dokumen terkait:** `memory/ENHANCEMENT_BACKLOG.md` (detail E16–E21) · `SSOT_MASTER_REPAIR_PLAN.md` (EN-00) · `FORENSIC_00_EXECUTIVE_SUMMARY.md` · `docs/09_ROADMAP.md`.
