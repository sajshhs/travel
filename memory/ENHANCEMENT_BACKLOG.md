# 🗂️ ENHANCEMENT BACKLOG & PLAN — Rahaza Travel/Fleet ERP
> Dibuat 2026-07-02. Sumber: permintaan user (analisis Fleet + Booking) + audit kode CRM/WA.
> Status: **PLANNING** (belum di-build). Payment gateway = DITUNDA atas permintaan user.

---

## BAGIAN A — VERIFIKASI MODUL (snapshot)

**Kesehatan sistem (kanonik):** `bash scripts/gate.sh` **HIJAU 10/10** pasca E15 —
audit_endpoint_sweep **0×5xx**, 32 invarian integritas PASS, mutation_smoke PASS.
`testing_agent_v3` iter 46 (E14) + iter 47 (E15) = **Backend 100% + Frontend 100%**.

### Inventaris modul & status
| # | Modul | Endpoint inti | Status |
|---|---|---|---|
| 1 | Dashboard | /api/dashboard | ✅ sehat |
| 2 | Booking | /api/bookings (+calendar/availability/confirm/cancel/complete) | ✅ sehat |
| 3 | Quotation | /api/quotations (+pdf/send/accept/convert) | ✅ sehat |
| 4 | CRM/Leads | /api/leads, /api/growth, /api/campaigns, /api/broadcasts | ✅ sehat |
| 5 | Customers | /api/customers | ✅ sehat |
| 6 | Fleet — Armada | /api/vehicles | ✅ sehat |
| 7 | Fleet — Maintenance | /api/maintenance, /api/workshops, /api/service_types | ✅ sehat |
| 8 | Fleet — GPS (E15) | /api/gps/* (webhook/live/devices/summary) | ✅ sehat |
| 9 | Drivers + Workspace | /api/drivers, /api/driver/* | ✅ sehat |
| 10 | Dispatch | /api/dispatch/* (assign→departure→enroute→arrived→pod) | ✅ sehat |
| 11 | Finance | /api/invoices, /api/payments, /api/expenses, /api/payroll, /api/reports, /api/finance | ✅ sehat |
| 12 | Inbox / WhatsApp | /api/inbox, /api/whatsapp (MOCK provider) | ✅ sehat (WA=MOCK) |
| 13 | Automation Engine | /api/automation (rules/runs) | ✅ sehat |
| 14 | CMS / Situs Publik | /api/content, /api/public/* | ✅ sehat |
| 15 | Users / Settings / Onboarding | /api/users, /api/settings, /api/pricing, /api/onboarding | ✅ sehat |
| 16 | Audit Log / Analytics | /api/audit_logs, /api/analytics | ✅ sehat |

### Peta integrasi CRM/WA (event → aksi otomatis)
Alur: setiap transaksi memancarkan **event** → **Automation Engine** menjalankan **rule** (WA / notifikasi / assign agen).

| Event | Dipancarkan dari | WA ke pelanggan | Notifikasi in-app |
|---|---|:--:|:--:|
| lead.created | leads, situs publik, ads | ✅ auto-ack + assign agen | ✅ |
| quotation.sent | quotations | ✅ ringkasan penawaran | — |
| **booking.confirmed** | bookings (create+confirm), quotation.convert | ✅ konfirmasi + instruksi DP | ✅ |
| trip.assigned | dispatch (assign) | ✅ driver+unit | ✅ |
| booking.departure_confirmed | dispatch (confirm-departure) | ✅ titik jemput | ✅ |
| trip.enroute | dispatch (enroute) | ✅ driver OTW | — |
| trip.arrived | dispatch (arrived) | ✅ tiba di tujuan | — |
| trip.completed | driver (checkout) | ✅ terima kasih + ulasan | — |
| payment.recorded | payments | ✅ konfirmasi pembayaran | — |
| booking.departure_due | scheduler notifications | ✅ reminder H-1 | ✅ |
| invoice.overdue | finance_automation, scheduler | ✅ tagih | ✅ |
| customer.at_risk | growth | ✅ winback | ✅ |
| wa.inbound | whatsapp | (routing) | ✅ + assign agen |
| lead.sla_breached | growth | — | ✅ |
| doc.expiring / driver.sim_expiring | scheduler | — (internal) | ✅ |
| payroll.period_due / payout_pending | scheduler | — (internal) | ✅ |
| gps.alarm (E15) | gps | — (internal ops) | ✅ |

**Kesimpulan:** Rantai pelanggan **lead → quote → booking → dispatch → perjalanan → pembayaran → selesai → winback** SUDAH terintegrasi WA/CRM secara end-to-end. 👍

### ⚠️ CELAH integrasi CRM/WA yang ditemukan (masuk rencana)
- **✅ G1 (SELESAI 2026-07-03). Pembatalan kini memberi tahu pelanggan.** `booking.cancel` memancarkan event baru `booking.cancelled` → rule "Notifikasi pembatalan booking" kirim WA (info batal + ajakan jadwal ulang) + notifikasi internal. Idempotent (dedupe per booking). Terverifikasi testing_agent iter 52 (BE 38/38, FE smoke).
- **✅ G2 (SELESAI 2026-07-03). Dua jalur penyelesaian kini konsisten.** POD via dispatch (`/dispatch/trips/{id}/pod`) mendelegasikan ke SSOT `services.trips.finalize_trip_completion` → trip `completed` + `trip.completed` dipancarkan → WA "terima kasih + ulasan" terkirim (identik dgn checkout driver). Terverifikasi testing_agent iter 52.
- **G3. `trip.started`** dipancarkan tapi tanpa rule default (dormant) — minor, sudah dicakup enroute/arrived. (belum dikerjakan; opsional)

---

## BAGIAN B — PARKING LOT (ide ditampung, belum dieksekusi)

### B0. DITUNDA eksplisit oleh user
- **Payment Gateway** (Midtrans/Xendit) untuk DP online — SKIP dulu.
- **Potong mesin / immobilizer** (device FMC130 mendukung) — SKIP dulu.

### B1. Batasan modul Booking (ditampung dari analisis)
- Reschedule booking (ubah tanggal/armada) dgn re-cek ketersediaan — belum ada.
- DP sebagai gate: status `hold`(pending DP) → `confirmed` + auto-expire bila DP telat.
- Multi-armada / rombongan dalam 1 booking.
- Booking berulang (recurring).
- Kebijakan pembatalan/denda/refund otomatis.
- Form booking publik self-service (customer pesan → `pending` approval ops).
- Channel/OTA integration.

### B2. FITUR BARU — Pinjam/Sewa Armada Antar-Travel (Sub-charter / Partner Fleet)
> User: "bisnis bisa meminjam unit dari travel lain". Dikembangkan menjadi modul **Partner Sourcing / Sub-charter**.

**Masalah bisnis:** saat semua unit milik sendiri penuh/bentrok/di-maintenance, booking tetap bisa dipenuhi dengan **menyewa unit dari travel partner** — praktik umum (sub-charter). Perlu tercatat rapi agar **margin & utang ke partner** akurat.

**Rancangan (usulan):**
1. **Master Partner Travel** (koleksi `partners`): nama, kontak/PIC, telepon, rating, catatan, saldo utang (AP).
2. **Unit pinjaman**: dua opsi —
   - (a) `vehicles.ownership = owned | partner` + `partner_id` (unit partner didaftarkan ringkas), **atau**
   - (b) unit ad-hoc pada level booking (tanpa masuk master permanen).
   → Usulan: **(a)** agar availability & histori konsisten dgn engine yang ada.
3. **Sub-charter order** (koleksi `subcharters`): booking_id, partner_id, unit, tgl, **biaya sewa ke partner** (cost), status (requested→confirmed→settled), bukti.
4. **Saran otomatis**: saat buat booking & semua unit owned bentrok → tawarkan "Pinjam dari partner".
5. **Keuangan**: biaya sewa partner = **COGS/expense per booking** → P&L per booking akurat (revenue − partner cost − driver − BBM). Tambah **AP (utang ke partner)** + settlement.
6. **CRM/WA**: event baru `subcharter.requested` / `subcharter.confirmed` → **WA ke partner** (pesanan unit) + notifikasi internal. Ke pelanggan tetap mulus (branding kita).
7. **Availability**: unit partner punya window sendiri; anti double-booking (INV-4) tetap berlaku.
8. **RBAC & audit**: mutasi owner/ops_admin; semua tercatat di audit log.

---

## BAGIAN C — RENCANA ENHANCEMENT (usulan prioritas)

> Metode tiap fase: POC → build (BE+FE) → testing_agent → gate HIJAU (konsisten dgn E15).

- **E16 — Partner Sourcing / Sub-charter (Pinjam Armada Antar-Travel)** [BESAR]
  ✅ **SELESAI & TERVERIFIKASI (sudah terbangun di repo; diverifikasi 2026-07-03).** Master partner + unit sub-charter order (requested→confirmed→settled) + biaya partner→COGS/expense + event WA `subcharter.*` + menu "Pinjam Armada". testing_agent iter 53 PASS.
- **E17 — Penutupan celah CRM/WA + Reschedule Booking** [SEDANG]
  ✅ **SELESAI (2026-07-03).** G1 (`booking.cancelled`+WA) & G2 (POD dispatch→`trip.completed`) + **Reschedule** (POST /bookings/{id}/reschedule, re-cek INV-4/INV-21/RC-07, event `booking.rescheduled`+WA, dialog FE). testing_agent iter 53 PASS.
- **E18 — DP sebagai gate + auto-expire (hold)** [SEDANG]
  ✅ **SELESAI (2026-07-03).** `require_dp` → status `hold` (mereservasi armada), DP masuk → auto-promote `confirmed` (emit booking.confirmed), scheduler auto-expire hold telat DP → `cancelled` + event `booking.hold_expired`. Toggle "Wajib DP" di form FE + badge Hold. testing_agent iter 53 PASS.
- **E19 — Booking publik self-service** [SEDANG]
  ✅ **SELESAI (2026-07-03).** POST /api/public/booking (rate-limit+honeypot) → booking `pending` (source=website) → event `booking.requested` (auto-ack WA + notif ops) → ops **Setujui** (assign armada + auto-price → confirmed) / **Tolak** (→ cancelled). Halaman publik `/booking` + antrian approval FE. testing_agent iter 53 PASS.
- **E20 — Multi-armada / rombongan & recurring** [BESAR] — bila diperlukan.
- **E21 — Kebijakan pembatalan/denda/refund** [SEDANG] — bila diperlukan.
- **DITUNDA:** Payment Gateway, Potong mesin, Channel/OTA.

**Status roadmap:** E16–E19 SELESAI & TERVERIFIKASI (gate HIJAU 13/13 + testing_agent iter 53: Backend 75/75, Frontend smoke PASS). Berikutnya (opsional): E20/E21 atau integrasi WhatsApp NYATA (kini MOCK).

---

## BAGIAN D — UX SITUS PUBLIK (permintaan user 2026-08-12) — **BELUM dieksekusi**

### D1 ⭐ P1 — Navbar publik "terlalu ramai" (sederhanakan arsitektur informasi)

**Fakta terukur (bukan selera):** `frontend/src/components/public/PublicLayout.jsx` merender
**9 menu** (`NAV`) + **5 utilitas** (tema, telepon, "Masuk ERP", tombol "Pesan Sekarang", tombol
"WhatsApp") = **14 target klik dalam satu baris**; pada layar **1920 px** bar sudah **pecah 2 baris**.
`Pesan Online` (menu) dan `Pesan Sekarang` (tombol) menuju tujuan yang SAMA (`/booking`), dan
tombol `WhatsApp` menjadi jalur ketiga untuk niat yang sama → aksi utama tidak punya pemenang.

**Permintaan user:** `Kontak` & `Tentang` keluar dari menu (cukup footer) · `Pesan Online` jadi
tombol / section beranda · `Cek Pesanan` dipindah · `Masuk ERP` ke footer · `Pesan Sekarang`
dihapus dari menu.

**Rencana (5 menu + 1 aksi utama + baris utilitas):**
1. `NAV` dipangkas → **Beranda · Armada · Destinasi · Kalkulator · Blog**.
2. Satu tombol **"Pesan Online"** (menggantikan `nav-booking-cta` "Pesan Sekarang") + WhatsApp
   sebagai aksi sekunder.
3. **Bar pengumuman** (lapis paling atas, kini hanya teks tanpa tautan) diisi utilitas:
   **Cek Pesanan · Masuk ERP · nomor telepon**.
4. Footer: `Tentang` & `Kontak` & `Cek Status Pesanan` & `Konsol Internal` **sudah ada** → cukup
   dipertegas (beri `data-testid` yang dipindahkan dari header).
5. Beranda: **section "Pesan online dalam 3 langkah"** + CTA (permintaan eksplisit user).
6. Drawer ponsel: setelah `NAV` dipangkas, WAJIB ditambah grup "Layanan & Bantuan"
   (Cek Pesanan · Minta Penawaran · Tentang · Kontak · Masuk ERP).

**Peringatan yang harus dihormati:**
- `/booking/status` = tempat tamu **mengunggah bukti DP**. Jangan hanya di footer → beban CS naik &
  DP bisa telat diverifikasi (hold auto-expire). Karena itu tetap di bar pengumuman + saran chip
  "Lanjutkan pesanan BK-00xx" dari `rememberBooking()` (localStorage).
- **Pindahkan** `data-testid` lama (`public-nav-about`, `public-nav-contact`,
  `public-nav-booking-status`, `public-nav-login`, `nav-booking-cta`), jangan dihapus — dipakai
  laporan uji lama.
- Update SSOT `docs/05_NAVIGATION_MAP.md` §1 (dibaca `scripts/check_nav_map.py`).
- `/lp/*` sudah menyembunyikan menu (`isLanding`) — jangan diubah.
- Tutup dengan `gate.sh` HIJAU + 1 putaran `testing_agent_v3` (desktop + drawer ponsel + jalur
  "tamu mencari Cek Pesanan").

**Dampak yang diharapkan:** satu aksi utama yang jelas di halaman yang trafiknya dibayar iklan,
bar tidak lagi pecah dua baris, dan menu hanya memuat halaman tahap MEMILIH.
