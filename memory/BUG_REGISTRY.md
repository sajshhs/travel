# 🐞 BUG REGISTRY — Lacak Bug & Cegah Berulang
## Travel & Fleet Management Ecosystem

> **Tujuan:** setiap bug dicatat, dipetakan ke Root-Cause (taksonomi `docs/07` & `docs/08`),
> dan dipastikan ada **gate** yang menangkapnya agar **tidak terulang**.
> Diisi via PB-6 (`docs/PLAYBOOKS.md`).
>
> **Aturan emas:** kalau sebuah bug LOLOS dari semua gate → itu artinya gate kurang.
> Wajib **perkuat gate** (tambah invarian/cek), bukan sekadar tambal kode.

---

## FORMAT ENTRI
```
### BUG-<nnnn> — <judul singkat>
- Tanggal      : YYYY-MM-DD
- Fase/Modul    : Phase X / <modul>
- Gejala        : <apa yang terlihat>
- Root Cause    : RC-? (<nama>)  — lihat docs/07 §2 / docs/08 §6
- Gate penangkap: <script yang seharusnya/akhirnya menangkap>
- Perbaikan     : <ringkas>
- Regression    : <invarian/cek yang ditambahkan agar tak terulang>
- Status        : OPEN | IN_PROGRESS | FIXED (bukti: <receipt/test>)
```

---

## REGISTRY

### BUG-0144 — Mutasi self-test B01 ter-commit LAGI dari sesi terhenti (kelas BUG-0139) — FIXED 2026-08-30
- Tanggal       : 2026-08-30 (sesi restore pasca-clone `awkasjasnaba/travel`)
- Fase/Modul    : schemas_booking.py / selftest_booking_guards
- Gejala        : gate MERAH saat restore — `PublicBookingSubmit.total_amount` (harga dari klien)
                  ada di repo; INV-NUM-01 + INV-BOOK-02 FAIL + selftest "B01/B02 revert tidak bersih".
- Root Cause    : sesi sebelumnya terhenti user di tengah `selftest_booking_guards` → mutasi B01
                  tidak sempat di-revert lalu ter-commit ("Auto-generated changes"). Kelas identik
                  BUG-0139.
- Gate penangkap: guard:numeric_bounds + guard:booking_public + selftest:booking_guards (bekerja
                  sesuai desain — repo kotor langsung memerah).
- Perbaikan     : hapus baris `total_amount: Optional[float] = 0` dari `PublicBookingSubmit`.
- Regression    : gate HIJAU 46/46; iteration_105 memverifikasi submit publik dgn `total_amount=1`
                  → diabaikan, total dihitung server.
- Status        : FIXED (bukti: /app/test_reports/iteration_105.json backend 12/12)

### BUG-0143 — Batch 7: titik jemput kembar tak bisa digabung/dibatalkan seperti destinasi — FIXED 2026-08-29
- Tanggal       : 2026-08-29 (sesi 8)
- Fase/Modul    : Master Data / pickup_points merge+unmerge
- Gejala        : aksi Gabung/Batalkan hanya ada utk destinasi; titik jemput kembar (mis.
                  "Stasiun Bandung" vs varian ejaan) tetap terpecah riwayat booking-nya.
- Perbaikan     : `POST /api/master/pickup-points/{id}/merge` (cascade `bookings.origin` →
                  nama target + catat `merged_moved.bookings`; sumber `active=False` +
                  `merged_into`; target wajib aktif & bukan hasil gabungan) dan
                  `POST .../unmerge` (kembalikan booking tercatat bila origin masih nama
                  target, sisanya `skipped`; sumber aktif kembali). FE `MasterData.jsx`
                  digeneralisasi: tombol Gabung/Batalkan Gabungan + panel konfirmasi kini
                  muncul di panel Titik Jemput dgn testid yang sama (`md-merge-*`,
                  `md-unmerge-*`); teks panel menyesuaikan "titik jemput"/"destinasi".
- Regression    : cek guard diperketat (merge & unmerge masing2 ≥2 di router) — tetap 34 cek.
                  Round-trip manual: merge (1 booking pindah) → unmerge (1 kembali, 0 skipped)
                  → unmerge ulang 400, merge diri sendiri 400.
- Status        : FIXED — gate HIJAU 46/46; testing_agent di sesi ini.

### BUG-0142 — Batch 6: gabungan destinasi tak bisa dibatalkan dari UI + kota bengkel masih teks bebas — FIXED 2026-08-29
- Tanggal       : 2026-08-29 (sesi 7)
- Fase/Modul    : RC-E batch 6 / Master Data (unmerge), workshops.city
- Gejala        : (a) merge destinasi (BUG-0141) hanya bisa dibatalkan lewat manipulasi DB —
                  dan bahkan itu TIDAK bisa mengembalikan dokumen yang ter-cascade (tidak ada
                  catatan dokumen mana yang pindah); (b) `workshops.city` belum ikut master
                  `cities` — bengkel "bandung" vs "Bandung" bercabang.
- Perbaikan     : (a) merge mencatat `merged_moved` (id per koleksi) → endpoint baru
                  `POST /api/master/destinations/{id}/unmerge` mengembalikan dokumen tercatat
                  (hanya bila destinasinya masih nama target; selainnya `skipped`), sumber
                  aktif kembali; UI: tombol "Batalkan Gabungan" pada baris ber-badge
                  (`md-unmerge-{id}` → panel `md-unmerge-panel-{id}` ber-jumlah
                  `merged_moved_count` → `md-unmerge-confirm-{id}`); (b) `city_or_400` di
                  create+update `routers/workshops.py`, FE `WorkshopFormDialog` → `CitySelect`
                  (wsh-city), rename kota cascade + usage + Excel sheet Kota mencakup bengkel.
- Regression    : INV-REF-02 → 34 cek (+3 statik). Round-trip teruji manual: merge (1 lead
                  pindah) → unmerge (1 kembali, 0 skipped) → unmerge ulang 400; kota bengkel
                  ngawur 400 & 'bandung' → 'Bandung'.
- Status        : FIXED — gate HIJAU 46/46; testing_agent di sesi ini.

### BUG-0141 — SSOT batch 5: kota pelanggan/mitra & tipe armada landing teks bebas; tanpa ekspor master; destinasi kembar tak bisa digabung — FIXED 2026-08-29
- Tanggal       : 2026-08-29 (sesi 6, lanjutan seri RC-E)
- Fase/Modul    : RC-E batch 5 / customers.city, partners.city, leads.vehicle_type, Master Data
- Gejala        : (a) kota pelanggan & mitra diketik bebas ("bandung" vs "Bandung") → laporan
                  per-kota bercabang; (b) tipe armada dari lead landing teks bebas → tidak cocok
                  SSOT `VEHICLE_TYPE_LABELS`; (c) tim ops tidak bisa mengunduh master sebagai
                  Excel; (d) destinasi kembar (mis. hasil warisan) tak bisa disatukan — riwayat
                  booking/lead/penawaran terpecah selamanya.
- Perbaikan     : (a) master KOTA baru `cities` (cty_) + `refs.city_or_400` KERAS di
                  create/update customers & partners + quick-add `POST /api/cities` +
                  selector FE `CitySelect` (cf-city/pf-city) + kelola `GET/PATCH
                  /api/master/cities[/{id}]` (rename cascade customers+partners, toggle);
                  (b) `refs.vehicle_type_normalize` LUNAK di lead landing +
                  `requested_vehicle_type` booking publik; (c) `GET /api/master/export`
                  → Excel 3 sheet (openpyxl) + tombol `md-export-excel`; (d) `POST
                  /api/master/destinations/{id}/merge` — cascade 3 koleksi ke nama target,
                  sumber `ops_active=False` + `merged_into` (tanpa hapus), UI panel Gabung
                  (`md-merge-*`) + badge "Digabung →". Seed + `scripts/migrate_ssot_batch5.py`;
                  `cities` terdaftar di verify_schema/validate_compliance/PURGE_COLLECTIONS.
- Regression    : INV-REF-02 diperluas → 30 cek (+ kota ngawur 400, GET /cities).
- Status        : FIXED — verifikasi manual: city 'bandung'→'Bandung', merge cascade 1 lead +
                  re-merge 400, ekspor xlsx 3 sheet; gate + testing_agent di sesi ini.

### BUG-0140 — SSOT batch 4: jalur publik/inbound masih menulis origin/destination teks bebas + rename master tanpa preview — FIXED 2026-08-29
- Tanggal       : 2026-08-29 (sesi 5, lanjutan seri RC-E)
- Fase/Modul    : RC-E batch 4 / booking_public, landing lead, lead ads, Master Data
- Gejala        : (a) pemesanan ONLINE menulis `bookings.origin/destination` apa adanya —
                  koleksi yang sama dgn ERP yang sudah divalidasi master → nama bercabang
                  kembali lewat pintu publik; (b) lead landing menyimpan `origin` mentah;
                  (c) lead ads menyimpan `destination` mentah; (d) tombol "Ganti Nama" di
                  Master Data langsung mengeksekusi cascade tanpa memberi tahu berapa
                  dokumen yang ikut berubah.
- Perbaikan     : (a) `services/refs.origin_normalize` BARU (lunak, vs master pickup_points);
                  `booking_public.create_booking` menormalkan origin+destination;
                  (b) `routers/public.py` landing lead → `origin_normalize`;
                  (c) `services/ads.py` → `destination_normalize`;
                  (d) `GET /master/destinations` + `used_by_quotations`; `MasterData.jsx`
                  panel konfirmasi preview cascade (jumlah booking/lead/penawaran) sebelum
                  rename, dgn testid `md-confirm-*`/`md-rename-confirm-*`/`md-rename-cancel-*`.
                  Prinsip batch tetap: jalur PUBLIK = LUNAK (tidak menolak), jalur ERP = keras.
- Regression    : INV-REF-02 diperluas +5 statik +1 runtime (probe /public/booking 'bandung'/
                  'bali' → tersimpan 'Bandung'/'Bali', verifikasi langsung di DB) → 23 cek.
- Status        : FIXED — verifikasi manual: ads 'bromo'→'Gunung Bromo', landing
                  'bandung'/'yogyakarta'→kanonik, guard PASS 23; gate + testing_agent di sesi ini.

### BUG-0138 — SSOT batch 3 + Master Data + Lead→Booking — FIXED & TUNTAS 2026-08-29 (sesi 4: gate 46/46 HIJAU + testing_agent iteration_96 0 bug)
- Tanggal       : 2026-08-29
- Fase/Modul    : RC-E batch 3 / quotations.destination, form penawaran publik, halaman Master Data, konversi lead
- Gejala        : (a) destinasi PENAWARAN (ERP & form web publik) masih teks bebas;
                  (b) tidak ada tempat kelola master (rename/nonaktif) — rename manual di DB
                  akan membuat nama bercabang; (c) lead menang harus disalin manual jadi booking.
- Perbaikan     : (a) quotations create/update via `destination_or_400` (update hanya-bila-diubah);
                  form publik memakai select dari `GET /api/public/destination-options`
                  (backend publik tetap LUNAK via `destination_normalize`);
                  QuotationFormDialog pakai selector master (`/leads/destination-options`).
                  (b) halaman baru `/app/masterdata` (section `masterdata`, owner+ops_admin;
                  RBAC 3 lapis: allowlist FE + RoleGuard + SECTION_ACCESS): kelola titik jemput
                  & destinasi — RENAME CASCADE (bookings/leads/quotations via
                  `PATCH /api/master/pickup-points/{id}` & `/api/master/destinations/{id}`),
                  NONAKTIF menyembunyikan dari semua selector + ditolak pemakaian baru
                  (filter `active`/`ops_active` di refs + endpoint options).
                  (c) `POST /api/leads/{id}/prepare-booking` (ensure_customer dedupe + prefill)
                  + tombol "Jadikan Booking" di drawer lead → BookingFormDialog prefilled;
                  setelah booking dibuat lead otomatis stage `won` + aktivitas tercatat.
- Regression    : INV-REF-02 diperluas (+5 cek: quotations, public options, master cascade);
                  INV-RBAC otomatis mencakup section `masterdata`.
- Status        : **FIXED & TUNTAS (2026-08-29, sesi 4).** Gate `scripts/gate.sh` HIJAU penuh
                  **46 PASS 0 FAIL 0 SKIP** (receipt memory/GATE_RECEIPT.md); testing_agent
                  iteration_96 backend 15/15 + frontend 4/4, 0 bug; INVARIANTS.md (INV-REF-02
                  batch 3) & PRD.md diperbarui. Suite regresi:
                  `backend/tests/backend_test_ssot_batch3.py`.

### BUG-0139 — Mutasi self-test B01 ter-commit ke repo tanpa revert (gate MERAH 6 titik) — FIXED 2026-08-29
- Tanggal       : 2026-08-29 (sesi 4, ditemukan saat menjalankan ritual gate batch 3)
- Fase/Modul    : guardrail selftest / schemas_booking.py
- Gejala        : gate MERAH 6 gate: numeric_bounds, booking_public, selftest:booking_guards
                  (B01+B02 "revert tidak bersih"), rbac_runtime, ux_audit, validate_compliance.
- Akar masalah  : (a) baris mutasi B01 `total_amount: Optional[float] = 0` di
                  `schemas_booking.PublicBookingSubmit` TER-COMMIT ke repo (sesi 3 terhenti di
                  tengah; revert selftest jadi "tidak bersih" karena baris ganda) — skema publik
                  menerima harga dari klien; (b) section baru `masterdata` belum punya probe di
                  `SECTION_PROBES` (verify_rbac_runtime.py); (c) `Quotation.jsx` select destinasi
                  tanpa empty-state (ux_audit E2); (d) `schemas.py` 809 baris > batas 800.
- Perbaikan     : (a) hapus baris `total_amount` dari `PublicBookingSubmit`; (b) tambah probe
                  `"masterdata": "/master/destinations"`; (c) placeholder select menampilkan
                  "Memuat destinasi…" saat `destOptions.length === 0`; (d) blok skema E16
                  Partner/Subcharter dipindah ke file baru `backend/schemas_partner.py`
                  (import di routers/partners.py & subcharters.py disesuaikan; schemas.py 756 baris).
- Regression    : gate ulang HIJAU penuh 46/46 (termasuk selftest mutasi B01/B02 revert bersih).
- Pelajaran     : jangan hentikan sesi saat selftest mutasi berjalan — mutasi bisa ikut
                  ter-commit; kalau selftest lapor "revert tidak bersih", curigai baris mutasi
                  yang SUDAH ada di kode sebelum selftest jalan.

### BUG-0137 — SSOT batch 2: titik jemput & destinasi lead masih teks bebas — FIXED 2026-08-29
- Tanggal       : 2026-08-29
- Fase/Modul    : RC-E batch 2 / bookings.origin + leads.destination
- Gejala        : Titik jemput booking & destinasi lead diketik bebas ("bandung" vs "Bandung");
                  laporan & pencocokan antar-entitas tidak konsisten.
- Root Cause    : lanjutan BUG-0135 — field relasional tersisa yang belum ber-master.
- Perbaikan     : master baru `pickup_points` (pkp_) + `refs.origin_or_400` (create/group/update
                  booking) + quick-add satu pintu `POST /api/pickup-points` + selector FE
                  `PickupPointSelect`; destinasi lead ERP via `destination_or_400` + selector
                  (`GET /leads/destination-options`); jalur PUBLIK lead memakai
                  `destination_normalize` LUNAK (inbound eksternal tak ditolak); migrasi
                  `scripts/migrate_ssot_batch2.py`; seed dikanonikkan. Bonus: alarm deviasi
                  Master Harga (unit vs tipe >±50% → warning kuning + toast, INV-PRICE-02).
- Regression    : INV-REF-02 diperluas (statik+runtime origin & lead), INV-PRICE-02 cek alarm.
- Status        : FIXED (bukti: curl 400 beralasan; 'bandung'→'Bandung'; warning 233% muncul)

### BUG-0132 — Quote "Hitung Otomatis" booking ERP mengabaikan tarif per unit — FIXED 2026-08-29
- Tanggal       : 2026-08-29
- Fase/Modul    : RC-A / routers/pricing.py (`POST /api/pricing/quote`)
- Gejala        : Ops menekan "Hitung Otomatis" di form Buat Booking → angka yang tampil memakai
                  tarif TIPE (mis. Hiace Premio 1.500.000) padahal unit terpilih punya tarif
                  KHUSUS (`vehicles.day_rate` 1.650.000). Mesin penagih (create/approve/web)
                  memakai `resolve_day_rate` → yang DITAGIH 2.100.000, yang DILIHAT 1.950.000.
- Root Cause    : `/pricing/quote` hanya me-resolve `vehicle_id → type`, tidak memanggil
                  `resolve_day_rate` (tarif unit > tarif tipe > default) — resolusi tarif
                  diduplikasi separuh.
- Gate penangkap: tidak ada (INV-PRICE-01 tak mencakup permukaan quote internal) → kini
                  `verify_price_master.py` (INV-PRICE-02) mengunci `resolve_day_rate` di quote.
- Perbaikan     : quote mengambil dokumen armada penuh + `resolve_day_rate`, day_rate diteruskan
                  ke `compute_quote` — identik dgn mesin penagih.
- Regression    : INV-PRICE-02 cek statik "quote memakai resolve_day_rate".
- Status        : FIXED (bukti: curl quote = 2.100.000 = harga booking tersimpan; gate HIJAU)

### BUG-0133 — Harga armada bisa DITULIS dari 2 halaman berbeda (tanpa master) — FIXED 2026-08-29
- Tanggal       : 2026-08-29
- Fase/Modul    : RC-B / Pengaturan (pricing_rules) vs form Armada (day_rate + price_from)
- Gejala        : Tarif diatur di Pengaturan→Aturan Harga DAN di form Tambah/Edit Armada.
                  Dua pintu tulis saling menimpa, ops bingung mana yang berlaku (keluhan user).
- Root Cause    : duplikasi jalur tulis; `price_from` (angka pemasaran mati) masih ikut form.
- Gate penangkap: tidak ada → kini `verify_price_master.py` (INV-PRICE-02).
- Perbaikan     : Master Harga TUNGGAL di Pengaturan (panel "Tarif Khusus per Unit",
                  `GET/PATCH /api/pricing/unit-rates`); `day_rate`/`price_from` DIHAPUS dari
                  VehicleCreate/VehicleUpdate + routers/vehicles.py; form Armada kini
                  read-only reference yang menunjuk ke Master Harga.
- Regression    : INV-PRICE-02 (schemas + router + FE form + endpoint master wajib ada).
- Status        : FIXED (bukti: PATCH /vehicles dgn day_rate=9999999 → nilai TIDAK berubah)

### BUG-0134 — Notif merah "berkas media hilang" PALSU (kegagalan cek dihitung hilang) — FIXED 2026-08-29
- Tanggal       : 2026-08-29
- Fase/Modul    : RC-C / services/media_store.exists + /api/media/health + MediaBrowser
- Gejala        : Banner merah "aset kehilangan berkas fisiknya" muncul padahal berkas ada.
- Root Cause    : `exists()` bool: SEMUA kegagalan pengecekan (kunci objstore tak diset,
                  gangguan jaringan, path mismatch/tidak sah, path kosong) dihitung sebagai
                  "hilang". Tidak dibedakan "terbukti hilang" vs "cek gagal".
- Gate penangkap: tidak ada (kelas false-positive) → perilaku dikunci di kode + docstring.
- Perbaikan     : `check_file()` tri-state per `storage_backend` aset: missing = bukti nyata
                  (404 objstore / file tak ada di disk lokal); unknown = cek gagal + alasan.
                  `/media/health` mengembalikan keduanya; FE: merah hanya utk missing,
                  kuning berALASAN utk unknown.
- Regression    : `exists()` kini 'unknown ≠ hilang' (dipakai pemulih media).
- Status        : FIXED (bukti: health missing=0 unknown=0 pada seed; kasus objstore tanpa
                  kunci → unknown, bukan merah)

### BUG-0135 — Destinasi booking ERP = teks bebas (pelanggaran SSOT, RC-E batch 1) — FIXED 2026-08-29
- Tanggal       : 2026-08-29
- Fase/Modul    : RC-E / bookings.destination vs master `destinations`
- Gejala        : "Bromo" vs "Gunung Bromo" vs "bromo " = 3 destinasi berbeda di laporan;
                  paket/penawaran (sudah `destination_id`) tak pernah cocok dgn booking.
- Root Cause    : input custom di 3 dialog booking ERP tanpa validasi server ke master.
- Gate penangkap: tidak ada → kini `verify_ssot_relations.py` (INV-REF-02, statik+runtime).
- Perbaikan     : validator satu pintu `refs.destination_or_400` (create/group/update; nilai
                  disimpan NAMA KANONIK; edit lama tak dipaksa ganti bila tak diubah);
                  selector FE `DestinationSelect` + `GET /bookings/destination-options`;
                  migrasi `scripts/migrate_booking_destinations.py` (master ops status draft
                  agar tak tayang di web + normalisasi 5 booking lama); seed dikanonikkan.
- Regression    : INV-REF-02 + fixture guard lama diselaraskan (destination "Guard"→"Bali").
- Status        : FIXED (bukti: POST destinasi 'Planet Mars' → 400 berALASAN; 'bali' → 'Bali')

### BUG-0136 — UX driver cacat: tak ada Upcoming Trips & aksi jemput membingungkan — FIXED 2026-08-29
- Tanggal       : 2026-08-29
- Fase/Modul    : RC-D / DriverWorkspace + DriverTaskCard
- Gejala        : Semua trip tampil rata (urut created_at) tanpa daftar upcoming; tombol
                  "Mulai" langsung ke to_pickup lalu "Tiba di Tujuan" bisa ditekan bahkan
                  sebelum penumpang naik — tidak ada tahap "penumpang dijemput".
- Root Cause    : UI satu daftar tanpa state stepper; transisi on_trip tidak pernah
                  dipakai driver (langsung to_pickup → completed).
- Gate penangkap: — (UX) → diverifikasi testing agent.
- Perbaikan     : Workspace v2: seksi Trip Aktif / Upcoming Trips (hari ini + mendatang,
                  urut jadwal) / Riwayat; stepper standby → berangkat jemput (odometer) →
                  penumpang naik (on_trip via `/trips/{id}/status` — state machine TUNGGAL,
                  bukan jalur kedua) → tiba → check-out odometer (jalur `checkout` SSOT).
                  RBAC scope driver tetap (hanya trip miliknya).
- Regression    : memakai jalur transisi yang sudah dijaga RC-03 (finalize_trip_completion).
- Status        : FIXED (bukti: screenshot workspace + testing agent)

### BUG-0131 — Isi artikel rich text tampil sebagai TAG MENTAH / paragraf pecah di halaman blog — FIXED 2026-08-17
- Tanggal       : 2026-08-17
- Fase/Modul    : CMS-09 (rich text) ↔ situs publik (`features/public/BlogDetail.jsx`)
- Gejala        : Setelah editor rich text aktif, `articles.body` berisi HTML. `BlogDetail` masih
                  memecah body dengan `split(/\n{2,}/)` dan merendernya sebagai TEKS, sehingga
                  pengunjung melihat `<h2>Rencana 3 hari</h2>` sebagai tulisan biasa — konten baru
                  praktis tak bisa dibaca, dan artikel lama (teks polos) berisiko rusak bila renderer
                  diganti serampangan ke HTML.
- Root Cause    : Penulis (CMS) diubah tanpa mengubah PEMBACA (renderer publik). Dua format hidup
                  bersama (HTML baru + teks polos lama) tetapi renderer hanya paham satu.
- Gate penangkap: tidak ada gate statik yang bisa menangkapnya → ditemukan verifikasi Playwright
                  main agent sesudah menyimpan artikel berisi HTML.
- Perbaikan     : Komponen `components/public/ArticleBody.jsx` mendeteksi format (`looksLikeHtml`):
                  HTML tersanitasi server dirender dengan `.article-prose` (tipografi via token tema),
                  teks polos lama tetap paragraf + drop-cap seperti sebelumnya, dan body kosong punya
                  state sendiri.
- Regression    : `data-testid` `blog-body-html` / `blog-body-text` / `blog-body-empty` supaya testing
                  agent bisa membedakan format yang dirender; POC CMS-09 tetap membuktikan sanitasi server.
- Status        : FIXED (bukti: Playwright — h2/li/blockquote/link terender, `<h2>` tidak muncul sebagai teks)

### BUG-0130 — `<script>` dibuang tetapi ISI-nya tersimpan jadi kalimat di artikel — FIXED 2026-08-17
- Tanggal       : 2026-08-17
- Fase/Modul    : CMS-09 (`services/richtext.py`)
- Gejala        : `<script>alert(1)</script>` di body artikel → tersimpan sebagai kalimat "alert(1)"
                  yang TERBACA pengunjung di tengah artikel. Bukan lubang XSS (tag tetap dibuang),
                  tetapi kotor & membingungkan; hal yang sama terjadi pada `<style>body{}</style>`.
- Root Cause    : `bleach.clean(strip=True)` membuang TAG, bukan isinya — perilaku benar untuk
                  `<b>`, salah untuk blok yang isinya bukan teks bacaan.
- Gate penangkap: POC `scripts/test_core_cms_cw2.py` (bagian B) memeriksa tag hilang, belum isi.
- Perbaikan     : Pra-strip regex `_BLOCK_RE`/`_SELF_CLOSING_BLOCK_RE` membuang
                  `script|style|iframe|object|embed|noscript|template` BESERTA isinya sebelum allowlist.
- Regression    : POC B tetap hijau + uji manual: `alert(1)`/`body{}` tidak lagi muncul di keluaran.
- Status        : FIXED (bukti: `richtext.sanitize` mengembalikan HTML tanpa sisa isi blok berbahaya)

### BUG-0129 — Sanitasi rich text GAGAL SENYAP karena dependency `bleach` tidak pernah dipasang/dipin — FIXED 2026-08-17
- Tanggal       : 2026-08-17
- Fase/Modul    : CMS-09 (`services/richtext.py` ↔ `backend/requirements.txt`)
- Gejala        : POC `scripts/test_core_cms_cw2.py` GAGAL 3 cek: struktur artikel (h2/p/ul/li/blockquote),
                  gambar sah, dan tautan sah "hilang" — keluaran server berubah jadi TEKS DATAR
                  ("Judul BagianParagraf tebal & tautan…"). Tidak ada satu pun error di log: fitur
                  editor kaya mustahil dipakai walau kodenya lengkap.
- Root Cause    : `richtext.py` sengaja *fail-closed* bila `bleach` tak ada (`_STRIP_RE` membuang SEMUA
                  markup) — keputusan keamanan yang benar, tetapi dependency-nya tidak pernah masuk
                  `requirements.txt`, jadi di pod baru paket itu memang tidak ada.
- Gate penangkap: POC CMS-CW2 (bagian B). Gate statik tidak memeriksa import opsional.
- Perbaikan     : `pip install bleach` + **dipin** `bleach==6.4.0` di `backend/requirements.txt`
                  (baris berkomentar alasan), backend di-restart.
- Regression    : POC CMS-CW2 kini **87/87 LOLOS**; dependency ikut terpasang otomatis lewat
                  `scripts/bootstrap.sh` di pod berikutnya.
- Status        : FIXED (bukti: POC 87/87 + `python -c "import bleach"` OK)

### BUG-0128 — Mesin bersih-bersih data uji MELEWATKAN dokumen tanpa field `id` → artefak POC tampil di panel Analitik Konten — FIXED 2026-08-17
- Tanggal       : 2026-08-17
- Fase/Modul    : Guardrail INV-CLEAN-01 (`scripts/guardrails/_common.py`) ↔ CMS-08
- Gejala        : Sesudah POC CMS-CW2 selesai (dan melaporkan "41 dokumen artefak dihapus"), panel
                  **Konten Web → Analitik** tetap menampilkan baris "Penjaga INV-CMS Artikel · 2 tampilan".
                  Kelas bug yang SAMA dengan BUG-0127: gate hijau, produk tidak bersih.
- Root Cause    : `purge_guard_artifacts()` menghapus dokumen dengan `delete_many({"id": {"$in": ids}})`
                  lalu **menyaring id kosong** (`[i for i in ids if i]`). `content_stats` sengaja dikunci
                  pasangan `(kind, slug)` dan TIDAK punya field `id` → daftar id-nya kosong → tidak ada
                  yang dihapus, padahal pemindai sudah menandainya.
- Gate penangkap: `guard:no_test_pollution` (INV-CLEAN-01) MEMANG akan memerahkan gate berikutnya —
                  jadi pemindainya benar, mesin penghapusnya yang bolong.
- Perbaikan     : `scan_test_pollution()` kini membawa `_oid` (ObjectId Mongo) tiap temuan, dan
                  `purge_guard_artifacts()` menghapus lewat `{"_id": {"$in": [...]}}` untuk koleksi
                  tanpa konvensi `id` (langkah 2b).
- Regression    : `python scripts/purge_test_pollution.py` membersihkan artefak lama (verifikasi ulang
                  "0 artefak uji tersisa"); `verify_no_test_pollution.py` PASS 18 cek; `content_stats`
                  didaftarkan di `NO_PREFIX` (`verify_schema.py`) + didokumentasikan di
                  `docs/03_DATA_MODEL.md` §7 sebagai koleksi tanpa `id`.
- Status        : FIXED (bukti: `gate.sh` HIJAU 42/42 sesudah perbaikan + DB 0 artefak)


### BUG-0127 — Data uji guardrail/smoke/POC BOCOR ke koleksi operasional (customer "AAAA…" 60.000 karakter) — FIXED 2026-08-13
- Tanggal       : 2026-08-13
- Fase/Modul    : Lintas-modul (Guardrail/Gate ↔ data produk) · dilaporkan LANGSUNG oleh user
- Gejala        : User: *"sebenarnya ada bug di skrip ada nama customer aaaaaaaaaaaaaaaaaaaa itu yang
                  mengganggu"*. Di `/app/customers` ada satu customer bernama **60.000 karakter "AAAA…"**.
                  Penelusuran menemukan polusi jauh lebih luas — **157 dokumen sampah per satu kali
                  `gate.sh`**: `audit_logs` punya baris `summary` **60.016 karakter**; Inbox berisi
                  percakapan "Penjaga INV-PRICE-01"/"Penjaga INV-BOOK-02"/"Smoke Customer"/"Guard Lead
                  489704" (2 di antaranya menunjuk customer yang sudah dihapus = referensi yatim);
                  34 `notification_tasks` hantu di lonceng ops; **35 dari 48** `events` +
                  `automation_runs` artefak uji; CRM menyimpan lead & penawaran berisi karakter **NUL**
                  serta segmen "AdvSeg"; Media Library menyimpan aset `guard-media-*`;
                  `conversion_events` (outbox konversi iklan) **menumpuk permanen** karena tidak pernah
                  di-reset seed → angka konversi dasbor pemasaran membengkak.
- Root Cause    : RC-"uji mencemari produk". Penjaga & smoke SENGAJA menulis lewat API sungguhan (itu
                  benar — supaya perilaku server teruji), tetapi pembersihannya hanya menyentuh
                  **dokumen UTAMA**. SIDE-EFFECT-nya tidak: percakapan/pesan WA mock, notifikasi,
                  event + automation_runs, entri audit, bukti bayar + asetnya, outbox konversi.
                  Kasus terburuk: `selftest_booking_guards.py` mutasi **S01** sengaja MELEPAS
                  `max_length` dari `CustomerCreate`, lalu `verify_string_bounds.py` mengirim
                  `"A"*60000` → **tersimpan** (memang itu yang dibuktikan MERAH), kode di-revert,
                  **dokumennya tak pernah dihapus**. Pembatalan booking pun bukan pembersihan: booking
                  sengaja tak punya endpoint DELETE, jadi POC hanya `cancel` → barisnya tetap ada.
- Gate penangkap: TIDAK ADA — inilah inti masalahnya. `gate.sh` melaporkan **HIJAU 40/40** sementara
                  database kotor; yang menemukan akhirnya PENGGUNA. Pelajaran: *"gate hijau" ≠
                  "produk bersih"*.
- Perbaikan     : 1) `scripts/guardrails/_common.py` — mesin bersih-bersih bersama
                  `purge_guard_artifacts()` + SSOT penanda (`GUARD_MARKERS`, `GUARD_PHONE_PREFIXES`,
                  `PURGE_COLLECTIONS` 40 koleksi, `OVERLONG_RULES`) dengan cascade penuh:
                  payments/invoices/expenses/trips/locations/trip_shares/payment_proofs + aset media
                  bukti + messages/conversations (termasuk yang lahir dari lead uji + percakapan
                  yatim) + notification_tasks + events + automation_runs + audit_logs (termasuk yang
                  MENYEBUT kode `BK-00xx`) + conversion_events + landing_stats. Dokumen bersumber
                  `seed` DIKECUALIKAN → data demo tak pernah tersentuh.
                  2) Semua penulis data uji memanggilnya di `finally`: `verify_string_bounds`,
                  `verify_reference_integrity`, `verify_identity_race`, `verify_media_runtime`,
                  `verify_adversarial_5xx`, `verify_pricing_integrity`, `verify_booking_public`,
                  `selftest_booking_guards`, `scripts/mutation_smoke.py`,
                  `scripts/test_core_booking_v1.py`, `scripts/test_core_lp_f8.py`. Dokumen uji yang
                  namanya ambigu diberi penanda ("AdvSeg"→"Penjaga INV-5XX Segmen",
                  "RaceProbe"→"Penjaga INV-IDENT").
                  3) `backend/services/audit.py` — `_clip()` memotong `summary` (300) / snapshot
                  (2000) / nama aktor (120): mustahil lagi ada baris audit 60.016 karakter.
                  4) `scripts/seed_data.py` — `conversion_events` masuk daftar reset + reseed
                  memanggil purge (Media Library sengaja tidak di-reset, jadi purge yang menuntaskan).
                  5) Alat perbaikan `scripts/purge_test_pollution.py` (+ `--dry-run`) &
                  `scripts/db_snapshot.py` (bukti "tidak menumpuk" via diff sebelum/sesudah).
- Regression    : **INV-CLEAN-01** — `scripts/guardrails/verify_no_test_pollution.py` (STATIK: tiap
                  skrip penulis WAJIB memanggil mesin purge + `services/audit.py` wajib punya `_clip`;
                  RUNTIME: 40 koleksi operasional wajib 0 dokumen berpenanda uji & 0 field identitas
                  di luar batas) + `selftest_no_test_pollution.py` (**5 mutasi MERAH↔HIJAU**).
                  Di-wire PALING AKHIR di `gate.sh` supaya kebocoran penjaga mana pun langsung
                  memerahkan gate. Terdaftar di `memory/INVARIANTS.md` (dipaksa INV-META-01).
                  Penjaga ini SENGAJA tidak membersihkan apa pun — membersihkan di sana akan
                  menutupi kebocoran ("hijau-palsu").
- Status        : FIXED — bukti: 157 dokumen sampah dibersihkan · `gate.sh` **HIJAU 42/42 (0 FAIL,
                  0 SKIP)** DAN database **0 artefak SESUDAH gate** (sebelumnya 157) · POC
                  `test_core_booking_v1.py` **74/74** & `test_core_lp_f8.py` **84/84** dengan diff
                  snapshot DB hanya `sessions`/`audit login` (aktivitas sah) · `testing_agent_v3`
                  `iteration_89.json` (kebersihan data 100% + RBAC 20/20).


### QUAL-1 — Bare `except Exception: pass` menelan error senyap (auto-reply WA) — FIXED 2026-07-05
- Tanggal      : 2026-07-05
- Fase/Modul    : Ekosistem Guardrail (Layer B) / services/whatsapp.py:317
- Gejala        : Cek jam-kerja auto-reply dibungkus `except Exception: pass` (tanpa log), inkonsisten dgn sisa file yang selalu `logger.warning`. Menelan error senyap → sulit debug.
- Root Cause    : Kerja dangkal (broad-catch tanpa observability) lolos ke produksi.
- Gate penangkap: `scripts/guardrails/verify_effort_quality.py` (INV-QUALITY-01) — menandai bare swallow sbg pelanggaran BERAT.
- Perbaikan     : `except Exception as exc: logger.debug("cek jam kerja auto-reply gagal: %s", exc)`.
- Status        : FIXED (INV-QUALITY-01 HIJAU; ditemukan & diverifikasi oleh guardrail baru).


### M1 — Gate kontrak FE↔BE "hijau palsu" (guardrail, bukan produksi) — FIXED 2026-07-05
- Tanggal      : 2026-07-05
- Fase/Modul    : Putaran 12 (Phase-1) / scripts/verify_api_contract.py
- Gejala        : CHECK B "FE call → route backend" selalu lolos tanpa memeriksa apa-apa. FE memakai `apiClient.<m>("/path")` (axios instance, baseURL=`${BACKEND_URL}/api`), tapi regex gate hanya menangkap `axios.<m>`/`fetch(` → **0 call terdeteksi** → gate hijau palsu (mismatch/404 senyap bisa lolos).
- Root Cause    : Guardrail tak mengikuti pola panggilan FE nyata (regex ketinggalan saat kode tumbuh) — kelas "gate kurang" (docs/BUG_REGISTRY §aturan emas).
- Gate penangkap: `verify_api_contract.py` (dijalankan via `seed_reset.sh` di gate.sh).
- Perbaikan     : Regex tangkap `apiClient|axios.<m>(...)` semua gaya kutip + `fetch`; path relatif apiClient di-prefix `/api`; buang interpolasi query yang menempel (`/crm/rfm${q}`); pencocokan berbasis-segmen (arity + literal cocok, `{p}`/`{param}` = wildcard). Kini **260 call (167 path unik) tervalidasi**, 0 mismatch nyata.
- Regression    : Self-test — sisip `apiClient.get("/route-ngawur")` → gate MERAH (tunjuk route+file) → revert → HIJAU.
- Status        : FIXED (bukti: contract gate 260 call OK + self-test MERAH↔HIJAU + testing_agent Putaran 12).

### ID-RACE — Pembuatan customer tidak aman-balapan (duplikat kontak) — FIXED 2026-07-05
- Tanggal      : 2026-07-05
- Fase/Modul    : Putaran 12 (Phase-1) / services/identity.py + routers/customers.py + server.py
- Gejala        : `POST /customers` & `ensure_customer` melakukan find-then-insert (TOCTOU). Dua+ request paralel kontak sama sama-sama lolos pengecekan dedupe → customer GANDA. (Terbukti: tanpa index, 8 POST paralel → 2 duplikat.)
- Root Cause    : RC-01 turunan (TOCTOU) — dedupe hanya di aplikasi tanpa jaminan atomik DB.
- Gate penangkap: `scripts/guardrails/verify_identity_race.py` (INV-IDENT-01) — statik + probe N-paralel.
- Perbaikan     : Index UNIK-PARSIAL `customers.phone_normalized` (`$gt ""`, abaikan kosong) sebagai SSOT (server.py startup) + tangani `DuplicateKeyError`: `ensure_customer` → re-find pemenang (dedupe idempoten); `create_customer` → 409; `update_customer` → 409.
- Regression    : Self-test — drop index → race buat 2 duplikat → MERAH → buat ulang index → HIJAU (2xx=1, 409=7, 5xx=0).
- Status        : FIXED (bukti: guardrail INV-IDENT-01 PASS + self-test + testing_agent Putaran 12).

### SET-1 — Tarif pricing/settings tak divalidasi (harga negatif/absurd) — FIXED 2026-07-05
- Tanggal      : 2026-07-05
- Fase/Modul    : Putaran 12 (Phase-1) / routers/settings.py
- Gejala        : `PATCH /settings` menyimpan `pricing_rules`/`pricing_defaults` apa adanya. Nilai negatif → harga negatif; `dp_percent`>100 → DP>total; non-numerik → 0 senyap (services/pricing.py `_num` koersi tanpa clamp).
- Root Cause    : Tak ada validasi di titik-tulis pengaturan (nilai dipakai langsung dalam perkalian harga).
- Gate penangkap: `scripts/guardrails/verify_settings_bounds.py` (INV-SET-01) — statik + runtime.
- Perbaikan     : `_validate_pricing` di settings.py → tolak tarif negatif, `dp_percent`∉[0,100], `min_rental_hours`<0, & non-numerik dgn **HTTP 400** pesan jelas (mis. "Nilai 'fuel_per_km' tidak boleh negatif", "Field 'x' harus berupa angka").
- Regression    : Self-test — nonaktifkan `_validate_pricing` → 6 tarif buruk tersimpan 200 senyap → MERAH → revert → HIJAU (semua 400, valid 200).
- Status        : FIXED (bukti: guardrail INV-SET-01 PASS + self-test + testing_agent Putaran 12).


### FEAT-E17 — Reschedule booking (jadwal ulang) — SELESAI 2026-07-03
- Fase/Modul: Phase A13 / bookings. Endpoint `/bookings/{id}/reschedule` re-cek INV-4/INV-21/RC-07 (exclude self) + event `booking.rescheduled` + rule WA + `BookingRescheduleDialog`. Bukti: gate 13/13 + testing_agent iter 53 (reschedule OK, tolak cancelled/completed & end<=start & bentrok). Status: DONE.

### FEAT-E18 — DP-gate/hold + auto-expire — SELESAI 2026-07-03
- Fase/Modul: Phase A13 / bookings+payments+scheduler. `require_dp`→`hold` (mereservasi armada; INV-4/INV-10), DP≥dp_amount→auto-`confirmed` (emit booking.confirmed, idempotent), `scan()` auto-expire hold telat→`cancelled`+`booking.hold_expired`. Bukti: gate 13/13 + iter 53. Status: DONE.

### FEAT-E19 — Booking publik self-service + approve/reject — SELESAI 2026-07-03
- Fase/Modul: Phase A13 / public+bookings. `/api/public/booking`(rate-limit+honeypot)→`pending`(source=website)+`booking.requested`; ops `/approve`(assign+auto-price→confirmed) & `/reject`. FE `/booking` + antrian approval + ThankYou kode. Bukti: gate 13/13 + iter 53 (BE 75/75). Status: DONE.

---

### GAP-G1 — Pembatalan booking tidak memberi tahu pelanggan (celah CRM/WA)
- Tanggal      : 2026-07-03
- Fase/Modul    : Phase A12 / bookings + automation
- Gejala        : `booking.cancel` tak memancarkan event → tak ada WA "dibatalkan/jadwal ulang" ke pelanggan.
- Root Cause    : Tidak ada tipe event `booking.cancelled` + tidak ada rule.
- Gate penangkap: testing_agent iter 52 (event + automation run) + self-test curl.
- Perbaikan     : Emit `booking.cancelled` di cancel_booking (payload SSOT wa_payload, dedupe per booking) + tambah ke EVENT_TYPES + rule seed "Notifikasi pembatalan booking" (send_wa + create_notification).
- Regression    : Idempotent (tak ada run duplikat pada cancel berulang); RC-04 resource-release tetap.
- Status        : FIXED (bukti: gate HIJAU 13/13 + iter 52 BE 38/38 + FE smoke).

### GAP-G2 — POD via dispatch tidak menyelesaikan trip / senyap ke pelanggan (celah CRM/WA)
- Tanggal      : 2026-07-03
- Fase/Modul    : Phase A12 / dispatch + trips
- Gejala        : `trip.completed` hanya dari checkout driver; POD via dispatch tidak memancarkannya → WA "terima kasih + ulasan" tak terkirim bila ops menutup via POD.
- Root Cause    : Dua jalur penyelesaian tak konsisten (RC-03 turunan) — dispatch POD hanya simpan foto.
- Gate penangkap: testing_agent iter 52 (POD → completed + trip.completed run) + self-test curl.
- Perbaikan     : `dispatch.upload_pod` delegasi ke SSOT `services.trips.finalize_trip_completion` (bebaskan armada + KM + selesaikan booking + emit `trip.completed` idempotent).
- Regression    : Checkout driver tetap emit trip.completed; efek identik (anti split-brain).
- Status        : FIXED (bukti: gate HIJAU 13/13 + iter 52 BE 38/38 + FE smoke).

---

### BUG-0010 — Rate-limit login tidak persisten (hilang saat restart / tak lintas-worker)
- Tanggal      : 2026-07-03
- Fase/Modul    : Phase A11 / auth + services/ratelimit
- Gejala        : Counter kegagalan login in-memory → reset saat restart backend & tak terbagi antar worker (anti brute-force lemah bila diskalakan).
- Root Cause    : RC-10 (ratelimit persistence) — state disimpan di memori proses (deque), bukan store bersama.
- Gate penangkap: verify_data_integrity / testing_agent (auth flow) + verifikasi curl 8×401→429.
- Perbaikan     : Pindah ke koleksi Mongo `login_failures` + TTL index (server.py startup). Fungsi `note_failure_db/failure_count_db/clear_failures_db` (ratelimit.py); auth.py memakai versi DB. Ambang 8/(ip+email)/5mnt → ke-9=429; login sukses membersihkan budget.
- Regression    : testing_agent iter 51 (429 + per-key isolation + budget-clear) PASS; bertahan lintas restart.
- Status        : FIXED (bukti: GATE_RECEIPT HIJAU 13/13 + iter 51 BE 52/52).

### BUG-0011 — Uang disimpan sebagai float (potensi drift akumulasi)
- Tanggal      : 2026-07-03
- Fase/Modul    : Phase A11 / core_utils + bookings/payments/expenses/invoices/payroll
- Gejala        : Nilai uang `float` + round(...,2) → risiko drift akumulasi (mis. 0.1+0.2) pada operasi berulang.
- Root Cause    : RC-11 (money as float) — IDR tak punya sub-satuan; seharusnya integer rupiah.
- Gate penangkap: verify_data_integrity INV-11 (money-integral) + testing_agent (cek whole-number).
- Perbaikan     : Helper `core_utils.money()` (int rupiah) di semua write-point uang; skrip `migrate_money_to_int.py` di-wire ke seed_reset.sh (23 dok dinormalisasi); INV-11 ditambahkan.
- Regression    : testing_agent iter 51 (booking/payment/expense/invoice/payroll semua integer) PASS.
- Status        : FIXED (bukti: GATE_RECEIPT HIJAU 13/13 + iter 51 BE 52/52).

### BUG-0001 — Race overpayment saat pembayaran paralel (regresi RC-01)
- Tanggal      : 2026-07-03
- Fase/Modul    : Phase A11 / routers/payments
- Gejala        : Pada implementasi RC-01 awal, jalur pembayaran meng-overwrite `paid_amount` via recompute Σpayments → di tengah balapan Σ bisa lagging → mereset reservasi → celah overpay (ditemukan `verify_concurrency`).
- Root Cause    : RC-01 (TOCTOU) — dua SSOT untuk paid_amount ($inc atomik vs recompute).
- Gate penangkap: verify_concurrency.py (RC-01 / INV-2) — N pembayaran paralel Σ ≤ total.
- Perbaikan     : `create_payment` jadikan `find_one_and_update $inc` sebagai SSOT tunggal; JANGAN recompute/overwrite di jalur bayar; payment_status diturunkan dari dokumen `AFTER`.
- Regression    : verify_concurrency konsisten 3×200 (Σ=900k) 4 run; testing_agent iter 51 (overpay 400, paid≤total, paid=Σpayments) PASS.
- Status        : FIXED (bukti: GATE_RECEIPT HIJAU 13/13 + iter 51).

---

### CMS-D3 — Paginasi & search di admin CMS list (skalabilitas) — SELESAI 2026-07-17
- Tanggal      : 2026-07-17
- Fase/Modul    : CMS CW0 Hardening / routers/content.py + features/app/ContentManager.jsx + server.py (CORS)
- Gejala        : `GET /content/{resource}` hardcoded `to_list(500)` tanpa paginasi. FE menampilkan semua item sekaligus → skalabilitas buruk saat konten banyak (mis. 500+ artikel).
- Root Cause    : Endpoint list tidak menerima `limit`/`offset`; tak ada mekanisme pagination.
- Gate penangkap: (Enhancement) — manual review CMS_REVIEW_AND_ENHANCEMENT_PLAN.md §2.
- Perbaikan     : (Backend) tambah `limit` (default 100, 1..500) + `offset` (>=0) query params + response headers `X-Total-Count`/`X-Limit`/`X-Offset`; MongoDB `.skip(offset).limit(limit)` + `count_documents(query)`. (CORS) `expose_headers=["X-Total-Count","X-Limit","X-Offset"]` di server.py. (Frontend) tombol "Muat Lebih Banyak (X tersisa)" + info "Menampilkan X dari Y"; state append; reset saat tab/search berubah.
- Regression    : Manual test — 6→66 artikel dgn seed 60 test items → info "Menampilkan 50 dari 66" + tombol muncul → klik → "Menampilkan 66 dari 66"; limit=600 → 422; invalid offset<0 → 422; search q=Bali → total & headers akurat.
- Status        : FIXED (bukti: `gate.sh` HIJAU 22/22 no regression + screenshot FE + curl 5 skenario).

### CMS-D1 — Input non-numerik di CMS crash 500 — VERIFIED FIXED (dari sesi sebelumnya)
- Verified     : `POST /content/packages {"days":"abc"}` → HTTP 400 `{"detail":"Field 'days' harus berupa angka"}` (bukan 500).
- Fix at       : `content.py::_clean` try/except (ValueError/TypeError) → 400.

### CMS-D2 — Slug/kode tidak unik per resource — VERIFIED FIXED (dari sesi sebelumnya, G1)
- Verified     : POST duplikat slug `test-slug-cw0` → HTTP 409 `{"detail":"Slug '...' sudah dipakai"}`.
- Fix at       : `content.py::_ensure_unique_slug` dipanggil di create/update.

---

## SESI 2026-08-10 — E27 (Kalender Keberangkatan: lapisan risiko + INV-21 dua arah)

### BUG-0101 — Perawatan bisa dijadwalkan di atas keberangkatan aktif (INV-21 satu arah)
- Tanggal       : 2026-08-10
- Fase/Modul    : E27 / maintenance + kalender keberangkatan
- Gejala        : `POST /api/maintenance` dgn `status=scheduled` + `start_date`/`end_date` yang menutupi
                  window booking `confirmed` LOLOS (HTTP 200). Armada jadi "dirawat" sekaligus "berangkat";
                  `verify_data_integrity` INV-21 akan MERAH pada data hasil pemakaian normal UI.
- Root Cause    : RC-16 (validasi ketersediaan tidak simetris). Jalur booking memanggil
                  `find_maintenance_conflicts`, tetapi jalur perawatan TIDAK pernah memanggil
                  `find_conflicts` → invariant hanya dijaga dari satu sisi.
- Gate penangkap: TIDAK ADA sebelumnya (gate hanya memeriksa DB hasil seed yang memang bersih).
                  Ditemukan POC isolasi `test_core_conflict.py` (KELAS 3) yang menembak API nyata.
- Perbaikan     : `routers/maintenance.py` — `_blocking_window()` + `_assert_no_departure_clash()`
                  di `POST /maintenance` dan `PATCH /maintenance/{id}` (nilai EFEKTIF rec+updates),
                  dibungkus `vehicle_lock` (mutex per-armada, sama dgn jalur booking → anti-TOCTOU).
                  Pesan 400 menyebut kode keberangkatan yang bentrok.
- Regression    : `test_core_conflict.py` KELAS 3 (harus 400). INV-RACE-01 tetap hijau (lock terpasang).
- Status        : FIXED (bukti: `test_core_conflict.py` OK=6/GAP=3/FAIL=0; `memory/GATE_RECEIPT.md` HIJAU 22/22)

### BUG-0102 — Deteksi "bentrok" kalender praktis mati + berbasis identitas yang salah
- Tanggal       : 2026-08-10
- Fase/Modul    : E27 / frontend kalender
- Gejala        : Banner bentrok SELALU 0 (`CONFLICT BANNER: False`, `CONFLICT-MARKED CHIPS: 0`) —
                  sesi sebelumnya berhenti di sini dan mengira ini bug rendering.
- Root Cause    : Bukan bug UI. (a) INV-4 sudah dikunci di SEMUA jalur tulis sehingga data bentrok armada
                  tak bisa terbentuk; (b) deteksi FE mengelompokkan berdasarkan `vehicle_name` (bukan
                  `vehicle_id`) dan `/bookings/calendar` bahkan tidak mengirim `vehicle_id`;
                  (c) status `completed` ikut dihitung → potensi false positive; (d) permintaan publik
                  `pending` selalu `vehicle_id=None` → risiko nyata (menumpuk tanpa diproses) TAK PERNAH terlihat.
- Gate penangkap: TIDAK ADA (tak ada gate yang menagih "peringatan harus relevan/bisa terjadi").
- Perbaikan     : Lapisan risiko dipindah ke backend `services/attention.py` +
                  `GET /api/departures/attention` (8 kelas risiko, berbasis `vehicle_id`, hanya status aktif
                  untuk bentrok armada). FE menampilkan panel "Perlu Perhatian" + chip filter + badge.
- Regression    : Seed E27 menghadirkan risiko NYATA (pending menunggu, bentrok sopir, tenggat DP) tanpa
                  melanggar invariant → panel selalu punya data untuk diverifikasi.
- Status        : FIXED (bukti: screenshot panel total=5, chip filter mengubah `dc-month-total` 8→2)

### BUG-0103 — FALSE-GREEN: `verify_delivery` melewati SELURUH cek karena drift ACTIVE_PHASE
- Tanggal       : 2026-08-10
- Fase/Modul    : E27 / guardrail
- Gejala        : `verify_delivery` selalu PASS. Padahal `ACTIVE_PHASE: CMS-G10` tak pernah cocok dengan
                  heading `### PHASE CMS-G1..G10` → `items` kosong → `return 0` (skip senyap).
                  Artinya D1/D1b/D2 (deliverable & orphan endpoint) TIDAK pernah dijalankan.
- Root Cause    : RC-FALSE-GREEN (skip diperlakukan sebagai lulus) — tema berulang di repo ini.
- Perbaikan     : `scripts/verify_delivery.py` — bila ACTIVE_PHASE ada tetapi tak cocok heading mana pun →
                  MERAH (exit 1) dgn pesan "DRIFT MANIFEST". Ditambah `NON_FE_ENDPOINTS` allowlist
                  ber-justifikasi utk `/api/sitemap.xml` & `/api/robots.txt` (dikonsumsi crawler, bukan FE).
- Regression    : Self-test: ACTIVE_PHASE palsu → rc=1; ACTIVE_PHASE `E27` → rc=0.
- Status        : FIXED (bukti: self-test MERAH↔HIJAU di log sesi)

### BUG-0104 — `verify_schema` MERAH-palsu: `bookings.vehicle_id` dianggap wajib tanpa syarat
- Tanggal       : 2026-08-10
- Fase/Modul    : E27 / guardrail
- Gejala        : Begitu ada permintaan booking publik nyata (E19, `vehicle_id=None`, status `pending`),
                  `verify_schema` FAIL "bookings.vehicle_id (→vehicles) wajib tapi kosong".
- Root Cause    : Aturan gate bertentangan dengan SSOT `docs/03_DATA_MODEL.md` yang menulis eksplisit
                  "`vehicle_id`(nullable saat status=pending)".
- Perbaikan     : `REQUIRED_EXEMPT` ber-predikat (pending/draft/cancelled) + jejak transparan
                  "[n dikecualikan: alasan]" pada output PASS. Bukan bypass — menyelaraskan gate ke SSOT.
- Regression    : `verify_schema` 77 PASS / 0 FAIL pada seed berisi 2 booking pending.
- Status        : FIXED

### BUG-0105 — `verify_auth_coverage` MERAH pada artefak SEO publik
- Tanggal       : 2026-08-10
- Fase/Modul    : E27 / guardrail
- Gejala        : `GET /sitemap.xml` & `GET /robots.txt` dianggap "endpoint bocor tanpa auth".
- Root Cause    : Allowlist belum mencakup artefak SEO yang MEMANG harus publik (crawler tak bisa login).
- Perbaikan     : Ditambahkan ke `PUBLIC_ENDPOINTS` dgn justifikasi tertulis.
- Status        : FIXED (INV-AUTH-01: 245 cek, 0 pelanggaran)

### HYGIENE-0106 — Script gate runtime meninggalkan `notification_tasks` yatim
- Tanggal       : 2026-08-10
- Gejala        : Menjalankan `verify_schema` SETELAH gate runtime → FAIL "notification_tasks.booking_id
                  → bookings: 10 referensi MENGGANTUNG" (bukan bug produksi; residu cleanup tes).
- Perbaikan     : `verify_concurrency.py`, `verify_cross_entity.py`, `verify_state_machine.py` kini
                  menghapus `notification_tasks` by `booking_id` DAN `payload.booking_id`.
- Status        : FIXED

## RINGKASAN RC TERSERING (update berkala)
| RC | Jumlah | Catatan |
|----|--------|---------|
| RC-01 (TOCTOU/race) | 1 | Fixed — atomic $inc SSOT (payments.py) |
| RC-10 (ratelimit persist) | 1 | Fixed — Mongo `login_failures`+TTL |
| RC-11 (money float→int) | 1 | Fixed — `money()` + migrasi + INV-11 |
| RC-02..RC-09 | 8 | Fixed sebelumnya (Phase A10) |

### BUG-0107 — RBAC-CAL-01: peran `driver` bisa membuka Kalender Keberangkatan (UI + API)
- Tanggal       : 2026-08-10
- Fase/Modul    : E28 / RBAC (frontend route + backend section + endpoint)
- Sumber temuan : `testing_agent_v3` iterasi 72 (F-G.2) — dilaporkan CRITICAL, dikonfirmasi NYATA.
- Gejala        : Login `driver@demo.local` → `/app/calendar` terbuka penuh (grid, panel Perlu
                  Perhatian, tombol aksi). Probe API: `GET /api/departures/attention`,
                  `GET /api/bookings/calendar`, `GET /api/bookings/calendar/export` → **HTTP 200**.
- Root Cause    : Tiga lapis gagal bersamaan — (1) `ROLE_MENU_ALLOWLIST.driver` memuat `"calendar"`
                  sehingga `RoleGuard` meloloskan; (2) `permissions_config.SECTION_ACCESS` tidak
                  mendeklarasikan section `calendar` sama sekali, sehingga `require_section` tak
                  terpakai dan endpoint hanya memakai `get_current_user`; (3) guardrail
                  `INV-RBAC-03` memakai daftar `FORBIDDEN` hardcoded yang tak pernah menyebut modul
                  baru → hijau palsu.
- Perbaikan     : `calendar: {owner, ops_admin}` (+ `driver-workspace`, `quotations`, `inbox`) di
                  `SECTION_ACCESS`; `require_section("calendar")` di `routers/departures.py` &
                  2 endpoint kalender `routers/bookings.py`; `"calendar"` dicabut dari allowlist
                  driver; `RoleGuard` kini memberi toast "Akses ditolak" + mengalihkan ke beranda
                  peran (driver → `/app/driver-workspace`).
- Guardrail     : **INV-RBAC-04** (sinkron 2-arah FE↔BE, membaca matriks backend langsung).
- Verifikasi    : driver → 403 di 3 endpoint kalender; owner & ops_admin → 200 (regresi aman).
- Status        : FIXED

### BUG-0108 — RBAC-SCOPE: driver melihat SELURUH booking & daftar sopir (kebocoran data row-level)
- Tanggal       : 2026-08-10
- Fase/Modul    : E28 / RBAC cakupan data (`routers/bookings.py`, `routers/drivers.py`)
- Sumber temuan : audit lanjutan sesi ini (bukan dari testing agent) saat menyapu peran driver.
- Gejala        : `GET /api/bookings` sebagai driver → 8/8 booking termasuk trip driver lain,
                  lengkap `customer_name`/`total_amount`/`paid_amount`; `GET /api/drivers` → semua
                  sopir + nomor telepon; `GET /api/drivers/{id}/performance` bebas diakses.
- Root Cause    : RBAC hanya dijaga di level **section** (pintu modul). Setelah pintu terbuka,
                  query tak punya filter kepemilikan, padahal SSOT `docs/05_NAVIGATION_MAP.md` §3
                  menulis "👁️ trip miliknya" / "👁️ profil sendiri".
- Perbaikan     : `backend/services/rbac_scope.py` (SSOT pemetaan user→driver + penyaring,
                  fail-closed) dipakai di `list_bookings`, `get_booking`, `list_drivers`,
                  `get_driver`, `driver_performance`; `routers/driver.py::_resolve_driver`
                  didelegasikan ke SSOT yang sama (hapus duplikasi logika).
- Guardrail     : **INV-RBAC-05** (statik: wajib ada pemanggilan `await scope_*`/`can_view_*`).
- Verifikasi    : driver → 3 booking (miliknya) & 1 profil sopir; `/api/driver/{my-trips,tasks,
                  summary}` tetap 200; owner tetap 8 booking / 2 sopir.
- Status        : FIXED


### BUG-0109 — Outbox konversi iklan tak pernah dipanggil (rantai terputus)
- Tanggal      : 2026-08-11
- Fase/Modul    : Fase F3 / marketing-ads
- Gejala        : Tidak ada gejala terlihat — TIDAK ADA error, TIDAK ADA log. Halaman Kesehatan Pelacakan selalu kosong kecuali saat tombol "Kirim Event Uji" ditekan.
- Root Cause    : `services/conversions.py` (outbox + payload + retry) dibangun & lulus POC di fase F2, tetapi tidak ada satu pun pemanggil di jalur bisnis. `rg conversions backend` → hanya `routers/marketing.py`. Akibatnya `booking.confirmed` & `payment.recorded` — dua konversi paling bernilai yang HANYA diketahui backend — tidak pernah dilaporkan ke Meta/Google, sehingga algoritma iklan dilatih memakai "form terkirim" saja (mengoptimalkan pengisi form, bukan pembeli).
- Gate penangkap: TIDAK ADA saat itu (POC hanya menguji modul secara terisolasi, bukan keterhubungannya). Ditutup guardrail baru **INV-CONV-01** (`scripts/guardrails/verify_conversion_hooks.py`): memaksa `services/events.emit` memanggil `conversion_hooks.handle_event`, memaksa 3 event wajib terpetakan & benar-benar dipancarkan, memaksa unique index + penanganan DuplicateKeyError, dan memaksa `dispatch_pending` terjadwal di `server.py`.
- Fix           : `services/conversion_hooks.py` (resolver identitas lead↔customer↔booking↔payment, termasuk membentuk `fbc` dari `fbclid`) + satu titik pemanggilan di `services/events.emit` + pekerja retry di scheduler `server.py` + tombol manual `POST /api/tracking/dispatch`.
- Pelajaran     : "Modul lulus POC" ≠ "modul terpakai". Setiap modul kritis wajib punya guardrail KETERHUBUNGAN, bukan hanya guardrail kebenaran internal.

### BUG-0110 — Payload Google Data Manager & versi Meta usang (akan ditolak saat kunci diisi)
- Tanggal      : 2026-08-11
- Fase/Modul    : Fase F3 / services/conversions.py
- Gejala        : Tidak terlihat sama sekali selama kredensial kosong (status selalu `skipped`). Baru akan muncul sebagai penolakan 400 dari Google/Meta pada hari user menempel kunci asli — saat itu penyebabnya sulit ditebak.
- Root Cause    : Kode mengikuti dokumentasi lama: `destinations[].operatingAccount.product` (field sudah diganti `accountType`), `consent: "CONSENT_GRANTED"` (nilai sah: `GRANTED`/`DENIED`), tanpa `encoding: "HEX"` (wajib untuk data ter-hash), tanpa `destinationReferences` per event. Meta masih `v25.0` dan tanpa `appsecret_proof`.
- Gate penangkap: tidak ada gate yang bisa memvalidasi kontrak pihak ketiga secara statik; ditangkap dengan **membandingkan kode terhadap playbook resmi terbaru** sebelum membangun UI, lalu dibekukan sebagai assertion di `scripts/test_core_ads_f3.py` (POC-3: 12 cek field-by-field, termasuk memastikan telepon Google di-hash sebagai E.164 ber-'+' sedangkan Meta tanpa '+').
- Fix           : `build_google_payload` ditulis ulang sesuai kontrak baru; Meta default `v26.0` + `appsecret_proof`; POC menguji kedua payload sampai level nama field.
- Pelajaran     : Integrasi pihak ketiga membusuk diam-diam. Sebelum menambah fitur di atasnya, cocokkan ulang payload dengan dokumentasi resmi & bekukan hasilnya jadi assertion.

### BUG-0111 — Satu template landing page selalu HTTP 500 + props template dibuang senyap
- Tanggal       : 2026-08-11
- Fase/Modul    : Fase F8 / services/landing_blocks.py + services/landing_templates.py
- Gejala        : `POST /api/landing/pages` dengan template `armada-cepat` balas **HTTP 500** (3 template lain 200). Di UI: pengguna menekan satu kartu template dan hanya melihat toast "Gagal membuat halaman", tanpa petunjuk bahwa kartu LAIN berfungsi. Gejala kedua lebih berbahaya karena TANPA error: pesan sukses formulir, tenggat hitung mundur, dan tombol banner CTA HILANG dari halaman yang sudah tayang.
- Root Cause    : (a) `landing_templates` mengirim `trust_badges.items` sebagai daftar STRING sementara `_trust()` memanggil `(it or {}).get("label")` → `AttributeError: 'str' object has no attribute 'get'`; `validate_blocks` tidak punya pagar sehingga error naik menjadi 500 walau docstring-nya sudah menjanjikan "tidak melempar". (b) Template memakai nama props yang TIDAK ADA di skema (`success_text` vs `thank_you`, `deadline` vs `until`, `cta` vs `ctas`, `vehicle_type`, `title` pada trust_badges) → validator membuangnya tanpa peringatan.
- Gate penangkap: TIDAK ADA. `test_core_ads.py` (POC F1) menguji `validate_blocks` dengan blok yang dirakit tangan, bukan dengan TEMPLATE NYATA — jadi ketidaksesuaian template↔skema tak pernah tersentuh. Ditutup guardrail baru **INV-LP-02** (`scripts/guardrails/verify_landing_contract.py`) yang benar-benar MEMBANGUN setiap template lalu menuntut: tiap key props ada di daftar kanonik, nilai terisi tidak boleh hilang, daftar tidak boleh menyusut, `validate_blocks` tidak melempar untuk bentuk aneh, tiap tipe blok bisa dibuat dari kosong, tiap template punya blok konversi, dan renderer frontend punya `case` untuk SEMUA tipe blok.
- Fix           : `_trust` menerima string maupun objek; `validate_blocks` dipagari try/except per blok (turun jadi peringatan + kembali ke setelan bawaan); seluruh nama props template diselaraskan ke kontrak kanonik; alias lama (`thank_you`, `until`, `text`, `cta`) tetap diterima agar data yang sudah tersimpan tidak rusak.
- Pelajaran     : Menguji sebuah validator dengan data yang kita rakit sendiri hanya membuktikan validator konsisten dengan asumsi kita. Yang wajib diuji adalah PASANGANNYA di produksi (template ↔ skema ↔ renderer). Guardrail harus diturunkan dari sumber yang benar-benar dipakai runtime, bukan dari daftar manual.

### BUG-0112 — Semua gambar & video halaman iklan 404 karena URL ditulis ke rute yang tidak ada
- Tanggal       : 2026-08-11
- Fase/Modul    : Fase F8 / routers/landing.py + routers/public.py
- Gejala        : Unggah media SUKSES (HTTP 200), dokumen `media_assets` benar, tetapi SETIAP foto/video di editor maupun halaman iklan publik gagal dimuat. Tidak ada error backend, tidak ada log — hanya kotak gambar rusak di halaman yang trafiknya dibayar iklan.
- Root Cause    : `upload_media` menyimpan `doc["url"] = f"/api/media/{id}"`, sedangkan endpoint pembacanya berada di router publik ber-prefix `/api/public` sehingga rute nyatanya `/api/public/media/{id}`. Docstring `media_store.py` bahkan sudah menuliskan jalur yang benar — kodenya yang menyimpang. Masalah kedua: `storage_ready()` bergantung `EMERGENT_LLM_KEY`, jadi tanpa kunci seluruh Media Library mati (HTTP 400) padahal fitur ini tidak butuh AI.
- Gate penangkap: TIDAK ADA. Semua uji sebelumnya berhenti pada "unggah 200 + metadata benar"; tidak satu pun MEMBACA KEMBALI URL yang disimpan. Ditutup guardrail baru **INV-MEDIA-02** (`scripts/guardrails/verify_media_safety.py`): membandingkan prefix URL yang ditulis router dengan rute yang benar-benar terdaftar di router publik, plus mengeksekusi `media_store.fetch` dengan jalur berbahaya (`../`, `/etc/passwd`, NUL) untuk memastikan pagar path-traversal hidup.
- Fix           : URL dibangun satu pintu lewat `media_url()` → `/api/public/media/{id}`; `media_store` diberi dua backend (`local` sebagai DEFAULT tanpa kredensial + `objstore` bila kunci ada), thumbnail `?thumb=1`, dimensi gambar, dan `_local_abs()` sebagai pagar anti path-traversal. POC `scripts/test_core_lp_f8.py` kini MENGAMBIL URL itu tanpa header Authorization dan membandingkan byte-nya dengan berkas asli.
- Pelajaran     : "Unggah berhasil" bukan bukti "gambar tampil". Uji integrasi penyimpanan wajib menutup lingkaran penuh: tulis → simpan URL → BACA lewat URL itu sebagai pengunjung anonim. Dan fitur yang tidak butuh kredensial jangan digantungkan pada kredensial.

---

### BUG-0113 — Satu field bertipe salah dari klien membuat operasi media balas HTTP 500
- Tanggal       : 2026-08-11
- Fase/Modul    : Fase 3 (Media Library SATU) / routers/media.py + services/media_lib.py
- Gejala        : `PATCH /api/media/{id}` dengan body `{"alt": {...}, "folder_id": 5}` → **HTTP 500 Internal Server Error**. Dari sisi pengguna: dialog "Ubah aset" gagal dengan pesan teknis tanpa penjelasan, dan tidak jelas apa yang harus diperbaiki. Endpoint lain yang menerima `folder_id`/`mode` dari body punya penyakit yang sama (`bulk-move`, `crop`).
- Root Cause    : RC-05 (validasi input tidak lengkap / koersi tipe). Pola `(body.get("folder_id") or "").strip()` mengasumsikan nilai selalu string; bila klien mengirim angka/objek, `.strip()` melempar `AttributeError` yang tidak tertangkap `except MediaLibError` → 500. Pola yang sama tersebar di 14 tempat `services/media_lib.py`.
- Gate penangkap: TIDAK ADA sebelumnya. Penjaga statik INV-MEDIA-03 hijau karena kodenya "terlihat benar", dan INV-5XX-01 hanya menembak endpoint CMS/finance — tidak satu pun jalur media. Ditemukan pada **percobaan pertama** gate runtime baru **INV-MEDIA-04** (`verify_media_runtime.py`, 14 permintaan adversarial ke jalur media). Dikunci juga secara STATIK di INV-MEDIA-03: `.strip()` di modul media wajib lewat `str(...)` (mutasi self-test `M24` membuktikan aturan itu menggigit).
- Fix           : koersi `str(...)` di `routers/media.py` (`update_media.folder_id`, `bulk_move.folder_id`, `crop_media.mode`) dan di seluruh `services/media_lib.py` (14 tempat: `folder_or_404`, `_ancestors`, `list_folders`, `create_folder`, `update_folder`, `asset_or_404`, `list_assets`, `register_asset`, `move_assets`, `usage`). Input bertipe salah kini berujung 400/404 berALASAN.
- Pelajaran     : penjaga STATIK membuktikan bentuk kode, bukan perilaku. Selama tidak ada yang benar-benar MENGIRIM `folder_id: 5`, bug ini tak terlihat oleh mata maupun oleh gate. Setiap modul baru butuh sepasang penjaga: satu statik (murah, mencegah pola), satu runtime (menembak input tak wajar ke jalur nyata).

---

### BUG-0114 — Nama 60.000 karakter TERSIMPAN & merusak tabel ERP (gate hijau karena hanya menuntut "bukan 5xx")
- Tanggal       : 2026-08-12
- Fase/Modul    : BOOKING-V1 / backend/schemas*.py (semua permukaan tulis) + frontend DataTable
- Gejala        : Baris `BK-0017` pada tabel Booking ERP melebar sampai kolom Armada/Total/Status terdorong keluar layar; kolom Customer berisi "AAAA…" ribuan karakter. Ditemukan mata sendiri saat verifikasi UI ops, BUKAN dari laporan pengguna.
- Root Cause    : RC-05 (validasi input tidak lengkap). Tidak satu pun field teks punya `max_length` — 389 dari 406 field `str` tak berbatas. Guardrail adversarial `verify_adversarial_5xx.py` sudah lama MENGIRIM `"A" * 60000` ke endpoint tulis, tetapi satu-satunya yang dituntut adalah "tidak 5xx"; server menjawab 200 dan nilai raksasa itu TERSIMPAN di `customers.name`, lalu ikut ter-snapshot ke `bookings.customer_name`.
- Gate penangkap: TIDAK ADA (ironisnya justru guardrail yang MEMBUAT datanya). Ditutup guardrail baru **INV-STR-01** (`scripts/guardrails/verify_string_bounds.py`): statik AST menuntut `max_length` pada setiap field teks bernama sensitif di `backend/schemas*.py`; runtime menembak 60.000 karakter ke 3 permukaan tulis (ERP + 2 publik) dan menuntut **4xx**, sekaligus memastikan nilai normal tetap 2xx (anti over-block). Self-test mutasi `S01` membuktikan penjaga MERAH saat batas dilepas.
- Fix           : 170 field teks sensitif diberi `max_length` lewat codemod AST sekali-pakai `scripts/_codemod_string_bounds.py` (batas dari kenyataan pemakaian: nama 120, telepon 24, email 160, alamat 300, catatan 1000/2000, pesan 4000 = batas WhatsApp). Pertahanan berlapis di UI: `components/shared/DataTable.jsx` memotong (`truncate` + `max-w`) sel teks mentah & menaruh nilai utuh di tooltip, jadi data ekstrem apa pun tidak lagi merusak tata letak. Data lama yang sudah tercemar dipotong sekali.
- Regression    : INV-STR-01 (statik + runtime) + mutasi S01 di `selftest_booking_guards.py`.
- Pelajaran     : **"tidak 5xx" BUKAN "tervalidasi".** Sebuah penjaga bisa hijau bertahun-tahun sambil MENANAM data rusak. Uang sudah dijaga batas bawah (INV-NUM-01 `ge=`); teks butuh batas atas yang sepadan — dan penjaganya harus menuntut PENOLAKAN, bukan sekadar ketiadaan error.
- Status        : FIXED (bukti: gate HIJAU 38/38 termasuk INV-STR-01 187 cek + self-test S01 MERAH↔HIJAU).

### BUG-0115 — Unit uji "Smoke Vehicle" TAYANG di katalog publik & bisa dipesan tamu
- Tanggal       : 2026-08-12
- Fase/Modul    : BOOKING-V1 / services/booking_search.py + scripts/mutation_smoke.py
- Gejala        : Hasil pencarian di `/booking` (halaman pemesanan publik) memuat kartu **"Smoke Vehicle · Hiace Commuter · Rp 3.300.000"** lengkap dengan tombol "Pilih unit" — armada yang tidak pernah ada, dibuat oleh smoke test write-path setiap kali gate dijalankan.
- Root Cause    : `publishable_filter()` menganggap `publish_to_web` yang KOSONG sebagai "boleh dijual" (`$exists: false` / `None` diloloskan) demi "data lama tetap tayang". Artinya setiap dokumen `vehicles` yang lahir dari jalur non-formulir (skrip uji, impor data, integrasi) langsung dijual ke tamu tanpa seorang pun memutuskannya. Nilai bawaan dipakai sebagai KEPUTUSAN PENJUALAN.
- Gate penangkap: TIDAK ADA (POC hanya menguji unit MITRA & unit yang di-set `False` secara eksplisit — tak pernah unit tanpa field). Kini dijaga **INV-BOOK-02** runtime: unit tak-tayang/mitra yang `vehicle_id`-nya ditebak wajib ditolak 4xx.
- Fix           : (a) `publishable_filter()` menuntut `publish_to_web == True` EKSPLISIT (data lama diselaraskan sekali oleh `scripts/migrate_booking_v1.py` langkah 2, yang sudah ada); (b) `mutation_smoke.py` membuat unitnya dengan `publish_to_web: False`; (c) smoke test kini membersihkan artefaknya sendiri (`cleanup()` by-ID di setiap jalur keluar) sehingga data uji tidak menumpuk di data yang dilihat pengguna.
- Regression    : INV-BOOK-02 (runtime: unit tak-tayang → 4xx) + `test_core_booking_v1.py` bagian 1 (katalog bersih).
- Pelajaran     : Toleransi "field kosong = izin" selalu berujung pada data uji/impor yang tayang di muka toko. Untuk keputusan yang bernilai uang, WAJIB opt-in eksplisit + jalur migrasi sekali jalan.
- Status        : FIXED (bukti: `/api/public/fleet` & pencarian booking hanya 3 unit nyata; gate HIJAU).

### BUG-0116 — mutation_smoke jadi SKIP palsu (409 duplikat) → alur TULIS tidak pernah diuji
- Tanggal       : 2026-08-12
- Fase/Modul    : BOOKING-V1 / scripts/mutation_smoke.py
- Gejala        : Setelah artefak smoke tertinggal di database dari jalan sebelumnya, `POST /api/customers` menjawab **409 duplikat** (benar — dedupe telepon INV-IDENT-01), lalu skrip menjawab `[SKIP] POST /api/customers → 409 (kontrak beda) — lewati.` dan keluar dengan status 0. Gate melaporkan gate itu **PASS** padahal M1/M2/M3 (create → anti double-booking → payment) tidak dieksekusi sama sekali.
- Root Cause    : Skrip memakai identitas TETAP (telepon 0810000000, plat "D 9 ZZ") tetapi tidak membersihkan sisa jalan sebelumnya, dan menerjemahkan 409 sebagai "kontrak beda" (skip) bukan "sisa data".
- Gate penangkap: tak ada — inilah "hijau palsu" yang justru dilarang `memory/INVARIANTS.md`. Terdeteksi saat menambahkan pembersihan artefak untuk BUG-0115.
- Fix           : `presweep()` membuang sisa artefak smoke (saringan sempit: nama+telepon uji) SEBELUM mulai, dan `cleanup()` menghapus artefak setelah selesai. Hasil sekarang: 5 pemeriksaan tulis dieksekusi, **SKIP 0**.
- Pelajaran     : Skrip verifikasi yang memakai data tetap wajib idempoten dari sisi DATA, bukan hanya dari sisi kode. "SKIP" pada gate harus dianggap kegagalan sampai dibuktikan sebaliknya.
- Status        : FIXED (bukti: `python scripts/mutation_smoke.py` → 5 OK, FAIL 0, SKIP 0).

### BUG-0117 — Ringkasan pesanan memajang "- → -" & daftar tipe unit hilang tanpa penjelasan
- Tanggal       : 2026-08-12
- Fase/Modul    : BOOKING-V1 / features/public/BookingWizard.jsx + features/public/BookingRequest.jsx
- Gejala        : (a) Pada langkah 3 wizard, baris **Perjalanan** menampilkan `- → -` bila tamu tidak mengisi asal/tujuan (keduanya OPSIONAL untuk sewa harian) — terlihat seperti data gagal dimuat. (b) Bila `GET /api/public/booking/config` gagal, dropdown "Preferensi Unit" pada formulir permintaan menyusut jadi satu opsi tanpa satu kata penjelasan; tamu menyangka pilihannya hilang. (b) juga membuat `ux_audit --strict` MERAH (aturan E2: daftar data tanpa EMPTY state) sehingga `gate.sh` tidak bisa hijau.
- Root Cause    : placeholder dirender tanpa syarat (`${origin || "-"} → ${destination || "-"}`); state "gagal muat" tidak dibedakan dari "sedang memuat".
- Gate penangkap: `scripts/ux_audit.py --strict` aturan **E2** (sudah ada) menangkap (b). (a) ditemukan saat verifikasi visual.
- Fix           : baris Perjalanan hanya dirender bila ADA isinya (`tripLabel`: "A → B" / "Dari A" / "Menuju B"); `prefsReady` memisahkan memuat vs kosong lalu menampilkan pesan jujur "Belum ada daftar tipe unit yang bisa dimuat. Anda tetap bisa mengirim permintaan…". Sekalian 5 WARN W1 (uang tanpa `tabular-nums`) di berkas booking ditutup → `ux_audit --strict` **0 ERROR 0 WARN**.
- Pelajaran     : Placeholder "-" untuk field opsional adalah kebohongan kecil yang membuat produk tampak rusak; dan setiap daftar yang datang dari API butuh state "gagal/kosong" yang menjelaskan langkah berikutnya.
- Status        : FIXED (bukti: ux_audit --strict 0 ERROR/0 WARN; screenshot langkah 3 & 4 alur pemesanan).

### BUG-0118 — Halaman /booking BLANK total (regresi yang saya sendiri buat saat memperbaiki BUG-0117)
- Tanggal       : 2026-08-12
- Fase/Modul    : BOOKING-V1 / frontend/src/features/public/BookingWizard.jsx
- Gejala        : Seluruh halaman **Pesan Online** kosong (putih), `#root` innerHTML = 0 byte, `pageerror`: **"Cannot read properties of null (reading 'origin')"**. Tidak ada pesan apa pun untuk pengunjung — alur pemesanan publik MATI TOTAL. Ditemukan oleh `testing_agent_v3` (iteration_80), bukan oleh saya.
- Root Cause    : Perbaikan BUG-0117 menghitung `tripLabel` di **badan render** memakai `search.origin`, padahal `search` bernilai `null` sampai `GET /api/public/booking/config` selesai. Render pertama langsung melempar sebelum satu elemen pun tampil. Sebelumnya seluruh akses ke `search` di jalur render sudah memakai optional chaining (`search?.service`) — pola itu ada justru karena state ini boleh null; saya menambahkan satu baris yang melanggarnya.
- Gate penangkap: TIDAK ADA gate otomatis (crash render tidak terlihat di lint/compile — `webpack compiled successfully`, dan tidak ada 5xx di backend). Yang menangkap: pengujian browser oleh testing agent. `ux_audit` menilai pola UI, bukan runtime.
- Fix           : `search?.origin` / `search?.destination` + komentar peringatan eksplisit di kode bahwa `search` null sampai config termuat.
- **Jebakan lingkungan (penting untuk sesi berikutnya)**: setelah fix ditulis, halaman MASIH blank dengan galat lama karena dev-server **tidak merekompilasi modul itu** (HMR macet, `webpack compiled successfully` tetap muncul). `sudo supervisorctl restart frontend` → halaman langsung normal. Jebakan yang sama sudah pernah dicatat di HANDOFF §E28b untuk `BookingRequest.jsx`; jangan buru-buru menyimpulkan "fix tidak bekerja".
- Pelajaran     : Menambahkan turunan (`derived value`) di badan render selalu berjalan pada render PERTAMA — sebelum data apa pun ada. Setiap state yang boleh `null` wajib diakses dengan optional chaining, dan perbaikan UI sekecil apa pun tetap harus dibuka di browser (bukan hanya dibaca).
- Status        : FIXED (bukti: /booking merender penuh, 0 pageerror, alur cari→pilih→isi data jalan; baris "Perjalanan" hilang saat asal/tujuan kosong sesuai BUG-0117).

### BUG-0119 — `marketing_admin` mendapat HTTP 200 pada 8 permukaan BACA operasional (booking, armada, sopir, GPS)
- Tanggal       : 2026-08-12
- Fase/Modul    : BOOKING-V1 (temuan sampingan) / routers/{bookings,vehicles,drivers,maintenance,gps,quotations,driver}.py
- Gejala        : Testing agent melaporkan `GET /api/bookings` menjawab **200** untuk `marketing_admin`. Audit lanjutan (`scripts/audit_rbac_sections.py`, dibuat untuk ini) menemukan **8 endpoint bocor**: `/bookings`, `/bookings/availability`, `/bookings/{id}`, `/vehicles*`, `/drivers*`, `/maintenance*`, `/gps/*`, `/quotations*`, `/driver/*`. Data yang terekspos: nama pelanggan + `total_amount`/`paid_amount`, nomor telepon sopir, posisi GPS armada, harga penawaran. Menunya memang tidak pernah tampil untuk peran itu — tetapi API terbuka bagi siapa pun yang tahu URL-nya (atau token peran itu).
- Root Cause    : RC-RBAC (pintu modul tidak ditegakkan). Endpoint BACA memakai `Depends(get_current_user)` = "cukup sudah login". Saat peran `marketing_admin` LAHIR di FASE F, tidak ada yang menguji ulang endpoint BACA LAMA terhadap peran baru: `SECTION_ACCESS` & `ROLE_MENU_ALLOWLIST` sudah benar (keduanya mengecualikan marketing), sehingga guardrail statik INV-RBAC-01..05 hijau — mereka memeriksa KONSISTENSI matriks, bukan penegakannya per endpoint. Ini pengulangan kelas BUG-0107, dengan peran yang berbeda.
- Gate penangkap: Lapis runtime INV-RBAC-06 SUDAH ada tetapi **hanya menguji peran `driver`** pada 3 endpoint kalender → buta terhadap peran lain. Diperbaiki: lapis **D "MATRIKS PENUH"** — satu endpoint GET perwakilan untuk SETIAP section di `SECTION_ACCESS` ditembak dengan SEMUA peran demo; peran di luar matriks wajib 403, peran di dalam matriks wajib bukan-403; `SECTION_PROBES` **wajib memuat semua section** (section baru tanpa probe → gate MERAH), dan probe yang 404 untuk semua peran ditolak agar penjaga tidak hampa. Kini 27 section × 4 peran = 155 cek.
- Fix           : `Depends(require_section("<section>"))` pada seluruh endpoint BACA di 6 router + `routers/quotations.py` dipindah dari section `crm` (yang memuat marketing) ke section `quotations` sesuai SSOT + `routers/driver.py` memakai section `driver-workspace`. Tidak ada over-block: driver tetap 200 di Ruang Kerja Driver/armada/maintenance/GPS, owner & ops_admin tetap 200 di semuanya, dan semua halaman marketing_admin (Dashboard, CRM, Customer 360, Ads, Landing, Media, Konten) tetap normal tanpa galat konsol.
- Regression    : INV-RBAC-06 lapis D (self-test mutasi: satu endpoint dikembalikan ke `require_role(...)` serba-izin → penjaga MERAH menyebut endpoint + section; revert → HIJAU).
- Pelajaran     : Menambah PERAN baru sama berisikonya dengan menambah endpoint baru. Setiap peran baru wajib memicu uji matriks penuh terhadap SELURUH permukaan lama — dan penjaganya harus digerakkan matriks (SSOT), bukan daftar kasus yang ditulis tangan.
- Status        : FIXED (bukti: `python scripts/audit_rbac_sections.py` → "Perilaku sesuai matriks SECTION_ACCESS"; INV-RBAC-06 155 cek 0 pelanggaran).

### BUG-0120 — Kode rute antar-jemput buatan otomatis menabrak dirinya sendiri (`DPS-DPS`) → arah balik mustahil dibuat
- Tanggal       : 2026-08-12
- Fase/Modul    : BOOKING-V2 (rute bandara) / frontend/src/components/app/TransferRoutesPanel.jsx
- Gejala        : Katalog "tambah cepat" untuk **Denpasar ↔ DPS** menghasilkan kode rute `DPS-DPS`. Setelah rute arah pergi disimpan, tombol **Arah balik** membalik kode `DPS-DPS` → `DPS-DPS` (identik) sehingga server menolak `HTTP 409 Kode rute 'DPS-DPS' sudah dipakai`. Ops tidak bisa membuat rute pulang untuk Bali, dan pesan galatnya membingungkan ("sudah dipakai" padahal rute pulang belum pernah dibuat). Kelas yang sama mengancam **Bandung–BDO, Solo–SOC, Semarang–SRG** (kode kota = kode IATA bandara di kotanya sendiri).
- Root Cause    : Kode rute dirakit `<'{'}kodeKota{'}'}-<kodeBandara>` tanpa memeriksa kemungkinan KEDUANYA sama. Untuk kota yang punya bandara ber-IATA sama dengan singkatan kotanya, hasilnya simetris; membalik string simetris menghasilkan string yang sama. Ditemukan main agent saat uji UI (bukan oleh testing agent: rute yang diujinya kebetulan asimetris).
- Gate penangkap: Tidak ada gate statik untuk logika perakitan kode di FE. Penjaga NYATA yang menyelamatkan data tetap bekerja: indeks unik `transfer_routes.code` + 409 berALASAN di `routers/transfer_routes.py` (tidak ada rute ganda yang lahir).
- Fix           : (1) alias kode kota bila bertabrakan dengan IATA-nya (`Bandung→BDG`, `Solo→SLO`, `Semarang→SMG`, `Denpasar→BALI`); (2) `reverseOf()` hanya membalik kode bila hasilnya BERBEDA — kode simetris dikosongkan agar ops menentukan sendiri, bukan dikirim untuk pasti ditolak.
- Regression    : Terbukti di UI: `BALI-DPS` (pergi) & `DPS-BALI` (balik) tersimpan dua-duanya, tarif per tipe unit ikut tersalin; rute baru langsung tampil di `/api/public/booking/config` dan dijual dengan tarif FLAT (Hiace Premio Rp 900.000, bukan tarif harian).
- Pelajaran     : Nilai yang dirakit otomatis (kode, slug, nomor) wajib diuji pada kasus **simetris/duplikat**, bukan hanya kasus normal. Dan pembalikan string bukan operasi yang aman untuk identitas.
- Status        : FIXED (bukti: dua arah rute Bali tersimpan; gate.sh HIJAU 0 FAIL 0 SKIP).

### BUG-0121 — Panel CTA `/blog/:slug` "rusak/belum selesai": gradient Tailwind dengan token triplet HSL → seluruh latar dibuang browser
- Tanggal       : 2026-08-12
- Fase/Modul    : Fase 7 (UI/UX readability) / frontend/src/features/public/BlogDetail.jsx
- Gejala        : User mengirim screenshot: di `/blog/:slug` ada kotak besar berisi HANYA tombol "Minta Penawaran" yang mengambang — judul "Siap merencanakan perjalanan Anda?", subjudul, dan tombol "Lihat Armada" TIDAK TERLIHAT. User menyimpulkan "UI-nya rusak atau belum selesai".
- Root Cause    : Class `bg-gradient-to-br from-primary to-[color:var(--primary)]`. Token tema proyek ini berisi **triplet HSL** (`--primary: 220 45% 14%`), bukan warna lengkap. `to-[color:var(--primary)]` menghasilkan `--tw-gradient-to: color:var(--primary)` yang **invalid**, sehingga browser membuang SELURUH deklarasi `background-image` → panel transparan. Teks `text-primary-foreground` (putih) lalu berada di atas kertas putih = tak terlihat. Gagal SENYAP: tidak ada error konsol; di mode gelap panel "kebetulan" terbaca sehingga bug ini lolos berkali-kali.
- Gate penangkap: TIDAK ADA sebelumnya (`ux_audit` hanya menilai state data & testid; gate lain menyentuh backend). Kini: **INV-THEME-01**.
- Fix           : Komponen baru `components/public/CtaBand.jsx` — latar `bg-primary` (warna solid dari token) + dekorasi `radial-gradient` lewat `style` inline yang selalu valid. Dipakai ulang di `/blog/:slug`, `/fleet`, `/destinations`, `/trip-calculator`.
- Regression    : `scripts/guardrails/verify_theme_contrast.py` melarang `from-/via-/to-[color:var(--token)]` dan `bg-/text-/border-[var(--token)]` di seluruh `frontend/src` (komentar dilucuti agar dokumentasi tidak jadi temuan palsu). Self-test mutasi **T01** membuktikan penjaga MERAH bila class itu kembali.
- Pelajaran     : Bila design system memakai token TRIPLET, arbitrary value Tailwind untuk warna adalah ranjau. Verifikasi latar panel dengan `getComputedStyle` (`backgroundImage`), bukan mata — dan ingat `backgroundColor` memang `transparent` bila latar dipasang via `background-image`.
- Status        : FIXED (bukti: iteration_86 & 87 — `blog-cta-band` latar `rgb(20,30,52)`, teks terbaca di light & dark).

### BUG-0122 — Modal & kartu kaca memaksa latar PUTIH untuk semua mode → teks putih di atas putih (mode gelap)
- Tanggal       : 2026-08-12
- Fase/Modul    : Fase 7 / frontend/src/index.css (`.glass-modal`, `.glass-3d`)
- Gejala        : Screenshot user (mode gelap, beranda): judul modal exit-intent nyaris tak terbaca dan deskripsinya HILANG. Di mode terang: label "Destinasi/Tipe Armada/Durasi" pada kartu estimator hero tersapu putih di atas foto terang.
- Root Cause    : Dua hal. (a) `.glass-modal` memakai `hsla(0 0% 100% / .94) !important` — putih untuk SEMUA mode; di mode gelap `--foreground` = putih. (b) `.glass-3d::before` memakai `mix-blend-mode: screen` opacity **0.55** dengan radial putih 60% tanpa mask, plus gradient stop putih 40–72% di 22% atas kartu — bagus di atas foto GELAP, mematikan di atas foto TERANG.
- Gate penangkap: TIDAK ADA sebelumnya. Kini: **INV-THEME-01**.
- Fix           : `.glass-modal` memakai `--glass-bg-strong` (ikut preset & mode) + scrim internal; `.glass-3d::before` → `--refraction-opacity: .22`, `--refraction-blend` (`soft-light` light / `normal` dark), dibatasi `--refraction-mask` ke tepi atas; token `--glass-edge`/`--glass-edge-soft` diturunkan di `.dark`; kelas baru `.glass-on-hero` (base `hsla(var(--card)/.93)`) untuk surface di atas foto; fallback `@supports` ikut mode.
- Regression    : INV-THEME-01 melarang `hsl(0 0% 100%)` pada blok glass + fallback, `mix-blend-mode: screen` hardcode, dan `--refraction-opacity` > 0.30. Self-test **T02** & **T07**.
- Pelajaran     : "Kaca premium" tidak boleh dibuat dengan menumpuk PUTIH — buat dengan token yang ikut mode, dan pisahkan dekorasi dari area teks memakai `mask-image`.
- Status        : FIXED (bukti: iter-87 — modal dark `rgba(15,22,36,.92)` + teks `rgb(242,245,247)`; estimator dark `rgba(15,22,36,.93)`, light `rgba(252,252,253,.93)`).

### BUG-0123 — Tombol close dialog berubah jadi "bulatan biru aneh" saat dialog terbuka
- Tanggal       : 2026-08-12
- Fase/Modul    : Fase 7 / frontend/src/components/ui/dialog.jsx
- Gejala        : Pada screenshot user, tombol X di modal tampak seperti artefak bulat biru, bukan tombol tutup.
- Root Cause    : Varian bawaan shadcn `data-[state=open]:bg-accent data-[state=open]:text-muted-foreground`. Karena state dialog SELALU `open` saat terlihat, latar tombol selalu `--accent` — pada preset azure mode gelap `--accent` = teal terang, jadi tombol jadi bulatan warna dengan ikon nyaris hilang.
- Gate penangkap: Tidak ada (komponen `components/ui/` sengaja dikecualikan `ux_audit`).
- Fix           : Tombol close diberi gaya stabil (`border-border` + `bg-secondary/80` + `text-foreground` + ring fokus), tanpa varian berbasis `data-state`.
- Regression    : Diverifikasi visual di light & dark (iter-87). Tidak diberi gate statik: perubahan berada di primitif shadcn yang jarang disentuh, dan pemeriksaan kontrasnya sudah tercakup pengukuran computed style testing agent.
- Status        : FIXED.

### BUG-0124 — Konten Radix yang di-PORTAL (Dialog/Select) tidak mewarisi tema → dialog & dropdown memakai palet ERP terang saat situs mode gelap
- Tanggal       : 2026-08-12
- Fase/Modul    : Fase 7 / frontend/src/context/ThemeContext.js + styles/public-themes.css
- Gejala        : Ditemukan **testing agent** (iteration_86) saat memverifikasi perbaikan BUG-0122: `--glass-bg-strong` KOSONG di mode gelap sehingga latar modal jatuh ke nilai `:root` (tema ERP terang) sementara token lain sudah gelap. Efek nyata: dialog exit-intent & seluruh daftar opsi Select (estimator hero, kalkulator, filter armada) memakai palet terang di situs gelap.
- Root Cause    : Token tema publik hanya di-scope pada `div[data-surface="public"][data-theme=…]` di `PublicLayout`. Radix mem-portal `DialogContent`/`SelectContent`/`Popover` ke `document.body` — DI LUAR div itu — sehingga mereka mewarisi `:root`. Ekor masalah kedua: setelah atribut dipasang di `<html>`, selector `.dark [data-surface][data-theme]` tetap TIDAK cocok karena `.dark X` hanya mencocokkan **descendant**, sedangkan `<html>` sendiri yang membawa `.dark`.
- Gate penangkap: TIDAK ADA sebelumnya. Kini: **INV-THEME-01** (cek 6 & 7).
- Fix           : `ThemeContext` memasang `data-surface="public"` + `data-theme=<preset>` pada `document.documentElement` (dan **membersihkannya** saat unmount agar konsol ERP tidak ketularan); `public-themes.css` diberi selector kembar `[data-surface="public"][data-theme="X"].dark` untuk 4 preset; `html[data-surface="public"] { background-image: none }` supaya lapisan hias tidak dilukis dua kali.
- Regression    : INV-THEME-01 menuntut ketiga pemanggilan (`setAttribute` surface & theme, `removeAttribute` saat unmount) dan kembaran selector untuk SETIAP preset. Self-test **T03** & **T04**.
- Pelajaran     : Setiap kali tema di-scope ke sebuah `div`, tanyakan "apa yang di-portal keluar dari div ini?". Dan isolasi ERP wajib diuji BOLAK-BALIK (publik→ERP→publik→ERP), bukan sekali jalan.
- Status        : FIXED (bukti: iteration_87 100% — html `{dark, surface:public, theme:azure}`, SelectContent dark `rgb(15,22,36)`, `/app/*` atribut null & tampilan normal).

### BUG-0125 — (regresi buatan sendiri) `--surface-on-hero: var(--card)/.93` di `:root` → kartu estimator tetap TERANG di mode gelap
- Tanggal       : 2026-08-12
- Fase/Modul    : Fase 7 / frontend/src/index.css
- Gejala        : Setelah perbaikan BUG-0122, kartu estimator hero di mode gelap tampil TERANG dengan label putih → judul & label hilang total (lebih buruk dari sebelumnya). Ditemukan main agent sendiri saat verifikasi screenshot, sebelum diserahkan ke testing agent.
- Root Cause    : Substitusi `var()` di dalam **custom property** terjadi pada elemen tempat property itu DIDEKLARASIKAN (`:root` = tema ERP terang), lalu nilai HASILNYA yang diwariskan ke bawah. Jadi `--surface-on-hero` membeku sebagai warna terang dan tidak pernah ikut mode/preset.
- Gate penangkap: TIDAK ADA sebelumnya. Kini: **INV-THEME-01** (cek 4).
- Fix           : `.glass-on-hero` memakai `hsla(var(--card) / .93)` LANGSUNG (diselesaikan di elemen pemakai); `.hero-scrim` juga ditulis langsung, bukan lewat `--scrim-hero`.
- Regression    : INV-THEME-01 melarang deklarasi custom property di `:root`/`.dark` yang menyusun token TEMA. Self-test **T06**.
- Pelajaran     : Custom property bukan fungsi — ia nilai yang dihitung sekali di tempat deklarasi. Untuk sesuatu yang harus "ikut tema", tulis ekspresinya di kelas pemakai.
- Status        : FIXED (bukti: pengukuran computed style light `rgba(252,252,253,.93)` vs dark `rgba(15,22,36,.93)`; iter-87).

### BUG-0126 — Panel chat menembus header pada viewport pendek ("posisi chat terlalu di atas")
- Tanggal       : 2026-08-12
- Fase/Modul    : Fase 7 / frontend/src/components/public/ChatWidget.jsx
- Gejala        : Screenshot user: panel chat terbuka menutupi navbar & bar pengumuman.
- Root Cause    : FAB `fixed bottom-24`, panel `fixed bottom-40` dengan **tinggi TETAP 440px**. Pada viewport pendek (1920×800, 390×640) 160px + 440px = 600px sehingga puncak panel melewati batas bawah header (±90px). Tidak ada satu pun angka yang tahu tinggi header maupun tinggi `StickyMobileCTA`.
- Gate penangkap: Tidak ada. Kini: **INV-THEME-01** (cek 5 & 6) + pengukuran bounding box oleh testing agent.
- Fix           : SSOT offset di `index.css` (`--header-h`, `--sticky-cta-h` 0/72px, `--fab-gap`, `--fab-bottom`, `--panel-bottom`, z-index bertingkat); ChatWidget memakai token itu + `height: clamp(320px, 58dvh, 460px)` + `maxHeight: calc(100dvh - var(--header-h) - var(--panel-bottom) - 12px)`; `ConsentBanner` dinaikkan ke z-70.
- Regression    : INV-THEME-01 menuntut token offset ada, ChatWidget memakai `var(--fab-bottom)`/`var(--panel-bottom)` + `maxHeight`, dan melarang `bottom-<n>` pada elemen `fixed`. Self-test **T05**. Pengukuran: 1920×800 panel y=544 > header 90,75; 390×640 panel y=120,8 > header 89,25, panel bawah 492 ≤ FAB 502,8, FAB bawah 553,2 ≤ sticky 570,75.
- Pelajaran     : Elemen mengapung wajib diuji dengan ANGKA (bounding box) di beberapa viewport, bukan hanya dilihat di layar lebar. Jangan menaruh offset di banyak tempat — turunkan dari satu SSOT token.
- Status        : FIXED (bukti: iteration_86 ITEM 6 PASSED; pengukuran main agent di 2 viewport).
