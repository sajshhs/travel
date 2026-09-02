# 🤝 HANDOFF — Rahaza Travel ERP

> **Bahasa kerja: Indonesia.** Agent berikutnya WAJIB merespons user dalam Bahasa Indonesia.
>
> ## ✅ STATUS SESI TERAKHIR (2026-08-30 — RESTORE + BROADCAST WA NYATA, TUNTAS)
> Repo di-restore dari `awkasjasnaba/travel`; **BUG-0144** (mutasi self-test B01 `total_amount`
> ter-commit di `PublicBookingSubmit` dari sesi terhenti, kelas BUG-0139) ditutup → gate HIJAU
> 46/46. **Broadcast WA nyata TUNTAS**: tab **Broadcast** di /app/crm (Crm.jsx → CrmBroadcast)
> di-wire ke backend `routers/broadcasts.py` (send_wa per penerima + jeda acak 4–9 dtk anti-ban
> utk provider openwa/meta_cloud + progres + klaim atomik). Tambahan: label status dilokalkan,
> **reaper startup** `reap_stale_sending()` (sending yatim → failed, terverifikasi restart
> nyata), `memory/test_credentials.md` diisi. testing_agent **iteration_105 0 bug** (backend
> 12/12, frontend 100%). Provider aktif = mock s.d. QR OpenWA discan user. Backlog minor:
> DELETE/edit broadcast draft; heading halaman tak ikut tab aktif (kosmetik).
>
> ## Riwayat sesi 8 (2026-08-29 — BATCH 7: GABUNG TITIK JEMPUT, TUNTAS)
> **BUG-0143**: merge + unmerge utk TITIK JEMPUT kembar, pola identik destinasi —
> `POST /api/master/pickup-points/{id}/merge` (cascade `bookings.origin` → nama target, catat
> `merged_moved.bookings`, sumber `active=false` + `merged_into`; target wajib aktif) &
> `POST .../unmerge` (kembalikan booking tercatat bila origin masih nama target, sisanya
> `skipped`). `master_pickup_points` kini mengembalikan `merged_moved_count`. FE
> `MasterData.jsx`: Row/MergePanel digeneralisasi via prop `kind` (merge tampil utk
> kind!=='city'), testid sama (`md-merge-*`/`md-unmerge-*`). Guard: cek diperketat
> `pk.count("/merge") ≥ 2` & `pk.count("/unmerge") ≥ 2` (tetap 34 cek). Gate **HIJAU 46/46**;
> testing_agent **iteration_100 0 bug** (backend 8/8; suite
> `backend/tests/backend_test_ssot_batch7.py`).
>
> ## Riwayat sesi 7 (2026-08-29 — batch 6: undo gabungan + kota bengkel)
> **BUG-0142**: (1) merge destinasi kini mencatat `merged_moved` (id dokumen per koleksi) →
> endpoint baru `POST /api/master/destinations/{id}/unmerge` mengembalikan dokumen tercatat
> (hanya bila destinasinya masih nama target; sisanya `skipped`), sumber `ops_active=true` +
> `$unset merged_*`; UI: tombol "Batalkan Gabungan" `md-unmerge-{id}` → panel
> `md-unmerge-panel-{id}` (jumlah dari `merged_moved_count` di GET /master/destinations) →
> `md-unmerge-confirm-{id}`. (2) `workshops.city` KERAS via `city_or_400` (create+update),
> FE `WorkshopFormDialog` → `CitySelect` (wsh-city); rename kota cascade + `used_by_workshops`
> + kolom Bengkel di Excel. Guard INV-REF-02 → **34 cek**. Gate **HIJAU 46/46**; testing_agent
> **iteration_99 0 bug** (backend 11/11; suite `backend/tests/backend_test_ssot_batch6.py`).
>
> ## Riwayat sesi 6 (2026-08-29 — SSOT batch 5 + ekspor + gabung destinasi)
> **BUG-0141**: (1) master KOTA baru `cities` (cty_) — `customers.city`/`partners.city` KERAS via
> `refs.city_or_400` (create+update), quick-add `POST /api/cities`, FE `CitySelect` (cf-city/
> pf-city), kelola `GET/PATCH /api/master/cities[/{id}]` (rename cascade customers+partners);
> `vehicle_type` landing/booking publik LUNAK via `refs.vehicle_type_normalize`; (2) **ekspor
> Excel** `GET /api/master/export` (3 sheet: Titik Jemput/Destinasi/Kota + pemakaian, tombol
> `md-export-excel`); (3) **GABUNG destinasi kembar** `POST /api/master/destinations/{id}/merge`
> (cascade 3 koleksi ke target; sumber nonaktif + `merged_into`; badge "Digabung →"; UNDO hanya
> via DB — belum ada di UI). Registrasi `cities`: verify_schema, validate_compliance,
> PURGE_COLLECTIONS, seed, `scripts/migrate_ssot_batch5.py`. Guard INV-REF-02 → **30 cek**.
> Gate **HIJAU 46/46 0 FAIL 0 SKIP**; testing_agent **iteration_98 0 bug** (backend 19/19; suite
> `backend/tests/backend_test_ssot_batch5.py`). ⚠ JANGAN jalankan `ruff check --fix backend/`
> global — pernah merusak string patch selftest (Optional→`str|None`); lint hanya per-file baru.
>
> ## Riwayat sesi 5 (2026-08-29 — SSOT batch 4 + preview cascade)
> **BUG-0140**: normalisasi LUNAK semua jalur tulis publik/inbound (`refs.origin_normalize` baru;
> booking online + lead landing + lead ads kini menyimpan origin/destination KANONIK bila cocok
> master, tetap menerima nilai di luar master); **Preview Cascade** di /app/masterdata (panel
> konfirmasi ber-jumlah booking/lead/penawaran sebelum rename, testid `md-confirm-*`/
> `md-rename-confirm-*`/`md-rename-cancel-*`/`md-rename-abort-*`; master destinasi +
> `used_by_quotations`). Guard INV-REF-02 → **23 cek** (+ probe runtime baca DB). Gate **HIJAU
> 46/46 0 FAIL 0 SKIP**; testing_agent **iteration_97 0 bug** (backend 7/7, frontend 2/2; suite
> `backend/tests/backend_test_ssot_batch4.py`). Kandidat batch 5: `vehicle_type` lead landing,
> kota customers/partners/workshops.
>
> ## Riwayat sesi 4 (2026-08-29 — ritual penutup batch 3)
> Sesi 4 menuntaskan ritual penutup batch 3: `bash scripts/gate.sh` **HIJAU penuh 46 PASS
> 0 FAIL 0 SKIP**, testing_agent **iteration_96 0 bug** (backend 15/15, frontend 4/4),
> `memory/INVARIANTS.md` (INV-REF-02 batch 3) & `memory/PRD.md` diperbarui. Dalam prosesnya
> ditemukan & diperbaiki **BUG-0139**: mutasi self-test B01 (`total_amount` di
> `PublicBookingSubmit`) ternyata TER-COMMIT ke repo dari sesi 3 yang terhenti — plus probe
> `masterdata` di SECTION_PROBES, empty-state select Quotation.jsx, dan pemisahan
> `schemas_partner.py` (schemas.py < 800 baris). Rincian di `memory/BUG_REGISTRY.md`.
>
> ## Riwayat sesi 3 (2026-08-29 — SSOT Batch 3 + Master Data + Lead→Booking, BUG-0138)
> Pekerjaan sesi 3 (**SSOT Batch 3 + halaman Master Data + Lead→Booking**, dicatat sebagai
> BUG-0138 di `memory/BUG_REGISTRY.md`) **kode sudah selesai ditulis & lolos verifikasi manual/curl,
> tetapi DIHENTIKAN USER sebelum ritual penutup**. Yang SUDAH:
> - **Batch 3 SSOT**: destinasi PENAWARAN divalidasi master — `routers/quotations.py` create/update
>   via `destination_or_400` (update hanya-bila-diubah); form penawaran WEB PUBLIK
>   (`features/public/Quotation.jsx`) kini `<select>` dari endpoint publik baru
>   `GET /api/public/destination-options` (backend publik tetap LUNAK via `destination_normalize`);
>   `QuotationFormDialog.jsx` pakai `DestinationSelect` (optionsPath `/leads/destination-options`).
> - **Halaman Master Data** `/app/masterdata` (`features/app/MasterData.jsx`, section BARU
>   `masterdata` = owner+ops_admin; sudah didaftarkan 3 lapis: `navigationConfig.js`
>   (NAV_TREE + PAGE_META + allowlist), `App.js` RoleGuard, `permissions_config.SECTION_ACCESS`,
>   dan `docs/05_NAVIGATION_MAP.md` §2+§3). Endpoint kelola di `routers/pickup_points.py`:
>   `GET/PATCH /api/master/pickup-points[/{id}]` & `GET/PATCH /api/master/destinations[/{id}]` —
>   **RENAME = CASCADE** ke bookings/leads/quotations (terverifikasi: rename Bandung→"Bandung Kota"
>   men-cascade 8 booking, lalu dikembalikan); **NONAKTIF** (`active`/`ops_active`) menyembunyikan
>   dari SEMUA selector + ditolak pemakaian baru (filter di `services/refs.py` + endpoint options).
> - **Lead→Booking**: `POST /api/leads/{id}/prepare-booking` (ensure_customer dedupe + prefill,
>   idempotent) + tombol **"Jadikan Booking"** (`data-testid="lead-to-booking"`) di
>   `LeadDetailDrawer.jsx` → membuka `BookingFormDialog` (prop baru `initial` utk prefill) →
>   setelah booking dibuat: aktivitas lead tercatat + stage otomatis `won`.
> - Guardrail **INV-REF-02 diperluas** (+5 cek batch 3: quotations, public options, master cascade)
>   → `verify_ssot_relations.py` **PASS 17 cek**; `verify_rbac_guards.py` PASS 193;
>   `verify_no_test_pollution.py` PASS; `check_nav_map.py` OK; screenshot halaman Master Data OK
>   (badge "ops/draft" sudah dibetulkan: hanya utk `status === "draft"`).
>
> ### ✅ Ritual penutup batch 3 (dikerjakan sesi 4, 2026-08-29) — SEMUA TUNTAS
> 1. ✅ `bash scripts/gate.sh` penuh → **HIJAU 46 PASS 0 FAIL 0 SKIP** (receipt memory/GATE_RECEIPT.md).
> 2. ✅ testing_agent iteration_96 → 0 bug: (a) POST /quotations destinasi ngawur → 400,
>    'bali' → kanonik 'Bali', PATCH hanya-bila-diubah OK; (b) form publik /quotation select
>    `q-destination` berisi opsi master, submit OK, nilai warisan tetap DITERIMA (lunak);
>    (c) /app/masterdata rename cascade (Bandung→Bandung Kota→restore) + toggle nonaktif
>    menghilangkan opsi dari `bf-destination`/`bf-origin` + ditolak utk pemakaian baru; RBAC:
>    marketing_admin & driver 403/redirect; (d) Lead→Booking prefill benar; (e) regresi lolos.
>    Suite: `backend/tests/backend_test_ssot_batch3.py`.
> 3. ✅ `memory/INVARIANTS.md` baris INV-REF-02 diperluas scope batch 3.
> 4. ✅ `memory/PRD.md` diperbarui (sesi 3+4).
> 5. Temuan kecil tak-blocking dari `check_nav_map.py`: INFO menu 'users' & 'vehicles' belum punya
>    PAGE_META — sudah begitu sejak sebelum sesi ini, BUKAN regresi; abaikan atau rapikan terpisah.
>
> ### Konteks teknis penting sesi 3 (agar tidak mengulang jalan buntu)
> - Prefix router publik = `/api/public` → endpoint options publik didefinisikan sebagai
>   `@router.get("/destination-options")` di `routers/public.py` (JANGAN tulis `/public/...` ganda).
> - Endpoint literal `/bookings/destination-options` HARUS tetap terdefinisi SEBELUM
>   `/bookings/{booking_id}` di `routers/bookings.py` (urutan route FastAPI).
> - `routers/bookings.py` dibatasi validate_compliance **maks 800 baris** (sekarang ~796) — kalau
>   perlu menambah, pindahkan logika ke `services/` (contoh: `release_booking_resources` sudah
>   dipindah ke `services/trips.py`).
> - Probe runtime guard memakai marker `Penjaga INV-REF-02` + `purge_guard_bookings()`/
>   `purge_guard_artifacts` (koleksi quotations/leads sudah tercakup purge).
> - Master destinasi: baris operasional dibuat `status:"draft"` agar TIDAK tayang di web publik
>   (public pakai visibility_filter published); toggle ops memakai field `ops_active`
>   (default aktif bila field tidak ada — filter `{"ops_active": {"$ne": False}}`).
> - Kredensial demo: `memory/test_credentials.md` (semua `demo12345`; login `/app/login`).
> - DB di-reseed oleh gate: booking/lead uji yang kamu buat akan hilang — jangan panik.
>
> ## Riwayat sesi 2026-08-29 (sudah TUNTAS + gate HIJAU + testing_agent)
> **Sesi 2 (SSOT BATCH 2 + ALARM HARGA**, BUG-0137: `bookings.origin` =
> relasi master baru `pickup_points` (pkp_, `refs.origin_or_400`, quick-add satu pintu
> `POST /api/pickup-points`, selector FE `PickupPointSelect` dgn dedupe); `leads.destination`
> jalur ERP divalidasi `destination_or_400` (+`GET /leads/destination-options`), jalur PUBLIK
> memakai `destination_normalize` LUNAK; alarm deviasi Master Harga (unit vs tipe >±50% →
> warning kuning + toast, `_rate_deviation` di routers/pricing.py); migrasi
> `scripts/migrate_ssot_batch2.py`; INV-REF-02 & INV-PRICE-02 diperluas. Gate HIJAU 46/46,
> testing_agent iteration_95: backend 100%, frontend 100%. Sesi 1 hari yang sama: RC-A..RC-E
> BUG-0132..0136 — lihat paragraf di bawah.)
> **Sesi 1:** (**SESI RC-A..RC-E**: 5 keluhan user diperbaiki — BUG-0132..0136 di
> `memory/BUG_REGISTRY.md`. (1) RC-A: `/pricing/quote` kini `resolve_day_rate` (angka yang dilihat
> ops = yang ditagih); (2) RC-B: **Master Harga tunggal** — `day_rate`/`price_from` DIHAPUS dari
> jalur tulis armada, tarif unit hanya via Pengaturan → panel `UnitRatesPanel`
> (`GET/PATCH /api/pricing/unit-rates`), dikunci guardrail baru **INV-PRICE-02**; (3) RC-C: media
> health tri-state (`media_store.check_file`) — merah hanya utk berkas TERBUKTI hilang, kasus
> ambigu = kuning berALASAN; (4) RC-D: Driver Workspace v2 — Upcoming Trips + stepper
> standby→jemput→on_trip (via `/trips/{id}/status`, state machine TUNGGAL)→tiba→checkout;
> (5) RC-E batch 1: `bookings.destination` = relasi master `destinations` (validator
> `refs.destination_or_400`, selector FE `DestinationSelect`, migrasi
> `scripts/migrate_booking_destinations.py`, guardrail baru **INV-REF-02**). Gate **HIJAU penuh**
> (0 FAIL 0 SKIP, incl. 2 gate baru). Riwayat sesi sebelumnya: FASE 7 — lihat §0.5.)
> **GOLDEN RULE:** Tidak ada klaim "selesai" tanpa `bash scripts/gate.sh` **HIJAU penuh (0 FAIL, 0 SKIP)** dan receipt `memory/GATE_RECEIPT.md`. SKIP ≠ PASS.

---

## 0) ANTREAN KERJA BERIKUTNYA (per 2026-08-12, sesudah FASE 7 / UI-READABILITY)

> **Kondisi masuk sesi berikutnya:** `bash scripts/gate.sh` **HIJAU 40/40 (0 FAIL, 0 SKIP)** ·
> `ux_audit --strict` **0 ERROR 0 WARN** · testing agent `iteration_87` & `iteration_88` **0 bug**.
> Brand di SELURUH permukaan = **RahazaTrans** (termasuk seed & dokumen DB). Rincian Fase 7 di
> **§0.5** — baca sebelum menyentuh CSS/tema, ada 6 jebakan yang sudah berbayar mahal.

| # | Pekerjaan | Prioritas | Catatan |
|---|-----------|-----------|---------|
| 1 | **Kredensial nyata** Meta Ads / Google Ads / WhatsApp Cloud / GA4 | **P1** | semua LIVE-READY tetapi masih **MOCK**. Kunci ditempel user sendiri di `/app/integrations`; pembuktian akhir lewat Meta Test Events / GA4 DebugView / akun test Google Ads |
| 2 | **Uji beban konkuren tinggi (load test)** | P1 | belum pernah dijalankan. Mutex reservasi terbukti pada 8–16 permintaan paralel, belum pada beban nyata |
| 3 | **Halaman promo publik** (`/promo` + kartu promo di beranda) | P2 | daftar promo yang bisa diklik SUDAH ada di dalam wizard `/booking`; yang belum: halaman khusus promo untuk trafik iklan |
| 4 | **Notifikasi proaktif hold hangus** | P2 | laporan sudah ada (`/app/reports` → Hold Hangus). Belum ada: dorongan harian ke ops saat ada hold hangus **yang buktinya sudah diunggah** (kasus paling mahal) |
| 5 | **Isi rute antar-jemput nyata + tarifnya** | P2 (kerja user) | katalog 11 bandara + tombol "Arah balik" sudah siap. Tarif per tipe unit WAJIB diisi pemilik — server menolak rute tanpa tarif; sistem sengaja TIDAK menebak harga |
| 6 | Berkas media lokal hilang di pod baru | P2 | biner di-gitignore; dokumen `media_assets` tetap ada → gambar 404. Pemulihan: unggah ulang atau `MEDIA_BACKEND=objstore` |
| 7 | GA4 Measurement Protocol server-side | P2 | lanjutan yang direncanakan setelah F8 |
| 8 | 7 WARN kosmetik `validate_compliance` | P3 | non-blocking, FAIL 0. `ux_audit --strict` sudah **0 ERROR 0 WARN** |

> ✅ **SUDAH SELESAI — jangan dikerjakan ulang:** §0.1 rapikan navbar publik · §0.2 sisa verifikasi
> UI BOOKING-V1 (8 user story — **TUNTAS**, penutupnya STORY H "Tayang di web") · daftar promo di
> wizard · laporan "Hold Hangus" · katalog rute bandara + arah balik · **§0.5 Fase 7: keterbacaan
> kaca/tema + 3 halaman publik diperkaya + CTA blog + posisi chat + rename RahazaTrans**.

### 0.1 ✅ SELESAI — Navbar situs publik dirapikan (permintaan user "terlalu ramai")

**Sebelum:** 9 menu + 5 utilitas = **14 target klik dalam satu baris**; pada 1920px label
`Pesan Online / Cek Pesanan / Masuk ERP / Pesan Sekarang` **pecah dua baris**; `Pesan Online`
(menu) dan `Pesan Sekarang` (tombol) menuju tujuan yang SAMA (`/booking`).

**Sesudah** (SSOT lengkap: `docs/05_NAVIGATION_MAP.md` **§1a**) — header terukur **90,75 px** (1 baris):
- Menu utama **5 item**: Beranda · Armada · Destinasi (mega) · Kalkulator · Blog.
- **Satu** aksi utama `nav-booking-cta` "Pesan Online" (gradien) + WhatsApp **sekunder** (outline).
- Bar pengumuman = rumah utilitas: **`resume-booking-chip`** · `public-nav-booking-status`
  (Cek Pesanan) · `nav-phone-cta` (nomor telepon) · `public-nav-login` (Masuk ERP).
- Footer: `public-nav-booking` · `public-nav-about` · `public-nav-contact` · `footer-nav-*`.
- Drawer ponsel: grup 1 `mnav-<id>` (5 menu) + grup 2 **`public-mobile-help-group`**
  "Layanan & Bantuan" (Pesan Online · Cek Pesanan · Penawaran · Tentang · Kontak · Masuk ERP).
- Bar bawah ponsel: `sticky-cta-calc` (ikon) + **`sticky-cta-booking`** + `sticky-cta-wa`.
- Beranda: section **`home-booking-steps`** "Pesan online dalam 3 langkah" — angka DP & lama hold
  diambil dari `/public/booking/config` (BUKAN hardcode) + `home-cta-booking`.
- `/lp/:slug` tetap header ringkas: menu DAN utilitas bar pengumuman disembunyikan (INV-LP).

**WAJIB dijaga ke depan:** `data-testid` di atas DIPINDAH, bukan dihapus · `/about` & `/contact`
tetap ada di `sitemap.xml` + ditaut footer (crawlability tidak turun) · jangan pernah menaruh
tautan keluar di header `/lp/*`.

**Kenapa chip "Lanjutkan pesanan BK-00xx" wajib ada:** `/booking/status` adalah SATU-SATUNYA tempat
tamu mengunggah bukti transfer DP. Sesudah "Cek Pesanan" keluar dari menu utama, chip inilah jaring
pengamannya (kode+token dari `localStorage` `rahaza_bookings`). Chip hanya muncul bila pesanan masih
menuntut tindakan (pending / hold / bukti ditolak), dan **token mati (404) dibuang sendiri** dari
localStorage — tidak ada chip hantu. Uji: buat pesanan BARU lewat API lalu suntik localStorage;
memakai kode lama yang sudah ter-reseed akan tampak seperti bug padahal itu self-healing bekerja
(kekeliruan yang sempat dilaporkan `iteration_83.json`).

### 0.2 ✅ TUNTAS — sisa verifikasi UI BOOKING-V1 (8 user story)

Semuanya kini terbukti di UI: render `/booking` · RBAC `marketing_admin` · alur **Verifikasi DP**
end-to-end · batas panjang teks · antar-jemput bandara · batalkan pesanan · promo ditolak berALASAN ·
mode `ops_approval` + tombol "ACC + Minta DP" · CRUD Rute Antar-Jemput · **tolak bukti + unggah
ulang** · **verifikasi dengan nominal melebihi tagihan** · **STORY H toggle "Tayang di web"**
(dimatikan → unit hilang dari `/fleet` DAN dari `POST /public/booking/search`; dinyalakan → kembali).

> 🧪 **Catatan uji yang menghindarkan laporan bug palsu (masih berlaku):** input tanggal di
> `/booking` TIDAK punya atribut `name` — selektornya `data-testid="booking-start"` /
> `"booking-end"`, dan `page.fill(...)` **bekerja** (menyetel `value` lewat JS tidak memicu
> `onChange` React). Dropdown tertentu memakai `SelectField`/Radix: **klik trigger → klik
> `<testId>-opt-<slug>`**, `select_option()` tidak berlaku. Bila DOM tampak "kode lama" setelah
> perubahan FE, itu jebakan HMR — `sudo supervisorctl restart frontend`.

### 0.3 Fitur BOOKING-V2 yang baru lahir (rujukan cepat)

| Fitur | Backend | Frontend | Bukti |
|-------|---------|----------|-------|
| Daftar promo bisa diklik di wizard | `POST /api/public/booking/promos` (subtotal **dihitung ulang server**) + `services/promos.list_for_context/terms_text/public_view` | `components/public/booking/PromoPicker.jsx` (+ dipakai `QuoteBreakdown`) | total 4.500.000 → 4.000.000 & DP ikut turun; promo tak layak tampil **beserta alasan** |
| Laporan "Hold Hangus" | `services/hold_report.py` + `GET /api/reports/hold-expired` & `/export` (CSV) | `components/app/HoldExpiredReport.jsx` di `/app/reports` | `iteration_84.json`; seed BK-0009/BK-0010 agar tidak kosong |
| Katalog rute bandara + arah balik | (CRUD lama `routers/transfer_routes.py`) | `components/app/TransferRoutesPanel.jsx` (`tr-catalog`, `tr-quick-*`, `tr-reverse-*`) | BALI-DPS & DPS-BALI dua arah tersimpan; rute baru langsung dijual dengan tarif FLAT |

**Angka yang mengubah keputusan di laporan Hold Hangus** (baca `services/hold_report.py` untuk
alasan tiap angka): `with_proof` = hangus PADAHAL bukti sudah diunggah (keterlambatan ops, bukan
tamu — ini pemicu peringatan merah), `expiry_rate` = indikasi `hold_hours` terlalu pendek,
`recovered` = tamu memesan lagi (sisanya layak dihubungi via tombol wa.me).

### 0.4 Riwayat: sesi BOOKING-V2 (arsip)

Isi lengkapnya ada di **§2a** (navbar publik dirapikan, section beranda "3 langkah", chip
"Lanjutkan pesanan", 3 fitur backlog) — dipindah ke arsip agar antrean di atas tetap ringkas.

### 0.5 ✅ SELESAI — FASE 7: Keterbacaan (kaca & tema portal) + 3 halaman publik + rename **RahazaTrans**

Permintaan user (7 poin, dari 4 screenshot): keterbacaan ("kalau font putih maka elemen visual
background-nya harus disesuaikan"), halaman **Armada/Destinasi/Kalkulator** terlalu sepi, CTA
`/blog/:slug` rusak, posisi chat terlalu di atas, brand → **RahazaTrans**.

**6 bug NYATA ditutup — semuanya kelas "gagal SENYAP" (tak ada satu pun error di konsol):**

| ID | Inti masalah | Kenapa lolos berkali-kali |
|----|--------------|---------------------------|
| **BUG-0121** | `to-[color:var(--primary)]` — token proyek ini **TRIPLET HSL**, jadi class itu invalid → browser membuang SELURUH `background-image` → panel CTA transparan, teks putih di kertas putih | di mode gelap panel "kebetulan" terbaca; `backgroundColor` panel memang `transparent` (latar dipasang via `background-image`) sehingga pengukuran naif tampak wajar |
| **BUG-0122** | `.glass-modal` memaku `hsla(0 0% 100%/.94) !important` untuk SEMUA mode + `.glass-3d::before` `mix-blend-mode: screen` opacity .55 tanpa mask | efek kaca dirancang di atas foto GELAP; baru mematikan saat dipakai di atas foto TERANG / mode gelap |
| **BUG-0123** | tombol close dialog `data-[state=open]:bg-accent` → bulatan warna, ikon nyaris hilang | `components/ui/` dikecualikan `ux_audit` |
| **BUG-0124** | konten Radix yang di-**PORTAL** ke `<body>` berada di luar `[data-surface][data-theme]` → dialog & SEMUA dropdown memakai palet ERP terang saat situs gelap | scope tema di `div`, bukan `<html>`; ditemukan **testing agent** (iter-86), bukan mata |
| **BUG-0125** | `--surface-on-hero: var(--card)/.93` di `:root` → `var()` disubstitusi DI `:root` (tema ERP terang) lalu HASILNYA diwariskan → kartu tetap TERANG di mode gelap | regresi buatan sendiri saat memperbaiki BUG-0122; tertangkap sebelum diserahkan |
| **BUG-0126** | ChatWidget `bottom-40` + tinggi TETAP 440px → panel menembus header pada viewport pendek | tidak ada angka yang tahu tinggi header / `StickyMobileCTA` |

**Kontrak baru (SSOT: `docs/06_UIUX_STANDARDS.md` §6 + `design_guidelines.md`), dijaga `INV-THEME-01`:**
1. Warna WAJIB lewat utilitas Tailwind / `hsl(var(--x))` / `var(--gradient-*)`. **DILARANG**
   `from-/via-/to-[color:var(--token)]` dan `bg-[var(--token)]`.
2. Permukaan kaca (termasuk fallback `@supports`) **dilarang** memaku `hsl(0 0% 100%)`.
   Surface di atas foto pakai **`.glass-on-hero`** (base `hsla(var(--card)/.93)`) / **`.hero-scrim`**.
3. Refraksi/sheen hanya lewat `--refraction-opacity` (**≤ .30**), `--refraction-blend`,
   `--refraction-mask`. `mix-blend-mode: screen` hardcode dilarang.
4. **Jangan** menyusun token TEMA di dalam custom property di `:root`/`.dark` (lihat BUG-0125).
5. Elemen mengapung memakai SSOT offset `--header-h` / `--sticky-cta-h` (0 desktop, 72px < lg) /
   `--fab-bottom` / `--panel-bottom`; z-index: sticky 40 · header 50 · chat 60 · consent 70.
6. `ThemeContext` **wajib** memasang `data-surface`/`data-theme` di `<html>` **dan**
   membersihkannya saat unmount; tiap preset gelap wajib punya selector kembar `[…].dark`
   (`.dark X` hanya cocok untuk **descendant**).

**Halaman publik diperkaya — SEMUA dari data nyata, 0 mock:**

| Halaman | Section baru | Sumber data |
|---------|--------------|-------------|
| `/fleet` | `fleet-quick-actions` (unit tayang · tipe bertarif · DP%) · `fleet-type-filter` · `vehicle-type-compare` · `fleet-standards` · `fleet-trip-estimator` · `airport-route-strip` · `promo-strip` · `fleet-faq` · `fleet-cta-band` | `/public/fleet` + `/public/booking/config` + `/public/promos` |
| `/destinations` | `destination-facts` (fun fact dari `highlights`/`best_time`/`itinerary`) · `package-strip` · `dest-narrative` · `dest-faq` (dirangkum dari `destinations[].faqs`) · `dest-cta-band` | `/public/destinations` + `/public/packages` |
| `/trip-calculator` | `calc-how-it-works` · empty-state `calc-empty-rates` (tarif nyata, bisa diklik) · `calc-dp` · `vehicle-type-compare` · `airport-route-strip` · `promo-strip` · `calc-faq` · `calc-cta-band` | `/public/booking/config` + `/public/promos` + `POST /public/trip-estimate` |

Komponen baru yang dipakai ulang: `CtaBand` (pengganti WAJIB untuk semua panel ajakan),
`VehicleTypeCompare`, `AirportRouteStrip`, `PromoStrip`, `PackageStrip`, `DestinationFacts`,
`FaqBlock`. `BookingWizard` kini menerima query **`route`** (deep-link kartu rute bandara).

**Rename brand:** 30 berkas FE/BE + `scripts/seed_data.py` + dokumen DB (`settings.company_info`,
`booking_flow.payment.bank_accounts[].holder` → "PT RahazaTrans", `articles`, `landing_pages`) +
`halo@rahazatrans.id`. Kunci localStorage & nama `@keyframes` (`rahaza_*`, `rahaza-shimmer`)
SENGAJA dibiarkan — internal, mengubahnya hanya memutus sesi tamu tanpa manfaat.

**Bukti:** `gate.sh` **HIJAU 40/40** · `ux_audit --strict` 0/0 · `iteration_86` (menemukan
BUG-0124) → `iteration_87` (**100 %**, termasuk uji isolasi ERP BOLAK-BALIK) → `iteration_88`
(**0 bug**: `/booking` end-to-end BK-0068, promo GATHERING500 Rp 5.850.000 → Rp 5.350.000,
STORY H dua arah, Hold Hangus cocok dengan API).

---

## 1) Ringkasan Sistem

- **Stack:** React + Shadcn/UI (frontend) · FastAPI + MongoDB (backend) · Bash guardrails (`scripts/`).
- **Karakter khusus:** sistem sangat diperkeras: **23 gate otomatis** (statik AST + runtime) via `scripts/gate.sh`, battery bug-hunt forensik (`scripts/run_forensics.sh`), SSOT invariant di `memory/INVARIANTS.md`.
- **Filosofi:** tiap kelas bug ditemukan → ditutup → **dikawal guardrail baru** → self-test (MERAH↔HIJAU). Meta-guardrail `INV-META-01` memaksa tiap `verify_*.py` ter-wire di `gate.sh` + terdaftar di `INVARIANTS.md`.
- **Kredensial uji:** `owner@demo.local` / `ops@demo.local` / `marketing@demo.local` / `driver@demo.local`, password `demo12345` (`memory/test_credentials.md`).
- **Reset data demo:** `cd /app && python scripts/seed_data.py`.

---

## 2) Status Terkini (Snapshot 2026-08-12, sesudah BOOKING-V2)

| Aspek | Status |
|-------|--------|
| Services | backend RUNNING · frontend RUNNING · mongodb RUNNING |
| `bash scripts/gate.sh` | ✅ **HIJAU penuh, 0 FAIL, 0 SKIP** (**37 gate** — INV-BOOK-02 statik DIPERKUAT: sasarannya kini SEMUA skema yang diimpor router publik, 71 cek) |
| POC | `scripts/test_core_booking_v1.py` **74/74** (dijalankan 2× sesi ini: sebelum & sesudah perubahan) · `scripts/test_core_lp_f8.py` **84/84** (F8) · `scripts/test_core_ads_f3.py` **120/120** |
| `ux_audit --strict` | ✅ **0 ERROR 0 WARN** (193 file) |
| Testing agent terakhir | `iteration_84.json` (BOOKING-V2: 3 fitur baru) → backend **100% (14/14)**, frontend **100%**, **0 bug** · `iteration_83.json` (navbar + STORY H) → backend 100%, frontend 97% dengan **1 laporan LOW yang terbukti FALSE POSITIVE** (kode booking sudah ter-reseed; chip terbukti bekerja dengan pesanan baru) |
| Fase berjalan | **BOOKING-V2 SELESAI** (Fase 0–6 `plan.md`). Berikutnya: antrean §0 (kredensial nyata, load test, halaman promo publik, notifikasi hold hangus) |
| Bug ditutup sesi ini | **BUG-0120** — kode rute antar-jemput otomatis simetris (`DPS-DPS`) membuat arah balik mustahil; kelas sama mengancam Bandung–BDO, Solo–SOC, Semarang–SRG |
| Guardrail sesi ini | **INV-BOOK-02 diperluas**: daftar skema yang dijaga DITURUNKAN dari `import` di `routers/booking_public.py` (bukan daftar manual) → endpoint publik BARU otomatis terjaga. Self-test: `BookingPromoListRequest.subtotal` disuntikkan → MERAH; revert → HIJAU |
| Integrasi platform | **MASIH MOCK** — Meta Ads/CAPI, Google Ads/Data Manager, WhatsApp Cloud, GA4. LIVE-READY: tempel kunci di `/app/integrations` |
| env baru yang WAJIB ada | `SETTINGS_ENCRYPTION_KEY_B64` (vault kredensial). `PUBLIC_SITE_URL` & `MEDIA_BACKEND=local` disetel di pod ini. `EMERGENT_LLM_KEY` OPSIONAL |

---

## 2a) Yang Dikerjakan Sesi Ini (BOOKING-V2, 2026-08-12)

**Titik masuk:** `/app` kosong (pod baru) → di-restore dari `github.com/wajauhmawa/travel`,
`bash scripts/bootstrap.sh --seed`, lalu **verifikasi dulu** (POC 74/74 + gate HIJAU) sebelum
menyentuh satu baris kode. Sesi sebelumnya berhenti tepat setelah STORY F+G terbukti di UI.

1. **STORY H** — penutup §0.2: toggle "Tayang di web" dibuktikan di UI dua arah (lihat §0.2).
2. **§0.1 navbar publik dirapikan** + drawer ponsel 2 grup + section beranda "Pesan online dalam
   3 langkah" + chip "Lanjutkan pesanan BK-00xx" (lihat §0.1 untuk peta `data-testid`).
3. **Daftar promo bisa diklik di wizard** `/booking` — endpoint `POST /public/booking/promos`
   menghitung ulang subtotal di server lalu menilai tiap promo dengan `promos.evaluate` yang SAMA
   dengan checkout. Promo tak layak tetap tampil **beserta alasannya** ("minimal 2 hari") karena
   itulah yang membuat tamu menambah durasi, bukan menyembunyikannya.
4. **Laporan "Hold Hangus"** (`/app/reports`) — menutup gap lama "auto-expire jalan, tapi tak ada
   laporannya". Tiga angka yang mengubah keputusan + CSV + tombol **Hubungi** (wa.me, nyata).
5. **Katalog rute bandara + Arah balik** — mempercepat entri rute NYATA **tanpa** menebak tarif
   (server menolak rute tanpa tarif; harga = keputusan pemilik).
6. **Dokumen SSOT diperbarui:** `docs/05_NAVIGATION_MAP.md` §1a (struktur header publik) ·
   `docs/04_API_CONTRACT.md` (3 endpoint baru) · `memory/INVARIANTS.md` (INV-BOOK-02 diperluas) ·
   `memory/BUG_REGISTRY.md` (BUG-0120) · `memory/SESSION_LOG.md` · `plan.md` (Fase 5 & 6).

---

## 2b) Yang Dikerjakan Sesi Sebelumnya (BOOKING-V1, 2026-08-12)

**Titik masuk:** `/app` kosong (pod baru) → di-restore dari `github.com/wajauhmawa/travel`,
`bash scripts/bootstrap.sh --seed`, lalu **verifikasi dulu** sebelum menyentuh kode.

**Pertanyaan user:** sesi sebelumnya berhenti tepat setelah `/booking` menampilkan
"**Tidak ada unit bebas di tanggal itu**". **Hasil verifikasi: itu BUKAN bug.** Data seed sengaja
mengisi 10–17 Agu 2026 (BK-0003 & BK-0004 memakai V-01/V-02; V-03 dalam perawatan 11–14 Agu), jadi
untuk 12–14 Agu jawaban yang BENAR memang "penuh" — lengkap dengan alasan per unit. Dengan jendela
bebas (25–27 Agu) muncul 4 unit dan pesanan **BK-0016** dibuat: status `hold`, countdown DP 2 jam,
rekening, form unggah bukti. Karena itu **armada demo TIDAK ditambah** (keputusan user).

**Lima bug NYATA yang ditemukan lewat pengujian, bukan dugaan** (detail: `memory/BUG_REGISTRY.md`):
- **BUG-0114** — SEMUA field teks tanpa `max_length` (389 dari 406). Guardrail adversarial sudah
  lama mengirim `"A"×60000` tetapi **hanya menuntut "bukan 5xx"**, jadi nilai raksasa itu
  TERSIMPAN: `customers.name` 60.000 karakter → satu baris **merusak tata letak tabel Booking ERP**
  (kolom lain terdorong keluar layar) dan akan merusak PDF invoice + payload WhatsApp (batas 4096).
  → 170 field dibatasi (codemod AST `scripts/_codemod_string_bounds.py`), `DataTable` memotong teks
  ekstrem + tooltip, guardrail **INV-STR-01** menuntut **penolakan 4xx**.
- **BUG-0115** — unit uji **"Smoke Vehicle"** milik `mutation_smoke.py` **tayang & bisa dipesan**
  di `/booking`, karena `publishable_filter()` menganggap `publish_to_web` KOSONG = boleh dijual.
  → field itu kini wajib `True` EKSPLISIT (data lama diselaraskan `migrate_booking_v1.py`), smoke
  membuat unitnya `publish_to_web: False` + membersihkan artefaknya sendiri.
- **BUG-0116** — `mutation_smoke` berubah jadi **SKIP palsu** (409 duplikat dari sisa jalan
  sebelumnya) → alur TULIS tak pernah diuji padahal gate hijau. → `presweep()` + `cleanup()`,
  sekarang 5 cek jalan, **SKIP 0**.
- **BUG-0117** — ringkasan wizard memajang **`- → -`** saat asal/tujuan (opsional) kosong, dan
  daftar tipe unit hilang tanpa penjelasan bila API gagal (ini yang membuat `ux_audit --strict`
  MERAH, aturan E2). → baris hanya dirender bila ada isinya; state degradasi jujur ditambahkan.
- **BUG-0119** — **8 permukaan BACA bocor ke `marketing_admin`** (booking + availability + detail,
  armada, sopir, perawatan, GPS, penawaran, ruang kerja sopir): endpoint memakai
  `Depends(get_current_user)` saja. Ditemukan testing agent, diperluas oleh audit baru
  `scripts/audit_rbac_sections.py`. → semua dipagari `require_section(...)`; `quotations` dipindah
  dari section `crm` ke `quotations`; **INV-RBAC-06 lapis D** kini menguji matriks penuh
  (27 section × 4 peran, 155 cek) dan MEMAKSA setiap section baru punya probe.

**Satu regresi yang SAYA sendiri buat & sudah diperbaiki — dicatat jujur:** **BUG-0118**, perbaikan
BUG-0117 menghitung `tripLabel` di badan render dengan `search.origin` padahal `search` null sampai
config termuat → **seluruh halaman `/booking` blank**. Ditemukan testing agent ronde 1. Diperbaiki
dengan optional chaining. **Jebakan lingkungan:** setelah fix, halaman MASIH blank karena HMR
menyajikan bundle lama (`webpack compiled successfully` tetap muncul) → `sudo supervisorctl restart
frontend`. Jebakan yang sama sudah pernah tercatat untuk `BookingRequest.jsx` (§E28b).

**Fase 3 (guardrail) & Fase 4 (docs) `plan.md` ditutup:** `INV-PRICE-01` + `INV-BOOK-02` +
`INV-STR-01` + `selftest_booking_guards.py` (5 mutasi, semua MERAH saat disuntik) ter-wire di
`gate.sh` & terdaftar di `INVARIANTS.md`; `INV-META-01` diperluas mendukung self-test 1:N (`COVERS`);
`verify_contract.CANONICAL_COLLECTIONS` dilengkapi (0 koleksi "tidak dikenal"); docs
`03_DATA_MODEL` (§6 + `### payment_proofs` + `### transfer_routes`), `04_API_CONTRACT` (§5, 4 tabel +
contoh respons), `05_NAVIGATION_MAP` (rute publik `/booking*` + panel bukti bayar + panel Pengaturan)
diperbarui; `DELIVERY_MANIFEST` fase **BOOKING-V1** = **P0 33/33 (100%)**, 0 orphan;
`memory/test_credentials.md` diisi lengkap (sebelumnya kosong).

**Verifikasi akhir:** POC **74/74** · `gate.sh` **HIJAU 37/37 (0 FAIL, 0 SKIP)** ·
`ux_audit --strict` **0 ERROR 0 WARN** · `verify_delivery` **33/33** ·
`audit_rbac_sections.py` "sesuai matriks" · testing agent `iteration_81` **0 isu**.

---

## 2c) Status Sebelumnya (Snapshot 2026-08-11, Fase F8) — arsip

| Aspek | Status |
|-------|--------|
| Testing agent terakhir | `test_reports/iteration_76.json` → backend **100% (32/32)**, frontend **93,3% (14/15)**, **0 isu** (satu-satunya kegagalan = permintaan analitik Cloudflare `/cdn-cgi/rum`, bukan aplikasi) |
| Fase berjalan | **FASE F SELESAI s/d F8.** Berikutnya: **GA4 Measurement Protocol server-side**, lalu uji beban konkuren |
| Guardrail baru sesi ini | **INV-LP-02** (template landing ↔ skema blok selaras) & **INV-MEDIA-02** (URL media benar + anti path-traversal) — keduanya self-test MERAH↔HIJAU |
| Integrasi platform | **MASIH MOCK** — Meta Ads/CAPI, Google Ads/Data Manager, WhatsApp Cloud. Semua LIVE-READY: cukup tempel kunci di `/app/integrations`, tak perlu deploy ulang |
| env baru yang WAJIB ada | `SETTINGS_ENCRYPTION_KEY_B64` (vault kredensial). **`EMERGENT_LLM_KEY` kini OPSIONAL**: media default ke disk lokal (`MEDIA_BACKEND=local`); kunci hanya perlu bila ingin `MEDIA_BACKEND=objstore` |

## 3b) Ronde F8b — GA4 server-side + SEO halaman iklan + alur Ads↔Landing Page + Pemulih Media

**GA4 Measurement Protocol** jadi provider KETIGA outbox konversi (`services/ga4.py`). Sesuai playbook
resmi: `client_id` STABIL per identitas (`ga4_identities`, bukan acak per event), `session_id` positif +
`engagement_time_msec`, `timestamp_micros` (mikro-detik), consent GRANTED/DENIED dari catatan consent,
nama event rekomendasi (`generate_lead`/`purchase`) + `transaction_id` untuk cegah konversi ganda,
batas 130 kB ditolak lokal. **Jebakan yang ditangani:** endpoint produksi GA4 membalas **204 walau
payload salah** — karena itu disediakan `validate()` ke `/debug/mp/collect`. Tanpa kunci → `skipped`
berALASAN. Kunci `ga4_measurement_id` + `ga4_api_secret` sudah ada di vault Google.

**SEO halaman iklan:** default **`noindex`** (bisa diubah per halaman) supaya halaman berbayar tidak
berebut kata kunci dengan halaman SEO utama; canonical menunjuk alamat TANPA parameter iklan (kalau
tidak, setiap variasi utm/gclid dianggap URL duplikat); JSON-LD `Service`; halaman yang sengaja
di-index otomatis masuk `/api/sitemap.xml`.

**Alur Ads↔Landing Page:** `GET /api/landing/ad-targets` + `GET /api/landing/pages/{id}/readiness`
(skor 0-100 berbobot dampak biaya-per-lead), pemilih **"Halaman tujuan iklan"** di pembuat kampanye
(menampilkan TERBIT/DRAF + skor, memperingatkan bila draf), **UTM otomatis** per platform + "Salin URL
iklan", dan tombol **"Pakai halaman ini untuk iklan"** di editor LP.

**Pemulih Media:** `readiness.missing_media` benar-benar MEMBACA berkas di penyimpanan, jadi gambar
yang dokumennya ada tetapi berkasnya hilang terdeteksi + tombol menuju Media Library.

**Verifikasi:** `python scripts/test_core_ga4_ads.py` **28/28** · gate HIJAU · ux_audit 0 ERROR.

**BELUM dikerjakan (ronde berikutnya):** Media Manager v2 — folder, unduh, ganti berkas, pilih
banyak/hapus massal, crop di browser, DAN penyatuan picker ke CMS lama (`/api/uploads/cms`) beserta
migrasi aset lama. Ini disepakati user tetapi sengaja dipisah agar tidak setengah jadi.

---

## 3) Yang Dikerjakan di Sesi Ini (F8) — Landing Page Builder + Media Library

**Konteks masuk:** `/app` kosong (pod baru) → di-restore dari GitHub, `pip install`, `yarn install`,
`python scripts/seed_data.py`, gate diverifikasi HIJAU SEBELUM menyentuh kode apa pun.

**Permintaan user:** selesaikan F8 penuh; media **lokal dulu** tetapi "media picker harus jelas,
viewer harus baik, UI/UX bagus dan mudah dipakai"; kredensial Meta/Google/WhatsApp **tetap MOCK**;
tambahkan **form lead di LP → CRM + konversi**, **A/B testing varian**, dan **duplikat halaman +
galeri template lebih banyak**.

**Dua bug NYATA yang ditemukan lewat pengujian, bukan dugaan** (detail: `memory/BUG_REGISTRY.md`):
- **BUG-0111** — `POST /api/landing/pages` template `armada-cepat` balas **HTTP 500**
  (`trust_badges.items` berupa STRING sementara validator memanggil `.get()`), dan props template
  yang salah nama (`success_text`/`deadline`/`cta`) **dibuang senyap** sehingga pesan sukses, tenggat
  promo, dan tombol banner hilang dari halaman yang sudah tayang. → `validate_blocks` kini dipagari
  try/except per blok + seluruh nama props diselaraskan + guardrail **INV-LP-02**.
- **BUG-0112** — URL media disimpan `/api/media/{id}` padahal rute nyata `/api/public/media/{id}`
  → **SEMUA** foto/video halaman iklan 404 tanpa satu pun error backend. → URL satu pintu lewat
  `media_url()` + guardrail **INV-MEDIA-02**.

**Media Library (LOKAL sebagai default).** `services/media_store.py` sekarang punya dua backend:
`local` (DEFAULT, tanpa kredensial apa pun; berkas di `backend/uploads/media/`, nama file UUID,
pagar anti path-traversal `_local_abs()`, thumbnail JPEG `?thumb=1`, dimensi gambar via PIL) dan
`objstore` (bila `MEDIA_BACKEND=objstore` + `EMERGENT_LLM_KEY`). `storage_backend` disimpan
PER-ASET sehingga aset lama tetap terbaca setelah backend default diganti — jalur migrasi tanpa
migrasi skema. UI: modal dua kolom (grid thumbnail + penampil besar dengan dimensi/ukuran/pengunggah/
tanggal, edit teks alternatif, salin URL, hapus, unggah banyak lewat TOMBOL bukan seret-lepas).

> ⚠️ **Batas jujur penyimpanan lokal:** berkas biner di-gitignore. Pada pod BARU hasil clone bersih,
> dokumen `media_assets` tetap ada di MongoDB tetapi berkasnya tidak → gambar 404. Pemulihan: unggah
> ulang lewat Media Library, atau pindah ke `MEDIA_BACKEND=objstore`.

**Halaman iklan publik `/lp/:slug` dibuat FUNGSIONAL.** Sebelumnya seluruh blok konversi hanya
placeholder (kotak abu-abu bertuliskan nama field, tombol yang justru pindah halaman). Sekarang:
formulir lead nyata (validasi + kirim di tempat + state sukses), kalkulator memanggil
`/api/public/trip-estimate` (tarif ERP yang sama dengan sales), testimoni dari CMS, grid armada/
destinasi memakai kontrak field yang BENAR (`photos[]`/`price_from` — renderer lama memakai
`photo_url`/`day_rate` yang tidak pernah ada sehingga gambar & harga selalu kosong), hitung mundur
berdetak, galeri punya penampil layar penuh. Header situs **disederhanakan** di `/lp/*` (8 tautan menu
= 8 jalan keluar dari formulir yang tetap dibayar penuh), tetapi rute tetap di dalam `PublicLayout`
supaya inisialisasi pixel, banner consent, dan widget chat tidak ikut hilang.

**Lead LP → CRM → konversi.** `POST /api/public/landing/{slug}/lead` menyimpan lead
`source=landing_page` + atribusi (first/last touch, `channel` dari gclid/fbclid, `click_ids` termasuk
`ctwa_clid` yang TIDAK di-hash) + `landing_slug`/`landing_variant` + consent, lalu `emit lead.created`
→ outbox konversi (satu pintu `services.events.emit`). **Idempoten di tingkat database** lewat unique
index `leads.lp_dedupe_key`: 6 submit paralel = 1 lead. Rate limit sengaja 30/menit/IP karena
pengunjung seluler Indonesia berbagi IP lewat CGNAT operator — ambang ketat justru menolak lead SAH.
CRM: badge "Iklan LP" di kanban + chip `/lp/{slug} · versi A|B` di panel Atribusi Akuisisi.

**Uji A/B.** Varian dipilih **deterministik** dari id pengunjung (`vid`, localStorage) sehingga refresh
tidak mengubah tampilan — tanpa ini angka tampilan-vs-lead per varian tidak bisa dipercaya. Sebaran
2000 pengunjung → 973/1027 (bobot 50/50). Statistik disimpan sebagai **agregat harian per varian**
(`landing_stats`, `$inc` upsert = idempoten). Pemenang **sengaja konservatif**: setiap varian wajib
mencapai `min_sample` tampilan DAN selisih relatif harus >10%, kalau tidak laporan berkata "belum
cukup data" / "beda tipis" — pengumuman prematur akan memindahkan anggaran iklan berdasarkan kebetulan.

**Lainnya:** duplikat halaman (draf baru, slug unik, statistik TIDAK dibawa agar angka iklan tidak
tercampur), galeri template **4 → 8** (armada: konversi/klik-ke-WA/antar-jemput bandara/kontrak
korporat; destinasi: paket wisata/promo terbatas/study tour sekolah/liburan keluarga), daftar halaman
menampilkan tampilan-klik-lead per halaman, panel SEO dengan pratinjau tautan + hitung karakter
(judul SEO WAJIB untuk terbit), penanda "Belum tersimpan", dan pratinjau desktop/ponsel.

**Perbaikan guardrail sebagai efek samping:** `verify_numeric_bounds.py` (INV-NUM-01) dulu hanya
memindai `backend/schemas.py`; begitu kontrak dipecah ke `schemas_landing.py` penjaga itu akan BUTA
tanpa peringatan. Sekarang memindai SEMUA `backend/schemas*.py`.

**Verifikasi:** POC `scripts/test_core_lp_f8.py` **84/84** · `bash scripts/gate.sh` **HIJAU 0 FAIL
0 SKIP** · `ux_audit --strict` **0 ERROR** · `validate_compliance` **FAIL 0** · testing agent
`test_reports/iteration_76.json` backend **32/32**, frontend **14/15**, **0 isu**.

---

## 3) Yang Dikerjakan di Sesi Ini (F3–F7) — Integrasi Meta Ads + Marketing End-to-End

**Permintaan user:** "saya lupa menambahkan integrasi meta ads, kaitkan dengan google ads dan meta
pixel lalu kembangkan; lihat CRM & marketing saat ini, buatkan analisis fitur marketing end-to-end
beserta integrasinya." Keputusan user: belum ada kredensial (harus live-ready mode kering), ERP boleh
MENULIS penuh ke platform, prioritas konversi → dashboard ROAS → akuisisi lead, jenis iklan Lead Ads +
web + Klik-ke-WhatsApp, audiens/Lookalike YA.

**Dokumen analisis:** `docs/18_MARKETING_END_TO_END_ANALYSIS.md` (SSOT analisis marketing).

### BUG-0109 · Rantai konversi terputus (ditemukan lewat audit, bukan laporan user)
`services/conversions.py` sudah lengkap & lulus POC di F2, tetapi `rg conversions backend` menunjukkan
HANYA `routers/marketing.py` yang mengimpornya → **booking dikonfirmasi & DP masuk tidak pernah
dilaporkan ke Meta/Google**. Ini gagal senyap paling mahal: algoritma iklan hanya belajar dari "form
terkirim" sehingga mengoptimalkan pengisi form, bukan pembeli. **Fix:** `services/conversion_hooks.py`
+ satu titik pemanggilan di `services/events.emit` + pekerja retry di scheduler. **Dikawal
INV-CONV-01.**

### BUG-0110 · Payload Google Data Manager memakai field usang
`operatingAccount.product` (harus `accountType`), `consent: "CONSENT_GRANTED"` (harus `GRANTED`),
tanpa `encoding: "HEX"`, tanpa `destinationReferences` → **semua kiriman akan ditolak** begitu user
menempel kunci. Meta juga masih v25.0 (kini v26.0) dan tanpa `appsecret_proof`. Ditemukan saat
mencocokkan kode dengan playbook resmi terbaru.

### Modul baru
`services/{pii,ads_safety,meta_ads,google_ads,ads_metrics,audiences,lead_ads,conversion_hooks,integrations}.py`,
`routers/{ads,ads_manage}.py`, halaman `/app/ads` (5 tab) + 6 komponen di
`components/app/ads/`, `scripts/test_core_ads_f3.py`, 4 guardrail baru.

### Pengaman belanja (karena ERP kini boleh membuat kampanye)
Semua tulis ke platform lewat `services/ads_safety.py`: mode `validate` → `validate_only`;
mode `publish` → status **DIPAKSA PAUSED**; aktivasi/ubah budget wajib **ketik ulang nama objek**
(`ConfirmNameDialog`) + plafon budget harian ditegakkan ERP. Router iklan DILARANG memanggil
httpx/Graph/Google API langsung (dijaga INV-ADS-01).

### Klik-ke-WhatsApp (CTWA) — jalur khas travel Indonesia
`_parse_meta_envelope` dulu membuang objek `referral`. Kini `ctwa_clid` + `source_id`(=ad_id)
disimpan **tanpa hash** → lead ber-atribusi iklan + konversi `action_source=business_messaging`,
`messaging_channel=whatsapp`. `verify_secret_exposure.py` punya cek TERBALIK: bila suatu saat
`ctwa_clid` di-hash → gate MERAH (karena atribusi akan gagal senyap).

---

## 3) Yang Dikerjakan di Sesi Ini (E28) — semua TERVERIFIKASI

**Titik masuk:** repo di-restore dari `github.com/janahababaja/travel` (folder `/app` semula template kosong).
`test_reports/iteration_72.json` ternyata SUDAH ada → ronde 2 frontend E27 sebenarnya selesai
(27/28) dan agent sebelumnya berhenti tepat sebelum menindaklanjuti **1 temuan CRITICAL**.

### BUG-0107 · RBAC-CAL-01 — driver bisa membuka Kalender Keberangkatan (UI **dan** API)
Bukan sekadar "RoleGuard lupa dipasang" (route-nya sudah dibungkus). **Tiga lapis gagal bersamaan:**
1. `ROLE_MENU_ALLOWLIST.driver` memuat `"calendar"` → `canAccess()` meloloskan guard.
2. `backend/permissions_config.SECTION_ACCESS` **tidak punya** section `calendar` → `require_section`
   tak mungkin dipakai → penulis endpoint memakai `get_current_user` saja → driver **HTTP 200**
   (terbukti curl) pada `/api/departures/attention`, `/api/bookings/calendar`, `/api/bookings/calendar/export`.
3. Guardrail `INV-RBAC-03` memakai daftar `FORBIDDEN` **hardcoded** → modul yang lahir setelah daftar
   itu ditulis tak pernah disebut → hijau palsu.

**Fix:** section `calendar {owner, ops_admin}` (+ `driver-workspace`, `quotations`, `inbox`, alias
`auditlog→audit`); `Depends(require_section("calendar"))` di `routers/departures.py` & 2 endpoint
kalender `routers/bookings.py`; `"calendar"` dicabut dari allowlist driver; SSOT
`docs/05_NAVIGATION_MAP.md` §3 kini punya baris eksplisit + catatan "penegakan WAJIB 3 lapis".

### BUG-0108 · RBAC-SCOPE — driver melihat SELURUH booking & daftar sopir (ditemukan sendiri)
`require_section` hanya menjaga **pintu modul**; query tanpa filter tetap mengembalikan semua baris.
Driver melihat 8/8 booking (termasuk `customer_name`, `total_amount`, `paid_amount`) & semua sopir +
telepon, padahal SSOT §3 menulis "👁️ trip miliknya" / "👁️ profil sendiri".
**Fix:** `backend/services/rbac_scope.py` (SSOT pemetaan user→driver + penyaring, **fail-closed**)
dipakai di `list_bookings`, `get_booking`, `list_drivers`, `get_driver`, `driver_performance`;
`routers/driver.py::_resolve_driver` didelegasikan ke SSOT yang sama.
**Hasil:** driver 3 booking / 1 profil; `/api/driver/*` tetap 200 (tidak over-block).

### Drift 2 penjaga RBAC frontend (ditemukan saat pra-cek browser)
Setelah lapis 1–3 beres, driver memang diblokir tapi dialihkan ke `/app/dashboard` **tanpa toast** —
ternyata `AppShell.jsx` punya guard RBAC terpusat berbasis path yang jalan **sebelum** `RoleGuard`.
**Fix:** perilaku penolakan disatukan di `frontend/src/lib/accessControl.js`
(`isDenied`/`roleHome`/`useDeniedNotice`); keduanya memakainya. Driver kini dialihkan ke
`/app/driver-workspace` + toast **"Akses ditolak — Modul ini tidak tersedia untuk peran akun Anda."**

### Backlog P1 lama: diverifikasi TUTUP (bukan diasumsikan)- **Warning Recharts `width(-1)/height(-1)`**: **tidak tereproduksi** (konsol bersih di
  `/app/dashboard` Ringkasan+BI Cockpit, `/app/reports`, `/app/finance` 6 tab, `/app/crm` 4 tab —
  dikonfirmasi ulang oleh testing agent F5). Anti-regresi: aturan **E4** di `scripts/ux_audit.py`
  (ERROR bila `<ResponsiveContainer>` tanpa `initialDimension`).
- **Duplikasi blok deklarasi `gate.sh` baris 42–48**: sudah TIDAK ADA (`BACKEND_UP`/`AUTH_READY`
  masing-masing 1×, `bash -n` lolos). Catatan HANDOFF lama sudah usang.

### Guardrail baru (semua self-test-proven MERAH↔HIJAU)
| ID | Jenis | Mencegah |
|----|-------|----------|
| **INV-RBAC-04** | statik | drift matriks: setiap section FE wajib ada di `SECTION_ACCESS` **dan** himpunan perannya identik (2 arah). Saat dibuat langsung menemukan 2 celah nyata: `inbox`, `quotations`. |
| **INV-RBAC-05** | statik | endpoint "milik-sendiri" wajib memanggil `await scope_*`/`can_view_*` (regex pemanggilan; versi lemah `needle in src` sempat lolos palsu karena baris import). |
| **INV-RBAC-06** | **runtime** | perilaku: driver 403 di 3 endpoint kalender, owner 200, cakupan data menyempit, workspace driver tetap 200. Self-test: `Depends` ditukar → MERAH (gate statik tetap hijau — inilah celah yang ditutup). |
| `ux_audit` **E4** | statik | kembalinya warning recharts `-1`. |
| Anchor INV-RBAC-01 | statik | `AppShell.jsx` & `RoleGuard.jsx` wajib memakai `@/lib/accessControl` (cegah drift 2 penjaga terulang). |

---

## 3b) Fase E28b — "Rapikan formulir": 4 dropdown native → `SelectField` (permintaan user)

`ux_audit` W2 menandai 4 `<select>` native di 3 file. Semua diganti komponen baru
**`frontend/src/components/shared/SelectField.jsx`** (pembungkus tipis shadcn/Radix Select):

| testid | lokasi | isi |
|--------|--------|-----|
| `dc-filter-status` | Kalender Keberangkatan | 7 status |
| `dc-filter-vehicle` | Kalender Keberangkatan | semua armada + per unit |
| `dc-assign-select` | panel detail (tugaskan sopir) | "— Tanpa sopir —" + daftar sopir |
| `br-vehicle-type` | form publik `/booking` | 5 preferensi unit |

**Dua jebakan yang ditangani di satu tempat (alasan komponen ini ada):**
1. Radix **melarang** `SelectItem` bernilai string kosong → SelectField memetakan opsi
   "tanpa pilihan" ke sentinel internal lalu mengembalikan `""` ke pemanggil (kontrak state
   halaman tidak berubah).
2. Setiap opsi otomatis diberi `data-testid` `<testId>-opt-<slug>` agar otomasi UI stabil.

> ⚠️ **Cara uji berubah:** elemen tersebut sekarang `<button>` trigger — `select_option()` TIDAK
> berlaku. Pola: **klik trigger → klik `<testId>-opt-<slug>`** (opsi kosong = `-opt-none`).
> Sudah dicatat di `docs/06_UIUX_STANDARDS.md`.

Tambahan: panel Ekspor kalender kini bisa ditutup dengan **Escape** (+ `role="dialog"`,
`aria-label`, `aria-expanded`) — tindak lanjut temuan LOW iter-74. Aturan `ux_audit` W2 juga
diperbaiki agar tidak menandai baris **komentar** yang menyebut elemen native (temuan palsu).

**Verifikasi:** `iteration_74.json` **100% (38/38)** — termasuk pengukuran konsistensi visual
(tinggi 36px & font 13px sama dengan input tetangga) dan form publik menyimpan
`requested_vehicle_type='elf'`. Jalur SUKSES tugaskan sopir dibuktikan main agent
(BK-0004 → "Driver Satu"), lalu data di-reseed. `gate.sh` tetap **HIJAU 23/23**.

> 🐞 **Jebakan lingkungan (catat!):** setelah mengubah `features/public/BookingRequest.jsx`,
> HMR dev-server sempat **tidak** merekompilasi modul itu (DOM masih `<select>` lama walau bundle
> sudah berisi kode baru). Solusi: `sudo supervisorctl restart frontend` lalu tunggu
> `webpack compiled successfully`. Jangan buru-buru menyimpulkan kode salah.

---

## 4) Daftar Issue Terbuka

| # | Issue | Prioritas | Catatan |
|---|-------|-----------|---------|
| ~~0~~ | ~~**Navbar publik terlalu ramai** (permintaan user 2026-08-12)~~ | ✅ **SELESAI 2026-08-12** | dieksekusi sesuai rekomendasi + lampu hijau user: 5 menu + 1 aksi utama, utilitas ke bar pengumuman, Tentang/Kontak ke footer, drawer 2 grup, section beranda "3 langkah", chip "Lanjutkan pesanan". Peta `data-testid` di **§0.1**; SSOT `docs/05_NAVIGATION_MAP.md` §1a |
| ~~0b~~ | ~~Sisa verifikasi UI BOOKING-V1 (8 user story)~~ | ✅ **TUNTAS 2026-08-12** | penutupnya **STORY H** (toggle "Tayang di web"). Rincian di **§0.2** |
| ~~0c~~ | ~~Daftar promo aktif bisa diklik di wizard · laporan "hold hangus" · rute bandara + tarif per tipe unit~~ | ✅ **SELESAI 2026-08-12** | 3 fitur backlog pilihan user (BOOKING-V2). Rujukan cepat di **§0.3**; `iteration_84.json` 0 bug |
| ~~0d~~ | ~~**Data uji guardrail/smoke/POC bocor ke ERP** — customer bernama "aaaaaaaa…" (keluhan user 2026-08-13)~~ | ✅ **SELESAI 2026-08-13** | **BUG-0127**. 157 dokumen sampah per satu kali `gate.sh` (customer 60.000 karakter, audit 60.016 karakter, percakapan Inbox "Penjaga INV-*"/"Smoke Customer", 34 notifikasi hantu, 35/48 event, lead & penawaran ber-NUL, segmen "AdvSeg", aset `guard-media-*`, `conversion_events` menumpuk permanen). Fix: mesin bersih-bersih bersama `purge_guard_artifacts()` di `_common.py` + 11 skrip penulis memanggilnya di `finally` + `_clip()` di `services/audit.py` + `conversion_events` masuk reset seed. Guardrail baru **INV-CLEAN-01** (`verify_no_test_pollution.py` + self-test 5 mutasi) di-wire PALING AKHIR di gate. Alat: `scripts/purge_test_pollution.py`, `scripts/db_snapshot.py`. Bukti: gate **HIJAU 42/42** + DB **0 artefak sesudah gate** + testing agent iter-89/90/91 |
| ~~0e~~ | ~~Verifikasi alur end-to-end (permintaan user 2026-08-13)~~ | ✅ **SELESAI 2026-08-13** | `testing_agent_v3` iter-90 (situs publik 9 halaman · pemesanan online → hold → bukti DP → ops verifikasi → confirmed · keuangan & laporan · 17 modul ERP) + iter-91 (dispatch → keberangkatan → enroute → arrived → driver check-in/out odometer 260 km → trip completed). Semua **100%**, 0 bug |
| 1 | Kredensial nyata Meta Ads / Google Ads / WhatsApp | **P1** | semua LIVE-READY tapi masih **MOCK**. Pengiriman akhir hanya bisa dipastikan via Meta Test Events / GA4 DebugView / akun test Google Ads. Kunci ditempel user sendiri di `/app/integrations` |
| 1f | Halaman promo publik (`/promo` + kartu promo di beranda) | P2 | daftar promo sudah bisa diklik DI DALAM wizard; halaman khusus untuk trafik iklan belum ada |
| 1g | Notifikasi proaktif "hold hangus" ke ops | P2 | laporan + CSV sudah ada; dorongan harian (terutama untuk kasus bukti SUDAH diunggah) belum |
| ~~1b~~ | ~~Landing Page Builder + media library (F8)~~ | ✅ **SELESAI** | editor, render publik `/lp/{slug}`, Media Library lokal, form lead → CRM, A/B, duplikat, 8 template. POC 84/84 + guardrail INV-LP-02 & INV-MEDIA-02 |
| ~~1e~~ | ~~Pemesanan online publik + verifikasi DP ops (BOOKING-V1)~~ | ✅ **SELESAI 2026-08-12** | wizard `/booking`, halaman status + unggah bukti, panel bukti bayar ops (`hold → confirmed`), rute antar-jemput, Pengaturan Alur Booking. POC 74/74 + guardrail INV-PRICE-01/INV-BOOK-02/INV-STR-01 |
| 1c | Berkas media lokal hilang di pod baru | P2 | biner di-gitignore; dokumen `media_assets` tetap ada → gambar 404. Pemulihan: unggah ulang, atau `MEDIA_BACKEND=objstore` + `EMERGENT_LLM_KEY` |
| 1d | GA4 Measurement Protocol server-side | P2 | pekerjaan lanjutan yang direncanakan setelah F8 |
| 2 | Uji beban konkuren tinggi (load testing) | P1 | belum pernah dijalankan |
| 3 | Uji live OSRM / Geocode berkala | P2 | terakhir dilaporkan LIVE OK |
| 4 | 7 WARN kosmetik `validate_compliance` + 3 WARN `ux_audit` (W1 tabular-nums) | P3 | non-blocking, FAIL 0. WARN W2 (native select) sudah 0 sejak E28b |
| 5 | Reschedule-overlap belum diuji eksplisit ronde ini | P3 | tercakup gate `verify_state_machine`/`verify_cross_entity` (PASS) + iter-71 |

Tidak ada issue P0 terbuka.

---

## 5) Alur Verifikasi Wajib (SOP Singkat)

```bash
supervisorctl status                       # 1. services hidup
bash scripts/gate.sh && cat memory/GATE_RECEIPT.md   # 2. WAJIB hijau, 0 SKIP
python scripts/test_core_booking_v1.py     # 2a. POC pemesanan online (inti BOOKING-V1/V2)
python scripts/test_core_lp_f8.py          # 2b. POC F8 (landing page + media + lead + A/B)
python scripts/guardrails/verify_rbac_runtime.py     # 3. cek cepat RBAC perilaku
bash scripts/run_forensics.sh              # 4. deep bug-hunt (opsional/berkala)
```
- Perubahan backend apa pun → panggil `testing_agent_v3` (jangan hanya curl sendiri).
- **JANGAN** hapus/bypass `scripts/guardrails/`. Endpoint baru WAJIB patuh `memory/INVARIANTS.md`.

---

## 6) Aturan WAJIB saat menambah modul/menu ERP baru (pelajaran E28)

Menyentuh **3 tempat + 1 opsional**, kalau tidak gate MERAH:
1. `frontend/src/config/navigationConfig.js` — `PAGE_META` + `ROLE_MENU_ALLOWLIST` + `<RoleGuard section="...">` di `App.js`.
2. `backend/permissions_config.py` — `SECTION_ACCESS["<section>"]` (+ `SECTION_ALIASES` bila ejaan FE≠BE).
3. Router-nya — `Depends(require_section("<section>"))`.
4. Bila menampilkan data "milik-sendiri" → penyaring di `backend/services/rbac_scope.py` + daftar di `SCOPE_REQUIREMENTS` (`verify_rbac_guards.py`).

---

## 7) File Referensi Kunci

| File | Peran |
|------|-------|
| `memory/INVARIANTS.md` | SSOT invariant + catatan self-test (BACA DULU) |
| `memory/BUG_REGISTRY.md` | riwayat bug + root cause (**BUG-0120** = sesi ini) |
| `memory/GATE_RECEIPT.md` | bukti gate terakhir (jangan edit manual) |
| `test_result.md` | protokol komunikasi dgn testing agent + riwayat task |
| `test_reports/iteration_84.json` · `iteration_83.json` | hasil verifikasi BOOKING-V2 (3 fitur baru) & navbar+STORY H |
| `docs/05_NAVIGATION_MAP.md` | SSOT matriks RBAC per section **+ §1a struktur header publik** |
| `docs/04_API_CONTRACT.md` | SSOT kontrak API (termasuk `POST /public/booking/promos`, `GET /reports/hold-expired`) |
| `backend/permissions_config.py` · `backend/services/rbac_scope.py` | SSOT RBAC pintu modul + cakupan data |
| `frontend/src/lib/accessControl.js` | SSOT perilaku penolakan RBAC di FE |
| `frontend/src/components/public/PublicLayout.jsx` | header/navbar publik + bar pengumuman + drawer (hasil §0.1) |
| `frontend/src/components/public/ResumeBookingChip.jsx` | chip "Lanjutkan pesanan" (jaring pengaman unggah bukti DP) |
| `frontend/src/components/public/booking/PromoPicker.jsx` | daftar promo bisa diklik (kelayakan dari server) |
| `backend/services/hold_report.py` | laporan "Hold Hangus" + alasan tiap angkanya |
| `scripts/gate.sh` | orkestrator gate (**40**) |
| `scripts/guardrails/verify_theme_contrast.py` | INV-THEME-01 — kontras & pewarisan tema (kaca, portal, offset mengapung) |
| `frontend/src/components/public/CtaBand.jsx` | pola WAJIB untuk semua panel ajakan-bertindak (pengganti gradient token yang invalid) |
| `frontend/src/context/ThemeContext.js` | pemasang `data-surface`/`data-theme` di `<html>` (agar konten Radix yang di-portal ikut bertema) |
| `docs/06_UIUX_STANDARDS.md` §6 | kontrak keterbacaan di atas kaca & foto (eksekutabel) |

---

## 8) Peringatan untuk Agent Berikutnya

1. **Respons dalam Bahasa Indonesia.**
2. **Jangan** ubah `frontend/.env` (`REACT_APP_BACKEND_URL`) atau `backend/.env` (`MONGO_URL`).
3. **Jangan** hapus/bypass guardrail; endpoint baru → patuh `INVARIANTS.md`.
4. **Jangan** klaim selesai tanpa receipt HIJAU + runtime gate benar-benar jalan (bukan SKIP).
5. Kalau `/app` kosong (pod baru), **restore dulu** dari GitHub (`github.com/yaiankao/travel (repo terkini; riwayat lama: wajauhmawa/travel)`)
   lalu jalankan `bash scripts/bootstrap.sh --seed` (pip + yarn PARALEL, restart, health check, seed).
   File `.env` di repo di-gitignore — JANGAN timpa `.env` milik environment; cukup TAMBAHKAN
   `SETTINGS_ENCRYPTION_KEY_B64` (32 byte base64) bila belum ada, karena vault kredensial
   integrasi menolak menyimpan tanpa kunci itu (dan tidak akan pernah jatuh ke plaintext).
6. WhatsApp real-send masih **MOCK**.
7. Waspada **daftar-larangan manual** (seperti `FORBIDDEN` lama): selalu tertinggal dari pertumbuhan
   kode. Turunkan penjaga dari SSOT yang benar-benar dipakai runtime.
8. **Sebelum menyentuh CSS/tema, baca §0.5 + `docs/06_UIUX_STANDARDS.md` §6.** Tiga jebakan yang
   sudah berbayar mahal: (a) token tema = **triplet HSL**, jadi `to-[color:var(--primary)]` /
   `bg-[var(--card)]` INVALID dan membuang seluruh deklarasi; (b) `var()` di dalam **custom
   property** disubstitusi di elemen deklarasi — menyusun token tema di `:root` membuat nilainya
   membeku pada tema terang; (c) konten Radix **di-portal ke `<body>`** sehingga tema harus ada di
   `<html>`, dan `.dark X` tidak cocok untuk `<html>` itu sendiri (butuh kembaran `X.dark`).
9. **Cara menguji UI dengan benar** (kesalahan ini menghasilkan laporan bug palsu): panel yang
   latarnya `background-image` akan melaporkan `backgroundColor: rgba(0,0,0,0)` — periksa
   `backgroundImage`. Di Playwright **async**, `page.set_viewport_size()` dan `page.inner_text()`
   WAJIB di-`await` (tanpa `await`, viewport tidak berubah dan pengukuran mobile jadi palsu).
   Semua `Select` adalah Radix: klik trigger → klik opsi ber-`data-testid`, bukan `select_option`.
10. **Brand = `RahazaTrans`.** Kunci `localStorage` & nama `@keyframes` (`rahaza_*`,
    `rahaza-shimmer`) SENGAJA tidak diubah (internal; menggantinya hanya memutus sesi tamu).
