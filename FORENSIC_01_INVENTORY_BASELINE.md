# 📊 FORENSIC 01 — INVENTORY BASELINE (Zero-Assumption)

**Tujuan:** baseline kuantitatif yang **dapat di-reproduksi** (`python scripts/forensic_dump.py` → `SSOT_FORENSIC_RAW_TRAVEL.json`).
Semua angka di bawah adalah **bukti hidup** per audit 2026-07-02, DB `test_database`.

---

## 1. Ukuran Sistem

| Metrik | Nilai |
|---|---|
| Backend LOC (non-test) | **12.445** |
| Frontend LOC (`.js`/`.jsx`) | **18.908** (188 file) |
| Router modules (`backend/routers/*.py`) | **40** |
| Service modules (`backend/services/*.py`) | **41** |
| Route FastAPI terdaftar (`/api/*`) | **261** (+ infra/health) = **265** total |
| GET routes (disweep) | **130** |
| Koleksi MongoDB | **41** |

**File terbesar (kandidat pantau, belum wajib refactor):**
- Backend: `schemas.py` (709) · `services/analytics.py` (415) · `services/whatsapp.py` (391) · `services/gps.py` (344) · `routers/public.py` (331).
- Frontend: `features/app/GpsTracking.jsx` (499) · `Finance.jsx` (463) · `Reports.jsx` (401) · `Inbox.jsx` (328).

> Semua < 800 LOC. Tidak ada "monster file". Arsitektur router-thin + services sudah rapi.

---

## 2. Registry Koleksi (SSOT) — nama + count + status

| Koleksi | Count | Status | Modul pemakai |
|---|---:|---|---|
| `users` | 3 | ✅ aktif | auth, users, dashboard |
| `sessions` | 3 | ✅ aktif | dependencies (auth) |
| `vehicles` | 5 | ✅ aktif | vehicles, bookings, dispatch, gps, public |
| `drivers` | 2 | ✅ aktif | drivers, dispatch, driver, payroll |
| `customers` | 4 | ✅ aktif | customers, bookings |
| `bookings` | 6 | ✅ aktif | bookings, payments, dispatch, finance |
| `payments` | 5 | ✅ aktif | payments, finance |
| `expenses` | 7 | ✅ aktif | expenses, finance, payroll |
| `invoices` | 2 | ✅ aktif | invoices, finance |
| `trips` | 4 | ✅ aktif | trips, driver, dispatch, gps |
| `locations` | 5 | ✅ aktif | gps, trips, public/track |
| `maintenance_records` | 3 | ✅ aktif | maintenance, availability |
| `workshops` | 3 | ✅ aktif | workshops |
| `service_types` | 3 | ✅ aktif | service_types, maintenance |
| `driver_payouts` | 2 | ✅ aktif | payroll |
| `leads` | 7 | ✅ aktif | leads, public, growth |
| `lead_activities` | 5 | ✅ aktif | leads (CRM) |
| `campaigns` | 1 | ✅ aktif | campaigns |
| `campaign_recipients` | 3 | ✅ aktif | campaigns |
| `segments` | 3 | ✅ aktif | growth/segments |
| `sequences` | 1 | ✅ aktif | sequences |
| `sequence_enrollments` | **0** | 🟡 DORMANT | sequences (belum ada enrollment) |
| `conversations` | 8 | ✅ aktif | inbox, public/chat, whatsapp |
| `messages` | 15 | ✅ aktif | inbox |
| `broadcasts` | 1 | ✅ aktif | broadcasts |
| `notification_tasks` | 18 | ✅ aktif | notifications |
| `events` | 13 | ✅ aktif | automation (event bus) |
| `automation_rules` | 16 | ✅ aktif | automation |
| `automation_runs` | 7 | ✅ aktif | automation |
| `quotations` | 1 | ✅ aktif | quotations |
| `partners` | 2 | ✅ aktif | partners, subcharters |
| `partner_settlements` | **(lazy)** | 🟡 DORMANT | partners, subcharters (dibuat saat settle) |
| `subcharters` | 1 | ✅ aktif | subcharters |
| `trip_shares` | 1 | ✅ aktif | shares, public/track |
| `settings` | 9 | ✅ aktif | settings, public, pricing |
| `counters` | 4 | ✅ BY-DESIGN | services/counters (nomor atomik) |
| `audit_logs` | 8 | ✅ aktif | audit_logs, services/audit |
| `destinations` | 4 | ✅ aktif | content, public |
| `articles` | 6 | ✅ aktif | content, public |
| `packages` | 2 | ✅ aktif | content, public |
| `promos` | 2 | ✅ aktif | content, public |
| `testimonials` | 3 | ✅ aktif | content, public |
| `geocode_cache` | **(lazy)** | 🟡 DORMANT | services/geocode (cache OSM) |
| `user_onboarding` | **(lazy)** | 🟡 DORMANT | onboarding |

> **Tidak ada koleksi PHANTOM** (dibaca kode tapi tak akan pernah ada). Semua "kosong/lazy" punya writer sah → **DORMANT**, bukan bug. **Aturan:** jangan isi data palsu; biarkan terisi natural saat fitur dipakai.

---

## 3. Peta Endpoint per Domain (ringkas)

| Domain | Prefix | Auth |
|---|---|---|
| Auth | `/api/auth/*` | publik (login) + Bearer (me/logout) |
| Publik/marketing | `/api/public/*` | **tanpa auth** (rate-limited + honeypot) |
| Booking & dispatch | `/api/bookings/*`, `/api/dispatch/*` | Bearer + section |
| Trip & driver | `/api/trips/*`, `/api/driver/*` | Bearer (+ ownership driver) |
| Finance | `/api/payments`, `/api/expenses`, `/api/invoices`, `/api/finance/*` | section `finance` (owner/ops) |
| Payroll | `/api/payroll/*`, `/api/drivers/{id}/compensation` | section `finance` |
| GPS | `/api/gps/*` | Bearer (webhook = shared secret) |
| CRM/growth | `/api/leads`, `/api/crm/*`, `/api/campaigns`, `/api/sequences` | section |
| CMS | `/api/content/*` | section `cms` |
| Admin | `/api/users`, `/api/settings`, `/api/audit-logs` | owner |
| WhatsApp | `/api/wa/*` | webhook publik (verify_token/signature) |

---

## 4. Cara Re-generate Baseline

```bash
cd /app/backend && python /app/scripts/forensic_dump.py
# → /app/SSOT_FORENSIC_RAW_TRAVEL.json  (koleksi+count+keys, endpoints, code_access, klasifikasi)
```

Skrip ini **read-only** (hanya `list_collection_names` + `count_documents` + `find_one`). Aman dijalankan kapan pun.
