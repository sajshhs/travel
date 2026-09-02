# PRD — RahazaTrans ERP (lanjutan repo nowfersiadeew/rahaza)

## Problem Statement Asli (sesi 2026-08-29)
Lanjutan development ERP existing (FARM stack) dengan disiplin guardrail (gate wajib HIJAU penuh).
5 keluhan: (1) booking manual ERP tidak bekerja benar; (2) harga armada diatur di 2 halaman
berbeda tanpa master; (3) notif merah "image hilang" palsu; (4) UX & logika driver cacat
(aksi jemput buruk, tak ada upcoming trips); (5) banyak field custom-input yang seharusnya
relasi antar-collection (pelanggaran SSOT). Disiplin: repro dulu → fix minimal → gate HIJAU →
testing_agent 0 bug. Bahasa kerja & UI: Indonesia.

## Arsitektur
- FastAPI (port 8001, prefix /api) · React + shadcn (port 3000) · MongoDB (MONGO_URL/DB_NAME)
- Guardrail: `bash scripts/gate.sh` — kini **46 gate PASS, 0 FAIL, 0 SKIP** (receipt: memory/GATE_RECEIPT.md)
- Seed demo: `bash scripts/seed_reset.sh`; kredensial: memory/test_credentials.md (semua demo12345)
- SETTINGS_ENCRYPTION_KEY_B64 baru digenerate (data seed, tanpa data lama terenkripsi)

## Sesi 2026-06 (E1) — RESTORE REPO + AKTIVASI OPENWA, TUNTAS
Repo di-clone ulang dari `awasakansabasa/travel` ke /app (env pod baru). Yang dikerjakan:
- backend/.env dibuat ulang: MONGO_URL, DB_NAME, OPENWA_API_KEY, OPENWA_BASE_URL,
  PUBLIC_SITE_URL, SETTINGS_ENCRYPTION_KEY_B64 (baru digenerate)
- deps: pip install (+reportlab/openpyxl yang hilang, requirements.txt di-freeze),
  yarn frontend, `yarn install --ignore-engines` sidecar /app/openwa (wa-automate v5 alpha.8)
- DB di-seed (`python scripts/seed_data.py`), memory/test_credentials.md diisi
- Provider WA di-set `openwa`; sidecar auto-spawn OK, QR tergenerate & ter-render di
  /app/settings (panel wa-openwa-box). Tinggal USER SCAN QR (WhatsApp → Perangkat Tertaut)
- Gate `bash scripts/gate.sh` HIJAU penuh 0 FAIL 0 SKIP; testing_agent iteration_106 0 bug
  (backend 10/10, frontend 100%)
Backlog minor lama (belum dikerjakan): DELETE/edit broadcast draft; heading halaman CRM tak ikut tab aktif.

## User Personas
Owner (kontrol penuh + Pengaturan/Master Harga), Ops Admin (booking/dispatch), Marketing (CMS), Driver (workspace tugas).

## Yang Diimplementasikan Sesi Ini (2026-08-29) — BUG-0132..0136
- **RC-A (P0)**: `/api/pricing/quote` kini memakai `resolve_day_rate` (tarif unit > tipe > default)
  → angka "Hitung Otomatis" = angka yang ditagih mesin. Edge teruji: overlap 400, harga 0 auto,
  unit tanpa tarif → tarif tipe.
- **RC-B (P0)**: Master Harga TUNGGAL — panel "Tarif Khusus per Unit" di Pengaturan
  (`GET/PATCH /api/pricing/unit-rates`); `day_rate`/`price_from` dihapus dari jalur tulis armada
  (schemas + router + form FE read-only). Guardrail baru **INV-PRICE-02** (verify_price_master.py).
- **RC-C (P1)**: `media_store.check_file()` tri-state per storage_backend; `/api/media/health`
  mengembalikan missing (merah, terbukti hilang) vs unknown (kuning + alasan). FE MediaBrowser 2 banner.
- **RC-D (P1)**: Driver Workspace v2 — Trip Aktif + Upcoming Trips (hari ini/mendatang, urut jadwal)
  + Riwayat; stepper standby→berangkat jemput(odometer)→penumpang naik(`/trips/{id}/status` on_trip,
  state machine TUNGGAL)→tiba→check-out odometer (jalur checkout SSOT). RBAC driver tetap.
- **RC-E batch 1 (P1)**: `bookings.destination` = relasi master `destinations` — validator
  `refs.destination_or_400` (create/group/update, nilai kanonik), selector FE `DestinationSelect`
  (3 dialog), endpoint `GET /api/bookings/destination-options`, migrasi
  `scripts/migrate_booking_destinations.py` (master ops status draft — tak tayang di web),
  seed dikanonikkan. Guardrail baru **INV-REF-02** (verify_ssot_relations.py, statik+runtime).
- Verifikasi: testing_agent iteration_94 — backend 14/14, frontend 4/4 alur, 0 bug fungsional.
  Suite regresi baru: backend/tests/backend_test_rc_abcde.py.

- **RC-E batch 2 (2026-08-29 sesi 2, BUG-0137)**: `bookings.origin` = relasi master baru
  `pickup_points` (validator + quick-add satu pintu + selector FE + seed + migrasi
  `scripts/migrate_ssot_batch2.py`); `leads.destination` ERP tervalidasi master (selector CRM),
  jalur publik normalisasi lunak; **Alarm Harga Aneh** di Master Harga (deviasi unit vs tipe
  >±50% → warning kuning + toast). Guardrail INV-REF-02/INV-PRICE-02 diperluas.
  Verifikasi: testing_agent iteration_95 backend 100% + frontend 100%; gate HIJAU 46/46.

- **RC-E batch 3 (2026-08-29 sesi 3+4, BUG-0138 — TUNTAS)**: destinasi PENAWARAN divalidasi
  master (`quotations.py` via `destination_or_400`, update hanya-bila-diubah); form penawaran
  web publik pakai select dari endpoint publik baru `GET /api/public/destination-options`
  (backend publik tetap lunak via `destination_normalize`); halaman **Master Data**
  `/app/masterdata` (owner+ops_admin, RBAC 3 lapis) — RENAME CASCADE ke bookings/leads/
  quotations + NONAKTIF (`active`/`ops_active`) menyembunyikan dari semua selector;
  **Lead→Booking**: `POST /api/leads/{id}/prepare-booking` + tombol "Jadikan Booking" di drawer
  CRM → BookingFormDialog prefilled → lead otomatis `won`. INV-REF-02 diperluas (17 cek).
  Sesi 4 (ritual penutup): **BUG-0139** diperbaiki (mutasi self-test B01 `total_amount`
  ter-commit di `PublicBookingSubmit` + probe `masterdata` di SECTION_PROBES + empty-state
  select Quotation.jsx + split `schemas_partner.py` agar schemas.py < 800 baris).
  Verifikasi: gate HIJAU penuh **46 PASS 0 FAIL 0 SKIP**; testing_agent iteration_96
  backend 15/15 + frontend 4/4, 0 bug (suite: backend/tests/backend_test_ssot_batch3.py).

- **RC-E batch 4 + Preview Cascade (2026-08-29 sesi 5, BUG-0140 — TUNTAS)**: normalisasi LUNAK
  menutup semua jalur tulis publik/inbound — `refs.origin_normalize` BARU; pemesanan online
  (`booking_public.create_booking`) menormalkan origin+destination; lead landing menormalkan
  origin; lead ads menormalkan destination (cocok master → kanonik, di luar master → diterima
  apa adanya). **Preview Cascade** di /app/masterdata: panel konfirmasi menampilkan jumlah
  booking/lead/penawaran yang ikut berubah SEBELUM rename (`md-confirm-*`); master destinasi
  kini melaporkan `used_by_quotations`. Guard INV-REF-02 → 23 cek (+5 statik, +1 runtime probe
  DB). Verifikasi: gate HIJAU 46/46; testing_agent iteration_97 backend 7/7 + frontend 2/2,
  0 bug (suite: backend/tests/backend_test_ssot_batch4.py).

- **RC-E batch 5 + Ekspor + Merge (2026-08-29 sesi 6, BUG-0141 — TUNTAS)**: master KOTA baru
  (`cities`, cty_) — `customers.city` & `partners.city` divalidasi KERAS `refs.city_or_400`
  (kanonik; quick-add `POST /api/cities`; selector FE `CitySelect` cf-city/pf-city; kelola +
  rename cascade + toggle di `/api/master/cities`); `vehicle_type` lead landing & booking publik
  dinormalkan LUNAK `refs.vehicle_type_normalize` vs SSOT tipe armada; **Gabung destinasi
  kembar** `POST /api/master/destinations/{id}/merge` (cascade booking/lead/penawaran ke target,
  sumber nonaktif + `merged_into`, badge "Digabung →" di UI, tanpa penghapusan data); **Ekspor
  Excel** `GET /api/master/export` (3 sheet + pemakaian) + tombol `md-export-excel`;
  seed + `scripts/migrate_ssot_batch5.py`. Guard INV-REF-02 → **30 cek**. Verifikasi: gate
  HIJAU 46/46; testing_agent iteration_98 backend 19/19 + frontend semua skenario, 0 bug
  (suite: backend/tests/backend_test_ssot_batch5.py).

- **Batch 6: Undo Gabungan + Kota Bengkel (2026-08-29 sesi 7, BUG-0142 — TUNTAS)**: merge kini
  mencatat `merged_moved` (id dokumen yang ikut pindah) → `POST /api/master/destinations/{id}/
  unmerge` mengembalikan dokumen tercatat (yang diubah manual sesudah merge dilewati/`skipped`)
  + sumber aktif kembali; UI tombol "Batalkan Gabungan" (`md-unmerge-*`) dgn panel konfirmasi —
  undo TANPA sentuh DB. `workshops.city` ikut master `cities` (city_or_400 create+update,
  `CitySelect` wsh-city, rename kota cascade+usage+Excel mencakup bengkel). Guard INV-REF-02 →
  **34 cek**. Verifikasi: gate HIJAU 46/46; testing_agent iteration_99 backend 11/11 + frontend
  end-to-end, 0 bug (suite: backend/tests/backend_test_ssot_batch6.py).

- **Batch 7: Gabung Titik Jemput (2026-08-29 sesi 8, BUG-0143 — TUNTAS)**: merge + unmerge utk
  titik jemput kembar — `POST /api/master/pickup-points/{id}/merge|unmerge` (cascade
  `bookings.origin`, catat `merged_moved`, sumber nonaktif + `merged_into`; unmerge kembalikan
  booking tercatat, `skipped` utk yang diubah manual); UI panel Titik Jemput kini punya tombol
  Gabung/Batalkan Gabungan yang sama dgn destinasi (Row/MergePanel digeneralisasi via prop
  `kind`). Verifikasi: gate HIJAU 46/46; testing_agent iteration_100 backend 8/8 + frontend
  end-to-end (termasuk regresi merge destinasi), 0 bug (suite:
  backend/tests/backend_test_ssot_batch7.py).

## Backlog Terprioritisasi
- **P1 — RC-E batch 8 (opsional)**: sisa kandidat kecil hasil audit bila ditemukan
- **P2**: kredensial nyata Meta/Google/WA/GA4 (menunggu user); migrasi media ke objstore
  (MEDIA_BACKEND masih local); load test (setelah integritas data beres)
- **P2**: batas/anggaran harga per tipe di Master Harga (saran reviewer: sudah ada cap 100 jt/unit)
- **P3 (rapikan terpisah)**: INFO check_nav_map — menu 'users' & 'vehicles' belum punya PAGE_META
  (bukan regresi); TTL cache utk `refs.*_or_400/normalize` & aggregation `$facet` utk usage count
  Master Data/ekspor; bulk_write utk unmerge bila dokumen ratusan; `skipped_ids` rinci di respons
  unmerge (saran reviewer iter_99, skala sekarang aman)

## Next Tasks
1. Fitur berikutnya sesuai arahan user (backlog SSOT praktis habis)
2. Keputusan user: data produksi / kredensial integrasi nyata

## Update 2026-06 (sesi lanjutan pasca-clone repo)
- Repo di-restore dari GitHub; deps terpasang; seed demo; gate HIJAU 46/46.
- Wiring 2 tab CMS yang terhenti: "Halaman" (PageBuilderPanel) & "Pengaturan Situs"
  (SiteSettingsPanel) di /app/cms; allowlist publik GET /api/public/pages/{slug};
  About.jsx skeleton loading (verified iteration_101, backend 17/17).
- UPGRADE Page Builder jadi editor advanced (verified iteration_102, 100%):
  live preview split-screen via iframe ?pbPreview=1 + postMessage (draft tampil
  sebelum simpan), click-to-select dua arah + highlight, drag & drop dnd-kit,
  picker gambar Media Library, mode device desktop/tablet/ponsel, overlay
  (chat/exit-intent/consent/CTA) disembunyikan di mode pratinjau.
  File kunci: components/cms/PageBuilderPanel|Preview|SectionCard.jsx,
  components/public/BuilderSection.jsx, hooks/useSitePage.js.

## Sesi Jun 2026 — Integrasi WhatsApp NYATA via OpenWA (SELESAI, iteration_103 0 bug)
Analisis kelayakan (uji nyata di container): v4.76.0 stable RUSAK dgn WA Web terkini
(hang cek window.Debug, issue #3346) → WAJIB **v5.0.0-alpha.8** (pinned, TERBUKTI jalan:
QR generated, Easy API 123 endpoint, --webhook inbound).
Implementasi:
- Sidecar Node /app/openwa (yarn --ignore-engines), dikelola backend `services/openwa.py`:
  auto-spawn saat provider=openwa (startup server.py + PATCH /wa/config), port **8033**
  (8010 bentrok service lain!), env OPENWA_BASE_URL/OPENWA_API_KEY, session persisten
  /app/openwa/_IGNORE_rahaza, log /app/openwa/openwa.log, qr-timeout 86400 (flag 0 TIDAK
  berarti forever di v5!), stop() = pgrep+SIGTERM→SIGKILL (proses kebal SIGTERM biasa).
- Provider `openwa` di services/whatsapp.py: OpenWaProvider (sendText via POST
  /api/messages/sendText {args:{to:"...@c.us",content}}, cost 0, gagal-rapi bila belum scan)
  + `_parse_openwa_event` (skip grup/status@broadcast/fromMe) — SEMUA jalur send_wa
  (otomasi, inbox, campaign, sequence, review, test-send) otomatis lewat provider ini.
- Endpoint baru routers/whatsapp.py: GET /wa/openwa/status (auto-spawn), GET /wa/openwa/qr,
  POST /wa/openwa/restart?fresh= (fresh=hapus sesi), POST /wa/openwa-webhook (PUBLIK,
  fail-closed key OPENWA_API_KEY di query — allowlist verify_auth_coverage.py).
- Inbound → handle_inbound → lead otomatis + Inbox + auto-reply (TERVERIFIKASI end-to-end).
- UI: components/app/OpenWaPanel.jsx (qrcode.react QR render, badge status poll 6s, tombol
  Restart/Reset Sesi) di Pengaturan → WhatsApp Adapter; PROVIDERS + opsi "openwa".
- Gate HIJAU penuh; testing_agent iteration_103: backend 16/16, frontend 1/1 — 0 bug.
Menunggu user: SCAN QR dgn nomor khusus bisnis (connected=false s.d. discan = EXPECTED).
Backlog: Broadcasts masih simulasi (perlu wiring send_wa + throttle anti-ban); CTWA
attribution tak tersedia via OpenWA; Meta/Google Ads & GA4 masih MOCKED.

## Sesi 2026-08-30 — Restore repo + BROADCAST WA NYATA TUNTAS (iteration_105, 0 bug)
- Restore dari GitHub `awkasjasnaba/travel` (rsync ke /app, .env platform dipertahankan +
  SETTINGS_ENCRYPTION_KEY_B64/PUBLIC_SITE_URL/MEDIA_BACKEND/OPENWA_* ditambah); bootstrap +
  seed OK.
- **BUG-0144 FIXED**: mutasi self-test B01 (`total_amount` di `PublicBookingSubmit`)
  ter-commit dari sesi terhenti (kelas BUG-0139) → dihapus, gate kembali HIJAU 46/46.
- **Broadcast WA nyata TUNTAS** (backlog "Broadcasts masih simulasi" DITUTUP):
  backend `routers/broadcasts.py` (sudah ada dari sesi terhenti; send_wa per penerima +
  jeda acak 4–9 dtk anti-ban utk provider openwa/meta_cloud + progres sent/failed/skipped
  + klaim atomik draft/failed→sending) di-wire ke UI: tab **Broadcast** baru di
  `/app/crm` (Crm.jsx → CrmBroadcast.jsx, testid tab-crm-broadcast/broadcast-*).
- Penyempurnaan pasca-test: label status dilokalkan (Draf/Terkirim/Gagal/mengirim…),
  **reaper startup** `reap_stale_sending()` (broadcast 'sending' yatim saat backend
  restart → failed + pesan "Kirim Ulang"; diverifikasi restart nyata),
  `memory/test_credentials.md` diisi.
- Verifikasi: testing_agent **iteration_105** backend 12/12 + frontend 100% (RBAC driver
  403, klaim atomik 400, Inbox render {customer_name}/{company}, regresi INV-BOOK-02:
  total_amount klien diabaikan); gate HIJAU 46/46.
- Catatan: provider aktif = mock s.d. user scan QR OpenWA; pengiriman nyata otomatis
  memakai jeda anti-ban begitu provider=openwa. Backlog minor: DELETE/edit broadcast
  draft; heading halaman tidak mengikuti tab aktif (kosmetik).

## Sesi 2026-08-30 (lanjutan) — QR OpenWA SIAP DISCAN
- User memilih "Scan QR OpenWA". Sidecar dipasang ulang (`cd /app/openwa && yarn install
  --ignore-engines`, node_modules tak ikut git), provider di-set `openwa`.
- **BUG akar QR gagal**: Chromium exit code 21 — profil sesi `_IGNORE_rahaza` ter-restore
  dari repo MEMBAWA `SingletonLock` milik pod lama ("profile in use by another computer").
  FIX: hapus `Singleton{Lock,Cookie,Socket}` + patch permanen `services/openwa.py::spawn()`
  (unlink lock yatim sebelum launch → tahan restore pod berikutnya). Catatan: default
  chromiumArgs OpenWA v5 SUDAH berisi --no-sandbox (bukan penyebabnya); `WA_CHROMIUM_ARGS`
  di backend/.env + `/app/openwa/cli.config.json` ditambahkan saat diagnosis (redundan
  tapi tak berbahaya).
- Hasil: state AUTHENTICATING, QR tampil di Pengaturan → SISTEM → panel OpenWA
  (badge "Menunggu Scan QR", tombol Restart/Reset Sesi/Test Kirim). MENUNGGU USER scan
  dgn nomor bisnis. Chat dua-arah via Inbox sudah wired (inbound webhook → lead + Inbox
  + auto-reply, terverifikasi iteration_103); begitu QR discan, Inbox & Broadcast langsung
  memakai WA nyata.

## Sesi 2026-08-30 (lanjutan) — Landing Page Builder: BLOK RUTE NYATA (iteration_107, 0 bug)
Keluhan user: builder "tidak mengambil sama sekali data dari rute yang ada, tampak mockup".
Investigasi: blok fleet/destinasi/testimoni SUDAH menarik data nyata; yang HILANG adalah blok
untuk rute antar-jemput bertarif flat (master `transfer_routes`, endpoint publik
`GET /api/public/booking/config` → routes[]).
Implementasi tipe blok BARU **`route_grid` ("Rute Antar-Jemput")**:
- Backend: `landing_blocks._route_grid` (props kanonik title/subtitle/ids/limit/show_price/cta,
  terdaftar di BLOCK_TYPES → INV-LP-02 otomatis menjaga); template `armada-bandara` kini
  berisi blok route_grid (highlights diperbarui).
- Frontend: komponen `RouteGrid` (EntityBlocks.jsx) — kartu rute NYATA (from→to, kode, durasi,
  "Mulai Rp X flat/sekali jalan"), klik → `/booking?service=airport_transfer&route={id}`
  (wizard booking preselect rute, atribusi iklan diteruskan); case di LandingRender;
  form editor (limit, toggle harga, picker rute `lp-route-ids`, CTA) di LandingBlockForm;
  refs.routes di-fetch di LandingBuilder (pratinjau) & LandingPage (publik).
- Verifikasi: gate HIJAU penuh; testing_agent **iteration_107** backend 7/7 + frontend 100%
  end-to-end (publik: klik "Pesan rute ini" → wizard booking rute ter-preselect; regresi
  /lp/sewa-hiace-jakarta & template lain aman). Suite: backend/tests/test_landing_route_grid.py.
- Catatan QA: opsi select "+ Tambah blok" (shadcn) belum punya testid per-opsi (kosmetik).

## Sesi 2026-08-30 (lanjutan 2) — Heading CRM ikut tab aktif (backlog kosmetik DITUTUP)
- Tab CRM kini hidup di URL (`/app/crm?tab=broadcast` dst, Crm.jsx pakai useSearchParams,
  replace:true, fallback pipeline utk tab tak valid) → bisa di-deep-link.
- `PAGE_TAB_TITLES` baru di navigationConfig.js (export TERPISAH dari PAGE_META agar parser
  guardrail INV-RBAC-04 tidak menganggapnya section) — Topbar membaca `?tab=` dan menampilkan
  judul per-tab ("CRM · Broadcast WhatsApp", "CRM · Skor & SLA", dst).
- Verifikasi self-test screenshot: 4 perpindahan tab + deep-link + fallback tab invalid → judul
  benar semua; gate HIJAU penuh. Pola siap dipakai halaman ber-tab lain (mis. Ads) bila diminta.




## Sesi 2026-08-30 (lanjutan 3) — Redesign Halaman Detail Armada gaya Takatrans + Eksterior 360°
- User minta lanjutan dev: redesign /fleet/:id terinspirasi takatrans.co.id (BUKAN copy) + galeri eksterior 360 dgn JUMLAH FRAME BEBAS per unit dan slider yang baik.
- Backend: field baru `vehicles.exterior_frames` (list URL frame berurutan) & `vehicles.rental_terms`
  (list string) di VehicleCreate/Update + diekspos `_fleet_public` (routers/public.py). Frame demo
  36 buah self-host di backend/uploads/spin360/hiace (dilayani /api/uploads, sumber eksternal kena 429).
- Frontend publik `FleetDetail.jsx`: hero "Interior 360°" imersif (tombol fleet-hero-360-start →
  PhotoSphereTour dgn prop `dark` baru utk kontras tab di hero); panel galeri carousel+thumbnail+
  Lightbox; tab Fasilitas / Syarat & Ketentuan; kartu "Butuh Penawaran Harga?" + tombol WhatsApp;
  section Eksterior 360° (`Exterior360.jsx`: drag-to-rotate, slider scrub shadcn, prev/next,
  auto-rotate play/pause, counter frame, progress preload — interaksi aktif setelah 6 frame awal).
- CMS `VehicleFormDialog`: editor `ExteriorFramesEditor` (GalleryManager urls + generator pola URL
  `{i}` + jumlah frame bebas + nomor awal) + textarea Syarat & Ketentuan.
- Verifikasi: gate HIJAU 46/46; testing_agent iteration_108 backend 9/9 + frontend 100%
  (1 defect kontras tab scene → FIXED via prop dark). memory/test_credentials.md dibuat ulang
  (hilang saat restore repo).
- Catatan: frame eksterior & panorama interior di seed adalah PLACEHOLDER demo (mobil sport AMG /
  foto wisata) — ganti via CMS Armada → Konten Web dgn foto asli unit.

## Sesi 2026-08-30 (lanjutan 4) — Feedback UI detail armada (3 poin user)
1. Komposisi kiri-kanan seimbang: galeri kiri sticky (lg:sticky top-24); elemen kanan diberi depth —
   kartu harga bergradien accent + glow + shadow, tab pill (rounded-full, shadow aktif), fasilitas
   2 kolom dgn badge check bergradien, kartu penawaran ber-glow blob.
2. Eksterior 360° FRAMELESS: tanpa border/kartu/counter/label jumlah frame; gambar lebih besar
   (h-560px, drop-shadow) — siap utk PNG transparan; cue "Swipe untuk memutar" (ikon Hand + chevron
   pulse) sampai interaksi pertama; kontrol minimal (prev/play/next + slider tanpa angka);
   interaksi aktif setelah 6 frame awal termuat (progressive).
3. CMS lengkap: VehicleFormDialog kini punya editor Fasilitas Unit (features, textarea 1/baris) dan
   SpecsEditor baru (components/cms/SpecsEditor.jsx — baris label+nilai, key auto-slug) di samping
   keunggulan/foto/galeri/tur/eksterior/syarat yang sudah ada. Round-trip PATCH specs+features
   diverifikasi via curl (200, tampil di /api/public/fleet, data demo direstore).

## Sesi 2026-08-30 (lanjutan 5) — Anti-flat seluruh section publik
- Upgrade utility bersama di index.css (mengangkat SEMUA section sekaligus):
  `--glass-shadow` 0.10→0.16; `--shadow-glass-3d` + lapisan contact shadow & glow aksen;
  `.card-premium::after` kilau aksen sudut atas (radial, pointer-events none);
  `.section-tint` + radial glow atas, border-y hairline, inset highlight (varian dark aman).
- `AirportRouteStrip`: icon-chip gradien + chip durasi di header, hairline pemisah,
  harga lebih besar, CTA "Pesan" jadi tombol pil gradien (cta-shine).
- Verifikasi screenshot: /fleet (rute bandara + promo) & beranda (3 langkah booking) —
  kartu berdimensi, teks tetap terbaca, dark-mode token disesuaikan.

## Sesi 2026-08-30 (lanjutan) — Restore walakasamana/travel + penutupan sesi terhenti
- Restore penuh ke pod baru: deps FE+BE (workaround konflik pip emergentintegrations/litellm — keduanya sudah ada di pod, dikecualikan dari install), env tambahan, seed, gate HIJAU 0 FAIL 0 SKIP.
- Verifikasi pekerjaan sesi terhenti (hover kartu rute bandara + testimoni berbintang & foto pelanggan) — sudah ter-commit, tampil benar light+dark.
- testing_agent iteration_109: backend 15/15, frontend 100%, 0 bug. Fix kecil: Stars clamp+toFixed(1); test_credentials.md diisi (login /app/login).
- Backlog LOW: redirect /login, avatar onError fallback, foto armada seed relevan, kalender shadcn di wizard booking.

## Sesi 2026-08-30 (batch 7 fitur ops/keuangan)
- (1) Quick-add customer di form booking (masuk master, dedupe 409). (2) Master ADD-ON (koleksi addons, router routers/addons.py, CRUD + quick-add dari form) + form booking multi baris add-on. (3) UX pesanan online: panel "Pesanan Website Masuk" (OnlineOrdersPanel) + filter Semua/Online/Manual + badge Online/Manual di tabel Booking & Trip. (4) Dispatch: klik baris -> DispatchDetailDialog (GET /api/dispatch/{id}/detail, timeline ops<->driver), auto-refresh senyap 20s; DriverWorkspace 25s. (5) Ruang Kerja Driver: override admin owner/ops_admin (pemilih driver, ?driver_id= di /driver/tasks|summary|fees, bypass kepemilikan ack/arrived/pod). (6) Maintenance: _restore_vehicle_if_free (armada pulih available HANYA bila tak ada in_progress lain) + kolom bengkel dobel dihapus. (7) FEE DRIVER per keberangkatan: rate /hari saat assign (AssignTripRequest.driver_fee_rate; 0=hapus, prefill saat re-assign), dikredit idempotent saat trip selesai (services/trips.py -> driver_fee_entries), recompute saat reschedule; pencairan driver_withdrawals: driver ajukan (saldo reservasi) -> finance bayar WAJIB bukti transfer (via media_store, INV-MEDIA-03) -> expense gaji_driver paid + klaim atomik anti double-pay -> saldo berkurang; tolak = saldo kembali. Tab Keuangan "Fee Driver" (DriverWithdrawalsPanel).
- testing_agent iteration_110: backend 25/25 + regresi i109 15/15, frontend 7/7 fitur 100%. 3 temuan minor DITUTUP (reset fee, recompute reschedule, atomic pay). Gate HIJAU.
- Koleksi baru terdaftar di PURGE_COLLECTIONS: addons, driver_fee_entries, driver_withdrawals. bookings.py kini 799/800 baris (hampir penuh!).

## Sesi 2026-08-30 (lanjutan 2 fitur kecil)
- Rate fee DEFAULT per driver: drivers.default_fee_rate (DriverCreate/Update; 0=reset null), field df-default-fee di DriverFormDialog, PREFILL otomatis di AssignTripDialog (prioritas: rate trip tersimpan > default driver > kosong).
- Kelola Master Add-on: panel AddonMasterPanel.jsx di /app/masterdata (md-addon-*) — tambah/edit/aktif-nonaktif/hapus; nonaktif hilang dari form booking, booking lama utuh (snapshot).
- testing_agent iteration_111: backend 18/18, frontend 100%, 0 temuan. Gate HIJAU.

## Sesi Jun 2026 (E1) — MODUL DOKUMEN BISNIS (meniru sipro) — Invoice DP/Pelunasan, Kwitansi, Konfirmasi, SPJ
Repo di-clone ulang dari `alsksjsbshhs/travel` ke /app; backend/.env dibuat ulang (MONGO_URL, DB_NAME, OPENWA_*, PUBLIC_SITE_URL, SETTINGS_ENCRYPTION_KEY_B64 baru); deps terpasang; seed demo dijalankan.
Fitur baru (backend):
- `services/doc_numbering.py` — pola nomor terkonfigurasi ({PREFIX},{SEQ},{YYYY},{MM},{MM_ROMAN},{DOC_TYPE},{BOOKING_CODE},{CUSTOMER_INITIALS},{VEHICLE_CODE}), reset never/yearly/monthly/daily, digit, nomor awal; registry: invoice, receipt, confirmation, spj. Counter atomik `counters` scope `docnum:*`.
- `services/doc_layout.py` — layout per kode (`__default__` + override): kop (logo via Media Library, identitas, mode kop/footer, warna, margin, kertas, watermark), gaya tabel, bagian tercetak, kolom ttd, opsi (tempat/tanggal, materai). Naskah per kode (intro/closing/terms) dgn placeholder tervalidasi. Config: pajak on/off (label, %), DP default, jatuh tempo, kwitansi otomatis, sinkron status invoice, rekening bank, caption WA per dokumen.
- `services/pdf_engine.py` — SATU renderer reportlab (kop/footer/watermark tiap halaman, meta grid, tabel item+total, rekening, S&K, ttd) dipakai dokumen nyata & pratinjau.
- `services/documents.py` — invoice kind dp|settlement|full (pajak per invoice, DP %/nominal, sisa setelah bayar), kwitansi (terbilang), konfirmasi pemesanan, SPJ; kirim PDF via WA (send_wa provider aktif); hook `on_payment_recorded` (status invoice→partial/paid, kwitansi otomatis, WA opsional).
- Router: `routers/invoices.py` (ditulis ulang, endpoint lama kompatibel + kind/tax), `routers/documents.py` (/api/documents: booking/{id}, receipts, booking/{id}/{confirmation|spj}/pdf|send-wa, config, layouts (+script, preview), numbering). Section RBAC baru `documents` (owner, ops_admin); ubah konfigurasi = owner (`settings`).
Frontend: halaman `/app/documents` (tab Invoice, Kwitansi, Kop & Tampilan + pratinjau PDF live, Naskah, Rekening/Pajak/WA, Penomoran); tombol **Dokumen** di tabel Booking → dialog semua dokumen booking (buat invoice DP/pelunasan/penuh, kwitansi, konfirmasi, SPJ, lihat/unduh/kirim WA); InvoiceFormDialog baru (jenis, DP %, toggle pajak); PaymentDialog opsi "Kirim kwitansi via WhatsApp".
Catatan: provider WA aktif di demo = mock (pengiriman disimulasikan & dicatat di Inbox).

## Jun 2026 — NOTA REFUND (selesai, testing_agent iteration_113: backend 20/21 → 1 bug 500 diperbaiki, frontend semua alur lolos)
- Kode layout `REFUND_NOTE` (kop/ttd 2 kolom: kasir & pelanggan), naskah bawaan + placeholder baru (cancellation_reason, cancellation_fee, refund_amount, cancelled_date), aturan penomoran `refund` (RFD/{YYYY}/{MM}/{SEQ}), caption WA `wa_caption_refund`.
- `services/documents.py`: build/ensure_refund_note (1 nota per booking, dari booking cancelled dgn refund_amount>0 + payment type=refund), refund_note_pdf (ringkasan: total, dana diterima, denda ditahan, refund), on_booking_cancelled (hook di POST /bookings/{id}/cancel; `send_refund_wa` di CancelBooking → response `refund_note` + `refund_wa`).
- Endpoint: GET/POST /api/documents/refund-notes, GET /{id}/pdf, POST /{id}/send-wa; `refund_note` di GET /api/documents/booking/{id}. POST /receipts menolak payment refund/negatif (400); terbilang() aman utk negatif.
- UI: tab "Nota Refund" di /app/documents; section "Pembatalan & Nota Refund" di dialog Dokumen booking cancelled (tombol Dokumen kini tampil juga utk booking cancelled; invoice baru/konfirmasi/SPJ dinonaktifkan); switch "Kirim Nota Refund via WhatsApp" di dialog Batalkan Booking.

## Jun 2026 — MANAJEMEN DATA: BACKUP & RESTORE LENGKAP (/app/data, section `data` = owner+ops_admin)
- `services/backup.py`: arsip ZIP = manifest.json + db/<koleksi>.jsonl (bson json_util) + media/ (backend/uploads + MEDIA_LOCAL_DIR). Registri `backups` (skip: backups, restore_logs, backup_jobs). BACKUP_DIR env (default backend/backups, di-gitignore). Restore: snapshot `pre_restore` otomatis → drop+insert per koleksi (penuh/sebagian) → tulis media → `restore_logs`. Retensi arsip `auto` (keep_last). Upload arsip divalidasi (manifest + format_version).
- `routers/data_management.py`: GET /api/data/overview, POST /api/data/backups, POST /api/data/backups/upload, GET /{id}/manifest, GET /{id}/download, DELETE /{id}, POST /api/data/restore (confirm="RESTORE"), GET/PATCH /api/data/schedule (settings key backup_schedule: enabled, keep_last, include_media, last_run_at/last_status), POST /api/cron/backup-daily (Bearer WEBHOOK_CRON_SECRET, idempoten via backup_jobs.run_id, BackgroundTasks).
- `.emergent/crons.yml`: backup-daily 02:00 Asia/Jakarta → /api/cron/backup-daily. `WEBHOOK_CRON_SECRET` di backend/.env.
- UI: `features/app/DataManagement.jsx` (statistik, tabel arsip: unduh/restore/hapus, unggah arsip, jadwal, riwayat restore, koleksi aktif) + `components/app/data/RestoreDialog.jsx` (mode penuh/per koleksi, media toggle, ketik RESTORE).

## Jun 2026 — EKSPOR EXCEL PER TABEL (halaman Manajemen Data)
- `services/table_export.py`: TABLES (customers, bookings, payments [+join booking_code/customer_name], invoices, receipts, vehicles, drivers) → xlsx openpyxl (header berwarna, freeze, autofilter, format Rp & tanggal, kolom kosong disembunyikan).
- Endpoint: GET /api/data/exports (katalog+count), GET /api/data/exports/{table}.xlsx (header X-Row-Count, di-expose CORS). Audit action=export.
- UI: section "Ekspor Excel per tabel" di /app/data (data-testid export-{key}).
- Filter ekspor (Jun 2026): `table_export.FILTERS` (bookings: start_datetime+status; payments: paid_at+type/method; invoices: issued_at+status/kind; receipts: issued_at+payment_type) → `build_query`; endpoint menerima ?date_from&date_to&<field>=v (multi). UI `components/app/data/ExportFilterDialog.jsx` (chip status, rentang tanggal) dibuka dari kartu tabel yang punya filter.

## Jun 2026 — IMPOR MASTER DATA (migrasi, /app/data) — testing_agent iteration_115: 22/22 backend + frontend lolos
- `services/master_import.py`: SHEETS (customers, vehicles, drivers, cities, partners, addons) → template multi-sheet (Petunjuk + header + contoh), parse_workbook (alias Indonesia: Korporat→corporate, tersedia→available, ya/tidak; tanggal YYYY-MM-DD/DD/MM/YYYY; baris contoh template otomatis dilewati), plan() pratinjau (insert/update/error/duplikat), commit() upsert|insert_only (kunci: pelanggan telepon/email/nama, armada plat, driver telepon/nama, lainnya nama; kota otomatis dibuat; code armada V-xx otomatis), `import_logs`.
- Endpoint: GET /api/data/import/template.xlsx, GET /sheets, POST /preview, POST /commit (form: mode, sheets, snapshot → backup kind `pre_import`), GET /history.
- UI: `components/app/data/MasterImportPanel.jsx` (unduh template, unggah→pratinjau per sheet, daftar error per baris, pilih sheet, mode, snapshot, Impor Semua Sekaligus, hasil & riwayat).
