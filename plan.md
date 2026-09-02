# Plan — CMS Continuation (RahazaTrans Travel ERP)

## 1) Objectives
- Menyelesaikan **SEMUA sisa** dari `CMS_REVIEW_AND_ENHANCEMENT_PLAN.md`: **CMS-05..CMS-09** + menutup **3 defect (A1–A3)**.
- Menghasilkan dampak bisnis nyata (end-to-end):
  - Konten bisa **draft / scheduled / published**, bisa **preview token** tanpa bocor ke publik.
  - Situs publik punya halaman **Packages** & **Promo** yang bisa dipakai traffic iklan.
  - **Multi-bahasa ID/EN** untuk pasar turis asing (terjemahan **manual via CMS**, bukan AI).
  - Promo bisa dikelola berbasis **aturan terstruktur** dan dipakai di booking.
  - Ulasan pelanggan masuk funnel → moderasi → tampil sebagai testimoni.
  - Ada analitik konten → lead → booking → revenue.
- Non-regression wajib: `bash scripts/gate.sh` **HIJAU (0 FAIL, 0 SKIP)**, RBAC+Audit+whitelist konsisten, UI mengikuti `design_guidelines.md` & invariant terbaru (INV-THEME-01, INV-CLEAN-01, dll.).

### Status awal sesi (terverifikasi sebelum coding — wajib dicatat)
- Repo `github.com/shsjskhd/Travel` sudah di-restore penuh ke `/app` (platform `.env` dipertahankan; ditambah `SETTINGS_ENCRYPTION_KEY_B64`, `PUBLIC_SITE_URL`, `MEDIA_BACKEND=local`). `scripts/bootstrap.sh` sukses; backend+frontend **RUNNING**.
- Gate baseline: `bash scripts/gate.sh` = **41 PASS / 1 FAIL** → FAIL tunggal: `ux_audit --strict` pada `frontend/src/features/public/PackageDetail.jsx` (list tanpa empty-state).
- POC CMS CW2: `python scripts/test_core_cms_cw2.py` = **82/86**.
  - Akar masalah ditemukan:
    - **CMS-09 sanitasi** gagal karena `services/richtext.py` memakai `bleach` tetapi dependency belum terpasang → **SUDAH diperbaiki**: `bleach==6.4.0` dipasang + dipin di `backend/requirements.txt`.
    - **AI translate** gagal karena `EMERGENT_LLM_KEY` kosong → sesuai keputusan user: **AI ditolak**, fitur terjemahan harus **manual**. POC/UX akan disesuaikan agar kondisi 503 berpesan jelas dianggap **degradasi mulus** (PASS), bukan failure.
- Kondisi kode: backend CMS-05..CMS-09 **sebagian besar sudah ada dan teruji**; titik berhenti adalah **wiring frontend** (routes publik, pemasangan LanguageSwitch, UI CMS untuk status/schedule/preview/i18n tab/richtext/promo rules/moderasi/analytics).

## 2) Implementation Steps

### Phase 1 — Core POC (isolation, wajib)
Fokus pada mekanik paling riskan: token preview, auto-publish scheduler, review-token funnel, sanitasi rich text, serta degradasi mulus saat AI off.

**POC-1: Scheduled Publish + Preview Token (CMS-05)**
- **Status:** Backend sudah ada: `services/content_publish.py` + scheduler `publish_due()` di `backend/server.py`; endpoint `POST /api/content/{resource}/{id}/preview-token`.
- **Sisa:** Verifikasi ulang end-to-end via `scripts/test_core_cms_cw2.py` sampai **PASS**.

**POC-2: Review Funnel Token (CMS-07)**
- **Status:** Backend sudah ada: token review + submit publik (`/api/public/reviews/{token}`) + admin moderation (`/api/reviews/*`), trigger saat booking complete.
- **Sisa:** Wiring frontend admin moderation + public route `/review/:token` + verifikasi ulang.

**POC-3: Multi-language (CMS-06) — MANUAL (AI OFF)**
- **Keputusan user:** Terjemahan AI **DITOLAK**. Terjemahan EN diisi manual di CMS.
- **Implikasi:**
  - Endpoint translate boleh tetap ada untuk masa depan, namun UI **tidak boleh menjanjikan** fitur AI.
  - Jika endpoint dipanggil tanpa key, wajib 503 dengan pesan jelas (degradasi mulus).
- **Sisa:** Pastikan POC memperlakukan “AI off + 503 berpesan” sebagai **PASS** (jujur sesuai keputusan owner).

**POC-4: Rich text sanitization (CMS-09)**
- **Status:** `services/richtext.py` sudah ada.
- **Fix sudah dilakukan:** pin dependency `bleach==6.4.0`.
- **Sisa:** Verifikasi ulang POC agar struktur HTML aman dipertahankan (h2/p/ul/li/blockquote/a/img) dan XSS dibuang.

> Stop rule: tidak lanjut Phase 2 sebelum POC di `scripts/test_core_cms_cw2.py` kembali HIJAU (dengan AI-off dianggap degradasi mulus).

### Phase 2 — V1 App Development (implement menyeluruh)

**A) Fix 3 Defects (A1–A3)**
1. **A1 Preview link + Package public pages**
   - Keputusan user: URL publik **bahasa Inggris**.
   - FE: aktifkan routes publik:
     - `/packages` (list)
     - `/packages/:slug` (detail + dukung `?preview=<token>`)
   - Perbaiki link pratinjau CMS agar menunjuk:
     - Destinations → `/destinations/:slug`
     - Packages → `/packages/:slug`
     - Articles → `/blog/:slug`
   - Pastikan `sitemap.xml` sudah mengandung packages (sudah ada di `routers/seo.py`), dan route FE benar-benar ada.
2. **A2 Promo rules UI lengkap (CMS-04 + defect)**
   - Lengkapi form promo CMS (admin) untuk field aturan terstruktur:
     - `valid_from`, `valid_until`, `min_days`, `min_amount`, `vehicle_types[]`, `services[]`, `weekend_only`, `max_uses`.
     - tampilkan `used_count` read-only.
   - Tambahkan endpoint meta (SSOT) agar FE tidak hardcode enum:
     - `GET /api/content/meta/promo-options` → vehicle_types (dari pricing) + services (dari booking_flow).
3. **A3 Public `/promo` page**
   - FE: route `/promo`.
   - UI: daftar promo aktif dari `/api/public/promos`:
     - render syarat dari data (`terms[]`/`terms_text`), tombol copy code, CTA “Use in Booking” membawa query `?promo=` ke wizard.

**B) CMS-05 Draft/Preview/Scheduled Publish**
- Backend sudah ada (status/publish_at/visibility filter/preview-token/scheduler).
- FE Admin:
  - Filter status (all/draft/scheduled/published) pada `ContentManager`.
  - Badge status yang konsisten (gunakan `effective_status` + `publish_at`).
  - Panel “Terbit & Jadwal” di `ContentFormDialog`:
    - `status` (draft/scheduled/published)
    - `publish_at` (datetime-local)
    - tombol “Buat Tautan Pratinjau” (mint token, copy link, open in new tab)

**C) CMS-06 Multi-language (ID/EN) — MANUAL**
- Backend sudah ada: `translations.en` + `?lang=en` pada endpoint publik + sitemap hreflang alternates.
- FE Publik:
  - Pasang **LanguageSwitch** (ID/EN) di header publik + drawer ponsel.
  - Pastikan `syncLangFromUrl()` dipanggil pada navigasi SPA agar `?lang=` konsisten.
  - `apiClient` interceptor `?lang=` sudah ada (tidak diulang).
- FE Admin:
  - Tab bahasa di `ContentFormDialog`: “Indonesia” vs “English”.
  - Field yang bisa diterjemahkan mengikuti whitelist backend (`services/i18n.TRANSLATABLE`).
  - Tombol “Salin dari Indonesia” untuk mempercepat isi awal EN (tanpa AI).
- SEO:
  - `useSEO` ditingkatkan untuk set `og:locale`, `html[lang]`, dan tag hreflang di halaman detail publik.

**D) CMS-07 Review → Testimonials**
- Backend sudah ada (trigger booking completed + public submit + admin moderation).
- FE Publik:
  - route `/review/:token` menampilkan `ReviewSubmit`.
- FE Admin (CMS):
  - Tab/Panel “Ulasan” di area CMS:
    - ringkasan response rate,
    - daftar permintaan terkirim,
    - eligible bookings (completed tapi belum diminta),
    - antrean pending testimonials,
    - aksi approve/reject + catatan moderasi.
- Publik:
  - pastikan testimoni hanya tampil bila approved (sudah), agregat rating tersedia.

**E) CMS-08 Content analytics + attribution**
- Backend sudah ada: `POST /api/public/content-view` + panel admin `GET /api/content/analytics/top`.
- FE Publik:
  - Pastikan tracking view dipanggil di detail pages (article/destination/package) dan dedupe bekerja.
- FE Admin:
  - Tab/Panel “Analitik” di CMS:
    - KPI ringkasan (views/leads/bookings/revenue)
    - tabel ranking (kind/title/views/leads/bookings/revenue/lead_rate)
    - export CSV (Phase 3 bila belum sempat).

**F) CMS-09 Rich text**
- Backend sanitasi sudah ada dan kini dependency sudah dipin.
- FE Admin:
  - Ganti input `articles.body` dari textarea ke editor rich text minimal (block-like atau WYSIWYG ringan).
  - Pastikan round-trip aman: HTML yang disimpan akan dibersihkan server.
- FE Publik:
  - Render aman (gunakan `dangerouslySetInnerHTML` hanya untuk HTML yang sudah disanitasi server) + fallback untuk body lama.

**V1 User Stories (wajib diverifikasi)**
1. Ops/owner bisa preview konten draft/scheduled lewat link token tanpa mempublish.
2. Editor bisa menjadwalkan artikel terbit otomatis sesuai waktu.
3. Owner bisa membuat promo dengan syarat nyata dan pelanggan dapat menggunakannya di booking.
4. Pengunjung bisa buka `/promo`, copy kode, lalu masuk BookingWizard dengan kode terisi.
5. Turis asing bisa membaca konten dalam English via language switch + fallback Indonesia.
6. Pelanggan selesai trip menerima (MOCK) link ulasan, mengisi, masuk antrean moderasi, lalu tayang setelah disetujui.
7. Owner melihat analitik konten: top views/leads/bookings/revenue.
8. Editor menulis artikel rich text; XSS mustahil tersimpan.
9. Public pages `/packages` + `/packages/:slug` berfungsi end-to-end (CTA ke booking/quotation).

**Close Phase 2:** `bash scripts/gate.sh` HIJAU + testing_agent_v3 uji E2E (publik + CMS + booking + promo + review).

### Phase 3 — Hardening + UX polish (production-friendly)
- Konsistensi UX:
  - Empty/error states konsisten (public + CMS), tambah `data-testid` yang relevan.
  - Perbaiki `PackageDetail.jsx` empty-state agar `ux_audit --strict` HIJAU (ini blocker gate saat ini).
- Performance & safety:
  - Rate-limit tambahan bila perlu untuk content-view (sudah dedupe) dan endpoint translate (tetap 503 jika AI off).
- Analytics:
  - Export CSV panel analitik konten.
- Promo:
  - Tampilkan quota promo terpakai vs tersisa (admin) dan status sold out (publik).
- Final regression:
  - `bash scripts/gate.sh` HIJAU + testing_agent_v3 putaran 2.

## 3) Next Actions (immediate)
1. **Stabilkan kembali gate**: bereskan `ux_audit --strict` pada `PackageDetail.jsx` (empty-state includes) → gate HIJAU baseline.
2. Jalankan ulang `python scripts/test_core_cms_cw2.py` sampai full PASS (dengan AI-off dianggap degradasi mulus).
3. Wiring publik: tambah route `/packages`, `/packages/:slug`, `/promo`, `/review/:token` di `frontend/src/App.js`.
4. Pasang LanguageSwitch di `PublicLayout` + sinkronisasi `?lang=` saat navigasi.
5. Wujudkan UI admin CMS (status/schedule/preview, tab EN manual, promo rules lengkap, moderasi ulasan, analitik konten).
6. Update dokumen SSOT + manifest + receipt gate; delegasikan verifikasi ke testing_agent_v3.

## 4) Success Criteria
- A1–A3 + CMS-05..CMS-09 **berfungsi end-to-end** di UI publik dan admin.
- `bash scripts/gate.sh` **HIJAU (0 FAIL, 0 SKIP)** dan `memory/GATE_RECEIPT.md` ter-update.
- POC `scripts/test_core_cms_cw2.py` **PASS** (AI translate: degradasi mulus sesuai keputusan user).
- SSOT & dokumen diperbarui:
  - `docs/03_DATA_MODEL.md`, `docs/04_API_CONTRACT.md`, `docs/05_NAVIGATION_MAP.md`, `docs/10_CODEBASE_MAP.md`
  - `memory/DELIVERY_MANIFEST.md` (ACTIVE_PHASE untuk wave CMS ini)
  - `memory/SESSION_HANDOFF.md`, `memory/SESSION_LOG.md`, `CMS_REVIEW_AND_ENHANCEMENT_PLAN.md` status
  - `test_result.md` diisi hasil testing_agent_v3.
- Integrasi eksternal tetap **MOCK** (WhatsApp/Meta/Google/GA4) dan dilabeli jelas.


---

## 5) Continuation — EN i18n Storefront Publik (2026-08-18) — SELESAI ✅
Menuntaskan backlog EN yang tercatat di `SESSION_HANDOFF.md` ("SISA PEKERJAAN (a)"): chrome + halaman + komponen publik kini dwibahasa penuh pada mode `?lang=en`.

**Cakupan (disepakati user: storefront publik saja; WA/Meta/Google/GA4 tetap DILEWATI):**
- Chrome `PublicLayout` (bar pengumuman, WhatsApp, drawer help, footer penuh).
- Halaman: Home, Fleet, FleetDetail, Destinations, DestinationDetail, Packages, PackageDetail, Blog, BlogDetail, Promos, ThankYou, PublicTrack.
- Komponen bersama: BookingStepsSection, StickyMobileCTA, TripEstimatorInline, MegaMenu, SectionHeading, Lightbox, PhotoSphereTour, FleetSpecGrid, DestinationFacts, FleetCard, ExitIntentModal, ConsentBanner, ScrollStory, ResumeBookingChip, PackageStrip, ChatWidget.
- Mekanisme: helper `bi(id,en,lang)` + kamus `t()` yang sudah ada; tanpa perubahan API/logika.

**Verifikasi:** `esbuild` 0 error · `bash scripts/gate.sh` HIJAU (0 FAIL; `ux_audit --strict` & `validate_compliance` PASS) · audit DOM Playwright 12 route publik mode EN bersih dari string UI Indonesia, `CONSOLE_ERRORS: []` · mode ID tanpa kebocoran English (non-regresi).

**Di luar cakupan (jujur):** sisa teks Indonesia = konten DB/CMS (label statistik, kutipan testimoni, kategori/judul artikel) → terjemahan MANUAL via CMS (AI OFF) sesuai keputusan CMS-CW2.
