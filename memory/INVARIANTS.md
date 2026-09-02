# \U0001F6E1\uFE0F INVARIANTS REGISTRY \u2014 Rahaza Travel ERP (Guardrail v2)

> **BACA INI DULU jika Anda sesi AI / kontributor baru.** File ini adalah **SSOT** dari
> semua invariant lintas-kelas-bug yang WAJIB dijaga. Tujuannya menutup masalah utama:
> *konteks hilang antar-sesi* + *kode tumbuh* \u2192 kelas bug lama muncul lagi di endpoint baru.
>
> **Aturan emas:** sebelum klaim "selesai", jalankan `bash scripts/gate.sh` dan pastikan **HIJAU**.
> Guardrail v2 memaksa invariant ini secara **statik + runtime** \u2014 melanggar = gate MERAH
> dengan pesan APA + DI MANA + INVARIANT-ID.

## Kenapa guardrail v2 ada
Audit Putaran 11 menemukan banyak bug bukan karena fondasi rapuh, melainkan karena **pola pengaman
yang benar tidak diterapkan konsisten di seluruh permukaan yang terus bertambah**, dan **tes lama
hanya menguji happy-path** (coverage 46%). Guardrail v2 mengubah aturan dari *"diingat developer"*
menjadi *"dipaksa oleh analisis kode"* sehingga tak bergantung pada memori sesi.

## Daftar Invariant

| ID | Invariant | Kelas bug dicegah | Penjaga (statik/runtime) | Allowlist / SSOT |
|----|-----------|-------------------|--------------------------|------------------|
| **INV-NUM-01** | Semua field numerik uang/kuantitas di `schemas.py` wajib ber-bound `ge=`/`gt=` | negative-value (57 field) | `scripts/guardrails/verify_numeric_bounds.py` (statik) | `ALLOW_UNBOUNDED` di skrip |
| **INV-RACE-01** | Jalur reservasi armada/sopir wajib serial via `vehicle_lock`/`driver_lock` saat cek+tulis | race / TOCTOU double-book | `scripts/guardrails/verify_reservation_locks.py` (statik) | `ALLOW` + `REGISTRY` di skrip |
| **INV-RBAC-01** | Tiap route modul ERP di `App.js` dibungkus `<RoleGuard>` (kecuali dashboard) | RBAC leakage FE (O-1) | `scripts/guardrails/verify_rbac_guards.py` (statik) | `EXEMPT_ROUTES` |
| **INV-RBAC-02** | Router sensitif (owner/ops-only) memakai `require_section`/`require_role` | RBAC bypass BE | idem | `SENSITIVE_ROUTERS` |
| **INV-RBAC-03** | `ROLE_MENU_ALLOWLIST` (FE) tidak mengekspos modul terlarang ke driver/ops | drift SSOT RBAC | idem | `FORBIDDEN` + `docs/05_NAVIGATION_MAP.md` |
| **INV-RBAC-04** | Setiap section FE (`ROLE_MENU_ALLOWLIST`/`PAGE_META`) WAJIB dideklarasikan di `backend/permissions_config.SECTION_ACCESS` dan himpunan perannya IDENTIK di kedua sisi (sinkron 2-arah) | modul BARU bocor diam-diam karena tak pernah masuk daftar `FORBIDDEN` & tak punya section BE (RBAC-CAL-01) | `scripts/guardrails/verify_rbac_guards.py` (statik, membaca matriks BE langsung) | `ALLOW_FE_ONLY_SECTIONS` (kosong) + `SECTION_ALIASES` |
| **INV-RBAC-05** | Endpoint daftar/detail "milik-sendiri" WAJIB memanggil penyaring row-level `services/rbac_scope.py` (`scope_bookings_query`/`can_view_booking`/`scope_drivers_query`/`can_view_driver`) | RBAC-SCOPE: pintu modul terbuka sah, tapi query mengembalikan SELURUH baris (driver melihat semua booking + nama pelanggan + nominal) | idem (statik: cek pemanggilan `await <fn>(`) | `SCOPE_REQUIREMENTS` |
| **INV-RBAC-06** | PERILAKU RBAC diuji runtime: driver → 403 di 3 endpoint kalender, owner → 200; driver hanya melihat trip & profil miliknya; `/api/driver/*` tetap 200 (tak over-block) | konfigurasi benar tapi perilaku bocor (Depends tertukar, urutan route menelan literal, filter dilewati di cabang tertentu) | `scripts/guardrails/verify_rbac_runtime.py` (runtime, wajib login) | akun demo di `scripts/seed_data.py` |
| **INV-5XX-01** | Endpoint tak boleh 5xx pada input adversarial (harus 2xx/4xx) | crash 500 (EXPORT-1, R6-4, R6-5, dst) | `scripts/guardrails/verify_adversarial_5xx.py` (runtime) | payload di skrip |
| **INV-IDENT-01** | Pembuatan identity (customer) aman-balapan: index unik-parsial `customers.phone_normalized` (non-kosong) + tangani `DuplicateKeyError` di semua jalur tulis | race/TOCTOU duplikat customer (ID-RACE) | `scripts/guardrails/verify_identity_race.py` (statik + runtime N-paralel) | index di `server.py`; handler di `routers/customers.py` + `services/identity.py` |
| **INV-SET-01** | Tarif `settings.pricing_rules`/`pricing_defaults` tervalidasi (tolak negatif/absurd/non-numerik → 400) | harga negatif/DP>total/koersi-0 senyap (SET-1) | `scripts/guardrails/verify_settings_bounds.py` (statik + runtime) | `_validate_pricing` di `routers/settings.py` |
| **INV-META-01** | Setiap `scripts/guardrails/verify_*.py` WAJIB ter-wire di `scripts/gate.sh` + mendeklarasikan INV-ID + terdaftar di file ini | guardrail hilang/tak-terdaftar antar-sesi (perlindungan mati diam-diam) | `scripts/guardrails/verify_guardrail_registry.py` (statik meta) | `ALLOW_UNWIRED` di skrip |
| **INV-AUTH-01** | Tiap endpoint router menegakkan auth (`Depends(get_current_user/require_role/require_section)`); publik hanya via allowlist ber-justifikasi | endpoint bocor tanpa login (data/aksi terekspos publik) | `scripts/guardrails/verify_auth_coverage.py` (statik) | `PUBLIC_ENDPOINTS`/`PUBLIC_FILES` di skrip |
| **INV-QUALITY-01** | Kualitas kerja minimal AI: tak ada endpoint stub (`NotImplementedError` di router), penelan error senyap (`except: pass`), rahasia/URL backend hardcoded | kerja dangkal "lapisan luar" lolos ke produksi | `scripts/guardrails/verify_effort_quality.py` (statik; berat=blocking, ringan=advisory) | `SEVERE_ALLOW` di skrip |
| **INV-CONV-01** | Event bisnis bernilai (`lead.created`, `booking.confirmed`, `payment.recorded`) WAJIB tersambung ke outbox konversi lewat SATU titik (`services/events.emit` → `conversion_hooks.handle_event`), outbox idempoten (unique `provider+event_key` + tangani `DuplicateKeyError`), dan pekerja retry (`dispatch_pending`) terjadwal di `server.py` | konversi paling bernilai (booking & DP) tak pernah dikirim ke Meta/Google → algoritma iklan salah optimasi & biaya per booking membengkak, TANPA satu pun error di log (ditemukan nyata di fase F3: `conversions.py` lengkap tapi tak pernah dipanggil) | `scripts/guardrails/verify_conversion_hooks.py` (statik) | `REQUIRED_EVENTS` di skrip |
| **INV-ADS-01** | Semua penulisan ke platform iklan WAJIB lewat `services/ads_safety.py`: mode `validate` → `validate_only`/`validateOnly`, mode `publish` → status DIPAKSA `PAUSED`; aktivasi & ubah budget wajib konfirmasi ketik nama + plafon `assert_budget_within_cap`; router iklan dilarang memanggil httpx/Graph/Google API langsung | membakar UANG NYATA tanpa error: lupa `validate_only`, lupa `PAUSED`, atau salah ketik nol pada budget | `scripts/guardrails/verify_ads_write_safety.py` (statik) | `FORBIDDEN_IN_ROUTERS` di skrip |
| **INV-AUD-01** | Sinkron audiens (Custom Audience / Customer Match) WAJIB menyaring `marketing_consent` lewat `audiences.split_by_consent` SEBELUM membangun payload, memakai daftar `eligible`, identitas ter-hash via `services/pii.py`, batas 10.000/batch + `last_batch_flag`, dan melaporkan `consent_filtered` | mengunggah kontak pelanggan tanpa izin ke platform iklan (pelanggaran privasi yang tak bisa ditarik & tanpa error) | `scripts/guardrails/verify_audience_consent.py` (statik) | — |
| **INV-SEC-02** | Rahasia integrasi & PII tidak keluar server: router tak mengembalikan `secrets_bundle`/`_secrets`, konfigurasi memakai `vault.public_view` (ter-mask), endpoint publik pelacakan bebas kata rahasia, log tak mencetak token, tak ada token hardcoded, PII ke platform selalu ter-hash sedangkan **click id (ctwa_clid/gclid) TIDAK boleh di-hash** | token iklan (bisa membelanjakan budget) & data pelanggan bocor via respons/log/kode; atau atribusi CTWA rusak karena click id ikut di-hash | `scripts/guardrails/verify_secret_exposure.py` (statik) | `SECRET_WORDS`/`HARDCODE_PATTERNS` di skrip |
| **INV-LP-02** | Props template landing page WAJIB memakai nama kanonik `landing_blocks.BLOCK_TYPES`; `validate_blocks` tak boleh melempar untuk bentuk props apa pun; tiap tipe blok bisa dibangun dari props kosong; tiap template punya blok konversi; `LandingRender.jsx` menangani SEMUA tipe blok | dua kelas bug nyata fase F8: (a) `trust_badges.items` berupa string → `AttributeError` → **HTTP 500** saat membuat halaman dari template, (b) props bernama beda (`success_text`/`deadline`/`cta`) DIBUANG senyap saat validasi → tombol/tenggat/pesan sukses hilang di halaman iklan tanpa satu pun error di log | `scripts/guardrails/verify_landing_contract.py` (statik + eksekusi ringan) | daftar props kanonik = `landing_blocks.canonical_props()` |
| **INV-MEDIA-02** | URL baca media yang ditulis router WAJIB cocok dengan rute publik yang benar-benar terdaftar; `media_store.fetch` menolak path traversal/jalur kosong/NUL; nama berkas hasil unggah acak (bukan nama pengguna); batas MIME+ukuran tetap hidup; unggah/ubah/hapus media di balik `require_section("landing")`; router publik media read-only | unggah SUKSES tapi SETIAP gambar/video halaman iklan 404 tanpa error backend (URL `/api/media/...` vs rute `/api/public/media/...`), dan endpoint media publik bisa membaca berkas sistem lewat `../` | `scripts/guardrails/verify_media_safety.py` (statik + eksekusi ringan) | `LOCAL_DIR`/`MEDIA_BACKEND` di `services/media_store.py` |
| **INV-MEDIA-03** | Media Library tetap **SATU**: semua penulisan aset publikasi lewat `services/media_store` + tercatat via `media_lib.register_asset` (termasuk `POST /api/uploads/cms` lama); tiap rute `/media*` memakai `Depends(MEDIA)` (dibaca **AST**, tahan format dekorator); unduh ber-`attachment` + nama tersanitasi; `public_media` mengirim **ETag di KEDUA jalur respons** (304 & 200) + revalidasi untuk URL tanpa versi; `replace_file` menaikkan `version` dan membuang berkas lama; `public_doc` tidak membocorkan `storage_path`; folder = LABEL (hapus folder MENAIKKAN aset ke induk; siklus & nama ganda ditolak); crop tervalidasi + berbatas (`> MAX_CROP_SIDE`); impor aset lama idempoten (`legacy_key` unik) & menyimpan `legacy_url`; `.strip()` pada nilai dari klien WAJIB lewat `str(...)`; frontend hanya punya SATU pemilih media (import sungguhan `components/media/MediaPickerDialog`) dan menu/route `media` tetap terjangkau (termasuk `ops_admin`) | **"dua dunia media"** kembali: `/api/uploads/cms` menulis berkas tanpa catatan Mongo → aset tak bisa dicari/dipakai ulang & ratusan berkas "tak terlihat" di disk; hapus folder memusnahkan ratusan foto tayang (tak bisa dibatalkan); folder jadi pulau terputus akibat siklus; foto hasil "Ganti berkas" membeku sehari di cache; jalur penyimpanan internal bocor; satu field bertipe salah dari klien → HTTP 500; pemilih media liar tumbuh kembali satu komponen per ronde | `scripts/guardrails/verify_media_unified.py` (statik **AST** + **eksekusi nyata** aturan folder memakai stub DB in-memory) + `scripts/guardrails/selftest_media_unified.py` (**self-test mutasi otomatis, 24 kelas bug**) | `WRITE_ALLOWLIST` (`dispatch.py`, `driver.py` = bukti pengiriman, bukan aset publikasi) + `FE_UPLOAD_ALLOWLIST` (inti Media Library) di skrip |
| **INV-MEDIA-04** | PERILAKU media diverifikasi runtime: driver → **403 di SEMUA rute `/api/media/*` yang terdaftar** (daftar rute dibaca dari OpenAPI aplikasi yang berjalan, jadi rute BARU otomatis ikut diuji); ops_admin → 200 di `GET /media`; 14 permintaan adversarial jalur media → 2xx/4xx (dilarang 5xx); hapus folder berisi aset → aset NAIK ke induk & tetap terbaca; siklus folder ditolak; "Ganti berkas" → versi naik + **ETag berubah** + `If-None-Match` → 304 + URL tanpa versi `must-revalidate` + URL berversi `immutable`; `import-legacy` dijalankan dua kali pada berkas legacy NYATA → jalan kedua `imported=0`; hapus massal melaporkan `used_by` | konfigurasi benar tapi perilaku bocor/rusak: urutan route menelan literal (`/media/{id}` mendahului `/media/health`), matriks section salah → driver dapat 200, **HTTP 500 pada input bertipe salah** (`folder_id: 5` → `.strip()` → AttributeError), indeks unik legacy tak pernah dibuat di pod baru → aset ganda, hapus folder memanggil fungsi yang salah → aset musnah | `scripts/guardrails/verify_media_runtime.py` (RUNTIME, wajib login) + `scripts/guardrails/selftest_media_runtime.py` (self-test: backend mati / serba-izin / menolak-semua → penjaga WAJIB MERAH) | akun demo di `scripts/seed_data.py`; aset uji berprefiks `guard-media-` dibersihkan otomatis |
| **INV-PRICE-01** | Harga jual digerakkan **HARI × TARIF**, bukan jarak: tak satu pun modul permukaan-harga boleh mengalikan `distance_km`/`fuel_per_km`; `dp_percent` HANYA dibaca lewat `services.pricing.get_dp_percent` (dilarang membaca dokumen `settings` sendiri); harga pada kartu = harga mesin (`resolve_day_rate`, bukan `vehicles.price_from`); RUNTIME: `distance_km` 0 vs 5000 → total IDENTIK, rincian tanpa baris BBM/km, `total` = jumlah rincian, `dp_amount` = total × dp_percent, pesanan yang dibuat menyimpan angka yang SAMA dengan yang ditampilkan (total palsu kiriman klien diabaikan), dan mengubah `dp_percent` di Pengaturan langsung mengubah DP di web | (a) total memuat "Estimasi BBM (x km)" dengan `distance_km` **diisi pengunjung** lewat penggeser → tamu menentukan harganya sendiri; (b) DUA sumber `dp_percent` (`pricing_rules` untuk web vs `pricing_defaults` untuk ERP) → DP di website ≠ DP yang ditagih ops; (c) kartu memajang `price_from` (angka pemasaran) sementara tagihan pakai tarif tipe → tamu membayar lebih dari yang dilihat | `scripts/guardrails/verify_pricing_integrity.py` (statik **AST** + runtime) | `PRICING_SURFACES`, `FUEL_MENTION_ALLOW`, `DP_SOURCE_ALLOW` di skrip |
| **INV-PRICE-02** | Master Harga TUNGGAL: tarif per unit (`vehicles.day_rate`) hanya bisa ditulis lewat `PATCH /api/pricing/unit-rates/{id}` (halaman Pengaturan → Master Harga); `schemas.VehicleCreate/VehicleUpdate` & `routers/vehicles.py` DILARANG membawa/menulis `day_rate`/`price_from`; FE `VehicleFormDialog.jsx` tak boleh punya input harga; `/pricing/quote` WAJIB memakai `resolve_day_rate` agar angka yang dilihat ops = angka yang ditagih | BUG-0133: harga armada diatur di 2 halaman (Pengaturan vs form Armada) → angka saling menimpa & membingungkan; BUG-0132: quote 'Hitung Otomatis' mengabaikan tarif unit → ops menagih beda dari yang dilihat | `scripts/guardrails/verify_price_master.py` (statik) | — |
| **INV-REF-01** | Referensi & pilihan dari luar wajib divalidasi SERVER lewat satu pintu `services/refs.py`: setiap `*_id` dari klien harus menunjuk dokumen yang BENAR-BENAR ada (`must_exist`), dan setiap field pilihan (`type`/`status`/`ownership`/`method`/`category`/`stage`/`role`) harus berasal dari daftar SSOT — tipe armada diambil dari `pricing.VEHICLE_TYPE_LABELS` (yang dipakai mesin harga), bukan daftar tandingan. Berlaku untuk jalur BUAT **dan** UBAH. RUNTIME: 31 probe menembak FK hantu & pilihan 'ngawur' pada 20+ endpoint → semua wajib 4xx berALASAN (atau dinormalkan); dokumen uji yang lolos dihapus & dilaporkan sebagai pelanggaran | dropdown FE sudah mengambil isi dari koleksi, tetapi API-nya tidak memeriksa apa pun: `type='ngawur'` membuat unit tak punya tarif & label UI menampilkan 'Ngawur'; `ownership='ngawur'` membuat unit HILANG dari katalog publik tanpa satu pun pesan galat (`publishable_filter` menuntut `owned`); `workshop_id`/`customer_id`/`lead_id`/`segment_id` hantu melahirkan dokumen YATIM sehingga tabel & laporan menampilkan '-' abadi; kampanye ke segmen hantu 'sukses' terkirim ke NOL penerima; `rates={'ngawur':500000}` membuat rute tampak bertarif tetapi tak pernah bisa dijual | `scripts/guardrails/verify_reference_integrity.py` (runtime; anti hijau-palsu: probe yang ditolak karena alasan LAIN dihitung pelanggaran) | `services/refs.py` |
| **INV-REF-02** | `bookings.destination` = RELASI ke master `destinations` (bukan teks bebas): validator satu pintu `services/refs.destination_or_400` dipanggil di jalur create/group/update `routers/bookings.py`; nilai disimpan sebagai NAMA KANONIK master; FE memakai selector dari `GET /bookings/destination-options`; destinasi operasional non-wisata disimpan ber-`status='draft'` agar tak tayang di web publik. RUNTIME: destinasi di luar master → 400 berALASAN destinasi. **Batch 2 (2026-08-29):** `bookings.origin` = relasi master `pickup_points` (`refs.origin_or_400` di create/group/update; quick-add satu pintu `POST /api/pickup-points`; seed + migrasi `scripts/migrate_ssot_batch2.py`); `leads.destination` jalur ERP divalidasi `destination_or_400`; jalur PUBLIK (lead web/landing) memakai `destination_normalize` LUNAK — inbound eksternal tidak ditolak, hanya dikanonikkan bila cocok master. **Batch 3 (2026-08-29):** destinasi PENAWARAN divalidasi master — `routers/quotations.py` create/update via `destination_or_400` (update hanya-bila-diubah); form penawaran WEB PUBLIK (`features/public/Quotation.jsx`) memakai `<select>` berisi opsi master dari endpoint publik baru `GET /api/public/destination-options` (backend publik tetap LUNAK via `destination_normalize` — nilai warisan/di luar master tetap DITERIMA); kelola master satu pintu di halaman `/app/masterdata` (owner+ops_admin) via `GET/PATCH /api/master/pickup-points[/{id}]` & `GET/PATCH /api/master/destinations[/{id}]` — **RENAME = CASCADE** ke bookings/leads/quotations, **NONAKTIF** (`active` publik / `ops_active` operasional, default aktif bila field tak ada) menyembunyikan dari SEMUA selector (filter di `services/refs.py` + endpoint options) dan pemakaian baru DITOLAK; guard `verify_ssot_relations.py` diperluas +5 cek batch 3 → total **17 cek** (quotations, public options, master cascade/nonaktif). **Batch 4 (2026-08-29):** normalisasi LUNAK menutup SEMUA jalur tulis publik/inbound — `services/refs.origin_normalize` (baru, mirror `destination_normalize` vs master `pickup_points`); pemesanan online `services/booking_public.create_booking` menormalkan `origin`+`destination` (booking publik menulis ke koleksi yang SAMA dgn ERP); lead landing (`routers/public.py`) menormalkan `origin`; lead ads (`services/ads.py`) menormalkan `destination`; **preview cascade** di Master Data — `GET /master/destinations` kini melaporkan `used_by_quotations`, dan FE `MasterData.jsx` menampilkan panel konfirmasi berisi jumlah booking/lead/penawaran yang akan ikut berubah SEBELUM rename dieksekusi (`md-confirm-*`, `md-rename-confirm-*`, `md-rename-cancel-*`); guard diperluas +5 statik +1 runtime (probe POST /public/booking 'bandung'/'bali' → dokumen tersimpan WAJIB 'Bandung'/'Bali') → total **23 cek**. **Batch 5 (2026-08-29):** master KOTA baru (koleksi `cities`, `cty_`) — `customers.city` & `partners.city` divalidasi KERAS `refs.city_or_400` (create+update, nama kanonik; kosong=sah), quick-add satu pintu `POST /api/cities`, selector FE `CitySelect` (form pelanggan `cf-city` & mitra `pf-city`), kelola di `GET/PATCH /api/master/cities[/{id}]` (rename CASCADE customers+partners, toggle `active`); `vehicle_type` lead landing dinormalkan LUNAK `refs.vehicle_type_normalize` vs SSOT `pricing.VEHICLE_TYPE_LABELS` (juga `requested_vehicle_type` booking publik); **GABUNG destinasi kembar** `POST /api/master/destinations/{id}/merge` — cascade bookings/leads/quotations ke nama target lalu sumber dinonaktifkan + `merged_into` (tidak ada penghapusan; target wajib aktif & bukan hasil gabungan); **ekspor Excel** `GET /api/master/export` (3 sheet: Titik Jemput/Destinasi/Kota + pemakaian); seed + `scripts/migrate_ssot_batch5.py`; koleksi `cities` terdaftar di verify_schema/validate_compliance/PURGE_COLLECTIONS; guard diperluas +5 statik +2 runtime (kota ngawur → 400; GET /cities) → total **30 cek**. **Batch 6 (2026-08-29):** **UNDO gabungan** — merge kini MENCATAT id dokumen yang ikut pindah (`merged_moved` di dokumen sumber); `POST /api/master/destinations/{id}/unmerge` mengembalikan HANYA dokumen tercatat yang destinasinya masih nama target (yang diubah manual sesudah merge dilewati + dilaporkan `skipped`), lalu sumber aktif kembali (`$unset merged_into/merged_moved`); UI tombol "Batalkan Gabungan" (`md-unmerge-*`) dgn panel konfirmasi ber-jumlah `merged_moved_count`; **kota BENGKEL** ikut master `cities` — `routers/workshops.py` create/update via `city_or_400`, FE `WorkshopFormDialog` pakai `CitySelect` (wsh-city), rename kota CASCADE + pemakaian + sheet Excel kini mencakup workshops; guard +3 statik (unmerge+merged_moved, workshops city_or_400 ≥2, cascade workshops) → total **34 cek**. **Batch 7 (2026-08-29):** GABUNG + BATALKAN utk **titik jemput kembar** — `POST /api/master/pickup-points/{id}/merge` (cascade `bookings.origin` ke nama target, catat `merged_moved.bookings`, sumber `active=False`+`merged_into`) & `POST .../unmerge` (kembalikan booking tercatat bila origin masih nama target, sisanya `skipped`); UI panel Titik Jemput kini punya tombol Gabung/Batalkan Gabungan yang sama dgn destinasi (testid `md-merge-*`/`md-unmerge-*` generik); cek guard merge/unmerge diperketat: `pk.count("/merge") ≥ 2` dan `pk.count("/unmerge") ≥ 2` | RC-E/BUG-0135: 'Bromo' vs 'Gunung Bromo' vs 'bromo ' = 3 destinasi berbeda di laporan; paket/penawaran (sudah `destination_id`) tak pernah cocok dgn booking; input bebas = pelanggaran SSOT | `scripts/guardrails/verify_ssot_relations.py` (statik + runtime, bersih-bersih via `purge_guard_bookings`) | migrasi data lama: `scripts/migrate_booking_destinations.py` |
| **INV-BOOK-02** | Pemesanan online: `schemas_booking.PublicBookingSubmit` DILARANG punya field harga; `create_booking` wajib memakai `publishable_vehicles` + `build_quote` (hitung ulang server) + `assert_free` (booking aktif **dan** jendela perawatan) + `vehicle_lock` yang MEMBUNGKUS `insert_one`; router publik ber-rate-limit & tak membaca harga dari body; RUNTIME: 8 pemesanan PARALEL pada unit+jendela sama → **TEPAT 1** sukses & 0×5xx, pesanan bentrok → 4xx berALASAN, unit tak-tayang/mitra → 4xx walau `vehicle_id` ditebak | formulir publik dulu menulis `vehicle_id=None, total_amount=0` tanpa cek apa pun (tamu "berhasil memesan" tanggal penuh, ditolak manual via WA berjam-jam kemudian); klien bisa memesan Rp 1 bila skema menerima total; cek ketersediaan di luar mutex → satu unit dijual dua kali (dua pelanggan sudah bayar DP); unit mitra/tersembunyi bisa dipesan dengan menebak id | `scripts/guardrails/verify_booking_public.py` (statik **AST** + runtime paralel) | `PRICE_FIELDS` di skrip |
| **INV-STR-01** | Setiap field bertipe `str` dengan NAMA sensitif (identitas/label/teks pendek) di `backend/schemas*.py` WAJIB punya `max_length=` (atau terdaftar di `ALLOW_UNBOUNDED` + alasan); RUNTIME: 60.000 karakter ke 3 permukaan tulis (ERP + publik) → **4xx** (bukan 2xx senyap, bukan 5xx) sementara nilai normal tetap 2xx | **BUG-0114 (nyata):** `verify_adversarial_5xx.py` mengirim `"A"*60000` dan hanya menuntut "tidak 5xx" → gate HIJAU padahal nilainya TERSIMPAN (`customers.name` 60.000 karakter). Akibat: satu baris merusak tata letak tabel Booking ERP, dan nama itu ikut masuk PDF invoice + payload WhatsApp (batas 4096) — semua rusak tanpa satu pun error di log. Pelajaran: "tidak 5xx" ≠ "input tervalidasi"; uang dijaga INV-NUM-01 (`ge=`), teks butuh `max_length=` | `scripts/guardrails/verify_string_bounds.py` (statik **AST** + runtime) | `SENSITIVE`/`ALLOW_UNBOUNDED` di skrip |
| **INV-THEME-01** | Kontras & pewarisan tema tidak boleh bergantung pada kebetulan. STATIK: (1) DILARANG class Tailwind arbitrary yang memakai token tema sebagai warna langsung (`from-/via-/to-[color:var(--primary)]`, `bg-[var(--card)]`) — token proyek ini berisi TRIPLET HSL sehingga deklarasinya invalid; (2) `.glass-modal`/`.glass-3d`/`.glass-on-hero` (termasuk fallback `@supports`) DILARANG memaku `hsl(0 0% 100%)` — latar wajib token yang ikut mode (`--glass-bg-strong`/`--card`); (3) refraksi/sheen wajib lewat `--refraction-opacity` (≤ 0.30) + `--refraction-blend` + `--refraction-mask`, `mix-blend-mode: screen` hardcode DILARANG; (4) DILARANG mendeklarasikan custom property di `:root`/`.dark` yang menyusun token TEMA (mis. `--x: var(--card) / .93`); (5) token offset elemen mengapung (`--header-h`, `--sticky-cta-h`, `--fab-bottom`, `--panel-bottom`) wajib ada dan `ChatWidget` wajib memakainya + `maxHeight` (dilarang `bottom-<n>` pada elemen `fixed`); (6) `ThemeContext` wajib memasang `data-surface`/`data-theme` di `<html>` DAN membersihkannya saat unmount; (7) tiap blok `.dark [data-surface="public"][data-theme="X"]` wajib punya kembaran `[data-surface="public"][data-theme="X"].dark` | **BUG-0121…0126 (nyata, dari screenshot user 2026-08-12):** CTA `/blog/:slug` memakai `to-[color:var(--primary)]` → browser membuang SELURUH `background-image`, panel jadi transparan dan teks putih hilang di kertas putih (user: "ada button cta namun UI-nya rusak"); `.glass-modal` dipaku putih `!important` → modal exit-intent putih-di-atas-putih di mode gelap; refraksi `screen` opacity .55 menyapu label/placeholder kartu estimator di atas foto terang; konten Radix yang di-PORTAL ke `<body>` berada di luar `[data-surface][data-theme]` sehingga dialog & dropdown memakai palet ERP terang saat situs gelap (ditemukan testing agent iter-86); `--surface-on-hero: var(--card)/.93` di `:root` disubstitusi di :root sehingga kartu tetap TERANG di mode gelap (regresi buatan sendiri, tertangkap saat verifikasi); ChatWidget `bottom-40` + tinggi tetap 440px menembus header pada viewport pendek (user: "posisi chat terlalu di atas"). Pelajaran: semua kegagalan ini SENYAP — tidak ada error konsol, tidak ada tes runtime yang merah | `scripts/guardrails/verify_theme_contrast.py` (statik) + `scripts/guardrails/selftest_theme_contrast.py` (7 mutasi MERAH↔HIJAU) | `THEME_COLOR_TOKENS` di skrip · `design_guidelines.md` §readability_on_glass_rules_executable |
| **INV-CLEAN-01** | Data uji DILARANG tertinggal di koleksi operasional. STATIK: setiap skrip yang menulis lewat API sungguhan (`verify_pricing_integrity`, `verify_booking_public`, `verify_string_bounds`, `verify_reference_integrity`, `verify_identity_race`, `verify_media_runtime`, `verify_adversarial_5xx`, `scripts/mutation_smoke.py`, `selftest_booking_guards`) WAJIB memanggil mesin bersih-bersih bersama `purge_guard_artifacts()`/`purge_guard_bookings()` dari `_common.py`; `services/audit.py` WAJIB memotong (`_clip`) `summary`/snapshot. RUNTIME: 40 koleksi operasional wajib **0** dokumen berpenanda data uji (`GUARD_MARKERS`: "Penjaga INV-", "Smoke Customer/Vehicle", "Guard Lead/Route ", "guard-media-", karakter NUL, nomor `0800000xxx`/`0810000000`) dan **0** field identitas melebihi `OVERLONG_RULES`. Penjaga ini dijalankan PALING AKHIR di gate dan TIDAK membersihkan apa pun (membersihkan = menutupi kebocoran) | **BUG-0127 (nyata, keluhan user 2026-08-13: "ada nama customer aaaaaaaa… itu yang mengganggu"):** penjaga membersihkan dokumen UTAMA tetapi tidak SIDE-EFFECT-nya. Akibat tiap kali `gate.sh` jalan: `customers` berisi nama **60.000 karakter "AAAA…"** (dari self-test mutasi INV-STR-01 yang sengaja melepas `max_length` — nilai tersimpan, kode di-revert, dokumen tak pernah dihapus), `audit_logs` punya baris ber-`summary` **60.016 karakter**, Inbox berisi percakapan "Penjaga INV-BOOK-02"/"Penjaga INV-PRICE-01"/"Smoke Customer" (2 di antaranya menunjuk customer yang sudah dihapus = referensi yatim), lonceng notifikasi ops penuh pengingat pesanan hantu, **35 dari 48** `events` + `automation_runs` adalah artefak uji, CRM menyimpan lead & penawaran berisi karakter NUL + segmen "AdvSeg", dan Media Library menyimpan aset `guard-media-*`. Semua SENYAP: gate melaporkan **HIJAU 40/40** dan yang menemukan justru PENGGUNA. Pelajaran: "gate hijau" ≠ "produk bersih" — uji yang menulis WAJIB bertanggung jawab atas seluruh jejaknya | `scripts/guardrails/verify_no_test_pollution.py` (statik + runtime) + `scripts/guardrails/selftest_no_test_pollution.py` (5 mutasi MERAH↔HIJAU) | `GUARD_MARKERS`/`GUARD_PHONE_PREFIXES`/`PURGE_COLLECTIONS`/`OVERLONG_RULES` di `scripts/guardrails/_common.py` · alat perbaikan `scripts/purge_test_pollution.py` |
| **INV-CMS-01** | Siklus hidup konten CMS wajib AMAN & PULIH. STATIK: (1) `DELETE /content/{resource}/{id}` WAJIB lewat `content_trash.move_to_trash` dan DILARANG memanggil `db[resource].delete_one` langsung; (2) `create_content` & `update_content` WAJIB menulis `content_versions.snapshot`, service WAJIB punya `MAX_VERSIONS` + `prune`, pemulihan versi WAJIB menyaring field lewat `content_versions.restorable`; (3) `update_content` WAJIB memanggil `content_redirects.record_slug_change`, service WAJIB meratakan rantai (`update_many({to_path: old})`) dan membuang pengalihan yang berasal dari slug baru (anti-lingkaran), endpoint publik `GET /public/redirect` WAJIB ada, dan `content_publish.preview_url` WAJIB memakai SSOT `PUBLIC_PATHS`; (4) pemulihan dari Tempat Sampah WAJIB memaksa `status = draft` + retensi (`RETENTION_DAYS`/`expires_at`) + penjadwal `purge_expired` ter-wire di `server.py`; (5) endpoint massal WAJIB `Depends(CMS)` + batas `BULK_MAX`; (6) koleksi `content_versions`/`content_trash`/`content_redirects` WAJIB terdaftar di `verify_contract`, `validate_compliance`, `verify_schema`, `seed_data`, **dan** DUA tempat di `_common.py` (daftar `PURGE_COLLECTIONS` + cascade `item_id`); (7) UI WAJIB benar-benar memakainya (`VersionHistoryDialog`, `TrashDialog`, `RedirectManagerPanel`, testid `content-bulk-bar`/`content-select-all`/`content-trash-open`/`content-history-*`) dan ketiga halaman detail publik WAJIB MEMANGGIL `useSlugRedirect(...)`. RUNTIME: buat konten → ubah slug → `/public/redirect` mengembalikan URL baru → hapus → muncul di Tempat Sampah → pulih sebagai **draft** → aksi massal jalan → driver 403 | **Gap NYATA yang ditutup fase CMS-CW3 (2026-08-18, audit atas pertanyaan user "cms apakah sudah clear semua?"):** (a) tombol hapus CMS memanggil `delete_one` — satu klik dan destinasi/paket/artikel hilang selamanya beserta galeri, tur 360°, & metadata SEO-nya (dialognya bahkan berbunyi "tidak dapat dibatalkan", dan itu benar); (b) tidak ada satu pun snapshot isi sebelum penyuntingan → salah tempel = kerusakan konten permanen, satu-satunya sisa adalah JSON mentah di Audit Log yang tak punya tombol pulihkan; (c) mengubah slug MEMATIKAN URL lama (404) — peringkat pencarian yang dibangun berbulan-bulan, tautan dari medsos/blog pihak lain, dan trafik iklan berbayar ikut mati tanpa peringatan; (d) tidak ada aksi massal sehingga editor menayangkan konten satu per satu. Pelajaran yang dikunci: fitur CMS dianggap "selesai" hanya bila kesalahan manusia bisa DIBATALKAN | `scripts/guardrails/verify_content_lifecycle.py` (statik + runtime) + `scripts/guardrails/selftest_content_lifecycle.py` (11 mutasi MERAH↔HIJAU) | `backend/services/content_versions.py` · `content_trash.py` · `content_redirects.py` · POC `scripts/test_core_cms_cw3.py` (100 cek) |

> Invariant runtime lama (RC-01..RC-07, INV-1..INV-21) tetap dijaga gate inti
> (`verify_state_machine`, `verify_concurrency`, `verify_cross_entity`, dll). Guardrail v2
> **menambah lapisan statik** agar kelas bug tertangkap SEBELUM runtime, di endpoint mana pun.

## Cara menambah invariant baru
1. Tambah penjaga di `scripts/guardrails/verify_*.py` (statik lebih disukai; runtime bila perlu perilaku).
2. Daftarkan di tabel ini + tambahkan ke `scripts/gate.sh` (blok STATIK atau RUNTIME).
3. Sertakan **self-test**: buktikan penjaga MERAH saat invariant dilanggar, HIJAU saat benar.
   Sejak Fase 3 bentuk yang DISUKAI adalah self-test **otomatis**: `scripts/guardrails/selftest_<nama>.py`
   yang menyuntikkan mutasi ke SANDBOX (salinan sementara, kode nyata tak disentuh), menuntut penjaga
   MERAH dengan pesan yang benar, lalu ikut dijalankan `gate.sh`. Contoh acuan:
   `selftest_media_unified.py` (24 mutasi) & `selftest_media_runtime.py` (server tiruan). Catatan self-test manual boleh, tapi kedaluwarsa sejak
   kode berikutnya berubah — dan sesi baru tak punya cara memverifikasinya ulang.
4. Pengecualian sah harus **eksplisit + beralasan** di allowlist (jangan pernah lolos diam-diam).

## Prinsip anti "hijau-palsu" (pelajaran dari M1)
Penjaga harus benar-benar menangkap pelanggaran. Setiap penjaga di atas telah di-self-test:
inject pelanggaran \u2192 gate MERAH \u2192 revert \u2192 gate HIJAU. Ulangi self-test bila mengubah penjaga.

**Tiga cara penjaga berhenti menggigit tanpa satu pun error (semuanya pernah terjadi di repo ini):**
1. **Puas oleh PROSA** — cek `"ETag" not in body` lolos karena kata itu ada di docstring. Obat:
   buang docstring/komentar sebelum mencocokkan (`code_only`/`jsx_code_only`).
2. **Regex yang rapuh** — dekorator ditulis multi-baris, regex berhenti cocok, 0 rute terpindai,
   0 pelanggaran, HIJAU. Obat: baca struktur (AST), dan tuntut jumlah minimum objek terpindai.
3. **Cabang yang tak pernah jalan** — `if src.exists():` menjadi False setelah folder dipindah →
   separuh penjaga dilewati diam-diam. Obat: ketiadaan sasaran = PELANGGARAN, bukan skip.

**Self-test Putaran 12 (Phase-1 fix M1/ID-RACE/SET-1):**
- **M1** (`verify_api_contract.py`): dulu 0 FE-call terdeteksi (hanya cari `axios.`/`fetch(`), padahal FE pakai `apiClient.<m>()` -> CHECK B lolos palsu. Fix: deteksi `apiClient` + prefix `/api` + pencocokan berbasis-segmen. Kini **260 call (167 path) tervalidasi**. Self-test: sisip `apiClient.get("/route-ngawur")` -> MERAH (tunjuk route+file) -> revert -> HIJAU.
- **INV-IDENT-01** (`verify_identity_race.py`): self-test: DROP index `phone_normalized_1` -> 8 POST paralel -> 2 duplikat dibuat -> MERAH -> buat ulang index -> HIJAU (2xx=1, 409=7).
- **INV-SET-01** (`verify_settings_bounds.py`): self-test: nonaktifkan `_validate_pricing` -> 6 tarif buruk tersimpan 200 senyap -> MERAH -> revert -> HIJAU (semua 400, valid 200).
- **INV-META-01** (`verify_guardrail_registry.py`): self-test: buat guardrail baru tanpa wiring/registrasi -> MERAH (2 pelanggaran: tak ter-wire + tak terdaftar) -> hapus -> HIJAU. (Saat dibuat, sempat menemukan gap nyata: format INV-ID gabungan `INV-RBAC-01/02/03` -> deteksi dibuat toleran.)

**Self-test Ekosistem Guardrail (Layer B/C, 2026-07-05):**
- **INV-AUTH-01** (`verify_auth_coverage.py`): 267 endpoint dipindai, 24 publik (allowlist), 243 wajib-auth SEMUA menegakkan auth. Self-test: tambah endpoint tanpa `Depends` auth -> MERAH (tunjuk `METHOD /path`) -> hapus -> HIJAU.
- **INV-QUALITY-01** (`verify_effort_quality.py`): self-test: sisip rahasia hardcoded (`sk-...`) + bare `except Exception: pass` + URL backend hardcoded di FE -> MERAH (3 sinyal berat) -> revert -> HIJAU. Kalibrasi: bare/`Exception` swallow = blocking; specific-exception & `# noqa`-acknowledged = advisory. (Saat dibuat menemukan 1 bug nyata: `services/whatsapp.py:317` bare `except Exception: pass` -> diperbaiki jadi log.)
- **INV-CONV-01** (`verify_conversion_hooks.py`): 12 cek. Self-test 2026-08-10: putuskan import `conversion_hooks.handle_event` di `services/events.py` -> **MERAH** ("SEMUA konversi iklan tidak pernah dijadwalkan") -> revert -> HIJAU. Penjaga ini lahir DARI bug nyata: sampai fase F2 `services/conversions.py` sudah lengkap & lulus POC, tetapi `rg conversions backend` menunjukkan HANYA `routers/marketing.py` yang mengimpornya — jadi booking & DP tak pernah dilaporkan ke platform.
- **INV-ADS-01** (`verify_ads_write_safety.py`): 19 cek. Self-test 2026-08-10: hapus baris `body["status"] = PAUSED` di `ads_safety.meta_write_payload` -> **MERAH** ("kampanye bisa langsung ACTIVE dan membelanjakan budget") -> revert -> HIJAU. Juga melarang router iklan memanggil `httpx`/`graph.facebook.com`/`googleads.googleapis.com` langsung (jalur pintas yang melewati pengaman).
- **INV-AUD-01** (`verify_audience_consent.py`): 10 cek. Self-test 2026-08-10: ubah `hash_rows_meta(eligible)` menjadi `hash_rows_meta(members)` di `audiences.sync_segment` -> **MERAH** ("filter jadi hiasan") -> revert -> HIJAU. Menutup kelas bug privasi yang tidak menghasilkan error apa pun.
- **INV-LP-02** (`verify_landing_contract.py`): 327 cek. Self-test 2026-08-11: kembalikan `_trust` agar hanya menerima dict + buang pagar try/except di `validate_blocks` -> **MERAH** ("validate_blocks MELEMPAR pada props adversarial (AttributeError) → editor bisa 5xx lagi") -> revert -> HIJAU. Penjaga ini lahir DARI bug nyata BUG-0111: `POST /api/landing/pages` dengan template `armada-cepat` balas **HTTP 500** sementara 3 template lain HTTP 200 — kegagalan yang hanya muncul di SATU jalur data. Ia juga menangkap `spacer` yang tak punya `case` di `LandingRender.jsx` (ukuran jarak diabaikan senyap).
- **INV-MEDIA-02** (`verify_media_safety.py`): 21 cek. Self-test 2026-08-11: ubah `media_url()` kembali menjadi `/api/media/{id}` -> **MERAH** ("semua gambar & video halaman iklan akan 404 tanpa error backend") -> revert -> HIJAU. Lahir dari BUG-0112. Pelajaran tambahan saat menulis penjaga ini: JANGAN mem-parsing tanda tangan Python dengan `[^)]*` — `File(...)`/`Query(default=...)` membuatnya terpotong dan menghasilkan temuan PALSU; dipakai penyeimbang tanda kurung (`signature()`).
- **INV-SEC-02** (`verify_secret_exposure.py`): 172 cek. Self-test 2026-08-10: ubah satu `logger.warning` di `services/meta_ads.py` agar mencetak `self.token` -> **MERAH** (menunjuk file:baris) -> revert -> HIJAU. Termasuk cek terbalik yang penting: `ctwa_clid` DILARANG di-hash (bila di-hash, konversi Klik-ke-WhatsApp tidak akan pernah cocok di Meta).

**Self-test Fase 3 (Media Library SATU) — pertama kali OTOMATIS & ikut gate:**
- **INV-MEDIA-03** (`verify_media_unified.py`, 58 cek): self-test-nya bukan lagi catatan manual, melainkan skrip `scripts/guardrails/selftest_media_unified.py` yang ikut `gate.sh`. Skrip itu membangun SANDBOX (salinan `backend/` + `frontend/src/` + penjaga di direktori sementara), menyuntikkan **24 mutasi** — masing-masing memperkenalkan kembali satu kelas bug nyata — lalu menuntut penjaga **MERAH dengan pesan yang benar**, dan memulihkan sandbox. Kode nyata tidak pernah disentuh. Hasil: **24/24 tertangkap** (`M01` router menulis berkas sendiri, `M04/M05` rute media tanpa `Depends(MEDIA)`, `M07/M23` ETag hilang, `M08` cache membeku, `M09` versi tak naik, `M12` folder pindah ke cucunya, `M13` hapus folder menghapus aset, `M17` batas crop mati, `M18..M22` penyatuan picker/menu/route/RBAC frontend, `M24` `.strip()` pada nilai klien tanpa `str()`, dst).
- Setiap mutasi **memvalidasi dirinya**: bila teks sasaran tak ditemukan lagi (kode di-refactor), self-test melaporkan **"mutasi basi"** sebagai KEGAGALAN — bukan lolos diam-diam. Ini menutup cara paling halus sebuah self-test kehilangan makna.
- **Dua lubang NYATA ditemukan oleh self-test ini pada penjaganya sendiri** (dan sudah ditutup):
  1. Cek `"ETag" not in public_media` selalu lolos karena kata **"ETag" ada di DOCSTRING** fungsi — header aslinya boleh diganti nama tanpa gate sadar. Perbaikan: semua cek tekstual kini memakai `code_only()` (docstring & komentar dibuang) + ETag dituntut hadir di **kedua** jalur respons (304 dan 200), karena kehilangan ETag hanya di jalur 200 membuat 304 mustahil terjadi.
  2. Pemindaian rute `/media*` berbasis **regex satu-baris** berhenti mencocokkan begitu dekorator ditulis multi-baris (`response_model=`, dst) → rute baru tanpa RBAC lolos diam-diam. Perbaikan: rute & `Depends(MEDIA)` sekarang dibaca lewat **AST** (`router_endpoints`/`guarded_by`), juga menerima bentuk sah `dependencies=[Depends(MEDIA)]`.
- Pengerasan lain yang lahir dari self-test: cek batas crop menuntut **penegakan** (`> MAX_CROP_SIDE`), bukan sekadar konstanta yang masih tertulis; `legacy_key` dituntut lewat regex `"legacy_key",\s*unique=True`; menu diuji lewat path nyata `"/app/media"` + route `App.js` + keanggotaan `ops_admin` (bukan sekadar kata "media" yang juga muncul di daftar peran lain); import picker frontend dituntut sebagai **import sungguhan** (baris yang dikomentari tidak lagi dianggap sah); dan bila `frontend/src` tak ditemukan, penjaga **MERAH** alih-alih melewati separuh invariant diam-diam.
- **INV-META-01 diperluas**: setiap `selftest_*.py` wajib ter-wire di `gate.sh` dan menguji penjaga yang benar-benar ada. Tanpa itu, satu baris yang dihapus dari gate bisa melenyapkan seluruh pembuktian anti-hijau-palsu tanpa jejak.
- **INV-MEDIA-04** (`verify_media_runtime.py`, 60 cek) — lapis RUNTIME yang dibuat karena statik saja tidak cukup, dan ia LANGSUNG menemukan bug nyata pada percobaan pertama: `PATCH /api/media/{id}` dengan `folder_id: 5` (angka) → `(body.get("folder_id") or "").strip()` melempar `AttributeError` → **HTTP 500**. Diperbaiki dengan koersi `str(...)` di `routers/media.py` + seluruh `media_lib` (14 tempat), lalu dikunci aturan statik baru di INV-MEDIA-03 (mutasi `M24`) supaya kelas bug ini tak bisa kembali.
  * Daftar rute yang diuji RBAC-nya dibaca dari **OpenAPI aplikasi yang berjalan** (17 rute), bukan daftar tetap di skrip: endpoint media BARU otomatis ikut diuji. Daftar manual selalu tertinggal — dan justru rute yang tertinggal itu yang bocor.
  * Idempotensi impor legacy diuji dengan **berkas legacy sungguhan** yang dibuat lalu dibersihkan. Sebelumnya cek ini hampa: kalau tak ada berkas untuk diimpor, "jalan kedua mengimpor 0" selalu benar tanpa membuktikan apa pun.
  * Self-test-nya (`selftest_media_runtime.py`) menjalankan penjaga terhadap **server tiruan**: (A) alamat mati → wajib MERAH ("tidak bisa login", bukan hijau/skip), (B) server serba-izin (semua 200) → wajib MERAH menyebut kebocoran RBAC driver, (C) server yang menolak semua peran → wajib MERAH menyebut REGRESI ops_admin (over-block juga kerusakan). Ketiganya membuktikan pemeriksaan benar-benar dieksekusi.
  * Temuan proses: versi pertama penjaga ini melaporkan "ETag hilang" pada aplikasi yang SEHAT karena `dict(resp.headers)` dicari dengan `"ETag"` padahal uvicorn mengirim `etag` huruf kecil. Temuan PALSU sama berbahayanya dengan lubang — sesi berikutnya belajar mengabaikan gate. Perbaikan: pencarian header case-insensitive.

---

## Tambahan Sesi E27 (2026-08-10) — Kalender Keberangkatan & anti hijau-palsu

### INV-21 sekarang DUA ARAH (simetris)
`INV-21` (maintenance window memblok booking aktif) dulu hanya dijaga dari sisi **booking**
(`create/reschedule/approve/confirm` memanggil `find_maintenance_conflicts`). Sisi **perawatan**
tidak pernah memeriksa booking → POC `test_core_conflict.py` (KELAS 3) membuktikan ops bisa
menjadwalkan perawatan di atas keberangkatan `confirmed` (HTTP 200) sehingga invariant bisa
dilanggar lewat pemakaian UI normal.

- Penjaga baru (runtime, kode produksi): `routers/maintenance.py::_assert_no_departure_clash`
  dipanggil `POST /maintenance` dan `PATCH /maintenance/{id}` (nilai EFEKTIF `rec + updates`),
  dibungkus `vehicle_lock` → serial per-armada, memakai mutex yang SAMA dengan jalur booking
  (`booking_locks`) sehingga tidak ada TOCTOU antara "tulis perawatan" dan "tulis booking".
- Aturan tambahan untuk kontributor: **setiap** jalur tulis baru yang menyentuh
  `[vehicle_id, start, end]` (booking, perawatan, sub-charter, dispatch) WAJIB memeriksa KEDUA
  arah (booking↔perawatan) di dalam `vehicle_lock`.
- Self-test: POST perawatan menutupi window `BK-000x` aktif → 400 (menyebut kode booking);
  window bebas → 200; ubah `cost`/`note` saja pada PATCH → 200 (tidak boleh false-reject).

### Lapisan risiko kalender = SATU sumber kebenaran di server
`services/attention.py` + `GET /api/departures/attention` adalah satu-satunya penghitung risiko
keberangkatan (8 kelas). **Frontend TIDAK boleh menghitung ulang bentrok** — pelanggaran lama:
FE mengelompokkan bentrok berdasarkan `vehicle_name` (bukan `vehicle_id`) dan ikut menghitung
status `completed`, sehingga peringatan bisa salah/mustahil muncul. Bentrok armada hanya dihitung
untuk status aktif `{hold, confirmed, ongoing}` (selaras `ACTIVE_BOOKING_STATUSES`), bentrok sopir
juga mencakup `pending` (sopir sudah dijanjikan meski belum mereservasi armada).

### Anti hijau-palsu: SKIP senyap dilarang di `verify_delivery`
`verify_delivery.py` dulu `return 0` (lulus) bila `ACTIVE_PHASE` tidak cocok heading fase mana pun
— kondisi yang BENAR-BENAR terjadi (`ACTIVE_PHASE: CMS-G10` vs heading `### PHASE CMS-G1..G10`),
sehingga D1/D1b/D2 (deliverable + orphan endpoint) tidak pernah dijalankan berbulan-bulan.
Sekarang kondisi itu **MERAH** ("DRIFT MANIFEST"). Self-test: ACTIVE_PHASE palsu → rc=1;
`E27` → rc=0. Konsekuensi bagi kontributor: **flip `ACTIVE_PHASE` ke token yang persis sama**
dengan heading fase, dan isi daftar deliverable-nya.

### Pengecualian allowlist yang ditambahkan (eksplisit + beralasan)
| Penjaga | Item | Alasan |
|---------|------|--------|
| `verify_auth_coverage.py` | `seo.py GET /sitemap.xml`, `GET /robots.txt` | artefak SEO wajib terbaca crawler tanpa login; tak memuat data privat |
| `verify_delivery.py` (`NON_FE_ENDPOINTS`) | `/api/sitemap.xml`, `/api/robots.txt` | dikonsumsi crawler, bukan kode FE → heuristik "orphan" tak berlaku |
| `verify_schema.py` (`REQUIRED_EXEMPT`) | `bookings.vehicle_id` untuk status `pending/draft/cancelled` | SSOT `docs/03_DATA_MODEL.md`: "nullable saat status=pending" (E19 self-service; armada ditetapkan saat approve) |

---

## Tambahan Sesi E28 (2026-08-10) — RBAC 3 lapis (RBAC-CAL-01 + RBAC-SCOPE)

### Akar masalah yang ditutup
`iteration_72` (ronde 2 frontend E27) menemukan **driver bisa membuka `/app/calendar`**. Investigasi
menunjukkan itu BUKAN sekadar RoleGuard lupa dipasang — route-nya SUDAH dibungkus `<RoleGuard
section="calendar">`. Kebocoran terjadi karena **tiga lapis gagal sekaligus**:

| Lapis | Kondisi sebelum fix | Akibat |
|-------|--------------------|--------|
| FE allowlist | `ROLE_MENU_ALLOWLIST.driver` memuat `"calendar"` | `canAccess()` bilang BOLEH → RoleGuard meloloskan |
| BE matriks SSOT | `SECTION_ACCESS` **tidak punya** key `calendar` | `require_section("calendar")` tak mungkin dipakai (selalu 403) → penulis endpoint memilih `get_current_user` saja |
| BE endpoint | `/departures/attention`, `/bookings/calendar`, `/bookings/calendar/export` hanya ber-auth | driver dapat **HTTP 200** (terbukti curl) meski UI-nya diblok |

Kenapa guardrail lama tidak menangkap: `INV-RBAC-03` memakai daftar `FORBIDDEN` yang **di-hardcode
manual**. Modul yang lahir SETELAH daftar itu ditulis (mis. `calendar`) tak pernah disebut → hijau
palsu. **Pelajaran:** daftar-larangan manual selalu tertinggal dari pertumbuhan kode; SSOT harus
matriks yang benar-benar dipakai runtime (`permissions_config.SECTION_ACCESS`), dan penjaga harus
membandingkannya **dua arah** dengan FE.

### Temuan tambahan saat audit (kelas baru): RBAC-SCOPE
Setelah pintu modul beres, probe row-level menunjukkan driver memanggil `GET /api/bookings` →
**8 dari 8 booking** (termasuk trip driver lain, `customer_name`, `total_amount`, `paid_amount`),
dan `GET /api/drivers` → seluruh daftar sopir + nomor telepon. SSOT §3 menyatakan
"👁️ trip miliknya" / "👁️ profil sendiri". Ditutup dengan `services/rbac_scope.py` (fail-closed:
driver tanpa dokumen `drivers` terpaut → sentinel `__tanpa_driver__`, bukan "lihat semua").
Sesudah fix: driver 3/8 booking (miliknya), 1 profil sopir; `/api/driver/*` (workspace) tetap 200.

### Self-test (MERAH ↔ HIJAU) — dijalankan 2026-08-10
1. Sisip kembali `"calendar"` ke allowlist driver + hapus `await scope_bookings_query(...)` dari
   `routers/bookings.py` → guardrail **MERAH 3 pelanggaran** (INV-RBAC-03 drift, INV-RBAC-04
   DRIFT FE→BE, INV-RBAC-05 anchor scope hilang).
2. Revert → **HIJAU 133 cek, 0 pelanggaran**.
3. Kalibrasi anchor: cek awal `"scope_bookings_query" in src` LOLOS palsu karena baris `import`
   masih menyebut nama fungsi → diperketat menjadi regex `await <fn>\(` (pemanggilan nyata).

### Aturan untuk kontributor berikutnya
Menambah modul/menu ERP baru = **wajib** menyentuh 3 tempat: `navigationConfig.js`
(allowlist + PAGE_META), `permissions_config.SECTION_ACCESS` (+`SECTION_ALIASES` bila ejaan beda),
dan `Depends(require_section("<section>"))` di router-nya. Bila modul itu menampilkan data
"milik-sendiri", tambahkan penyaring di `services/rbac_scope.py` + daftarkan di
`SCOPE_REQUIREMENTS` (guardrail). Melewatkan salah satunya = gate MERAH.

### Self-test INV-RBAC-06 (runtime) — 2026-08-10
Ganti `Depends(CALENDAR)` menjadi `Depends(get_current_user)` di `routers/departures.py`
(mensimulasikan "Depends tertukar" — pola kesalahan aslinya) → gate **MERAH**:
`BOCOR: peran driver mendapat HTTP 200 pada GET /departures/attention?... — seharusnya 403`.
Revert → **HIJAU 15 cek**. Ini bukti gate runtime benar-benar menguji PERILAKU, bukan hanya
membaca konfigurasi (gate statik tetap hijau selama injeksi tsb — itulah celah yang ditutup).

### Backlog P1 lama yang diverifikasi TUTUP (bukan diasumsikan)
- **Warning Recharts `width(-1)/height(-1)`**: TIDAK tereproduksi. Bukti: console browser bersih
  (0 warning) di `/app/dashboard` (tab Ringkasan + BI Cockpit), `/app/reports`, `/app/finance`
  (6 tab), `/app/crm` (4 tab). Semua `<ResponsiveContainer>` memakai `initialDimension` + parent
  ber-tinggi tetap (`h-52`/`h-64`). Anti-regresi: aturan **E4** baru di `scripts/ux_audit.py`
  (ERROR bila ada `<ResponsiveContainer>` tanpa `initialDimension`) — masuk gate via `ux_audit --strict`.
- **Duplikasi blok deklarasi `scripts/gate.sh` baris 42–48** (dilaporkan HANDOFF.md §3):
  sudah TIDAK ADA di kode terkini (`BACKEND_UP=0`/`AUTH_READY=0` masing-masing muncul 1×,
  `bash -n` lolos). HANDOFF.md sudah usang pada poin ini.

---

## Tambahan Sesi FASE F / E29 (2026-08-10) — Marketing & Ads: fondasi terbukti (POC)

### Yang sudah dibuktikan (`python scripts/test_core_ads.py` → 62/62 LULUS, tanpa kredensial platform)
| Fondasi | Bukti |
|---------|-------|
| Vault rahasia | AES-256-GCM round-trip; ciphertext berbeda tiap enkripsi (nonce acak); `public_view()` tidak memuat plaintext MAUPUN ciphertext, hanya `*_set` + `*_masked`; input kosong = pertahankan rahasia lama; sentinel `__HAPUS__` menghapus |
| Object storage | Unggah+unduh **gambar 1MB & VIDEO 12MB** identik (SHA-256), content-type dipertahankan (~0,4–0,5 s); `.exe` ditolak; gambar >10MB ditolak; path UUID berprefiks app; nama berkas disanitasi |
| Outbox konversi | 8 enqueue paralel `event_id` sama → tepat **1 dokumen per provider** (unique index); payload Meta CAPI & Google Data Manager sesuai skema resmi (SHA-256 PII, IDR integer, `event_id` = ID bisnis untuk dedup pixel↔server, `test_event_code`/`validateOnly` hanya saat uji); kredensial kosong → `skipped` **berALASAN**; HTTP 400 → `failed` + retry terjadwal → `dead` setelah 5 attempt; respons tersimpan tidak memuat token |
| Blok landing page | 16 tipe blok; sanitasi XSS (buang `<script>/<iframe>` **beserta isinya**, `onclick`, `href="javascript:"`, tambah `rel=noopener`); nilai di luar batas dijepit; blok asing dibuang + peringatan; aturan layak-terbit (wajib blok konversi, poster video, SEO title); aset media terhapus tidak jadi tautan mati |
| RBAC peran baru | `marketing_admin` sinkron FE↔BE untuk 4 modul baru (`ads`,`landing`,`tracking`,`integrations`); guardrail INV-RBAC-01..05 **HIJAU 177 cek**; `gate.sh` tetap **HIJAU 23/23** |

### Keputusan arsitektur yang WAJIB dipatuhi fase berikutnya
1. **Kredensial tenant TIDAK di `.env`.** `.env` hanya memuat KUNCI MASTER `SETTINGS_ENCRYPTION_KEY_B64` (+ `EMERGENT_LLM_KEY` untuk object storage). Semua ID/token Meta/Google/WhatsApp ada di koleksi `settings` dalam bentuk terenkripsi.
2. **`event_id` konversi = ID bisnis** (`lead_<id>`, `booking_<id>`, `payment_<id>`). Pixel di browser WAJIB memakai nilai yang SAMA, kalau tidak Meta menghitung ganda (jendela dedup 48 jam).
3. **Google offline conversion via Data Manager API** (`datamanager.googleapis.com/v1/events:ingest`) — sejak 15 Juni 2026 jalur Google Ads API diblokir kecuali token di-allowlist. `developer_token` hanya untuk laporan/kampanye.
4. **`api_version` Meta ada di settings** (kini `v25.0`) — v24.0 kedaluwarsa 6 Okt 2026. Jangan hardcode.
5. **Video landing page**: unggah ≤50MB + poster WAJIB (object storage tanpa presigned URL → di-proxy backend); video berat memakai embed URL.
6. **Object storage tanpa API hapus** → penghapusan = `is_deleted` di Mongo; jangan pernah mengandalkan daftar objek (maks 1000).

### Guardrail yang akan ditambahkan (fase pengerasan, belum dibuat)
INV-SEC-01 (rahasia tak pernah plaintext di respons/log) · INV-CONV-01 (outbox idempoten + tak ada penelan error senyap) · INV-TRACK-01 (endpoint tracking-config hanya field publik) · INV-LP-01 (halaman terbit wajib slug unik + blok konversi + SEO) · INV-LP-02 (template selaras skema blok, tak ada props hilang senyap) · INV-MEDIA-01 (validasi MIME/ukuran + hanya owner/marketing_admin) · INV-MEDIA-02 (URL media benar + anti path traversal).


---

## Tambahan Sesi BOOKING-V1 (2026-08-12) — Pemesanan online: harga, reservasi, batas teks

Tiga invariant baru menutup kelas bug yang ditemukan **lewat verifikasi nyata**, bukan dugaan:
**INV-PRICE-01**, **INV-BOOK-02**, **INV-STR-01** (definisi lengkap di tabel §Daftar Invariant).

### Self-test mutasi (`scripts/guardrails/selftest_booking_guards.py`, ter-wire di `gate.sh`)
Penjaga yang tak pernah terbukti MENGGIGIT tak bisa dibedakan dari `return 0`. Lima bug NYATA
disuntikkan satu per satu; penjaga wajib MERAH, lalu HIJAU lagi setelah revert — semuanya lulus:

| Mutasi | Bug yang disuntikkan | Penjaga |
|--------|----------------------|---------|
| P01 | `core + fuel_per_km × distance_km` kembali ke mesin harga | INV-PRICE-01 |
| P02 | `dp_percent` dibaca langsung dari `settings.pricing_defaults` (sumber kedua) | INV-PRICE-01 |
| B01 | `PublicBookingSubmit.total_amount` ditambahkan (klien mengirim harga) | INV-BOOK-02 |
| B01b | `BookingPromoListRequest.subtotal` ditambahkan (klien menentukan nilai transaksi agar promo bersyarat lolos) | INV-BOOK-02 |
| B02 | `insert_one` dikeluarkan dari `vehicle_lock` (mutex reservasi hilang) | INV-BOOK-02 |
| S01 | `max_length` dilepas dari 4 field `CustomerCreate` | INV-STR-01 |

### Pelajaran yang dikunci sesi ini
1. **"Tidak 5xx" ≠ "tervalidasi".** `verify_adversarial_5xx` sudah lama mengirim `"A"*60000` dan
   selalu HIJAU karena hanya menuntut bukan-5xx; nilainya TERSIMPAN. Satu nama 60.000 karakter
   merusak tata letak tabel Booking ERP dan akan merusak PDF + WhatsApp (batas 4096). Sejak kini
   `verify_string_bounds` menuntut **penolakan 4xx**, dan `DataTable` memotong teks ekstrem
   (pertahanan berlapis: kontrak + UI).
2. **Regex tidak cukup untuk menilai "dipakai menghitung".** Percobaan pertama INV-PRICE-01
   memakai regex dan salah tuduh dua kali: tanda tangan `def compute_quote(..., distance_km=0)`
   dan docstring `distance_km/basis` (garis miring prosa dibaca sebagai pembagian). Penilaian
   dipindah ke **AST** (`BinOp` Mult/Div), lalu dibatasi pada modul permukaan-harga saja —
   karena `distance_km` MEMANG sah untuk laporan trip/odometer & uang jalan sopir per km.
3. **Nilai bawaan bukan keputusan penjualan.** `publishable_filter()` dulu menganggap
   `publish_to_web` yang KOSONG sebagai "boleh dijual", sehingga setiap dokumen `vehicles` dari
   jalur non-formulir langsung tayang: unit "Smoke Vehicle" milik `scripts/mutation_smoke.py`
   benar-benar muncul sebagai unit yang bisa dipesan tamu di `/booking`. Sekarang field itu
   wajib `True` EKSPLISIT (data lama diselaraskan `scripts/migrate_booking_v1.py` langkah 2),
   dan skrip smoke membuat unitnya dengan `publish_to_web: False`.

### Perluasan INV-RBAC-06 — lapis D "MATRIKS PENUH" (2026-08-12)

Lapis A/B/C hanya pernah menguji peran **driver**. Testing agent menemukan `marketing_admin`
mendapat **HTTP 200** pada `GET /api/bookings`; audit lanjutan (`scripts/audit_rbac_sections.py`)
menemukan **8 permukaan BACA bocor** (booking + availability + detail, armada, sopir, perawatan,
GPS, penawaran, ruang kerja sopir) — lihat **BUG-0119**. Akar masalah: peran BARU yang lahir di
fase belakangan (`marketing_admin`, FASE F) tak pernah diuji terhadap endpoint BACA LAMA yang
memakai `Depends(get_current_user)` saja, sementara guardrail statik hanya memeriksa KONSISTENSI
matriks FE↔BE, bukan penegakannya per endpoint.

Lapis D karena itu digerakkan **SSOT matriks**, bukan daftar kasus:
1. `SECTION_PROBES` wajib memuat **SEMUA** kunci `SECTION_ACCESS` → section baru tanpa probe
   membuat gate MERAH (tidak bisa lolos diam-diam). Section tanpa endpoint sendiri (`sales`)
   harus ditulis eksplisit `None` beserta alasannya.
2. Untuk tiap section: peran DI LUAR matriks wajib **403**; peran DI DALAM matriks wajib
   **bukan-403** (over-block = kerusakan juga).
3. Probe yang menjawab 404 untuk SEMUA peran ditolak → mencegah penjaga hampa akibat jalur usang.
Hasil: **27 section × 4 peran, 155 cek**. Self-test: satu endpoint dikembalikan ke
`require_role(...)` serba-izin → penjaga MERAH menyebut peran + endpoint + section; revert → HIJAU.
Self-test: satu endpoint dikembalikan ke
`require_role(...)` serba-izin → penjaga MERAH menyebut peran + endpoint + section; revert → HIJAU.
