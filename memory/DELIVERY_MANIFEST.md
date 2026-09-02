# 📦 DELIVERY MANIFEST — Kontrak Deliverable per Fase
## Travel & Fleet Management Ecosystem

> **Fungsi:** mengubah "selesai" menjadi **terukur & bisa ditagih mesin**.
> Dibaca oleh `scripts/verify_delivery.py` (fase berstatus ACTIVE).
> **Aturan:** sebuah fase TIDAK boleh ditandai COMPLETED bila ada item **P0** yang belum ada
> atau ada **orphan endpoint** (backend tanpa UI). Lihat `docs/14_ANTI_UNDERDELIVERY_PROTOCOL.md`.
>
> Format ringan & dapat di-parse:
> `- [P0|P1] <type>: <identifier>` — type ∈ {endpoint, page, collection, invariant, screenshot, script, doc}

---

## ACTIVE_PHASE: CMS-CW2

### PHASE 0 — Governance & Foundation  (status: COMPLETED)
<!-- 0.4 Auth+RBAC+skeleton SELESAI 2026-06-27: gate.sh HIJAU (10/10), testing_agent 100% (27/27 BE, FE all). Flip ACTIVE_PHASE -> 1 saat mulai Phase 1. -->
- [P0] doc: docs/AGENT_START_HERE.md
- [P0] doc: docs/PLAYBOOKS.md
- [P0] doc: docs/13_ARCHITECTURE_BEST_PRACTICES.md
- [P0] doc: docs/14_ANTI_UNDERDELIVERY_PROTOCOL.md
- [P0] script: scripts/preflight.py
- [P0] script: scripts/verify_schema.py
- [P0] script: scripts/verify_delivery.py
- [P0] script: scripts/verify_architecture.py
- [P0] script: scripts/mutation_smoke.py
- [P0] script: scripts/gate.sh
- [P1] endpoint: /api/auth/login
- [P1] endpoint: /api/auth/me
- [P1] endpoint: /api/users
- [P1] page: features/app/Login
- [P1] page: features/app/Dashboard
- [P1] invariant: users-seeded

---

### PHASE 1 — POC GPS + Anti Double-Booking  (status: DONE)
<!-- Phase 1 SELESAI & TERVERIFIKASI: gate.sh HIJAU 10/10, verify_delivery 5/5 P0, INV-4/INV-6 PASS, testing_agent 100%, POC 14/14. -->
- [P0] endpoint: /api/locations
- [P0] endpoint: /api/locations/live
- [P0] endpoint: /api/bookings/availability
- [P0] page: features/app/GpsTracking
- [P0] page: features/app/DriverCheckin
- [P0] invariant: INV-4 (anti double-booking)
- [P0] invariant: INV-6 (locations monotonic)
- [P0] screenshot: gps-live-map

---

### PHASE 2 — ERP Core  (status: DONE)
- [P0] endpoint: /api/vehicles
- [P0] endpoint: /api/drivers
- [P0] endpoint: /api/customers
- [P0] endpoint: /api/bookings
- [P0] endpoint: /api/dashboard
- [P0] page: features/app/Bookings
- [P0] page: features/app/Vehicles
- [P0] page: features/app/Drivers
- [P0] page: features/app/Customers
- [P0] page: features/app/Dashboard
- [P0] invariant: INV-1
- [P0] invariant: INV-9 (dashboard KPI)
- [P1] endpoint: /api/payments
- [P1] invariant: INV-2 (paid == Σ payments)
- [P1] invariant: INV-3 (payment_status derivation)

> Fase 3–6: deliverable diisi saat fase mendekat (hindari manifest basi). Acuan ruang lingkup: `docs/09_ROADMAP.md`.

<!-- PHASE 3 SELESAI & TERVERIFIKASI 2026-06-28: gate.sh HIJAU 10/10, verify_delivery P0 10/10 (100%), 0 orphan. testing_agent_v3 (iter 5) = 100% (64/64 BE, FE semua halaman + form + E2E lead->CRM). Invarian lead-from-website PASS. ACTIVE_PHASE tetap 3 (P0 100%); fase berikutnya = Phase 4 (CRM Internal) — isi manifest P0-nya saat mulai. -->
### PHASE 3 — Website Publik + Lead  (status: DONE)
- [P0] endpoint: /api/public/fleet
- [P0] endpoint: /api/public/destinations
- [P0] endpoint: /api/public/quotation
- [P0] endpoint: /api/public/trip-estimate
- [P0] page: features/public/Home
- [P0] page: features/public/Fleet
- [P0] page: features/public/Destinations
- [P0] page: features/public/TripCalculator
- [P0] page: features/public/Quotation
- [P0] page: features/public/ThankYou
- [P0] invariant: lead-from-website (quotation → leads → CRM)
- [P1] endpoint: /api/public/articles
- [P1] endpoint: /api/public/testimonials
- [P1] page: features/public/Blog
- [P1] page: features/public/Contact
- [P1] page: features/public/About

---

<!-- PHASE 4 dimulai 2026-06-28: CRM Internal (pipeline kanban, detail+timeline, auto-assign, reminder, broadcast). -->
<!-- PHASE 4 SELESAI & TERVERIFIKASI 2026-06-28: gate.sh HIJAU 10/10, verify_delivery P0 10/10 (100%), 0 orphan. ux_audit --strict 0 ERROR. testing_agent_v3 (iter 6) = 100% (85/85 BE; FE: Kanban 6 kolom, Lead Detail Drawer stage/assign/value/note/convert, Tambah Lead, Reminder H-7/H-3/H-1/overdue, Broadcast create+send). Broadcast send = SIMULASI (belum integrasi WA nyata). ACTIVE_PHASE tetap 4 (P0 100%); fase berikutnya = Phase 5 (Fleet & Booking) — MENUNGGU instruksi user sebelum mulai. -->
### PHASE 4 — CRM Internal  (status: DONE)
- [P0] endpoint: /api/leads/pipeline
- [P0] endpoint: /api/leads/{lead_id}
- [P0] endpoint: /api/leads/{lead_id}/stage
- [P0] endpoint: /api/leads/{lead_id}/assign
- [P0] endpoint: /api/leads/{lead_id}/convert
- [P0] endpoint: /api/leads/{lead_id}/activities
- [P0] endpoint: /api/leads/agents
- [P0] collection: lead_activities
- [P0] page: features/app/Crm
- [P0] invariant: INV-7 (lead.stage ∈ {new,contacted,quoted,negotiation,won,lost})
- [P1] endpoint: /api/leads/reminders
- [P1] endpoint: /api/broadcasts
- [P1] page: components/app/LeadDetailDrawer
- [P1] page: components/app/CrmBroadcast

---

<!-- PHASE 5 dimulai 2026-06-28: Keuangan & Laporan (expenses, invoice+export PDF/Excel, laba-rugi per periode, piutang/AR, laporan agregat). Acuan: docs/09_ROADMAP.md Phase 5 + docs/04_API_CONTRACT.md §Finance. -->
<!-- PHASE 5 SELESAI & TERVERIFIKASI 2026-06-28: gate.sh HIJAU 10/10, verify_delivery P0 10/10 (100%), verify_schema 38/0, ux_audit --strict 0 ERROR, audit_endpoint_sweep 0×5xx. testing_agent_v3 (iter 7) = Backend 117/117 (100%), Frontend semua fitur OK. RBAC finance/reports = owner+ops_admin (driver 403). Export invoice PDF (reportlab) + Excel (openpyxl); laporan Excel. INV-5 (trip.profit) & INV-8 (number unik) terjaga. ACTIVE_PHASE tetap 5 (P0 100%); fase berikutnya = Phase 6 (GPS lengkap + Maintenance) — MENUNGGU instruksi user. -->
### PHASE 5 — Keuangan & Laporan  (status: DONE)
- [P0] endpoint: /api/expenses
- [P0] endpoint: /api/invoices
- [P0] endpoint: /api/invoices/{invoice_id}/export
- [P0] endpoint: /api/finance/profit-loss
- [P0] endpoint: /api/finance/ar
- [P0] endpoint: /api/reports/summary
- [P0] collection: expenses
- [P0] collection: invoices
- [P0] page: features/app/Finance
- [P0] page: features/app/Reports
- [P0] invariant: INV-5 (trip.profit == revenue - Σ expenses)
- [P0] invariant: INV-8 (number-series unik: invoices.number)
- [P1] endpoint: /api/invoices/{invoice_id}
- [P1] endpoint: /api/finance/summary
- [P1] endpoint: /api/reports/export
- [P1] page: components/app/ExpenseFormDialog
- [P1] page: components/app/InvoiceFormDialog

---

<!-- PHASE 6 dimulai 2026-06-28: GPS lengkap + Maintenance. Acuan: docs/09_ROADMAP.md Phase 6 + plan.md §6 M4 (Maintenance) & M6 (GPS) + §0.5-C Gap Tier A. Scope: maintenance_records (CRUD + reminder KIR/pajak/servis H-30/14/7 + unit in-service memblok availability), GPS lengkap (live multi-unit + indikator stale/offline, geofence auto-status, riwayat track lintas-trip, share-link korporat token+expiry+revoke + halaman publik /track/:token). Maps tetap Leaflet+OSM+OSRM (adapter Google Maps disiapkan, key nanti). -->
### PHASE 6 — GPS lengkap + Maintenance  (status: DONE ✅ 2026-06-28)
- [P0] endpoint: /api/maintenance
- [P0] endpoint: /api/maintenance/reminders
- [P0] endpoint: /api/maintenance/{maintenance_id}
- [P0] endpoint: /api/shares
- [P0] endpoint: /api/locations/history
- [P0] endpoint: /api/public/track/{token}
- [P0] collection: maintenance_records
- [P0] collection: trip_shares
- [P0] page: features/app/Maintenance
- [P0] page: features/public/PublicTrack
- [P0] invariant: INV-21 (maintenance window memblok booking aktif per vehicle)
- [P0] invariant: INV-22 (share token: tak kedaluwarsa & tak dibatalkan saat aktif)
- [P1] endpoint: /api/maintenance/summary
- [P1] endpoint: /api/shares/{share_id}/revoke
- [P1] endpoint: /api/locations/live
- [P1] page: components/app/MaintenanceFormDialog
- [P1] page: components/app/ShareLinkPanel

---

<!-- PHASE 7 dimulai 2026-06-28: Gap Tier A (CRM Inbox + Notification&Scheduler + Settings Admin). WA = SIMULASI. Acuan: plan.md §0.5-C + §6 (M-CRM Inbox, M-Admin). Scope: conversations/messages (inbox multi-admin: thread, status pesan sent/delivered/read, assign, catatan internal, filter unassigned/mine/all, web-chat live publik + simulasi WA), notification_tasks (reminder otomatis KIR/pajak/servis + follow-up lead + booking + scheduler background loop + notification center di bell topbar), settings (profil perusahaan, harga & kebijakan DP/cancellation, kalender libur/jam operasional). Reuse section RBAC 'crm' (inbox) & 'settings' (owner). -->
<!-- PHASE 7 SELESAI & TERVERIFIKASI 2026-06-30: gate.sh HIJAU 10/10; testing_agent_v3 (iter 25) = Backend 98.6% (73/74; 1 minor note = pilihan desain API, bukan bug) + Frontend 100% (0 bug). Diverifikasi end-to-end: Inbox (list+filter status/assigned/channel/q, create, thread+messages, assign dgn validasi agen, reply + catatan internal, mark read, status open/snoozed/closed), Notifications (list, unread_count, scan owner/ops, read_all, read, dismiss, visibilitas role driver≠manager), Settings (GET/PATCH owner-only + audit log tercatat), AuditLog (owner-only), Public web-chat (POST/GET /api/public/chat → masuk Inbox kanal 'web', catatan internal disembunyikan). RBAC driver→403 di inbox/settings/audit terverifikasi. INV-23 PASS. -->
### PHASE 7 — Gap Tier A: Inbox + Notifications + Settings  (status: DONE ✅ 2026-06-30)
- [P0] endpoint: /api/conversations
- [P0] endpoint: /api/conversations/{conversation_id}
- [P0] endpoint: /api/notifications
- [P0] endpoint: /api/notifications/scan
- [P0] endpoint: /api/settings
- [P0] endpoint: /api/public/chat
- [P0] collection: conversations
- [P0] collection: messages
- [P0] collection: notification_tasks
- [P0] page: features/app/Inbox
- [P0] page: features/app/Settings
- [P0] invariant: INV-23 (message.conversation_id selalu rujuk conversation sah)
- [P1] endpoint: /api/notifications/unread_count
- [P1] endpoint: /api/conversations/{conversation_id}/messages
- [P1] endpoint: /api/public/chat/{token}
- [P1] page: components/public/ChatWidget

---

<!-- PHASE 8 dimulai 2026-06-28: Hardening MVP (Tahap A) — A1 Audit Log Engine, A2 Atomic Counters, A3 Rate-limit publik, A4 Pagination, A5 Onboarding. Tiap item ditutup gate.sh + testing_agent_v3. Manifest diisi PROGRESIF per item agar verify_delivery hijau tiap checkpoint. -->
### PHASE 8 — Hardening MVP (Tahap A)  (status: DONE ✅)
- [P0] collection: audit_logs
- [P0] endpoint: /api/audit-logs
- [P0] page: features/app/AuditLog
- [P0] collection: counters
- [P0] collection: user_onboarding
- [P0] endpoint: /api/onboarding
- [P0] page: components/app/OnboardingChecklist

---

<!-- PHASE 9 dimulai 2026-06-29: Tahap B (Value MVP) — B1 Pricing Engine, B2 Quotation Lifecycle, B3 Light CMS, B4 Identity/Dedupe. Diisi PROGRESIF per sub-fase; tiap sub-fase ditutup gate.sh HIJAU + testing_agent_v3. Arsitektur user-chosen: 1a/2a/3a/4a. -->
<!-- B1 SELESAI & TERVERIFIKASI 2026-06-29: gate.sh HIJAU 10/10; testing_agent_v3 backend 14/14 (100%) + frontend 97% (0 bug). Pricing Engine konfigurabel menggantikan hardcode. -->
<!-- B2 SELESAI & TERVERIFIKASI 2026-06-29: gate 10/10; testing backend 28/28 (100%) + frontend 95% (0 bug fungsional; +fix denied-state utk akses driver via URL). -->
<!-- B3 SELESAI & TERVERIFIKASI 2026-06-29: gate 10/10; testing backend 68/68 (100%) + frontend 16/16 (100%). CMS CRUD 5 entitas + read publik packages/promos. -->
<!-- B4 SELESAI & TERVERIFIKASI 2026-06-29: gate 10/10; testing backend 66/69 (0 bug; 3 'fail' = perilaku dedupe benar) + frontend 14/14 (100%). Normalisasi +62, dedupe customer, auto-link lead, Contact 360. -->
### PHASE 9 — Tahap B: Pricing · Quotation · CMS · Identity  (status: B1–B4 SELESAI ✅)
<!-- B1 Pricing Engine (aktif): tarif konfigurabel (settings.pricing_rules) gantikan hardcode; dipakai estimator publik + quote internal + auto-base_price booking; surcharge weekend/libur; DP saran. -->
- [P0] endpoint: /api/pricing/quote
- [P0] page: features/app/Settings
- [P1] endpoint: /api/pricing/rules
- [P1] endpoint: /api/public/trip-estimate
<!-- B2 Quotation Lifecycle (aktif): penawaran QUO-xxxx dari lead → kirim → terima → konversi ke booking (+ customer dedupe ringan) + PDF. INV-19: tak boleh double-convert. -->
- [P0] collection: quotations
- [P0] endpoint: /api/quotations
- [P0] endpoint: /api/quotations/{quotation_id}/convert
- [P0] page: features/app/Quotations
- [P0] invariant: INV-19 (penawaran accepted→1 booking; no double-convert)
- [P1] endpoint: /api/quotations/{quotation_id}/send
- [P1] endpoint: /api/quotations/{quotation_id}/pdf
<!-- B3 Light CMS (aktif): CRUD admin untuk seluruh konten website (destinations, packages, articles, testimonials, promos) via /api/content/{resource}. Read publik via /api/public/*. Section RBAC 'cms'. -->
- [P0] collection: packages
- [P0] collection: promos
- [P0] endpoint: /api/content/{resource}
- [P0] page: features/app/ContentManager
- [P1] endpoint: /api/public/packages
- [P1] endpoint: /api/public/promos
<!-- B4 Identity/Dedupe (aktif): normalisasi +62, dedupe customer (409 saat create), auto-link lead→customer, konversi via ensure_customer, Contact 360 (booking+lead+penawaran+percakapan+timeline). -->
- [P0] endpoint: /api/customers/{customer_id}
- [P0] page: features/app/Customers
- [P0] invariant: INV-20 (nomor +62 ter-normalisasi; dedupe kontak)

---

<!-- PHASE E1 dimulai 2026-06-30: ERP Enhancement E1 — Event Bus + Automation Engine + WhatsApp Adapter (mock-first) + upgrade In-App Inbox. Keputusan user: 1c (config rules di Settings + menu Otomasi utk monitoring), 2a (seed rule contoh AKTIF), 3a (tombol simulasi WA masuk di Inbox), 4a (stub meta_cloud, aktif E6). POC test_core_e1.py 23/23 PASS. gate.sh HIJAU. -->
### PHASE E1 — Event Bus · Automation Engine · WhatsApp Adapter (mock)  (status: SELESAI ✅)
<!-- Event domain dipancarkan dari aksi nyata (lead.created, quotation.sent, booking.confirmed, payment.recorded, trip.started/completed, booking.departure_due, invoice.overdue, doc.expiring, wa.inbound) → Automation Engine evaluasi rules (kondisi→aksi) idempotent + audit (automation_runs). WhatsApp provider-agnostic: mock aktif, meta_cloud stub (E6). Inbox WA real-ready: session-window 24 jam, status, cost tracking, opt-in/out, template. -->
- [P0] collection: events
- [P0] collection: automation_rules
- [P0] collection: automation_runs
- [P0] endpoint: /api/automation/rules
- [P0] endpoint: /api/automation/runs
- [P0] endpoint: /api/automation/events
- [P0] endpoint: /api/automation/stats
- [P0] endpoint: /api/automation/event-types
- [P0] endpoint: /api/wa/config
- [P0] endpoint: /api/wa/templates
- [P0] page: features/app/Automation
- [P0] page: components/app/AutomationSettings
- [P0] page: components/app/WhatsAppSettings
- [P0] page: features/app/Inbox
- [P0] script: test_core_e1.py
- [P1] endpoint: /api/wa/webhook
- [P1] endpoint: /api/wa/simulate-inbound

<!-- PHASE E2 dimulai 2026-06-30: ERP Enhancement E2 — CRM Growth Engine (Scoreboard/SLA, RFM/LTV, Segmentasi, Sequence nurturing, Campaign broadcast WA tersegmentasi). Backend E2 sudah ada & ter-POC (test_core_e2.py). Tugas penyelesaian: WIRING 5 komponen React ke halaman CRM (urutan tab user-chosen: Pipeline → Skor&SLA → RFM → Segmen → Sequence → Campaign → Reminder), GANTI tab "Broadcast" lama dengan tab "Campaign" baru. WA = MOCK (provider mock services/whatsapp.py). -->
### PHASE E2 — CRM Growth Engine (Scoreboard · RFM · Segmen · Sequence · Campaign)  (status: SELESAI ✅ 2026-06-30)
<!-- E2 SELESAI & TERVERIFIKASI 2026-06-30: gate.sh HIJAU 10/10; testing_agent_v3 (iter 31) = Backend 100% (58/58), Frontend 99% (36/37; 1 minor testid 'crm-reminders' DIPERBAIKI). 7 tab CRM render sesuai urutan, tab 'Broadcast' lama DIHAPUS dari CRM & DIGANTI tab 'Campaign'. Campaign flow end-to-end (buat segmen → buat kampanye → kirim → stats + recipients) PASS. WA send = MOCK. -->
- [P0] collection: segments
- [P0] collection: sequences
- [P0] collection: sequence_enrollments
- [P0] collection: campaigns
- [P0] collection: campaign_recipients
- [P0] endpoint: /api/crm/scoreboard
- [P0] endpoint: /api/crm/aging
- [P0] endpoint: /api/crm/rfm
- [P0] endpoint: /api/crm/recompute
- [P0] endpoint: /api/crm/segments
- [P0] endpoint: /api/crm/segments/{segment_id}/preview
- [P0] endpoint: /api/crm/sequences
- [P0] endpoint: /api/crm/sequences/{sequence_id}/enroll
- [P0] endpoint: /api/crm/campaigns
- [P0] endpoint: /api/crm/campaigns/{campaign_id}
- [P0] endpoint: /api/crm/campaigns/{campaign_id}/send
- [P0] page: components/app/CrmScoreboard
- [P0] page: components/app/CrmRfm
- [P0] page: components/app/CrmSegments
- [P0] page: components/app/CrmSequences
- [P0] page: components/app/CrmCampaigns
- [P0] script: test_core_e2.py
- [P1] endpoint: /api/crm/sequences/{sequence_id}/enrollments
- [P1] endpoint: /api/wa/templates

<!-- PHASE E3 dimulai 2026-06-30: ERP Enhancement E3 — Dispatch & Komunikasi Operasi (Ops Cockpit "Hari Ini"). Assign driver+unit + geocode tujuan via Nominatim (perbaiki gap G1), Konfirmasi keberangkatan (WA), status driver→customer enroute/arrived (WA), POD (Bukti Layanan lokal: foto+penerima+catatan disajikan via /api/uploads). WA = MOCK (provider mock services/whatsapp.py). RESTORE catatan: fix import `Navigation` di navigationConfig.js + yarn install (leaflet, photo-sphere-viewer) agar webpack compile. -->
### PHASE E3 — Dispatch & Komunikasi Operasi (Ops Cockpit)  (status: SELESAI ✅ 2026-06-30)
<!-- E3 SELESAI & TERVERIFIKASI 2026-06-30: POC test_core_e3.py 14/14 PASS (live Nominatim geocode + 4 trigger WA baru + idempotency). gate.sh HIJAU 10/10 (integrity 31/0). testing_agent_v3 (iter 34) = Backend 100% (26/26) + Frontend 100% (0 bug) + RBAC OK (driver tanpa menu dispatch). WA send = MOCK. -->
- [P0] collection: geocode_cache
- [P0] endpoint: /api/dispatch/today
- [P0] endpoint: /api/dispatch/{booking_id}/assign
- [P0] endpoint: /api/dispatch/{booking_id}/confirm-departure
- [P0] endpoint: /api/dispatch/trips/{trip_id}/enroute
- [P0] endpoint: /api/dispatch/trips/{trip_id}/arrived
- [P0] endpoint: /api/dispatch/trips/{trip_id}/pod
- [P0] page: features/app/Dispatch
- [P0] page: components/app/AssignTripDialog
- [P0] page: components/app/PodDialog
- [P0] script: test_core_e3.py
- [P0] invariant: dispatch-geocode-cache
- [P1] screenshot: dispatch-ops-cockpit

<!-- PHASE E4 dimulai 2026-06-30: ERP Enhancement E4 — BI & Management Cockpit (tab di Beranda/Dashboard). Exec KPI + Sales Funnel + Channel mix/ROAS (ad-spend manual settings.marketing_spend → CPL/CAC/ROAS) + Fleet ROI/utilisasi + Driver performance + AR aging + Retention/Cohort + Forecast moving-average. Export PDF+Excel. Range 30/90/365 + custom + pembanding periode lalu. Read-only (services/analytics.py); section RBAC 'analytics' (owner/ops_admin). -->
### PHASE E4 — BI & Management Cockpit (Beranda Tab)  (status: SELESAI ✅ 2026-06-30)
<!-- E4 SELESAI & TERVERIFIKASI 2026-06-30: POC test_core_e4.py 20/20 PASS (KPI+delta, funnel monotonic, channel ROAS/CPL math, AR aging==outstanding, fleet ROI, retention 0..1, forecast MA, ad-spend round-trip). gate.sh HIJAU 10/10. testing_agent_v3 (iter 35) = Backend fungsional 100% (10 'gagal' = timeout infra saat uji RBAC driver; curl driver=403 ~2.4ms), Frontend 100% (0 bug), RBAC OK (driver tanpa tab BI). marketing_spend = settings key (bukan koleksi baru). -->
- [P0] endpoint: /api/analytics/summary
- [P0] endpoint: /api/analytics/funnel
- [P0] endpoint: /api/analytics/channels
- [P0] endpoint: /api/analytics/fleet
- [P0] endpoint: /api/analytics/drivers
- [P0] endpoint: /api/analytics/ar-aging
- [P0] endpoint: /api/analytics/retention
- [P0] endpoint: /api/analytics/forecast
- [P0] endpoint: /api/analytics/ad-spend
- [P0] endpoint: /api/analytics/export
- [P0] page: components/app/BiCockpit
- [P0] page: components/app/BiCharts
- [P0] page: components/app/BiTables
- [P0] page: components/app/AdSpendDialog
- [P0] script: test_core_e4.py
- [P1] invariant: ar-aging-equals-outstanding
- [P1] screenshot: bi-management-cockpit

<!-- PHASE E5 dimulai 2026-06-30: ERP Enhancement E5 — Finance Automation. Menutup gap keuangan: G4 (biaya perawatan masuk P&L total + per unit), G5 (rekonsiliasi invoice↔pembayaran + sinkronisasi status invoice paid/partial/sent), AR collection otomatis (reminder WA via event invoice.overdue → automation engine; mock), arus kas bulanan (kas masuk vs keluar incl. perawatan) + proyeksi moving-average, export laporan keuangan PDF+Excel. Read-only kecuali sync status & emit reminder. Backend: services/finance_automation.py + services/finance_export.py + extend routers/finance.py. Frontend: 2 tab baru di Keuangan (Rekonsiliasi, Arus Kas) + upgrade tab Laba-Rugi ke pl-full (perawatan + per-unit) + tombol export PDF/Excel + tombol reminder AR (per-baris + Ingatkan Semua). WA = MOCK (provider mock services/whatsapp.py). -->
### PHASE E5 — Finance Automation (P&L+Perawatan · Rekonsiliasi · AR Collection · Arus Kas)  (status: SELESAI ✅ 2026-06-30)
<!-- E5 SELESAI & TERVERIFIKASI 2026-06-30: POC test_core_e5.py 19/19 PASS (profit==revenue-opex-maintenance & per-unit, reconciliation diff/status, sync idempotent, cashflow saldo kumulatif + proyeksi, AR reminder event→automation→WA mock bertambah, assemble report). gate.sh HIJAU 10/10 (0 orphan). testing_agent_v3 (iter 36) = Backend 100% (70/70) + Frontend 100% (6 tab Keuangan OK, export PDF/Excel, reminder AR, status 'Sebagian'/partial, per-unit incl. perawatan), RBAC OK (driver 403). WA send = MOCK. -->
- [P0] endpoint: /api/finance/pl-full
- [P0] endpoint: /api/finance/reconciliation
- [P0] endpoint: /api/finance/reconciliation/sync
- [P0] endpoint: /api/finance/cashflow
- [P0] endpoint: /api/finance/ar/overdue
- [P0] endpoint: /api/finance/ar/{booking_id}/remind
- [P0] endpoint: /api/finance/ar/remind-all
- [P0] endpoint: /api/finance/export
- [P0] page: features/app/Finance
- [P0] page: components/app/FinanceReconciliation
- [P0] page: components/app/FinanceCashflow
- [P0] script: test_core_e5.py
- [P1] invariant: pl-maintenance-in-profit (profit == revenue − opex − maintenance)
- [P1] invariant: invoice-status-sync (status invoice mengikuti Σ pembayaran)

<!-- PHASE EADS dimulai 2026-06-30: E-ADS (atribusi & marketing, mock-first) + E6-PREP (WhatsApp Meta Cloud siap-colok). E-ADS: capture UTM/gclid/fbclid/ttclid (first-touch + last-touch) di leads + channel kanonik (google_ads/meta_ads/tiktok_ads/instagram/email/referral/website/direct); consent marketing; webhook Lead Ads mock /api/public/lead-ads/{provider}; channels_roi dikelompokkan per channel (CPL/CAC/ROAS) tampil di BI Cockpit (ChannelsCard + kolom Menang/CAC); segmen by channel/consent (untuk blasting via Campaign E2). E6-PREP: MetaCloudProvider kirim NYATA via Graph API (httpx, gagal rapi tanpa kredensial), POST /api/wa/test-send, field api_version + badge 'Siap kirim' + tombol Test Kirim di Settings WA. WA aktivasi NYATA tetap menunggu kredensial WABA user. -->
### PHASE EADS — E-ADS Attribution & Marketing + E6 WhatsApp Prep  (status: SELESAI ✅ 2026-06-30)
<!-- EADS SELESAI & TERVERIFIKASI 2026-06-30: POC test_core_eads_e6.py 35/35 PASS (derive_channel UTM/click-id, build_attribution first+last, ads.create_ad_lead+parse envelope Meta, channels_roi CPL/CAC/ROAS per channel, segments by channel/consent, MetaCloudProvider graceful tanpa kredensial + send_wa mock). Pilihan user: 1b (dashboard di BI Cockpit), 2a (first+last touch), 3a (webhook Lead Ads mock), 4a (consent di form publik), 5b (Test Kirim nyata). WA send NYATA menunggu kredensial WABA. -->
- [P0] endpoint: /api/public/lead-ads/{provider}
- [P0] endpoint: /api/wa/test-send
- [P0] endpoint: /api/analytics/channels
- [P0] page: features/public/Quotation
- [P0] page: components/app/LeadDetailDrawer
- [P0] page: components/app/BiCharts
- [P0] page: components/app/WhatsAppSettings
- [P0] script: test_core_eads_e6.py
- [P1] invariant: attribution-channel-derive (gclid→google_ads, fbclid→meta_ads, ttclid→tiktok_ads)
- [P1] invariant: meta-cloud-graceful (tanpa kredensial → status failed, tanpa raise)

<!-- PHASE E8 dimulai 2026-06-30: Driver Workspace + Fleet (Servis Preventif Terjadwal + Master Vendor/Bengkel). Tanpa integrasi API eksternal (MongoDB/React + Leaflet/OSRM gratis). Driver Workspace: surface /api/driver/* (tasks/summary/ack/arrived/pod) scoped ke driver yang login (ownership 403); halaman /app/driver-workspace (kartu tugas + konfirmasi + navigasi Leaflet + unggah POD). Fleet Preventive: services/preventive.py hitung jatuh tempo per armada (basis km + waktu → overdue|due_soon|ok); GET /api/maintenance/preventive + POST /api/maintenance/preventive/{vehicle_id}/schedule. Workshops master: koleksi baru `workshops` (wsh_) + CRUD /api/workshops + tab Vendor/Bengkel di Maintenance + dropdown bengkel di form perawatan (maintenance_records.workshop_id). -->
### PHASE E8 — Driver Workspace + Fleet Preventive & Vendor/Bengkel  (status: DONE)
- [P0] endpoint: /api/driver/tasks
- [P0] endpoint: /api/driver/summary
- [P0] endpoint: /api/driver/tasks/{trip_id}/ack
- [P0] endpoint: /api/driver/tasks/{trip_id}/arrived
- [P0] endpoint: /api/driver/tasks/{trip_id}/pod
- [P0] endpoint: /api/workshops
- [P0] endpoint: /api/maintenance/preventive
- [P0] endpoint: /api/maintenance/preventive/{vehicle_id}/schedule
- [P0] collection: workshops
- [P0] page: features/app/DriverWorkspace
- [P0] page: components/app/DriverTaskCard
- [P0] page: components/app/DriverPodDialog
- [P0] page: components/app/DriverNavDialog
- [P0] page: components/app/MaintenancePreventive
- [P0] page: components/app/WorkshopsManager
- [P0] script: test_core_e8.py
- [P1] invariant: driver-task-ownership (driver hanya bisa ack/arrived/pod trip miliknya → 403)
- [P1] invariant: preventive-status (overdue bila sisa km ≤ 0 atau sisa hari < 0; due_soon bila ≤ ambang)

<!-- PHASE E9 dimulai 2026-06-30: Fleet↔Driver Trip/KM & Odometer. Persist jarak tempuh trip dari odometer (akurat) atau fallback estimasi OSRM (dihitung saat assign). Driver input odometer awal/akhir di Driver Workspace (OdometerDialog) → distance_km + update vehicles.odometer. Drill-down: GET /api/drivers/{id}/performance (total trip/km/revenue/completion + riwayat) & GET /api/vehicles/{id}/trips (totals + riwayat) → DriverDetailDrawer & VehicleDetailDrawer (klik baris di halaman Driver/Armada). Tanpa API eksternal. -->
<!-- PHASE E8/E9 status → DONE (2026-07-01): verifikasi ulang saat gap-analysis — test_core_e8.py 26/26 PASS, test_core_e9.py 14/14 PASS, gate HIJAU. Deliverable & FE lengkap; marker sebelumnya belum di-flip. -->
### PHASE E9 — Fleet↔Driver: Trip/KM & Odometer  (status: DONE)
- [P0] endpoint: /api/drivers/{driver_id}/performance
- [P0] endpoint: /api/vehicles/{vehicle_id}/trips
- [P0] page: components/app/OdometerDialog
- [P0] page: components/app/DriverDetailDrawer
- [P0] page: components/app/VehicleDetailDrawer
- [P0] script: test_core_e9.py
- [P1] invariant: trip-distance (checkout pakai odometer end-start; fallback est_distance_km OSRM; vehicles.odometer auto-update)

<!-- PHASE E10 dimulai 2026-06-30: Fleet Service configurable + riwayat service per-armada. Koleksi baru service_types (svt_) + CRUD /api/service-types (master jenis service + interval default), dipakai sbg maintenance_records.type. Vehicle Detail Drawer tab Riwayat Service via GET /api/vehicles/{id}/maintenance. Tanpa API eksternal. -->
<!-- PHASE E10 SELESAI & TERVERIFIKASI 2026-07-01: FE Phase A dituntaskan (ServiceTypesManager + ServiceTypeFormDialog = tab "Jenis Service" di /app/maintenance; MaintenanceFormDialog dropdown Jenis kini gabung builtin + service_types custom aktif; VehicleDetailDrawer tab "Riwayat Service" via GET /api/vehicles/{id}/maintenance → totals count/total_cost/done/next_service_date/last_service_date + tabel records). POC test_core_e10.py 12/12 PASS; bash scripts/gate.sh HIJAU 10/10 (P0 6/6 100%); testing_agent_v3 iter 40 = Backend 100% (44/44) + Frontend 100% (0 bug), RBAC driver read-only OK (403 mutasi). Tanpa API eksternal. Berikutnya: PHASE C (E11 — Driver Payroll/HR Lite) menunggu instruksi user. -->
### PHASE E10 — Fleet: Service Configurable + Riwayat per-Armada  (status: DONE)
- [P0] endpoint: /api/service-types
- [P0] endpoint: /api/vehicles/{vehicle_id}/maintenance
- [P0] collection: service_types
- [P0] page: components/app/ServiceTypesManager
- [P0] page: components/app/ServiceTypeFormDialog
- [P0] script: test_core_e10.py
- [P1] invariant: service-type-key (jenis custom aktif boleh jadi maintenance.type; cegah duplikat/builtin)

<!-- PHASE E11 dimulai 2026-07-01: Driver Payroll/HR Lite. Kompensasi per driver (embedded drivers.comp: gaji pokok bulanan + komisi/trip + %revenue[trip|booking] + uang jalan/km, toggle per komponen). Koleksi baru driver_payouts (dpo_) + /api/payroll/* (generate akrual dari trip selesai, draft→approved→paid, bonus/potongan baris manual, slip PDF+Excel). Integrasi Finance: approve→expense gaji_driver (akrual P&L), pay→expense paid (kas). UI: tab Payroll di /app/finance + tab Kompensasi di Driver Detail Drawer. Tanpa API eksternal. -->
### PHASE E11 — Driver Payroll / HR Lite  (status: DONE)
- [P0] endpoint: /api/payroll/payouts
- [P0] endpoint: /api/payroll/payouts/generate
- [P0] endpoint: /api/payroll/summary
- [P0] endpoint: /api/drivers/{driver_id}/compensation
- [P0] collection: driver_payouts
- [P0] page: components/app/PayrollManager
- [P0] page: components/app/PayoutFormDialog
- [P0] page: components/app/PayoutDetailDialog
- [P0] page: components/app/DriverCompDialog
- [P0] script: test_core_e11.py
- [P1] invariant: payroll-finance (payout approved→expense gaji_driver akrual; paid→expense.paid=true; tidak dobel-hitung)


<!-- PHASE E12 dimulai 2026-07-01: Payroll Enhancements. (1) Rekap Payroll di modul Laporan: /api/reports/payroll (period totals + per_driver + YTD + SDM-vs-revenue) + merge ke /api/reports/summary + export PDF+Excel (/api/reports/payroll/export). (2) Generate payout MASSAL: /api/payroll/payouts/generate-bulk (semua driver, skip existing). (3) Otomasi/pengingat Payroll: event payroll.period_due & payroll.payout_pending + reminder di notifications.scan (akhir periode + payout menunggu). FE: section Rekap Payroll di /app/reports + tombol Generate Massal (PayoutBulkDialog) di tab Payroll. Tanpa koleksi baru & tanpa API eksternal. -->
### PHASE E12 — Payroll Enhancements (Rekap Laporan + Bulk + Otomasi)  (status: DONE)
- [P0] endpoint: /api/reports/payroll
- [P0] endpoint: /api/reports/payroll/export
- [P0] endpoint: /api/payroll/payouts/generate-bulk
- [P0] page: components/app/PayoutBulkDialog
- [P0] page: features/app/Reports
- [P0] script: test_core_e12.py
- [P1] event: payroll.period_due + payroll.payout_pending (reminder scheduler notifications.scan)

### PHASE E13 — Laporan Driver (Leaderboard) + Revenue-per-Trip  (status: DONE)
- [P0] endpoint: /api/reports/drivers
- [P0] endpoint: /api/reports/drivers/export
- [P0] page: features/app/Reports
- [P0] script: test_core_e13.py
- [P1] doc: docs/04_API_CONTRACT.md

<!-- PHASE E14 SELESAI & TERVERIFIKASI 2026-07-01 (restore env baru): gate.sh HIJAU 10/10; testing_agent_v3 iter 46 = Backend 100% (50/50) + Frontend 100% — A1 guard RBAC terpusat 11/11 URL manager-only redirect driver→/app/dashboard; B1 reminder SIM driver (sim_reminder target manager) muncul di /api/notifications + NotificationBell; regresi endpoint kritis & halaman 0 bug. -->

### PHASE E14 — Guard RBAC Terpusat + Reminder SIM Driver  (status: DONE)
- [P0] page: components/app/AppShell
- [P0] script: test_core_e14.py
- [P1] event: driver.sim_expiring

---

### PHASE E15 — GPS Dual-Source: Device fisik (Teltonika) via Traccar  (status: DONE)
<!-- E15 SELESAI 2026-07-01: POC 23/23 PASS (webhook ingest, knot→km/j, mapping IMEI, failover device>phone, alarm→notif, unmapped ignored, auth 401). Backup pelacakan GPS fisik + HP driver. -->
- [P0] endpoint: /api/gps/webhook
- [P0] endpoint: /api/gps/live
- [P0] endpoint: /api/gps/devices
- [P0] endpoint: /api/gps/summary
- [P0] endpoint: /api/gps/devices/{vehicle_id}/assign
- [P0] page: features/app/GpsTracking
- [P0] script: test_core_e15.py
- [P1] event: gps.alarm

### PHASE E16 — Pinjam Armada / Sub-charter (Partner Sourcing + AP + COGS + WA)  (status: DONE)
<!-- E16 SELESAI 2026-07-02: master Mitra + order sub-charter (requested->confirmed->settled/cancelled). Confirm membukukan COGS 'sewa_mitra' (P&L per booking/trip, INV-5). AP mitra dinamis + pelunasan (partner_settlements). WA ke MITRA via event subcharter.requested/confirmed (mock). RBAC section 'partners' (owner/ops_admin; driver 403). gate.sh HIJAU; verify_schema PASS (FK/prefix/numeric koleksi baru); testing_agent verifikasi BE+FE. -->
- [P0] collection: partners
- [P0] collection: subcharters
- [P0] collection: partner_settlements
- [P0] endpoint: /api/partners
- [P0] endpoint: /api/partners/{partner_id}/settlements
- [P0] endpoint: /api/subcharters
- [P0] endpoint: /api/subcharters/{subcharter_id}/confirm
- [P0] page: features/app/Partners
- [P0] invariant: INV-E16 (partner AP = Σ cost subcharter confirmed+settled − Σ settlements)
- [P1] endpoint: /api/subcharters/available-partners
- [P1] event: subcharter.confirmed

### PHASE E20 — Booking Rombongan (Group Booking Multi-Unit / Multi-Leg)  (status: DONE)
<!-- E20 SELESAI 2026-07-03: POST /api/bookings/group menerima N unit -> validasi per-unit INV-4 + intra-group anti-overlap (armada sama) -> insert atomic (semua-atau-tidak) semua booking anak dgn group_id sama (prefix grp_). Reuse dispatch/pembayaran/INV-4/INV-10. FE: GroupBookingDialog (repeatable unit rows + per-row availability + auto-price) + tombol 'Buat Rombongan' di /app/bookings + badge Grup x/y pada kolom Kode. Emit booking.confirmed per unit dgn dedupe_key group. -->
- [P0] endpoint: /api/bookings/group
- [P0] page: features/app/Bookings
- [P0] page: components/app/GroupBookingDialog

### PHASE E21 — Pembatalan dgn Denda & Refund Manual  (status: DONE — refund ledger IMPLEMENTED; denda tetap memo)
<!-- E21 SELESAI 2026-07-03. POST /api/bookings/{id}/cancel menerima body opsional CancelBooking{reason, cancellation_fee, refund_amount}. Validasi: fee/refund >=0; refund <= paid_amount (400 bila lebih). Simpan snapshot cancellation_reason/cancellation_fee/refund_amount/cancelled_at/cancelled_by pada bookings; event booking.cancelled payload +3 var. Backward-compat body kosong -> perilaku lama. FE: CancelBookingDialog dgn form denda+refund+alasan+preview total/terbayar. UPDATE 2026-07-03: refund otomatis diposting sbg payments negatif (type=refund, method=refund) IDEMPOTENT per booking; paid_amount berkurang via recompute (INV-2 & INV-3 tetap). Denda tetap MEMO (tidak diposting jurnal). Detail: memory/HANDOFF_E21_REFUND.md. -->
- [P0] endpoint: /api/bookings/{booking_id}/cancel
- [P0] page: components/app/CancelBookingDialog
- [P0] doc: memory/HANDOFF_E21_REFUND.md

### PHASE E26 — Denda Pembatalan → Auto Invoice (Paper Trail Revenue)  (status: DONE)
<!-- E26 SELESAI 2026-07-03. POST /api/bookings/{id}/cancel dgn cancellation_fee>0 otomatis membuat invoice type='cancellation_fee' status='paid' amount=cancellation_fee, IDEMPOTENT per booking. Paper trail utk denda; TIDAK menaikkan P&L revenue (revenue dari Σ payments; denda sudah tercakup di residual paid_amount - refund_amount). Nomor invoice memakai counter INV-YYYY-#### (E5). -->
- [P0] endpoint: /api/bookings/{booking_id}/cancel
- [P0] doc: docs/03_DATA_MODEL.md

### PHASE CMS-G1..G10 — CMS Gap Closure (2026-07-03) (status: DONE)
<!-- CMS-G1..G10 SELESAI. G1: validasi unik slug/code per resource (409). G2: /public/promos filter valid_until >= today. G3: POST /uploads/cms upload gambar (jpg/png/webp/gif <=6MB) ke /app/backend/uploads/cms/, di-serve via /api/uploads/cms/. G4: FE SCHEMAS destinations expose faqs/intro/route_points. G5: search bar (?q=) di ContentManager (debounce 350ms). G6: SEO metadata (meta_title/meta_description/og_image) di destinations/packages/articles/promos - grouping via <details> di form. G7: tombol Preview publik (Eye icon) buka /destinasi|paket|blog/<slug> di tab baru. G8: POST /content/{resource}/{id}/duplicate clone dgn slug/code auto-suffix (-copy, -copy-2). G9: testimonials +field approved; /public/testimonials filter approved-true (kompat lama: docs tanpa field ttp tampil). G10: field position per resource, sort primary ascending, fallback ke default sort resource. Inline edit position via icon ArrowUpDown di list. -->
- [P0] endpoint: /api/content/{resource}
- [P0] endpoint: /api/uploads/cms
- [P0] endpoint: /api/content/{resource}/{item_id}/duplicate
- [P0] page: features/app/ContentManager
- [P0] page: components/app/ContentFormDialog

### PHASE E27 — Kalender Keberangkatan: lapisan "Perlu Perhatian" + INV-21 dua arah (2026-08-10) (status: DONE)
<!-- E27 SELESAI 2026-08-10. Latar: sesi lalu berhenti saat menambah badge "bentrok" di day-list; verifikasi
visual menunjukkan banner bentrok SELALU 0. POC /app/test_core_conflict.py membuktikan itu bukan bug UI —
INV-4 sudah dikunci di semua jalur tulis (POST /bookings 400, reschedule 400) sehingga data bentrok armada
tidak bisa terbentuk. POC menemukan 4 celah nyata: (1) POST /maintenance LOLOS menabrak booking aktif
(melanggar INV-21), (2) keberangkatan aktif tanpa sopir tak terlihat di kalender, (3) permintaan publik
`pending` selalu vehicle_id=None sehingga MUSTAHIL terdeteksi logika lama yang berbasis vehicle_name,
(4) deteksi lama ikut menghitung status `completed` -> potensi false positive.
Hasil: (A) POST/PATCH /maintenance menolak 400 window yang menabrak keberangkatan aktif, dibungkus
vehicle_lock (anti-TOCTOU, mutex sama dgn jalur booking). (B) services/attention.py + GET
/api/departures/attention: 8 kelas risiko (vehicle_conflict, driver_conflict, maintenance_conflict,
hold_expired, hold_expiring, no_driver, pending_request, unpaid_soon), berbasis vehicle_id & status aktif;
projection /bookings/calendar diperkaya. (C) Banner diganti panel "Perlu Perhatian" (chip filter + badge di
sel bulan/timeline minggu/day-list + alert di panel detail); DepartureCalendar.jsx dipecah 754 -> 460 baris
+ 8 modul components/app/calendar/* (semua < 500 baris) sehingga validate_compliance FAIL 1 -> 0.
(D) gate.sh HIJAU 22/22 0 SKIP. Perbaikan guardrail: verify_schema FK bookings.vehicle_id ber-kondisi
(selaras docs/03_DATA_MODEL.md "nullable saat status=pending"); verify_auth_coverage allowlist
sitemap.xml/robots.txt (artefak SEO wajib publik); cleanup notification_tasks di 3 script gate runtime. -->
- [P0] endpoint: /api/departures/attention
- [P0] page: features/app/DepartureCalendar
- [P0] page: components/app/calendar/AttentionPanel
- [P0] page: components/app/calendar/CalendarMonthGrid
- [P0] page: components/app/calendar/DepartureDetailPanel
- [P0] script: test_core_conflict.py
- [P0] doc: docs/04_API_CONTRACT.md
- [P1] doc: memory/GATE_RECEIPT.md

### PHASE BOOKING-V1 — Pemesanan Online Publik + Verifikasi DP Ops (2026-08-12) (status: DONE)
<!-- BOOKING-V1 SELESAI & TERVERIFIKASI 2026-08-12. Sesi sebelumnya berhenti saat memverifikasi
/booking di browser: hasilnya "Tidak ada unit bebas di tanggal itu". Verifikasi ulang membuktikan itu
BUKAN bug — 12-14 Agu memang penuh (BK-0003 & BK-0004 memakai V-01/V-02, V-03 dalam perawatan 11-14 Agu);
dengan jendela bebas (25-27 Agu) muncul 4 unit, pesanan BK-0016 dibuat (hold + countdown DP + rekening +
form unggah bukti). POC scripts/test_core_booking_v1.py LULUS 74/74.
Yang dikerjakan sesi ini: (1) gate MERAH ux_audit E2 ditutup dengan state degradasi NYATA di
BookingRequest.jsx (daftar tipe unit gagal dimuat -> pesan jelas, tamu tetap bisa mengirim) + 5 WARN W1
tabular-nums. (2) BUG-0115: unit uji "Smoke Vehicle" milik mutation_smoke TAYANG di katalog & pencarian
booking publik -> publishable_filter kini menuntut publish_to_web == True EKSPLISIT + smoke membuat unit
dengan publish_to_web False + presweep/cleanup artefak (juga menutup SKIP palsu 409 duplikat pada smoke).
(3) BUG-0114: SEMUA field teks tanpa max_length -> nama 60.000 karakter (dari verify_adversarial_5xx)
tersimpan & merusak tata letak tabel Booking; 170 field teks sensitif dibatasi + DataTable memotong teks
ekstrem + guardrail INV-STR-01. (4) Ringkasan wizard tak lagi memajang "- -> -" saat asal/tujuan kosong.
(5) Fase 3 plan.md: guardrail INV-PRICE-01, INV-BOOK-02, INV-STR-01 + selftest mutasi 5 kelas bug
(semua MERAH saat disuntik, HIJAU setelah revert) + INV-META-01 diperluas mendukung self-test 1:N (COVERS).
(6) Sisi ops diverifikasi lewat UI: BK-0066 Hold(Menunggu DP) -> klik "Verifikasi & Catat" -> Terkonfirmasi + DP.
gate.sh HIJAU 38/38 (0 FAIL, 0 SKIP). -->
- [P0] endpoint: /api/public/booking/config
- [P0] endpoint: /api/public/booking/search
- [P0] endpoint: /api/public/booking/quote
- [P0] endpoint: /api/public/booking/submit
- [P0] endpoint: /api/public/booking/{code}
- [P0] endpoint: /api/public/booking/{code}/proof
- [P0] endpoint: /api/public/booking/{code}/cancel
- [P0] endpoint: /api/public/booking/lookup
- [P0] endpoint: /api/bookings/payment-proofs
- [P0] endpoint: /api/bookings/{booking_id}/proofs/{proof_id}/verify
- [P0] endpoint: /api/bookings/{booking_id}/proofs/{proof_id}/reject
- [P0] endpoint: /api/bookings/{booking_id}/approve-hold
- [P0] endpoint: /api/transfer-routes
- [P0] page: features/public/BookingWizard
- [P0] page: features/public/BookingStatus
- [P0] page: components/public/booking/BookingSearchForm
- [P0] page: components/public/booking/UnitOptionCard
- [P0] page: components/public/booking/QuoteBreakdown
- [P0] page: components/public/booking/PaymentInstructions
- [P0] page: components/app/PaymentProofsPanel
- [P0] page: components/app/BookingFlowPanel
- [P0] page: components/app/TransferRoutesPanel
- [P0] collection: payment_proofs
- [P0] collection: transfer_routes
- [P0] script: scripts/test_core_booking_v1.py
- [P0] script: scripts/migrate_booking_v1.py
- [P0] script: scripts/guardrails/verify_pricing_integrity.py
- [P0] script: scripts/guardrails/verify_booking_public.py
- [P0] script: scripts/guardrails/verify_string_bounds.py
- [P0] script: scripts/guardrails/selftest_booking_guards.py
- [P0] doc: docs/03_DATA_MODEL.md
- [P0] doc: docs/04_API_CONTRACT.md
- [P0] doc: docs/05_NAVIGATION_MAP.md
- [P1] doc: memory/GATE_RECEIPT.md

---

### PHASE BOOKING-V2 — Navbar publik dirapikan + Promo di wizard + Laporan Hold Hangus (2026-08-12) (status: DONE)
<!-- BOOKING-V2 SELESAI & TERVERIFIKASI 2026-08-12.
(1) STORY H menutup sisa verifikasi UI BOOKING-V1 (§0.2 HANDOFF): toggle "Tayang di web" dibuktikan dua
arah di UI - unit hilang/muncul di katalog /fleet DAN di POST /public/booking/search.
(2) §0.1 navbar publik (permintaan user "terlalu ramai", lampu hijau diberikan): 14 target klik satu baris
-> 5 menu + 1 aksi utama "Pesan Online"; utilitas (Cek Pesanan/telepon/Masuk ERP) pindah ke bar pengumuman;
Tentang/Kontak ke footer; drawer ponsel dapat grup "Layanan & Bantuan"; header terukur 90,75 px (1 baris);
seluruh data-testid lama DIPINDAH bukan dihapus; /lp/:slug tetap ringkas (INV-LP). SSOT docs/05 §1a.
(3) Section beranda "Pesan online dalam 3 langkah" + chip "Lanjutkan pesanan BK-00xx" (localStorage;
token mati 404 dibuang sendiri) - jaring pengaman agar tamu yang baru transfer menemukan halaman unggah bukti.
(4) Daftar promo bisa diklik di wizard: POST /api/public/booking/promos menghitung ULANG subtotal di server
lalu menilai tiap promo dgn promos.evaluate yang sama seperti checkout; promo tak layak tetap tampil beserta
ALASANNYA. (5) Laporan "Hold Hangus": services/hold_report.py + GET /api/reports/hold-expired (+ /export CSV)
+ panel di /app/reports; angka kunci with_proof (hangus padahal bukti sudah diunggah = keterlambatan ops),
expiry_rate (indikasi hold_hours terlalu pendek), recovered (tamu memesan lagi); tombol Hubungi via wa.me.
(6) Katalog 11 bandara untuk tambah-cepat rute + tombol "Arah balik" (tarif per tipe unit tersalin; TARIF
tetap diisi pemilik - server menolak rute tanpa tarif).
Bug ditutup: BUG-0120 (kode rute otomatis simetris DPS-DPS -> arah balik mustahil).
Guardrail: INV-BOOK-02 statik diperluas ke SEMUA skema yang diimpor router publik (self-test MERAH<->HIJAU).
Bukti: gate.sh HIJAU (0 FAIL, 0 SKIP) - POC test_core_booking_v1.py 74/74 - ux_audit --strict 0/0 -
testing agent iteration_83.json & iteration_84.json (backend 14/14, frontend 100%, 0 bug). -->
- [P0] endpoint: /api/public/booking/promos
- [P0] endpoint: /api/reports/hold-expired
- [P0] endpoint: /api/reports/hold-expired/export
- [P0] page: components/public/booking/PromoPicker
- [P0] page: components/public/ResumeBookingChip
- [P0] page: components/public/BookingStepsSection
- [P0] page: components/app/HoldExpiredReport
- [P0] page: components/public/PublicLayout
- [P0] page: components/app/TransferRoutesPanel
- [P0] script: scripts/guardrails/verify_booking_public.py
- [P0] doc: docs/05_NAVIGATION_MAP.md
- [P0] doc: docs/04_API_CONTRACT.md
- [P1] doc: memory/GATE_RECEIPT.md
- [P1] doc: memory/BUG_REGISTRY.md

---

### PHASE UI-READABILITY (Fase 7) — Kontras kaca & tema portal + 3 halaman publik + brand RahazaTrans (2026-08-12) (status: DONE)
<!-- FASE 7 SELESAI & TERVERIFIKASI 2026-08-12. Dipicu 7 permintaan user dari 4 screenshot.
(1) KONTRAK KETERBACAAN: .glass-modal tidak lagi memaku hsla(0 0% 100%/.94) !important untuk semua mode
(di mode gelap --foreground putih -> teks putih di panel putih); .glass-3d::before refraksi diturunkan ke
--refraction-opacity .22 + --refraction-blend (soft-light/normal) + --refraction-mask (hanya tepi atas);
kelas baru .glass-on-hero (base hsla(var(--card)/.93)) & .hero-scrim untuk surface di atas foto; token
--glass-edge/--glass-edge-soft diturunkan di .dark. SSOT: docs/06_UIUX_STANDARDS.md section 6.
(2) TEMA UNTUK KONTEN YANG DI-PORTAL: ThemeContext memasang data-surface + data-theme di <html> (Radix
mem-portal Dialog/Select ke <body>, di luar div bertema) dan MEMBERSIHKANNYA saat unmount supaya konsol
ERP tidak ketularan; public-themes.css diberi selector kembar [data-surface][data-theme].dark untuk 4
preset karena ".dark X" hanya cocok untuk DESCENDANT.
(3) HALAMAN PUBLIK DIPERKAYA dari DATA NYATA (0 mock): /fleet (quick-action bar unit/tipe/DP, filter tipe,
perbandingan tipe + tarif dari /public/booking/config, standar unit, estimator, rute bandara tarif FLAT,
promo, FAQ, CTA), /destinations (fun fact dari highlights+best_time+itinerary, paket wisata price_from,
narasi, FAQ dirangkum dari destinations[].faqs, CTA), /trip-calculator (cara kerja, empty-state berisi
tarif nyata yang bisa diklik, perkiraan DP, perbandingan tipe, rute flat, promo, FAQ harga, CTA).
(4) BookingWizard menerima query "route" -> kartu rute bandara deep-link ke rute yang tepat.
(5) RENAME BRAND -> RahazaTrans di 30 berkas FE/BE + seed_data.py + dokumen DB (settings.company_info,
booking_flow.payment.bank_accounts[].holder, articles, landing_pages) + halo@rahazatrans.id.
Bug ditutup: BUG-0121 (gradient token triplet HSL membuang seluruh background-image -> CTA blog kosong),
BUG-0122 (kaca dipaku putih + refraksi screen menyapu label), BUG-0123 (tombol close dialog jadi bulatan
warna), BUG-0124 (konten portal tidak mewarisi tema - ditemukan testing agent), BUG-0125 (custom property
menyusun token tema di :root -> membeku pada tema terang), BUG-0126 (offset chat hardcode menembus header).
Guardrail baru: INV-THEME-01 (verify_theme_contrast.py, 290 cek) + selftest_theme_contrast.py (7 mutasi
MERAH<->HIJAU), ter-wire di gate.sh & terdaftar di memory/INVARIANTS.md.
Bukti: gate.sh HIJAU 40/40 (0 FAIL, 0 SKIP) - ux_audit --strict 0 ERROR 0 WARN - testing agent
iteration_86.json (menemukan BUG-0124), iteration_87.json (100%), iteration_88.json (0 bug: /booking
end-to-end BK-0068 + promo GATHERING500, STORY H dua arah, panel Hold Hangus cocok dengan API). -->
- [P0] page: components/public/CtaBand
- [P0] page: components/public/VehicleTypeCompare
- [P0] page: components/public/AirportRouteStrip
- [P0] page: components/public/PromoStrip
- [P0] page: components/public/PackageStrip
- [P0] page: components/public/DestinationFacts
- [P0] page: components/public/FaqBlock
- [P0] page: features/public/Fleet
- [P0] page: features/public/Destinations
- [P0] page: features/public/TripCalculator
- [P0] page: features/public/BlogDetail
- [P0] page: components/public/ChatWidget
- [P0] script: scripts/guardrails/verify_theme_contrast.py
- [P0] script: scripts/guardrails/selftest_theme_contrast.py
- [P0] invariant: INV-THEME-01
- [P0] doc: docs/06_UIUX_STANDARDS.md
- [P1] doc: memory/BUG_REGISTRY.md
- [P1] doc: memory/GATE_RECEIPT.md

---

### PHASE CMS-CW2 — CMS-05…CMS-09 + defect A1–A3  (status: ACTIVE)
<!-- Menutup SISA CMS_REVIEW_AND_ENHANCEMENT_PLAN.md. Backend sebagian besar sudah ada dari sesi
sebelumnya; sesi 2026-08-17 menyelesaikan WIRING FRONTEND + UI admin + SSOT + guardrail.
Keputusan pemilik: terjemahan English MANUAL (AI OFF), URL publik bahasa Inggris, WA/Ads/GA4 MOCK. -->
- [P0] endpoint: /api/content/{resource}/{item_id}/preview-token
- [P0] endpoint: /api/content/{resource}/translate
- [P0] endpoint: /api/content/meta/i18n
- [P0] endpoint: /api/content/meta/promo-options
- [P0] endpoint: /api/content/analytics/top
- [P0] endpoint: /api/reviews/summary
- [P0] endpoint: /api/reviews/requests
- [P0] endpoint: /api/reviews/eligible-bookings
- [P0] endpoint: /api/reviews/pending
- [P0] endpoint: /api/reviews/{testimonial_id}/moderate
- [P0] endpoint: /api/public/packages
- [P0] endpoint: /api/public/packages/{slug}
- [P0] endpoint: /api/public/promos
- [P0] endpoint: /api/public/content-view
- [P0] endpoint: /api/public/reviews/{token}
- [P0] page: features/public/Packages
- [P0] page: features/public/PackageDetail
- [P0] page: features/public/Promos
- [P0] page: features/public/ReviewSubmit
- [P0] page: components/public/LanguageSwitch
- [P0] page: components/public/PreviewBanner
- [P0] page: components/public/ArticleBody
- [P0] page: components/cms/RichTextEditor
- [P0] page: components/cms/PublishControls
- [P0] page: components/cms/TranslationFields
- [P0] page: components/app/ReviewModerationPanel
- [P0] page: components/app/ContentAnalyticsPanel
- [P0] page: features/app/ContentManager
- [P0] collection: content_previews
- [P0] collection: review_requests
- [P0] collection: content_stats
- [P0] script: scripts/test_core_cms_cw2.py
- [P0] doc: docs/03_DATA_MODEL.md
- [P0] doc: docs/04_API_CONTRACT.md
- [P0] doc: docs/05_NAVIGATION_MAP.md
- [P0] doc: docs/10_CODEBASE_MAP.md
- [P1] doc: memory/BUG_REGISTRY.md
- [P1] doc: memory/test_credentials.md
- [P1] doc: memory/GATE_RECEIPT.md
