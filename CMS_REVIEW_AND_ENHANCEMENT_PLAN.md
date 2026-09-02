# 🎨 REVIEW CMS + ENHANCEMENT PLAN — Rahaza Travel (Berdampak Bisnis)

**Dibuat:** 2026-07-02 · **Penyusun:** Neo · **Bahasa:** Indonesia
**Status per 2026-08-17:** **CMS-01 … CMS-09 SELESAI & TERVERIFIKASI** + 3 defect lanjutan (A1/A2/A3) ditutup.

| ID | Isi singkat | Status | Bukti |
|----|-------------|--------|-------|
| CMS-01 | Hardening validasi + slug unik + paginasi | ✅ SELESAI (CW0/G10) | 409 duplikat slug, 400 angka non-numerik, `X-Total-Count` |
| CMS-02 | SEO toolkit (meta/OG/canonical/sitemap/JSON-LD) | ✅ SELESAI | `routers/seo.py`, `hooks/useSEO.js` |
| CMS-03 | Upload gambar → Media Library terpadu | ✅ SELESAI | `POST /api/uploads/cms` → `media_assets` |
| CMS-04 | Promo fungsional (kode → diskon nyata) | ✅ SELESAI | `services/promos.py` + INV-PRICE-01 |
| CMS-05 | Draft / jadwal terbit / pratinjau bertoken | ✅ SELESAI 2026-08-17 | `services/content_publish.py`, tab **Terbit** di CMS, POC A |
| CMS-06 | Dua bahasa ID+EN (isi konten) + hreflang | ✅ SELESAI 2026-08-17 (**terjemahan MANUAL — AI OFF atas keputusan pemilik**) | `services/i18n.py`, tab **English**, `lang-switch`, sitemap alternates, POC C |
| CMS-07 | Testimoni dari ulasan nyata (funnel review) | ✅ SELESAI 2026-08-17 (WhatsApp **MOCK**) | `services/reviews.py`, `/review/:token`, tab **Ulasan**, POC E |
| CMS-08 | Analitik konten + atribusi lead/pesanan | ✅ SELESAI 2026-08-17 | `services/content_stats.py`, tab **Analitik**, POC F |
| CMS-09 | Rich text artikel (tersanitasi server) | ✅ SELESAI 2026-08-17 | `services/richtext.py` + `RichTextEditor.jsx` + `ArticleBody.jsx`, POC B |
| A1 | Link pratinjau CMS 404 + paket tanpa halaman publik | ✅ DITUTUP | `publicPath` → `/destinations/`, `/packages/`, `/blog/`; route `/packages`, `/packages/:slug` |
| A2 | Form promo tidak punya field aturan | ✅ DITUTUP | `valid_from`/`min_days`/`min_amount`/`vehicle_types[]`/`services[]`/`weekend_only`/`max_uses` + `used_count` read-only |
| A3 | Tidak ada halaman `/promo` publik | ✅ DITUTUP | route `/promo` + syarat dirender dari DATA + salin kode → `/booking?promo=` |

**Bukti global:** POC `scripts/test_core_cms_cw2.py` **87/87 LOLOS** · `bash scripts/gate.sh` **HIJAU (0 FAIL, 0 SKIP)** · `ux_audit --strict` **0 ERROR 0 WARN**.
**Catatan jujur:** WhatsApp/Meta Ads/Google Ads/GA4 tetap **MOCK**; terjemahan English diisi manual di CMS (endpoint terjemahan otomatis tetap ada dan membalas 503 berpesan bila kunci LLM tak dipasang).
**Cakupan review:** Modul **Light CMS** (Content Manager) — pengelola konten situs publik.
**File yang ditinjau:** `backend/routers/content.py`, `backend/routers/public.py`, `frontend/src/features/app/ContentManager.jsx`, `components/app/ContentFormDialog.jsx`, `components/cms/{GalleryManager,TourSceneBuilder,LivePreviewPanel,ThemeManagerPanel}.jsx`.

> **Konteks bisnis CMS:** situs publik = **mesin akuisisi lead** (SEO + konten wisata Jawa–Bali). Kualitas & jangkauan konten langsung menentukan **traffic → lead → booking**. Maka enhancement CMS diikat ke tuas **L2 (Konversi)**, **L3 (Nilai transaksi)**, dan **jangkauan pasar (turis asing)**.

---

## 1. SNAPSHOT — Apa yang SUDAH ADA (terverifikasi)

**Arsitektur:** CRUD generik berbasis whitelist field per-resource (aman: hanya field terdaftar ditulis + koersi tipe). RBAC section `cms` (owner + ops_admin). Semua mutasi tercatat di **Audit Log**.

| Resource | Field kaya | Publik (baca) |
|---|---|---|
| `destinations` | slug, hero, galeri, **tur 360°**, itinerary, highlights, rekomendasi hotel, FAQ, lat/lng, popular | `GET /api/public/destinations` (+`/{slug}`) |
| `packages` | harga mulai, durasi, includes, aktif | `GET /api/public/packages` (`active:true`) |
| `articles` | slug, cover, body, kategori, tag, featured, **published + published_at** | `GET /api/public/articles` (`published:true`) |
| `testimonials` | nama, peran, quote, rating, avatar | `GET /api/public/testimonials` |
| `promos` | kode, diskon (persen/nominal), berlaku, aktif | `GET /api/public/promos` |
| **Tema Situs** | preset warna + mode → `PATCH /settings.theme_config` | dipakai surface publik |

**Kekuatan (jangan diubah):**
- ✅ Editor kaya: **GalleryManager**, **TourSceneBuilder (360°)**, **LivePreviewPanel** (split-screen untuk destinasi/artikel).
- ✅ Whitelist field → aman dari mass-assignment.
- ✅ Audit trail penuh + RBAC section.
- ✅ Pemisahan admin (`/content/*`) vs publik (`/public/*`) rapi; publik hanya menampilkan yang `active/published`.
- ✅ Theme manager dengan pratinjau.

---

## 2. TEMUAN — Gap & Defect (dengan bukti)

### 🐞 Defect (hardening)
| ID | Prioritas | Temuan | Bukti |
|---|---|---|---|
| **CMS-D1** | 🟠 P1 | **Crash 500 pada input non-numerik.** `_clean` memakai `int(v or 0)`/`float(...)` tanpa try/except → `days:"abc"` → **500 Internal Server Error** (harusnya 422 pesan jelas). | `content.py:54-57`; live: `POST /content/packages {days:"abc"}` → 500, log `ValueError: invalid literal for int()`. |
| **CMS-D2** | 🟠 P1 | **Slug tidak dijamin unik.** Tak ada validasi; slug ganda mungkin. Publik `find_one({"slug"})` ambil yang pertama → konten "hilang" secara senyap + URL bentrok (buruk untuk SEO). | `content.py` (tak ada cek), `public.py:69/83`. |
| **CMS-D3** | 🟡 P2 | **Tanpa paginasi/pencarian** di admin — `to_list(500)` hardcoded. Skalanya buruk bila artikel/destinasi banyak. | `content.py:72`. |

### 🕳️ Gap fungsional (peluang bisnis)
| ID | Gap | Dampak bisnis |
|---|---|---|
| **G-SEO** | **Tidak ada field/infrastruktur SEO**: `meta_title`, `meta_description`, `og_image`, canonical, `sitemap.xml`, `robots.txt`, JSON-LD. | Situs adalah mesin lead, tapi **tak dioptimalkan mesin pencari** → traffic organik & lead di bawah potensi. |
| **G-I18N** | **Satu bahasa (Indonesia) saja** — tak ada konten English. | Wisata Bali = **pasar turis asing besar**. Tanpa English, segmen bernilai tinggi ini tak tersentuh. |
| **G-PROMO** | **Promo hanya tampilan** — tidak terhubung ke pricing/booking (tidak ada redeem kode). | "Promo" = teks marketing, **bukan diskon fungsional** → tak bisa ukur konversi promo, kupon tak berlaku otomatis. |
| **G-UPLOAD** | **Gambar hanya via URL** — editor harus hosting gambar di tempat lain. Infra upload lokal ada (POD) tapi CMS tak memakainya; belum ada object storage. | Friksi besar bagi editor non-teknis → konten jarang di-update → situs basi. |
| **G-WORKFLOW** | Tidak ada **draft/preview/scheduled publish/versioning**. `published` hanya bool. | Tak bisa siapkan konten lebih awal (mis. artikel musim liburan) atau rollback perubahan. |
| **G-REVIEW** | Testimoni **input manual**; balasan WA "ajakan ulasan" tidak difunnel jadi testimoni/rating. | Bukti sosial (social proof) tak dimanfaatkan → konversi lebih rendah. |
| **G-ANALYTICS** | Tak ada **analitik konten** (views, artikel→lead attribution). | Tak tahu konten mana yang menghasilkan booking → keputusan konten menebak. |
| **G-RICHTEXT** | Body artikel **plain textarea** (paragraf dipisah baris kosong). | Konten kurang menarik (tanpa heading/gambar inline/list) → engagement rendah. |

---

## 3. ENHANCEMENT PLAN (diikat dampak bisnis + RICE)

> Format: **Tuas · Masalah · Solusi · Hipotesis dampak · KPI · Effort.** RICE = R×I×C÷E.

### 🟥 CW0 — Hardening (prasyarat cepat) — ✅ SELESAI 2026-07-17
**CMS-01 — Validasi input & slug unik (fix D1+D2+D3) — SELESAI & TERVERIFIKASI**
- **Solusi:** bungkus koersi tipe dengan try/except → 400/422 pesan jelas; enforce slug unik per-resource (index + cek saat create/update); auto-slugify dari nama/judul; tambah paginasi+search di admin list.
- **Status:** ✅ **D1 (VERIFIED FIXED):** `_clean` di `content.py` sudah try/except (ValueError/TypeError) → 400 pesan jelas ("Field 'x' harus berupa angka"). Curl test: `POST packages {"days":"abc"}` → HTTP 400. ✅ **D2 (VERIFIED FIXED, dari G1):** `_ensure_unique_slug` dipanggil di create/update → 409 saat duplikat. Curl test: dup slug `test-slug-cw0` → HTTP 409. ✅ **D3 (IMPLEMENTED 2026-07-17):** `GET /content/{resource}` sekarang menerima `limit` (1..500, default 100) + `offset` (>=0), response headers `X-Total-Count`/`X-Limit`/`X-Offset` (via CORS `expose_headers`), MongoDB `skip().limit()` + `count_documents()`. FE `ContentManager.jsx` menampilkan "Menampilkan X dari Y" + tombol "Muat lebih banyak (Z tersisa)" (append pattern). Playwright test: 66 artikel → info benar → klik load-more → total tercapai. `gate.sh` HIJAU 22/22 pasca-perubahan.
- **KPI tercapai:** 0 error 500 CMS ✅; 0 slug duplikat ✅; skalabilitas admin OK (paginasi via load-more). **Effort:** S. **RICE:** tinggi (prasyarat).

### 🟩 CW1 — Quick Wins (impact tinggi, effort rendah–sedang)

**CMS-02 — SEO Toolkit (⭐ impact tertinggi)**
- **Tuas:** L2. **Masalah:** G-SEO. **Solusi:** field `meta_title/meta_description/og_image/canonical` per destinasi & artikel; auto-generate `/sitemap.xml` & `/robots.txt`; JSON-LD (Article/TouristAttraction/Product) + Open Graph di halaman publik.
- **Hipotesis dampak:** **traffic organik +15–40%** (jangka menengah) → lebih banyak lead tanpa biaya iklan.
- **KPI:** halaman terindeks, klik organik, lead dari organik. **Effort:** M · **RICE:** ⭐ sangat tinggi.

**CMS-03 — Upload Gambar Langsung (Media)**
- **Tuas:** operasional konten. **Masalah:** G-UPLOAD. **Solusi:** endpoint upload gambar untuk CMS (hero/cover/galeri) — pola sama seperti POD upload; **disarankan object storage** (via integration agent) agar persisten (bukan disk ephemeral).
- **Hipotesis dampak:** frekuensi update konten naik → situs "hidup" → SEO & konversi ikut naik.
- **KPI:** jumlah konten diperbarui/bulan, waktu buat artikel. **Effort:** M (S bila disk lokal; M+ bila object storage). **RICE:** tinggi.
- **⚠ Keputusan:** object storage (persisten, disarankan) vs disk lokal (cepat tapi ephemeral)?

**CMS-04 — Promo Fungsional (redeem kode → diskon nyata)**
- **Tuas:** L3/L2. **Masalah:** G-PROMO. **Solusi:** hubungkan `promos` ke pricing/booking — validasi kode (aktif + belum kedaluwarsa + kuota), terapkan diskon di estimasi & booking, catat pemakaian untuk atribusi.
- **Hipotesis dampak:** kampanye promo terukur; **konversi kampanye +5–15%**; upsell musiman.
- **KPI:** redemption rate, revenue dari promo, conversion lift. **Effort:** M · **RICE:** tinggi.

**CMS-05 — Draft / Preview / Scheduled Publish**
- **Tuas:** operasional. **Masalah:** G-WORKFLOW. **Solusi:** status `draft/scheduled/published` + `publish_at`; preview-as-draft (token); scheduler auto-publish (infra scheduler sudah ada).
- **Hipotesis dampak:** konten musiman siap tepat waktu; kualitas naik (bisa direview sebelum tayang).
- **KPI:** konten terjadwal, error publish. **Effort:** M · **RICE:** sedang.

### 🟦 CW2 — Strategic (impact besar)

**CMS-06 — Multi-bahasa (ID + EN) untuk Pasar Turis Asing** ⭐
- **Tuas:** jangkauan pasar baru. **Masalah:** G-I18N. **Solusi:** field terjemahan (mis. `translations.en`) untuk destinasi/artikel/paket; selector bahasa di situs; hreflang untuk SEO internasional.
- **Hipotesis dampak:** **buka segmen turis asing** (booking bernilai tinggi) yang saat ini nol.
- **KPI:** traffic/lead EN, booking dari kanal EN. **Effort:** L · **RICE:** tinggi (pasar baru) tapi effort besar.

**CMS-07 — Testimoni dari Ulasan Nyata (funnel review)**
- **Tuas:** L2 (social proof). **Masalah:** G-REVIEW. **Solusi:** setelah trip selesai, kirim link ulasan; balasan/rating masuk sebagai testimoni `pending` → moderasi → publish; tampilkan rating agregat.
- **Hipotesis dampak:** testimoni segar & autentik → **konversi naik**; kurangi input manual.
- **KPI:** ulasan terkumpul, rating rata-rata, konversi halaman dengan testimoni. **Effort:** M · **RICE:** sedang-tinggi.

**CMS-08 — Analitik Konten + Atribusi Lead**
- **Tuas:** keputusan berbasis data. **Masalah:** G-ANALYTICS. **Solusi:** hitung views per artikel/destinasi; tandai lead dengan sumber konten (UTM/last-page); dashboard "konten → lead → booking".
- **Hipotesis dampak:** alokasi effort konten ke yang menghasilkan uang → ROI konten naik.
- **KPI:** view, content→lead rate, revenue-attributed content. **Effort:** M · **RICE:** sedang.

**CMS-09 — Rich Text / Block Editor untuk Artikel**
- **Tuas:** engagement. **Masalah:** G-RICHTEXT. **Solusi:** editor blok (heading, gambar inline, list, quote) → simpan sebagai HTML/blok tersanitasi.
- **Hipotesis dampak:** artikel lebih menarik → dwell time & SEO naik.
- **KPI:** dwell time, bounce rate. **Effort:** M · **RICE:** sedang.

---

## 4. PRIORITISASI RICE (urutan disarankan)

| ID | Enhancement | R | I | C | E | **RICE** | Wave |
|---|---|:-:|:-:|:-:|:-:|:-:|---|
| CMS-01 | Hardening (validasi+slug) | 5 | 2 | 1.0 | 1 | **10.0** | CW0 |
| CMS-02 | SEO Toolkit | 5 | 3 | 0.8 | 2 | **6.0** | CW1 |
| CMS-04 | Promo fungsional | 4 | 3 | 0.8 | 2 | **4.8** | CW1 |
| CMS-03 | Upload gambar | 4 | 2 | 0.9 | 2 | **3.6** | CW1 |
| CMS-07 | Testimoni dari ulasan | 3 | 2 | 0.8 | 2 | **2.4** | CW2 |
| CMS-06 | Multi-bahasa EN | 3 | 3 | 0.7 | 4 | **1.6** | CW2 |
| CMS-05 | Draft/scheduled publish | 3 | 2 | 0.8 | 3 | **1.6** | CW1 |
| CMS-08 | Analitik konten | 3 | 2 | 0.7 | 3 | **1.4** | CW2 |
| CMS-09 | Rich text editor | 3 | 2 | 0.7 | 3 | **1.4** | CW2 |

**Urutan:** CMS-01 → CMS-02 → CMS-04 → CMS-03 → (CMS-05) → CMS-07 → CMS-06 → CMS-08 → CMS-09.

---

## 5. ROADMAP

```
CW0 Hardening : CMS-01 (validasi + slug unik + paginasi)      [cepat, prasyarat]
      │
CW1 Quick Win : CMS-02 SEO → CMS-04 Promo fungsional → CMS-03 Upload → CMS-05 Publish workflow
      │           (traffic organik + promo terukur + konten mudah diupdate)
      ▼
CW2 Strategic : CMS-07 Ulasan → CMS-06 Multi-bahasa EN → CMS-08 Analitik → CMS-09 Rich text
```

**Metode tiap item (konsisten guardrail):** `POC → build (BE+FE) → gate.sh HIJAU → testing_agent_v3 → update docs`.

---

## 6. KEPUTUSAN YANG DIBUTUHKAN DARI USER

1. Mulai dari mana? **a.** CW0 hardening (CMS-01) dulu · **b.** langsung SEO (CMS-02, impact tertinggi) · **c.** promo fungsional (CMS-04) · **d.** cukup rencana ini dulu.
2. **Upload gambar (CMS-03):** pakai **object storage** (persisten, disarankan — perlu setup via integration agent) atau **disk lokal** (cepat tapi bisa hilang saat redeploy)?
3. **Multi-bahasa (CMS-06):** apakah pasar turis asing (English) jadi prioritas bisnis sekarang atau nanti?
4. **Promo (CMS-04):** perlu fitur kuota/limit pemakaian & pelacakan per-kode sekarang, atau cukup diskon dasar dulu?

---

**Dokumen terkait:** `ENHANCEMENT_PLAN_BUSINESS_IMPACT.md` (rencana besar) · `SSOT_MASTER_REPAIR_PLAN.md` (integritas) · `memory/ENHANCEMENT_BACKLOG.md`.
