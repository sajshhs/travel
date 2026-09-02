#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
  - task: "E28 RBAC-CAL-01: section 'calendar' owner/ops_admin + require_section di endpoint kalender"
    implemented: true
    working: true
    file: "backend/permissions_config.py + backend/routers/departures.py + backend/routers/bookings.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: false
        -agent: "testing"
        -comment: "iter-72 (F-G.2): driver bisa membuka /app/calendar. Diverifikasi main agent lewat curl: driver mendapat HTTP 200 pada /api/departures/attention, /api/bookings/calendar, /api/bookings/calendar/export -> kebocoran nyata juga di API, bukan hanya UI."
        -working: true
        -agent: "testing"
        -comment: "iter-73 (ronde 3): DIVERIFIKASI LULUS. driver 403 pada 3 endpoint kalender; owner & ops 200 (ekspor benar-benar mengembalikan xlsx & pdf). 10/10 cek kalender lulus."
        -working: true
        -agent: "main"
        -comment: "SECTION_ACCESS kini punya 'calendar' {owner,ops_admin} + 'driver-workspace' + 'quotations' + 'inbox' (2 terakhir ditemukan guardrail baru sebagai celah SSOT) + SECTION_ALIASES {auditlog->audit}. Endpoint kalender memakai Depends(require_section('calendar')). Hasil probe: driver 403 x3, owner & ops 200 x3. Perlu regresi: ekspor PDF/Excel kalender owner tetap terunduh, /api/bookings biasa tetap 200 utk semua peran."

  - task: "E28 RBAC-SCOPE: cakupan data row-level driver (bookings & drivers) via services/rbac_scope.py"
    implemented: true
    working: true
    file: "backend/services/rbac_scope.py + backend/routers/bookings.py + backend/routers/drivers.py + backend/routers/driver.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: true
        -agent: "testing"
        -comment: "iter-73: DIVERIFIKASI LULUS. driver 3 booking vs owner 9; driver 1 profil sopir vs owner 2; 403 saat membuka booking/sopir milik orang lain; /api/driver/{my-trips,tasks,summary} tetap 200 (tidak over-block)."
        -working: true
        -agent: "main"
        -comment: "Sebelum: driver lihat 8/8 booking + 2/2 sopir. Sesudah: 3 booking (miliknya) + 1 profil sopir; detail booking/sopir milik orang lain -> 403; /api/driver/{my-trips,tasks,summary} tetap 200. Fail-closed: driver tanpa dokumen drivers terpaut -> sentinel '__tanpa_driver__' (bukan lihat semua). PENTING utk diregresi: owner/ops_admin TIDAK boleh terkena penyempitan (owner tetap 9 booking, 2 sopir) dan Dispatch/Kalender/Booking milik ops tetap penuh."

  - task: "E28 Guardrail INV-RBAC-04/05 (statik) + INV-RBAC-06 (runtime) + wiring gate.sh"
    implemented: true
    working: true
    file: "scripts/guardrails/verify_rbac_guards.py + scripts/guardrails/verify_rbac_runtime.py + scripts/gate.sh"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "INV-RBAC-04 sinkron 2-arah FE ROLE_MENU_ALLOWLIST <-> BE SECTION_ACCESS (langsung mengimpor matriks backend, bukan daftar hardcoded) -> saat dibuat langsung menemukan 2 celah nyata (inbox, quotations). INV-RBAC-05 anchor pemanggilan penyaring row-level (regex `await <fn>(`; versi lemah `needle in src` sempat lolos palsu karena baris import). INV-RBAC-06 runtime membuktikan perilaku (403/200 + cakupan data). Self-test: injeksi pelanggaran -> MERAH 3 (statik) & MERAH 1 (runtime, Depends tertukar) -> revert -> HIJAU."
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
  - task: "E28 RoleGuard: driver tidak boleh membuka /app/calendar + UX pesan akses ditolak"
    implemented: true
    working: true
    file: "frontend/src/config/navigationConfig.js + frontend/src/components/app/RoleGuard.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: false
        -agent: "testing"
        -comment: "iter-72 F-G.2 FAIL: 'Driver can view full calendar page with all features'."
        -working: "NA"
        -agent: "main"
        -comment: "'calendar' dicabut dari ROLE_MENU_ALLOWLIST.driver (SSOT docs/05_NAVIGATION_MAP.md §3 kini punya baris eksplisit 'Kalender Keberangkatan | ✅ | ✅ | ❌'). RoleGuard kini juga menampilkan toast 'Akses ditolak' + mengalihkan ke beranda peran (driver -> /app/driver-workspace, bukan /app/dashboard). BELUM diuji testing agent -> mohon verifikasi ronde 3."
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

user_problem_statement: |
  Lanjutkan development repo Rahaza Travel ERP (github.com/manabavanama/travel). Titik henti sesi
  sebelumnya: menambahkan badge "bentrok" pada day-list Kalender Keberangkatan, lalu verifikasi
  visual menunjukkan CONFLICT BANNER: False dan CONFLICT-MARKED CHIPS: 0 (banner bentrok tidak
  pernah muncul).

  Investigasi (POC /app/test_core_conflict.py, API nyata) membuktikan itu BUKAN bug UI: backend
  sudah mengunci INV-4 di semua jalur tulis (POST /bookings -> 400, reschedule -> 400) sehingga
  tidak ada data bentrok armada. POC justru menemukan 4 celah nyata yang tidak terlihat di kalender.

  Lingkup fase ini (disetujui user "lanjut A-D", perawatan = tolak keras):
  A. POST/PATCH /api/maintenance WAJIB menolak (400) window perawatan yang menabrak keberangkatan
     aktif (menegakkan INV-21 dua arah).
  B. /api/bookings/calendar mengembalikan vehicle_id/driver_id/driver_name; lapisan risiko dihitung
     backend via GET /api/departures/attention (services/attention.py) memakai vehicle_id (bukan
     vehicle_name) dan hanya status aktif untuk bentrok armada.
  C. Banner "bentrok" lama diganti panel "Perlu Perhatian" (8 kelas risiko) + chip filter + badge di
     sel bulan/timeline minggu/day-list + alert di panel detail. DepartureCalendar.jsx dipecah jadi
     8 modul < 500 baris (memperbaiki FAIL validate_compliance).
  D. Verifikasi: bash scripts/gate.sh HIJAU 22/22 + testing_agent_v3.

  === FASE E28 (sesi lanjutan, 2026-08-10) ===
  Titik henti sebelumnya: iteration_72 (ronde 2 frontend E27) SELESAI dgn 27/28 lulus, menyisakan
  1 temuan CRITICAL yang BELUM ditangani: F-G.2 "driver@demo.local bisa membuka /app/calendar".

  Investigasi menunjukkan itu bug NYATA dan berlapis-3 (bukan sekadar RoleGuard lupa dipasang):
  (1) ROLE_MENU_ALLOWLIST.driver memuat "calendar" -> canAccess() meloloskan RoleGuard;
  (2) backend permissions_config.SECTION_ACCESS TIDAK punya section "calendar" -> require_section
      tak terpakai, endpoint kalender hanya ber-auth; driver terbukti dapat HTTP 200 via curl pada
      /api/departures/attention, /api/bookings/calendar, /api/bookings/calendar/export;
  (3) guardrail INV-RBAC-03 memakai daftar FORBIDDEN hardcoded yang tak pernah menyebut modul baru.

  Audit lanjutan peran driver menemukan kelas bug KEDUA (RBAC-SCOPE): GET /api/bookings sebagai
  driver mengembalikan 8/8 booking (termasuk trip sopir lain + customer_name + total/paid amount)
  dan GET /api/drivers mengembalikan seluruh sopir + telepon, padahal SSOT
  docs/05_NAVIGATION_MAP.md §3 menulis "trip miliknya" / "profil sendiri".

  Lingkup E28 (disetujui user): (A) tutup RBAC-CAL-01 3 lapis + audit modul lain,
  (B) tutup RBAC-SCOPE via services/rbac_scope.py, (C) guardrail baru INV-RBAC-04/05/06 dgn
  self-test MERAH<->HIJAU, (D) backlog P1: warning Recharts + duplikasi blok gate.sh,
  (E) gate.sh HIJAU penuh + verifikasi testing_agent_v3.

backend:
  - task: "INV-21 dua arah: POST /api/maintenance tolak 400 bila window perawatan menabrak keberangkatan aktif"
    implemented: true
    working: true
    file: "backend/routers/maintenance.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: false
        -agent: "main"
        -comment: "POC test_core_conflict.py KELAS 3 membuktikan celah: POST /maintenance dgn start_date/end_date menutupi window booking confirmed LOLOS (200) -> melanggar INV-21."
        -working: true
        -agent: "main"
        -comment: "Fix: _blocking_window() + _assert_no_departure_clash() dibungkus vehicle_lock (anti-TOCTOU, mutex sama dgn jalur booking). POC ulang: ditolak 400 'Perawatan bertabrakan dengan keberangkatan aktif: BK-0002...'. gate.sh HIJAU 22/22."

  - task: "INV-21 dua arah pada PATCH /api/maintenance/{id} (nilai efektif rec+updates)"
    implemented: true
    working: true
    file: "backend/routers/maintenance.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "PATCH kini menghitung eff_status/eff_start/eff_end lalu re-validasi dlm vehicle_lock (pola R6-1 subcharters)."
        -working: false
        -agent: "testing"
        -comment: "iter-71 melaporkan CRITICAL: PATCH ke window bentrok mengembalikan 200, bukan 400."
        -working: true
        -agent: "main"
        -comment: "FALSE POSITIVE terbukti. backend_test.py BACKEND 6 membuat perawatan pada vehicles[0], lalu BACKEND 9a mem-PATCH ke window booking milik ARMADA LAIN (BK-0009 = 'Smoke Vehicle') -> memang TIDAK ada tabrakan -> 200 BENAR. Verifikasi presisi via scripts/verify_patch_inv21.py (armada DIPAKSA sama): PATCH ke window booking aktif -> 400 'Perawatan bertabrakan dengan keberangkatan aktif: BK-0009', window perawatan TIDAK berubah (penolakan atomik), PATCH cost saja -> 200, dan skenario armada-berbeda -> 200 (benar). SEMUA CEK LOLOS."

  - task: "GET /api/departures/attention (services/attention.py) - 8 kelas risiko keberangkatan"
    implemented: true
    working: true
    file: "backend/routers/departures.py + backend/services/attention.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: true
        -agent: "main"
        -comment: "Kelas: vehicle_conflict, driver_conflict, maintenance_conflict, hold_expired, hold_expiring, no_driver, pending_request, unpaid_soon. Mendukung ?month=YYYY-MM ATAU ?start&end. Diverifikasi manual: month=2026-08 -> total 5, by_type driver_conflict=2, no_driver=2, pending_request=2, hold_expiring=1, unpaid_soon=1. Butuh regresi: auth wajib (401 tanpa token), month invalid tidak 5xx, rentang start>end di-normalkan."

  - task: "Projection /api/bookings/calendar diperkaya (vehicle_id, driver_id, driver_name, hold_expires_at, source, requested_vehicle_type, pax)"
    implemented: true
    working: true
    file: "backend/routers/bookings.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
        -working: true
        -agent: "main"
        -comment: "Diverifikasi manual: field baru muncul di respons. Perlu regresi bahwa endpoint tetap 200 dan urut start_datetime."

  - task: "Seed demo skenario risiko (2 permintaan pending publik, bentrok sopir pending vs confirmed, hold DP mendekat)"
    implemented: true
    working: true
    file: "scripts/seed_data.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "BK-0006/BK-0007 pending (source=public), BK-0007 diberi sopir yang beririsan dgn BK-0005, BK-0008 hold dgn hold_expires_at +4 jam. verify_data_integrity 35/35 PASS (INV-1/3/4/10/21 aman) - sengaja TIDAK menyeed bentrok armada/perawatan karena melanggar invariant."

  - task: "Guardrail: verify_schema FK bookings.vehicle_id boleh kosong utk status pending/draft/cancelled (selaras docs/03_DATA_MODEL.md)"
    implemented: true
    working: true
    file: "scripts/verify_schema.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Aturan lama menandai vehicle_id wajib tanpa syarat -> MERAH begitu ada 1 permintaan publik nyata (routers/public.py memang menulis vehicle_id=None). Ditambahkan REQUIRED_EXEMPT ber-predikat + jejak '[n dikecualikan: alasan]'. Bukan bypass: SSOT doc menulis 'nullable saat status=pending'."

frontend:
  - task: "Panel 'Perlu Perhatian' di Kalender Keberangkatan (ganti banner bentrok yang selalu 0)"
    implemented: true
    working: true
    file: "frontend/src/components/app/calendar/AttentionPanel.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: true
        -agent: "main"
        -comment: "Screenshot verifikasi: panel tampil, total=5, 5 chip risiko, 4 item preview + 'Lihat 1 lainnya'. Empty state hijau 'Semua aman' saat 0 risiko. Butuh regresi UI oleh testing agent."

  - task: "Chip filter risiko menyaring kalender + tombol 'Saring di kalender' + 'Hapus saringan'"
    implemented: true
    working: true
    file: "frontend/src/features/app/DepartureCalendar.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: true
        -agent: "main"
        -comment: "Screenshot: klik chip 'Bentrok sopir' -> dc-month-total berubah dari 8 menjadi 2 keberangkatan, data-active=1."

  - task: "Penanda risiko pada sel bulan (data-risk/data-severity/data-conflict), timeline minggu, dan day-list"
    implemented: true
    working: true
    file: "frontend/src/components/app/calendar/CalendarMonthGrid.jsx + CalendarWeekTimeline.jsx + DayListPanel.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: true
        -agent: "main"
        -comment: "Screenshot: RISK-MARKED CHIPS=5, CONFLICT-MARKED CHIPS=2 (sebelumnya 0). Timeline minggu belum diverifikasi visual -> minta testing agent cek view Minggu."

  - task: "Alert risiko + tautan 'buka <KODE>' pada panel detail keberangkatan"
    implemented: true
    working: true
    file: "frontend/src/components/app/calendar/DepartureDetailPanel.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: true
        -agent: "main"
        -comment: "Screenshot: dc-detail-risks tampil 'Perlu perhatian - Mendesak' + rincian per risiko. Tautan dc-detail-related-<KODE> (lompat ke booking bentrok) belum diuji klik."

  - task: "Refactor DepartureCalendar.jsx 754 -> 460 baris + 8 modul components/app/calendar/* (semua < 500 baris)"
    implemented: true
    working: true
    file: "frontend/src/features/app/DepartureCalendar.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: true
        -agent: "main"
        -comment: "validate_compliance FAIL 1 -> FAIL 0; ux_audit --strict ERROR 0. Regresi WAJIB: semua fitur lama masih jalan (nav bulan/minggu, Hari ini, cari, filter status/armada, mode warna, ekspor PDF/Excel + rentang khusus + kelompok per armada, buat/edit/jadwal-ulang/setujui/tolak/bayar/batal, tugaskan sopir)."

  - task: "Daftar item panel 'Perlu Perhatian' mengikuti chip filter risiko (perbaikan UX pasca-verifikasi)"
    implemented: true
    working: true
    file: "frontend/src/components/app/calendar/AttentionPanel.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: false
        -agent: "main"
        -comment: "Ditemukan sendiri saat verifikasi tautan booking terkait: chip 'Bentrok sopir' hanya menyaring KALENDER, sedangkan daftar item panel tetap menampilkan semua risiko -> klik 'Tindak lanjuti' pertama membuka booking yang tidak relevan (BK-0004) sehingga tautan dc-detail-related tidak muncul."
        -working: true
        -agent: "main"
        -comment: "Daftar kini tersaring (shown = items.filter(risk_types includes filter)) + baris konteks dc-attention-scope 'Menampilkan 2 dari 6 keberangkatan - saringan Bentrok sopir' + tombol 'Lihat n lainnya' memakai jumlah tersaring. Terverifikasi: saring bentrok sopir -> [BK-0005, BK-0007]; buka BK-0005 -> tautan 'buka BK-0007' -> pindah ke BK-0007 dgn alert risiko tampil."

  - task: "Day-list muncul saat klik sel tanggal (dilaporkan MEDIUM oleh iter-71)"
    implemented: true
    working: true
    file: "frontend/src/components/app/calendar/DayListPanel.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
        -working: false
        -agent: "testing"
        -comment: "iter-71: [data-testid='dc-daylist'] tidak ditemukan setelah klik sel kalender."
        -working: true
        -agent: "main"
        -comment: "FALSE POSITIVE (artefak selektor). Selektor [data-testid^='dc-cell-']:has([data-testid^='dc-event-']) + .click() mengeklik TITIK TENGAH sel yang tepat berada di atas chip event -> chip men-stopPropagation dan membuka panel DETAIL (perilaku benar), bukan day-list. Verifikasi ulang dgn klik area nomor tanggal: dc-daylist tampil, 2 item, badge dc-daylist-riskcount '1 perlu perhatian', 1 item ber-badge risiko; klik chip event -> dc-detail; dc-detail-back -> dc-daylist kembali."

  - task: "E28 Drift 2 penjaga RBAC frontend (AppShell vs RoleGuard) disatukan di lib/accessControl.js"
    implemented: true
    working: true
    file: "frontend/src/lib/accessControl.js + frontend/src/components/app/AppShell.jsx + frontend/src/components/app/RoleGuard.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: false
        -agent: "main"
        -comment: "DITEMUKAN SENDIRI saat pra-cek browser: setelah 'calendar' dicabut, driver memang diblokir TAPI dialihkan ke /app/dashboard tanpa toast — perbaikan UX di RoleGuard tak pernah jalan karena AppShell.jsx punya guard RBAC terpusat berbasis path yang dieksekusi LEBIH DULU (logika terduplikasi)."
        -working: true
        -agent: "main"
        -comment: "Perilaku penolakan dipindah ke SSOT frontend/src/lib/accessControl.js (isDenied/roleHome/useDeniedNotice); AppShell + RoleGuard sama-sama memakainya. Hasil: /app/calendar & /app/settings sebagai driver -> dialihkan ke /app/driver-workspace + toast 'Akses ditolak'. Anti-regresi: guardrail INV-RBAC-01 kini juga memastikan KEDUA file mengimpor @/lib/accessControl."
        -working: true
        -agent: "testing"
        -comment: "iter-73 F1.2/F1.2b: DIVERIFIKASI LULUS (redirect ke /app/driver-workspace + toast Bahasa Indonesia)."

  - task: "E28 Backlog P1: warning Recharts width/height -1 (verifikasi TUTUP + anti-regresi ux_audit E4)"
    implemented: true
    working: true
    file: "scripts/ux_audit.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Tidak tereproduksi: console bersih di /app/dashboard (Ringkasan + BI Cockpit), /app/reports, /app/finance (6 tab), /app/crm (4 tab). Semua <ResponsiveContainer> sudah memakai initialDimension + parent tinggi tetap. Ditambah aturan E4 (ERROR) di ux_audit --strict agar tidak bisa kembali."
        -working: true
        -agent: "testing"
        -comment: "iter-73 F5.1-F5.4: DIVERIFIKASI 0 error / 0 warning recharts di 4 halaman."

  - task: "E28b Rapikan formulir: 4 dropdown native -> SelectField seragam (shadcn Select)"
    implemented: true
    working: true
    file: "frontend/src/components/shared/SelectField.jsx + features/app/DepartureCalendar.jsx + components/app/calendar/DepartureDetailPanel.jsx + features/public/BookingRequest.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
        -working: true
        -agent: "testing"
        -comment: "iter-74 (ronde 4): DIVERIFIKASI LULUS 100% (38/38). dc-filter-status 7 opsi & menyaring 9->6->9; dc-filter-vehicle 6 opsi & menyaring 9->3->9; dc-assign-select 3 opsi termasuk -opt-none + validasi bentrok jalan; br-vehicle-type 5 opsi & BK-0016 tersimpan requested_vehicle_type='elf'. Konsistensi visual terukur: tinggi 36px & font 13px SAMA dengan input di sebelahnya. Tidak ada regresi RBAC/kalender. Catatan LOW: panel ekspor tidak tertutup dgn Escape."
        -working: true
        -agent: "main"
        -comment: "4 native <select> diganti: dc-filter-status, dc-filter-vehicle, dc-assign-select, br-vehicle-type. Dibungkus komponen baru SelectField (menangani larangan Radix atas SelectItem value=\"\" via sentinel internal + memberi data-testid <testId>-opt-<slug> pada setiap opsi). PENTING utk otomasi: kini KLIK TRIGGER lalu KLIK ITEM (bukan select_option). ux_audit WARN turun 6->3, W2 = 0 (aturan W2 juga diperbaiki agar tidak menandai baris komentar). Verifikasi manual browser: filter status 9->6->9 keberangkatan, opsi armada 6, dc-assign-select menampilkan 3 opsi + tombol Tugaskan aktif + validasi bentrok sopir tetap jalan ('Driver bentrok dengan booking aktif: BK-0003'), form publik /booking submit sukses -> BK-0016 tersimpan dgn requested_vehicle_type='alphard' (data lalu di-reseed). CATATAN LINGKUNGAN: modul BookingRequest sempat tidak ikut ter-recompile oleh HMR -> perlu `supervisorctl restart frontend` (bukan bug kode)."

  - task: "E28b Panel ekspor kalender bisa ditutup dgn Escape + atribut a11y (tindak lanjut LOW iter-74)"
    implemented: true
    working: true
    file: "frontend/src/components/app/calendar/CalendarExportPanel.jsx"
    stuck_count: 0
    priority: "low"
    needs_retesting: false
    status_history:
        -working: false
        -agent: "testing"
        -comment: "iter-74 (LOW): 'Export panel backdrop does not dismiss with Escape key'."
        -working: true
        -agent: "main"
        -comment: "Ditambahkan listener keydown Escape (aktif hanya saat panel terbuka, dibersihkan saat unmount) + role='dialog' + aria-label + aria-expanded/aria-haspopup pada tombol pemicu. Diverifikasi browser: buka [data-testid='dc-export-panel'] -> tekan Escape -> panel hilang (jumlah elemen 1 -> 0)."

  - task: "E28b Bukti jalur SUKSES tugaskan sopir lewat dropdown baru"
    implemented: true
    working: true
    file: "frontend/src/components/app/calendar/DepartureDetailPanel.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "iter-74 hanya membuktikan jalur PENOLAKAN (bentrok sopir). Main agent melengkapi: pilih 'Driver Satu' pada BK-0004 (10 Agu 14:00, tidak beririsan dgn BK-0005/0007) -> tersimpan. Bukti API: BK-0004 driver_id=drv_..., driver_name='Driver Satu'. Data lalu di-reseed agar demo kembali bersih. Catatan: heuristik pencarian kata 'bentrok' di body halaman TIDAK dapat dipakai sebagai penanda gagal, karena daftar panel Perlu Perhatian memang memuat teks 'Bentrok sopir'."

  - task: "FASE F1 (E29) POC Marketing & Ads: vault rahasia + object storage (video) + outbox konversi + blok landing + peran marketing_admin"
    implemented: true
    working: true
    file: "backend/services/secrets_vault.py + media_store.py + conversions.py + landing_blocks.py + scripts/test_core_ads.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "POC dijalankan sendiri (bukan asumsi): python scripts/test_core_ads.py -> 62/62 LULUS. Bukti nyata: (1) AES-256-GCM + mask, respons publik tidak memuat plaintext maupun ciphertext, input kosong mempertahankan rahasia, sentinel __HAPUS__ bekerja; (2) object storage Emergent: gambar 1MB & VIDEO 12MB unggah+unduh identik SHA-256 ~0,5s, .exe & gambar >10MB ditolak; (3) outbox konversi: 8 enqueue paralel event_id sama -> 1 dokumen per provider (unique index), payload Meta CAPI & Google Data Manager sesuai skema resmi (SHA-256 PII, IDR integer, event_id=ID bisnis, test_event_code/validateOnly hanya saat uji), kredensial kosong -> skipped berALASAN, HTTP 400 -> failed+retry -> dead setelah 5 attempt, token tidak tersimpan di respons; (4) 16 tipe blok landing + sanitasi XSS (script/iframe beserta isinya dibuang) + aturan layak-terbit (blok konversi wajib, poster video wajib) + aset terhapus tidak jadi tautan mati; (5) peran marketing_admin sinkron FE<->BE, INV-RBAC-01..05 HIJAU 177 cek, gate.sh HIJAU 23/23. BELUM diuji testing agent karena belum ada UI (Fase F2)."

  - task: "FASE F2 (E29): halaman Integrasi API (Meta/Google/WhatsApp) + pelacakan situs publik (Pixel/gtag + consent) + Kesehatan Pelacakan"
    implemented: true
    working: true
    file: "backend/routers/marketing.py + frontend/src/features/app/Integrations.jsx + TrackingHealth.jsx + frontend/src/lib/tracking.js + components/public/ConsentBanner.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: true
        -agent: "main"
        -comment: "Diverifikasi sendiri via curl + browser: (1) RBAC — owner & marketing_admin 200, ops_admin & driver 403 pada /api/integrations/config, /api/tracking/health, /api/wa/config, PATCH integrasi; (2) masking — token disimpan lalu respons hanya '••••••9999', tidak ada plaintext maupun ciphertext (_enc) yang bocor; (3) /api/public/tracking-config bisa diakses tanpa login TAPI hanya memuat ID publik (guardrail INV-AUTH-01 sempat MERAH dan diperbaiki dengan allowlist ber-justifikasi); (4) consent gate — banner tampil, sebelum izin window.fbq=false & tag Google belum dimuat, setelah izin fbevents.js + gtag/js dimuat dan dataLayer mencatat consent default:denied -> update:granted; (5) event funnel — PageView/page_view tepat 1x per URL, ViewContent + view_item (value 1500000) di detail armada, dengan pengaman anti-ganda. DUA BUG DITEMUKAN & DIPERBAIKI sendiri: (a) dataLayer harus menerima objek `arguments` (versi array membuat event tercatat KOSONG); (b) ConsentBanner memakai setTimeout sehingga banner tak muncul saat fetch config lambat -> diganti mekanisme notifikasi onTrackingReady. Provider di-reset ke MOCK/nonaktif setelah uji. BELUM diuji testing agent."

metadata:
  created_by: "main_agent"
  version: "2.1"
  test_sequence: 74
  run_ui: true

test_plan:
  current_focus:
    - "SELESAI E28: RBAC-CAL-01 + RBAC-SCOPE + guardrail INV-RBAC-04/05/06 (iter-73 100%, 75/75)"
    - "SELESAI E28b: 4 dropdown native -> SelectField seragam + Escape pada panel ekspor (iter-74 100%, 38/38)"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: |
      Repo di-restore dari github.com/manabavanama/travel (repo 'rahaza' kosong). Deps terinstal,
      services RUNNING, DB di-seed. bash scripts/gate.sh = HIJAU 22/22, 0 SKIP
      (memory/GATE_RECEIPT.md). Kredensial: owner@demo.local / ops@demo.local / driver@demo.local,
      password demo12345 (lihat memory/test_credentials.md).

      Mohon uji (Bahasa Indonesia untuk pesan UI):
      BACKEND
      1. GET /api/departures/attention?month=YYYY-MM dan ?start&end -> 200, struktur
         {period,summary{total,high,medium,by_type},meta[],items[{booking_id,code,severity,risk_types,risks[]}]}.
         Tanpa Authorization -> 401/403. month='abcd'/'2026-13' -> TIDAK boleh 5xx.
      2. POST /api/maintenance dgn start_date/end_date yang menutupi window booking AKTIF -> 400
         (pesan berisi kode booking). Window BEBAS -> 201/200. status='done' + window bertabrakan ->
         boleh lolos (tidak memblok availability).
      3. PATCH /api/maintenance/{id}: geser start_date/end_date ke window booking aktif -> 400;
         ubah cost/note saja -> 200 (tidak boleh false-reject).
      4. GET /api/bookings/calendar?month= -> memuat vehicle_id, driver_id, driver_name.
      5. Regresi cepat: /api/bookings (list), /api/bookings/{id}, POST /api/bookings overlap -> 400,
         reschedule overlap -> 400, /api/bookings/calendar/export?format=pdf|excel -> file terunduh.

      FRONTEND (login owner, buka /app/calendar)
      6. Panel dc-attention-panel tampil dgn dc-attention-total; chip dc-attention-chip-<type>
         menyaring kalender (dc-month-total berubah); dc-attention-clear mengembalikan.
      7. dc-attention-open-<booking_id> ('Tindak lanjuti') membuka panel detail + dc-detail-risks.
      8. Klik dc-detail-related-<KODE> berpindah ke booking yang bentrok.
      9. View Minggu (dc-view-week): blok berdampingan + ring merah pada blok berisiko; kembali ke Bulan.
      10. Regresi fitur lama kalender: dc-prev/dc-next/dc-today, dc-search, dc-filter-status,
          dc-filter-vehicle, dc-color-vehicle, dc-export-open -> dc-export-panel (scope aktif + rentang
          khusus + kelompok per armada, klik PDF & Excel), dc-cell-<tgl> -> day-list + badge risiko,
          dc-assign-select + dc-assign-save (tugaskan sopir), tombol Setujui/Tolak pada booking pending.
      11. Role ops_admin: pastikan halaman kalender tetap berfungsi. Role driver: tidak boleh bisa
          mengakses menu kalender (RoleGuard).

      CATATAN: jangan uji drag-and-drop/kamera/voice (tidak ada di fitur ini). WhatsApp real-send
      masih MOCK (by design).

    -agent: "main"
    -message: |
      RONDE 2 (setelah iter-71). Dua temuan iter-71 sudah DIINVESTIGASI dan keduanya FALSE POSITIVE
      (bukti di status_history masing-masing task):
      - "CRITICAL PATCH /api/maintenance tidak re-validasi INV-21": test membuat perawatan pada
        vehicles[0] tapi mem-PATCH ke window booking milik ARMADA LAIN -> 200 memang benar.
        Bukti presisi: `python /app/scripts/verify_patch_inv21.py` (SEMUA CEK LOLOS). Bila ingin
        menguji ulang, WAJIB pakai maintenance.vehicle_id == booking.vehicle_id.
      - "Day-list tidak tampil": selektor mengeklik titik tengah sel yang tertutup chip event
        (chip stopPropagation -> membuka DETAIL, itu perilaku benar). Klik area nomor tanggal
        (pojok kiri-atas sel) atau sel tanpa event untuk memunculkan day-list.

      SATU BUG UX NYATA ditemukan sendiri & sudah diperbaiki: daftar item panel tidak mengikuti chip
      filter. Sekarang tersaring + ada baris konteks [data-testid='dc-attention-scope'].

      MOHON UJI (FRONTEND SAJA, backend sudah 23/24 + 1 false positive):
      F-A. Chip filter menyaring DAFTAR panel: klik [data-testid='dc-attention-chip-driver_conflict']
           -> hanya item BK-0005 & BK-0007 tersisa, [data-testid='dc-attention-scope'] muncul
           ("Menampilkan 2 dari N ... saringan Bentrok sopir"); [data-testid='dc-attention-clear']
           mengembalikan daftar penuh.
      F-B. Tautan booking terkait: dari daftar tersaring, klik [data-testid^='dc-attention-open-']
           pertama -> detail BK-0005 -> klik [data-testid^='dc-detail-related-'] -> detail berganti
           ke BK-0007 dan [data-testid='dc-detail-risks'] tetap tampil.
      F-C. Day-list (pakai KLIK POJOK KIRI-ATAS sel, bukan titik tengah): [data-testid='dc-daylist']
           tampil, item ber-risiko punya [data-testid^='dc-daylist-risk-'], badge
           [data-testid='dc-daylist-riskcount'] muncul; klik chip event -> [data-testid='dc-detail'];
           [data-testid='dc-detail-back'] -> day-list lagi.
      F-D. BELUM diuji di iter-71 — ekspor UI: [data-testid='dc-export-open'] ->
           [data-testid='dc-export-panel']; cek [data-testid='dc-scope-text']; pilih
           [data-testid='dc-scope-custom'] + isi [data-testid='dc-export-start']/[dc-export-end];
           centang [data-testid='dc-export-group']; klik [data-testid='dc-export-excel'] lalu
           [data-testid='dc-export-pdf'] -> toast sukses, tanpa error konsol.
      F-E. BELUM diuji — aksi ops: buka detail booking confirmed tanpa sopir (BK-0004) ->
           [data-testid='dc-assign-select'] pilih sopir -> [data-testid='dc-assign-save'] -> toast
           sukses & risiko "Belum ada sopir" hilang utk booking itu setelah panel refresh.
           Buka BK-0006 (pending) -> pastikan [data-testid='dc-approve'] & [data-testid='dc-reject']
           ADA (cukup buka dialog Setujui, JANGAN selesaikan approve).
      F-F. BELUM diuji — empty state: [data-testid='dc-search'] ketik 'zzzzzz' ->
           [data-testid='dc-empty-hint'] + [data-testid='dc-reset-filters'] mengembalikan tampilan.
      F-G. BELUM diuji — RBAC UI: login ops@demo.local -> /app/calendar berfungsi penuh.
           login driver@demo.local -> route /app/calendar TIDAK boleh terbuka (RoleGuard mengalihkan).
      Reset data bila perlu: cd /app && python scripts/seed_data.py

    -agent: "main"
    -message: |
      RONDE 3 — FASE E28 (perbaikan temuan CRITICAL iter-72 + 1 kelas bug baru yang saya temukan sendiri).

      KONTEKS: iteration_72 sudah membuktikan seluruh fitur E27 (F-A..F-I) LULUS kecuali F-G.2
      (driver bisa membuka /app/calendar). Temuan itu NYATA dan sudah diperbaiki 3 lapis, plus saya
      menemukan kebocoran data row-level (driver melihat semua booking & sopir) yang juga sudah ditutup.
      bash scripts/gate.sh = HIJAU 23/23, 0 SKIP (memory/GATE_RECEIPT.md), termasuk gate runtime baru
      INV-RBAC-06. Kredensial: owner@demo.local / ops@demo.local / driver@demo.local, password demo12345.
      Reset data bila perlu: cd /app && python scripts/seed_data.py

      MOHON UJI (Bahasa Indonesia untuk pesan UI):

      BACKEND
      B1. RBAC kalender: login driver -> GET /api/departures/attention?month=2026-08,
          /api/bookings/calendar?month=2026-08, /api/bookings/calendar/export?month=2026-08&format=excel
          => WAJIB 403 (tiga-tiganya). Login owner DAN ops -> ketiganya WAJIB 200 (ekspor mengembalikan file).
      B2. Cakupan data driver: GET /api/bookings sebagai driver -> hanya booking dgn driver_id miliknya
          (bandingkan dgn owner yang melihat semua). GET /api/drivers sebagai driver -> TEPAT 1 baris
          (profil sendiri). GET /api/bookings/{id_milik_sopir_lain} sebagai driver -> 403.
          GET /api/drivers/{id_sopir_lain} dan /performance sebagai driver -> 403.
      B3. TIDAK BOLEH over-block: driver -> GET /api/driver/my-trips, /api/driver/tasks,
          /api/driver/summary => 200; POST /api/driver/checkin & /checkout untuk trip MILIKNYA tetap jalan.
      B4. Regresi manajemen (owner & ops): /api/bookings (list+detail), POST /api/bookings overlap -> 400,
          reschedule overlap -> 400, /api/departures/attention (struktur summary/items),
          POST+PATCH /api/maintenance INV-21 (window menabrak booking aktif -> 400; ubah cost/note -> 200),
          /api/bookings/calendar/export pdf & excel, /api/dispatch/today, /api/drivers CRUD (owner).
      B5. Tanpa Authorization -> 401/403 di endpoint kalender; month='abcd'/'2026-13' -> TIDAK boleh 5xx.

      FRONTEND
      F1. Login driver@demo.local -> coba buka /app/calendar via URL langsung: WAJIB dialihkan
          (harapan: ke /app/driver-workspace) + muncul toast 'Akses ditolak'. Menu 'Kalender
          Keberangkatan' TIDAK boleh tampil di sidebar driver. Halaman Ruang Kerja Driver tetap normal.
      F2. Driver buka /app/bookings: daftar hanya menampilkan trip miliknya (tidak ada booking sopir lain).
      F3. Login ops@demo.local -> /app/calendar tetap berfungsi PENUH: panel [data-testid='dc-attention-panel'],
          grid, tombol 'Buat Keberangkatan', chip filter [data-testid^='dc-attention-chip-'],
          [data-testid='dc-export-open'] -> panel ekspor, klik Excel & PDF -> toast sukses.
      F4. Login owner -> regresi kalender E27 singkat: chip 'Bentrok sopir' menyaring daftar panel
          (dc-attention-scope muncul), dc-attention-clear mengembalikan, dc-attention-open-* membuka
          [data-testid='dc-detail'] + dc-detail-risks, tautan dc-detail-related-* berpindah booking,
          day-list via klik area NOMOR TANGGAL (pojok kiri-atas sel; JANGAN titik tengah sel karena
          chip event stopPropagation -> membuka detail, itu perilaku benar), view Minggu (dc-view-week)
          lalu kembali (dc-view-month), pencarian 'zzzzzz' -> dc-empty-hint + dc-reset-filters.
      F5. Konsol browser harus BERSIH: khususnya TIDAK ADA warning recharts "width(-1) and height(-1)".
          Sapu /app/dashboard (tab Ringkasan + BI Cockpit), /app/reports, /app/finance (semua tab),
          /app/crm (tab RFM/Skor/Segmen/Campaign). Laporkan bila ada.
      F6. Tidak boleh red screen / error boundary di seluruh alur di atas untuk KETIGA peran.

      CATATAN: jangan uji drag-and-drop, kamera, atau voice (tidak ada di fitur ini).
      WhatsApp real-send masih MOCK (by design). Jangan menyelesaikan aksi 'Tolak' (reject) pada
      booking pending agar data demo tetap utuh.

    -agent: "testing"
    -message: |
      iter-73 (RONDE 3 / FASE E28) — HASIL: 100% (75/75 cek fungsional lulus), 0 bug kritis,
      0 temuan medium. RBAC-CAL-01 & RBAC-SCOPE terverifikasi bekerja; tidak ada regresi pada
      fitur kalender E27 maupun modul manajemen owner/ops; konsol bersih (0 warning recharts).
      Satu catatan LOW: skrip uji /app/backend_rbac_test.py salah menangani expected_status=None
      (3 false positive di skrip, bukan bug aplikasi).

    -agent: "main"
    -message: |
      Tindak lanjut iter-73 (SELESAI):
      1. Catatan LOW diperbaiki: `backend_rbac_test.py` kini menerima expected_status berupa
         int / tuple / None (None = status dinilai oleh check_fn). Hasil ulang: 28/28 LULUS
         (sebelumnya 25/28 karena artefak skrip).
      2. Dua cek B4 yang tidak dijalankan testing agent diverifikasi manual oleh main agent:
         - INV-21 dua arah: `python scripts/verify_patch_inv21.py` -> SEMUA CEK LOLOS
           (POST/PATCH perawatan ke window booking aktif armada SAMA -> 400 dgn kode booking;
            armada BEDA -> 200; ubah cost/note -> 200).
         - Anti double-booking: POST /api/bookings pada window booking aktif -> 400
           "Armada bentrok dengan booking aktif: BK-0009".
         - Reschedule-overlap tetap dijaga gate `verify_state_machine` + `verify_cross_entity` (PASS).
      3. `bash scripts/gate.sh` dijalankan ulang setelah semua perubahan -> HIJAU (receipt di
         memory/GATE_RECEIPT.md, 23 gate, 0 SKIP) termasuk gate runtime baru INV-RBAC-06.

    -agent: "main"
    -message: |
      RONDE 4 (E28b) — perubahan KECIL tapi menyentuh interaksi: 4 dropdown native diganti komponen
      seragam `SelectField` (shadcn/Radix Select).

      PERUBAHAN CARA UJI (WAJIB dibaca): elemen ber-data-testid berikut kini <button> trigger,
      BUKAN <select>. Jadi JANGAN pakai select_option(); pola benar:
        klik [data-testid='<id>']  ->  klik [data-testid='<id>-opt-<slug>']
      Slug = nilai opsi di-lowercase, karakter non-alfanumerik jadi '-'; opsi kosong = 'none'.

      MOHON UJI:
      G1. Owner /app/calendar: klik [data-testid='dc-filter-status'] -> ada 7 opsi
          ([data-testid^='dc-filter-status-opt-']); pilih 'dc-filter-status-opt-confirmed' ->
          [data-testid='dc-month-total'] berubah; kembalikan lewat 'dc-filter-status-opt-all'.
      G2. Owner: klik [data-testid='dc-filter-vehicle'] -> opsi 'dc-filter-vehicle-opt-all' + per armada;
          pilih satu armada -> grid & dc-month-total menyaring; kembalikan ke 'all'.
      G3. Owner: buka detail booking confirmed TANPA sopir (mis. lewat [data-testid^='dc-attention-open-']
          pada item ber-badge 'Belum ada sopir') -> klik [data-testid='dc-assign-select'] ->
          opsi [data-testid^='dc-assign-select-opt-'] muncul (termasuk 'dc-assign-select-opt-none'
          = tanpa sopir); pilih SOPIR yang tidak bentrok -> [data-testid='dc-assign-save'] ->
          toast Bahasa Indonesia. Bila muncul 'Driver bentrok dengan booking aktif: ...' itu BENAR
          (validasi RC-07) — coba sopir lain untuk membuktikan jalur sukses.
      G4. Publik /booking: [data-testid='br-vehicle-type'] -> 5 opsi
          ([data-testid^='br-vehicle-type-opt-'], termasuk '-opt-none'); pilih 'br-vehicle-type-opt-elf',
          isi form minimal (nama, WhatsApp, mulai, selesai) -> [data-testid='br-submit'] -> halaman
          /thank-you muncul dgn No. Pesanan. Pastikan booking tersimpan dgn requested_vehicle_type='elf'
          (boleh cek via GET /api/bookings sebagai owner).
      G5. Regresi cepat: keyboard/aksesibilitas dasar (fokus trigger dgn Tab lalu Enter membuka daftar),
          tidak ada error konsol / red screen, dan tampilan dropdown SERAGAM dgn input di sebelahnya
          (tinggi sama, font sama) di kalender maupun form publik.
      G6. Pastikan TIDAK ADA regresi RBAC dari ronde 3: driver tetap tidak bisa membuka /app/calendar
          (dialihkan + toast) dan tetap hanya melihat trip miliknya di /app/bookings.

      Data demo baru saja di-reseed. Reset ulang bila perlu: cd /app && python scripts/seed_data.py

    -agent: "testing"
    -message: |
      iter-74 (RONDE 4 / E28b) — HASIL: 100% (38/38). Keempat dropdown SelectField bekerja dengan pola
      klik-trigger lalu klik-opsi; data-testid opsi konsisten `<testId>-opt-<slug>`; tinggi 36px & font
      13px seragam dengan input tetangga; form publik menyimpan requested_vehicle_type ke database;
      tidak ada regresi RBAC (ronde 3) maupun fitur kalender E27; konsol bersih.
      Satu catatan LOW: panel ekspor tidak tertutup dengan tombol Escape.

    -agent: "main"
    -message: |
      Tindak lanjut iter-74 (SELESAI):
      1. Catatan LOW diperbaiki: `CalendarExportPanel.jsx` kini menutup panel saat Escape ditekan
         (+ role="dialog", aria-label, aria-expanded/aria-haspopup pada tombol Ekspor).
         Diverifikasi di browser: panel 1 -> 0 elemen setelah Escape.
      2. Jalur SUKSES tugaskan sopir dibuktikan (iter-74 hanya menguji penolakan bentrok):
         BK-0004 + 'Driver Satu' -> tersimpan (driver_name='Driver Satu' via GET /api/bookings).
         Data demo di-reseed setelahnya.
      3. `bash scripts/gate.sh` dijalankan ulang -> HIJAU 23/23, 0 SKIP.
      4. SSOT UI diperbarui: `docs/06_UIUX_STANDARDS.md` mewajibkan pemakaian
         `@/components/shared/SelectField` (bukan merangkai Select/SelectTrigger/SelectItem manual)
         dan mencatat pola otomasi barunya. Aturan `ux_audit` W2 juga diperbaiki agar tidak
         menandai baris KOMENTAR yang menyebut elemen native (dulu memicu temuan palsu).

    -agent: "main"
    -message: |
      Sentuhan akhir E28b (setelah iter-74): keseragaman visual dibuat PERSIS, bukan "mirip".
      Pengukuran computed-style di browser: [data-testid='dc-search'] vs dc-filter-status vs
      dc-filter-vehicle => tinggi 36px, font 13px, border-radius 14px, border rgb(229,229,234)
      IDENTIK ketiganya. (Sebelum sentuhan ini radius trigger 12px karena `rounded-md` shadcn =
      calc(var(--radius) - 2px), sedangkan input aplikasi memakai `rounded-lg` = var(--radius) =
      0.875rem/14px, dan warna border `border-input` beda tipis.) Fungsi tetap: saring 'Hold' ->
      1 keberangkatan, reset 'Semua status' -> 9. gate.sh HIJAU 23/23 setelah perubahan.

    -agent: "main"
    -message: |
      FASE F1 (POC Marketing & Ads) SELESAI — belum perlu testing agent (belum ada UI).
      Rincian & bukti ada di test_result.md (task FASE F1) + memory/INVARIANTS.md (bagian FASE F/E29)
      + plan.md (blok paling atas). Fase F2 akan menambah UI: Pengaturan->Integrasi (kredensial
      ter-mask), consent banner, pemuat Meta Pixel + Google tag runtime, dan 4 halaman modul
      Marketing (Iklan, Landing Page, Kesehatan Pelacakan, Integrasi API) untuk 4 peran.
      Akun demo BARU: marketing@demo.local / demo12345 (peran marketing_admin).

    -agent: "main"
    -message: |
      FASE F2 selesai (Integrasi API + pelacakan publik + Kesehatan Pelacakan). Mohon QA pada giliran
      berikutnya bersama F3, dengan fokus: RBAC 4 peran pada /app/integrations & /app/tracking
      (marketing@demo.local BOLEH, ops@demo.local & driver@demo.local DITOLAK), masking kredensial
      (token tidak boleh tampil), banner consent di situs publik (tolak = tidak ada pixel), event
      funnel (page_view 1x per URL, view_item di detail armada/destinasi, Lead saat submit form),
      serta tombol 'Kirim Event Uji' di Kesehatan Pelacakan (harus melaporkan 'skipped' + alasan
      saat kredensial kosong). Akun: marketing@demo.local / demo12345.

---

## FASE F8 — Landing Page Builder + Media Library (lokal) + Lead LP + A/B + Duplikat

user_problem_statement: |
  Lanjutkan development repo travel (ERP + Marketing Rahaza Travel). Titik berhenti: FASE F8
  Landing Page Builder baru selesai di-wiring (LandingPage.jsx /lp/:slug + route + menu) tapi
  BELUM PERNAH DIUJI. Keputusan user ronde ini: (1) selesaikan F8 penuh, (2) penyimpanan media
  LOKAL dulu dengan media picker/viewer yang jelas & UX bagus, (3) kredensial Meta/Google/WhatsApp
  tetap MOCK, (4) tambah: form lead langsung di LP -> CRM + konversi, uji A/B varian, duplikat
  halaman + galeri template lebih banyak.

backend:
  - task: "F8 Perbaiki HTTP 500 saat buat halaman dari template (trust_badges items string) + validate_blocks tidak boleh melempar"
    implemented: true
    working: true
    file: "backend/services/landing_blocks.py, backend/services/landing_templates.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "BUG-0111. Dibuktikan SEBELUM fix: POST /api/landing/pages template armada-cepat -> HTTP 500 (AttributeError 'str' object has no attribute 'get'), 3 template lain 200. Setelah fix: 8/8 template HTTP 200. Pagar try/except per blok ditambahkan di validate_blocks. Guardrail BARU INV-LP-02 (verify_landing_contract.py) self-test MERAH->HIJAU."
  - task: "F8 Media Library penyimpanan LOKAL (default) + URL publik benar + thumbnail + dimensi + alt + soft delete"
    implemented: true
    working: true
    file: "backend/services/media_store.py, backend/routers/landing.py, backend/routers/public.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "BUG-0112: URL media tersimpan '/api/media/{id}' padahal rute nyata '/api/public/media/{id}' -> SEMUA gambar/video halaman iklan 404 tanpa error backend. Sudah diperbaiki. media_store kini 2 mode: local (DEFAULT, tanpa kredensial) / objstore (bila EMERGENT_LLM_KEY ada). Endpoint: GET/POST /api/landing/media, PATCH /api/landing/media/{id} (alt), DELETE (soft). GET /api/public/media/{id}?thumb=1. Guardrail BARU INV-MEDIA-02 (verify_media_safety.py) self-test MERAH->HIJAU. 4 foto nyata terunggah & terbukti termuat di halaman publik (naturalWidth 1600)."
  - task: "F8 Endpoint publik lead dari Landing Page + atribusi iklan + idempoten + honeypot + consent"
    implemented: true
    working: true
    file: "backend/routers/public.py, backend/schemas_landing.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "POST /api/public/landing/{slug}/lead. Menyimpan lead source=landing_page + channel dari gclid/fbclid + landing_slug/landing_variant + click_ids + consent + auto-assign agen. Emit lead.created -> outbox konversi (meta+google 'pending' karena MOCK). Idempoten via unique index leads.lp_dedupe_key: 6 submit PARALEL = 1 lead. Tanpa consent -> 400, nomor tak valid -> 400, honeypot -> 200 tanpa tulis DB, slug belum terbit -> 404. Rate limit 30/menit per IP (disengaja lebih longgar: pengunjung seluler Indonesia berbagi IP lewat CGNAT operator)."
  - task: "F8 Uji A/B halaman iklan: pilih varian deterministik, override headline/CTA, statistik & pemenang"
    implemented: true
    working: true
    file: "backend/services/landing_blocks.py, backend/services/landing_stats.py, backend/routers/landing.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "GET /api/public/landing/{slug}?vid=&variant= memilih varian DETERMINISTIK dari vid (2000 seed -> 973/1027, sesuai bobot 50/50). POST /api/public/landing/{slug}/track (view|cta_click, jenis lain -> 400). GET /api/landing/pages/{id}/ab -> laporan per varian + pemenang; pemenang HANYA diumumkan bila tiap varian mencapai min_sample DAN selisih >10%."
  - task: "F8 Duplikat halaman + galeri template diperbanyak (4 -> 8) + daftar halaman dengan statistik + lead per halaman"
    implemented: true
    working: true
    file: "backend/routers/landing.py, backend/services/landing_templates.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "POST /api/landing/pages/{id}/duplicate (draf baru, slug unik, statistik TIDAK terbawa). GET /api/landing/pages/{id}/leads. GET /api/landing/pages menyertakan stats views/cta_clicks/leads + ab_enabled. 8 template (4 armada + 4 destinasi) semua lolos kontrak INV-LP-02."

frontend:
  - task: "F8 Halaman iklan publik /lp/:slug fungsional (form lead nyata, estimator, testimoni, search hero aktif, countdown hidup, galeri lightbox)"
    implemented: true
    working: true
    file: "frontend/src/features/public/LandingPage.jsx, frontend/src/components/app/landing/LandingRender.jsx, frontend/src/components/app/landing/blocks/*.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Sebelumnya SEMUA blok konversi hanya placeholder (kotak abu-abu + tombol pindah halaman). Sekarang: form lead nyata (validasi + submit + state sukses), estimator memanggil /api/public/trip-estimate, testimoni dari /api/public/testimonials, fleet/destination grid memakai kontrak field yang BENAR (photos[]/price_from -- renderer lama memakai photo_url/day_rate yang tidak pernah ada sehingga gambar & harga selalu kosong), countdown berdetak nyata, galeri punya penampil layar penuh. Header situs disederhanakan di /lp/* (8 tautan menu = 8 jalan keluar dari formulir). Diverifikasi di browser: submit lead -> lead masuk CRM dengan channel=meta_ads dari fbclid."
  - task: "F8 Media Library UI (grid + viewer besar + pencarian + filter + alt + hapus + unggah banyak)"
    implemented: true
    working: true
    file: "frontend/src/components/app/landing/MediaLibrary.jsx, frontend/src/components/app/landing/MediaPicker.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Permintaan eksplisit user ('media picker harus jelas, viewer harus baik'). Modal 2 kolom: grid thumbnail (memakai ?thumb=1 agar ringan) + penampil besar dengan dimensi/ukuran/pengunggah/tanggal, edit alt, salin URL, hapus, unggah via TOMBOL (bukan drag&drop saja) sehingga bisa diotomasi. MediaPicker menampilkan pratinjau media yang sedang dipakai blok."
  - task: "F8 Editor Landing Page: panel blok sadar-tipe, tema, SEO, A/B, panel lead, duplikat, pratinjau desktop/ponsel, penanda belum tersimpan"
    implemented: true
    working: true
    file: "frontend/src/features/app/LandingBuilder.jsx, frontend/src/components/app/landing/LandingBlockForm.jsx, LandingAbPanel.jsx, LandingSidePanels.jsx, LandingPagesHome.jsx, BlockFieldEditors.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Panel setelan lama menebak kolom dari props yang 'kebetulan ada' sehingga tab, kolom formulir, tenggat promo, batas kartu TIDAK bisa diubah. Sekarang per-tipe untuk 17 tipe blok memakai nama props kanonik. Panel SEO menampilkan pratinjau tautan + hitung karakter (judul SEO WAJIB untuk terbit)."

metadata:
  created_by: "main_agent"
  version: "8.0"
  test_sequence: 76
  run_ui: true

test_plan:
  current_focus:
    - "F8 Halaman iklan publik /lp/:slug fungsional"
    - "F8 Endpoint publik lead dari Landing Page + atribusi iklan + idempoten"
    - "F8 Media Library penyimpanan LOKAL + URL publik benar"
    - "F8 Uji A/B halaman iklan"
    - "F8 Editor Landing Page"
    - "F8 Duplikat halaman + galeri template"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    - agent: "main"
      message: |
        FASE F8 selesai. POC `python scripts/test_core_lp_f8.py` LULUS 84/84. `bash scripts/gate.sh`
        HIJAU (0 FAIL, 0 SKIP) termasuk 2 guardrail BARU: INV-LP-02 (verify_landing_contract.py) &
        INV-MEDIA-02 (verify_media_safety.py), keduanya sudah di-self-test MERAH->HIJAU.
        ux_audit --strict 0 ERROR, validate_compliance FAIL 0.

        KREDENSIAL: owner@demo.local / ops@demo.local / marketing@demo.local / driver@demo.local,
        password `demo12345`. RBAC section "landing" = owner + marketing_admin SAJA (ops_admin &
        driver HARUS 403).

        HALAMAN UJI YANG SUDAH TERBIT: /lp/sewa-hiace-jakarta (A/B aktif: A = "Sewa Hiace, Elf & Bus
        + Driver", B = "Butuh Hiace Besok? Unit Siap Jalan" + tombol "Cek Ketersediaan"). Paksa
        varian dengan `?variant=A` atau `?variant=B`.

        MOHON UJI:
        1. Editor /app/landing sebagai marketing_admin: buat halaman dari BEBERAPA template (semua 8
           harus HTTP 200, khususnya `armada-cepat` yang dulu 500), ubah teks blok, Simpan, isi SEO,
           Terbitkan.
        2. Coba Terbitkan halaman yang belum layak (hapus semua blok konversi ATAU kosongkan judul
           SEO) -> harus ditolak dengan alasan JELAS (400), bukan 5xx.
        3. Media Library: unggah gambar (tombol `ml-upload` + input `ml-file-input`), cari, filter
           Foto/Video, edit teks alternatif, salin URL, hapus. Pastikan gambar yang dipakai blok hero
           benar-benar TAMPIL (bukan gambar rusak) di halaman publik.
        4. Halaman publik /lp/sewa-hiace-jakarta: isi form lead TANPA centang consent (harus ditolak
           sopan), lalu DENGAN consent (harus muncul state sukses `lp-lead-success`). Cek lead muncul
           di CRM (/app/crm) dengan atribusi + slug halaman.
        5. Kirim form DUA KALI dengan nomor sama -> hanya boleh ada SATU lead di CRM.
        6. Kalkulator "Hitung Estimasi" (`lp-est-submit`) di halaman publik harus mengeluarkan rincian
           biaya nyata.
        7. Duplikat halaman -> jadi DRAF dengan slug berbeda; hapus halaman uji setelahnya.
        8. Panel A/B: aktifkan, isi varian B, Simpan, buka `?variant=B` -> judul & label tombol berubah.
        9. RBAC: login ops_admin & driver -> menu "Landing Page Iklan" TIDAK boleh ada; akses langsung
           /app/landing ditolak; GET /api/landing/pages harus 403.
        10. Regresi singkat: /app/ads, /app/tracking, /app/crm, dan situs publik (/, /fleet) tetap normal.

        JANGAN uji: drag & drop, kamera, mikrofon/suara. Unggah berkas HARUS via input file
        (`ml-file-input`) / tombol `ml-upload`, bukan drag & drop.

        MOCKED: pengiriman konversi ke Meta/Google & WhatsApp masih MOCK (belum ada kredensial); entri
        outbox akan berstatus `pending`/`skipped` — itu perilaku yang BENAR, bukan bug.

---

## RONDE BOOKING-V2 (2026-08-12) — navbar publik + 3 fitur backlog

backend:
  - task: "POST /api/public/booking/promos — daftar promo aktif + kelayakan (dihitung server)"
    implemented: true
    working: true
    file: "backend/routers/booking_public.py · backend/services/promos.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: "Subtotal dihitung ULANG server (klien tidak boleh kirim angka). Promo tak layak tetap tampil + alasan. Anti-tamper diuji: field `subtotal` dari klien diabaikan."
        - working: true
          agent: "testing"
          comment: "iteration_84: 7/7 cek lolos (eligible 2 hari akhir pekan, reason 'minimal 2 hari', reason layanan salah, anti-tamper, 404 unit tak ada, 400 tanggal ngawur/end<start). 0 5xx."

  - task: "GET /api/reports/hold-expired (+ /export CSV) — laporan hold hangus"
    implemented: true
    working: true
    file: "backend/services/hold_report.py · backend/routers/reports.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: "Dibuktikan dengan skenario NYATA: 3 pesanan hold dimundurkan batas DP-nya lalu penjadwal (notifications.scan) membatalkannya; laporan menampilkan with_proof=1 & recovered=1. Seed menambah BK-0009/BK-0010 agar data demo tidak kosong."
        - working: true
          agent: "testing"
          comment: "iteration_84: struktur + RBAC benar (owner/ops 200, driver 403, marketing 403, tanpa auth 401; days=0/999 -> 422). CSV memuat BK-0009."

frontend:
  - task: "Navbar publik dirapikan (5 menu + 1 aksi utama) + drawer 2 grup + chip 'Lanjutkan pesanan'"
    implemented: true
    working: true
    file: "frontend/src/components/public/PublicLayout.jsx · ResumeBookingChip.jsx · StickyMobileCTA.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "testing"
          comment: "iteration_83: 5 menu tepat, 'Pesan Sekarang' hilang, header 90,75 px (1 baris), bar pengumuman & footer lengkap, drawer 5+6 item, /lp/* tetap ringkas."
        - working: true
          agent: "main"
          comment: "Laporan LOW 'chip tidak muncul' pada iteration_83 = FALSE POSITIVE (kode booking sudah terhapus saat gate re-seed; self-healing 404 justru bekerja). Dibuktikan ulang dengan pesanan BARU: chip muncul ('Menunggu bukti DP') & klik mendarat di halaman status; token palsu -> chip hilang + entri localStorage dibuang."

  - task: "Section beranda 'Pesan online dalam 3 langkah' (DP & lama hold dari server)"
    implemented: true
    working: true
    file: "frontend/src/components/public/BookingStepsSection.jsx · features/public/Home.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        - working: true
          agent: "testing"
          comment: "iteration_83/84: 3 kartu + chip 'DP 30%' & 'Unit ditahan 2 jam' sama dengan /api/public/booking/config."

  - task: "PromoPicker di wizard /booking (klik 'Pakai' langsung menerapkan promo)"
    implemented: true
    working: true
    file: "frontend/src/components/public/booking/PromoPicker.jsx · QuoteBreakdown.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "testing"
          comment: "iteration_84: total 4.500.000 -> 4.000.000 saat GATHERING500 dipakai; hapus promo -> kembali; promo tak layak menampilkan alasan tanpa tombol Pakai."

  - task: "Panel 'Hold Hangus' di /app/reports (KPI + insight + tabel + WA + CSV)"
    implemented: true
    working: true
    file: "frontend/src/components/app/HoldExpiredReport.jsx · features/app/Reports.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "testing"
          comment: "iteration_84: KPI count=2, with_proof=1, insight merah tampil, baris BK-0009 ber-flag bukti, BK-0010 punya tombol WhatsApp, rentang & muat ulang bekerja."

  - task: "Katalog rute bandara (tambah cepat) + tombol 'Arah balik'"
    implemented: true
    working: true
    file: "frontend/src/components/app/TransferRoutesPanel.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        - working: false
          agent: "main"
          comment: "BUG-0120 ditemukan sendiri saat uji UI: kota yang kode-nya sama dengan IATA bandaranya (Denpasar-DPS, Bandung-BDO, Solo-SOC, Semarang-SRG) menghasilkan kode rute simetris `DPS-DPS`; arah balik jadi kode identik -> 409."
        - working: true
          agent: "main"
          comment: "Fix: alias kode kota bila bertabrakan (BALI/BDG/SLO/SMG) + kode simetris dikosongkan pada arah balik. Terbukti: BALI-DPS & DPS-BALI dua-duanya tersimpan, tarif tersalin, rute baru langsung dijual dengan tarif FLAT (Hiace Premio Rp 900.000)."

metadata:
  created_by: "main_agent"
  version: "2.0"
  test_sequence: 84
  run_ui: true

test_plan:
  current_focus: []
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    - agent: "main"
      message: |
        RONDE BOOKING-V2 SELESAI. Bukti: gate.sh HIJAU (0 FAIL, 0 SKIP) · POC
        scripts/test_core_booking_v1.py 74/74 (dijalankan sebelum & sesudah perubahan) ·
        ux_audit --strict 0 ERROR 0 WARN · verify_delivery fase BOOKING-V2 P0 12/12 & 0 orphan
        endpoint · testing agent iteration_83 (navbar + STORY H) & iteration_84 (3 fitur, 0 bug).

        CATATAN UNTUK RONDE UJI BERIKUTNYA (mencegah laporan bug palsu):
        1. Input tanggal /booking TIDAK punya atribut `name` -> pakai
           [data-testid='booking-start'] / [data-testid='booking-end'] + page.fill.
        2. [data-testid='hold-range'] adalah Radix Select -> klik trigger lalu klik
           [data-testid='hold-range-opt-7']; select_option() tidak berlaku.
        3. Chip [data-testid='resume-booking-chip'] WAJIB diuji dengan pesanan BARU (buat via API
           lalu suntik localStorage 'rahaza_bookings'). Kode lama yang sudah ter-reseed memang
           dibuang otomatis (self-healing), itu BUKAN bug.
        4. Promo AKHIRPEKAN10 = akhir pekan + Hiace Premio; GATHERING500 = min 2 hari & min Rp 3jt;
           keduanya punya valid_until -> bila tanggal sistem melewatinya, promo memang tidak muncul.
        5. MOCKED: WhatsApp Cloud / Meta Ads / Google Ads / GA4 masih MOCK (belum ada kredensial).

#====================================================================================================
# RONDE KEBERSIHAN DATA (BUG-0127) — 2026-08-13
#====================================================================================================

user_problem_statement: |
  User meminta 2 hal:
  (1) "saya ingin cek flow dari awal hingga akhir apakah tidak ada masalah dan aman"
  (2) "untuk data seed customer dihapus saja" — diperjelas user: "sebenarnya ada bug di skrip ada
      nama customer aaaaaaaaaaaaaaaaaaaaaaaa itu yang mengganggu, maksud saya hapus adalah seed ini,
      mending seed diperbaiki namun tetap ada data demo".
  Jadi: DATA DEMO TETAP ADA, yang harus hilang adalah DATA SAMPAH hasil skrip uji.

backend:
  - task: "BUG-0127 — artefak data uji (guardrail/smoke/POC) bocor ke koleksi operasional"
    implemented: true
    working: "NA"
    file: "scripts/guardrails/_common.py + verify_no_test_pollution.py + selftest_no_test_pollution.py + scripts/purge_test_pollution.py + backend/services/audit.py + scripts/seed_data.py + scripts/gate.sh"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: false
          agent: "main"
          comment: |
            RCA: penjaga & smoke test menulis lewat API sungguhan lalu hanya menghapus dokumen
            UTAMA. Side-effect-nya tidak. Bukti pada database hasil `gate.sh` HIJAU 40/40:
            customers berisi nama 60.000 karakter "AAAA…" (dari selftest_booking_guards mutasi S01
            yang melepas max_length -> tersimpan -> kode di-revert TAPI dokumen tak dihapus);
            audit_logs punya baris summary 60.016 karakter; Inbox berisi percakapan
            "Penjaga INV-BOOK-02"/"Penjaga INV-PRICE-01"/"Smoke Customer"/"Guard Lead"; 34
            notification_tasks hantu; 35 dari 48 events + automation_runs artefak; CRM menyimpan
            lead & penawaran berisi karakter NUL + segmen "AdvSeg"; Media Library menyimpan aset
            guard-media-*; conversion_events (outbox konversi iklan) menumpuk permanen karena TAK
            PERNAH di-reset seed. Total 157 dokumen sampah per jalan gate.
        - working: true
          agent: "main"
          comment: |
            FIX (belum diverifikasi testing agent):
            1. `_common.py` — mesin bersih-bersih bersama `purge_guard_artifacts()` + SSOT penanda
               (GUARD_MARKERS/GUARD_PHONE_PREFIXES/PURGE_COLLECTIONS/OVERLONG_RULES) dengan cascade
               penuh: payments/invoices/expenses/trips/locations/trip_shares/payment_proofs +
               aset media bukti + messages/conversations (termasuk yang lahir dari lead uji) +
               notification_tasks + events + automation_runs + audit_logs (termasuk yang MENYEBUT
               kode BK-00xx) + conversion_events + landing_stats + percakapan yatim.
            2. Semua penulis data uji memanggilnya di `finally`: verify_string_bounds,
               verify_reference_integrity, verify_identity_race, verify_media_runtime,
               verify_adversarial_5xx, verify_pricing_integrity, verify_booking_public,
               selftest_booking_guards, scripts/mutation_smoke.py, scripts/test_core_booking_v1.py,
               scripts/test_core_lp_f8.py.
            3. `services/audit.py` — `_clip()` memotong summary (300) / snapshot (2000) / nama aktor
               (120) => tak mungkin lagi ada baris audit 60.016 karakter.
            4. `seed_data.py` — `conversion_events` masuk daftar reset + reseed memanggil purge.
            5. Guardrail baru INV-CLEAN-01 (`verify_no_test_pollution.py`, statik+runtime) di-wire
               PALING AKHIR di gate.sh + self-test 5 mutasi (`selftest_no_test_pollution.py`)
               + terdaftar di memory/INVARIANTS.md. Alat perbaikan: `scripts/purge_test_pollution.py`.
            BUKTI: 157 dokumen sampah dibersihkan; `gate.sh` HIJAU 42/42 (0 FAIL 0 SKIP) DAN
            database tetap 0 artefak SESUDAH gate; POC 74/74 & 84/84; snapshot DB sebelum-sesudah
            POC hanya berselisih sessions/audit login (aktivitas sah).

frontend:
  - task: "ERP tidak lagi menampilkan data sampah (Customer 360 / Inbox / Jejak Audit / Media)"
    implemented: true
    working: "NA"
    file: "(tanpa perubahan FE — verifikasi data)"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: |
            Screenshot Playwright sesudah fix: /app/customers = TEPAT 4 customer demo (PT Maju Jaya,
            Keluarga Andi, CV Sentosa Wisata, Keluarga Hendra) tanpa "AAAA…"; /app/inbox tanpa
            percakapan "Penjaga INV-*"/"Smoke Customer"; /app/auditlog tanpa baris raksasa.
            Perlu verifikasi menyeluruh oleh testing agent (alur end-to-end + regresi).

metadata:
  created_by: "main_agent"
  version: "2.1"
  test_sequence: 89
  run_ui: true

test_plan:
  current_focus:
    - "BUG-0127 — artefak data uji bocor ke koleksi operasional"
    - "Alur end-to-end publik -> ERP (pesan online -> hold -> bukti DP -> ops konfirmasi -> dispatch -> selesai -> keuangan/laporan)"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    - agent: "main"
      message: |
        Fokus ronde ini: (A) verifikasi alur END-TO-END masih aman, (B) buktikan tidak ada lagi
        data sampah uji yang terlihat pengguna.
        CATATAN ANTI BUG-PALSU (dari ronde sebelumnya, masih berlaku):
        1. Login ERP di /app/login (BUKAN /login) — pakai data-testid login-email-input /
           login-password-input / login-submit-button. Akun: owner@demo.local, ops@demo.local,
           driver@demo.local, marketing@demo.local — password demo12345.
        2. Input tanggal /booking TIDAK punya atribut `name` -> pakai data-testid booking-start /
           booking-end + page.fill.
        3. Semua Select adalah Radix (klik trigger lalu klik opsi ber-testid); select_option()
           tidak berlaku. hold-range -> hold-range-opt-<n>.
        4. Seed SENGAJA penuh pada 10-17 Agu 2026 (BK-0003/BK-0004 memakai V-01/V-02, V-03
           perawatan). Kalau /booking bilang "tidak ada unit bebas", GESER TANGGAL — itu BUKAN bug.
        5. Promo AKHIRPEKAN10 = akhir pekan + Hiace Premio; GATHERING500 = min 2 hari & min Rp 3jt.
        6. MOCKED: WhatsApp Cloud / Meta Ads / Google Ads / GA4 (belum ada kredensial user).
        7. JANGAN uji drag-and-drop, kamera, atau suara.

#====================================================================================================
# RONDE CMS-CW2 (2026-08-17) — CMS-05…CMS-09 + defect A1/A2/A3
#====================================================================================================

backend:
  - task: "CMS-05 siklus terbit + token pratinjau (draft/scheduled/published)"
    implemented: true
    working: true
    file: "backend/services/content_publish.py, backend/routers/content.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: "POC test_core_cms_cw2.py bagian A LOLOS: draft tidak bocor ke publik, token pratinjau membuka draft, jadwal terbit otomatis, publish_due merapikan status."
  - task: "CMS-06 dua bahasa (translations.en) + fallback + hreflang"
    implemented: true
    working: true
    file: "backend/services/i18n.py, backend/routers/public.py, backend/routers/seo.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: "POC bagian C LOLOS. Terjemahan MANUAL (AI OFF keputusan pemilik); endpoint translate membalas 503 berpesan 'isi manual tetap bisa'."
  - task: "CMS-09 sanitasi rich text artikel"
    implemented: true
    working: true
    file: "backend/services/richtext.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: false
          agent: "main"
          comment: "BUG-0129: paket bleach tidak pernah dipasang/dipin -> sanitizer fail-closed membuang SEMUA tag (3 cek POC gagal)."
        - working: true
          agent: "main"
          comment: "bleach==6.4.0 dipin di requirements.txt; BUG-0130 blok script/style/iframe kini dibuang BESERTA isinya. POC 87/87."
  - task: "CMS-07 funnel ulasan (token -> testimoni -> moderasi)"
    implemented: true
    working: true
    file: "backend/services/reviews.py, backend/routers/reviews.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: "POC bagian E LOLOS (token sekali pakai, rating 1-5, ulasan masuk moderasi, approve -> tayang + ikut rata-rata). WhatsApp MOCK."
  - task: "CMS-08 analitik konten + atribusi lead/pesanan"
    implemented: true
    working: true
    file: "backend/services/content_stats.py, backend/routers/content.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: "POC bagian F LOLOS (dedupe 1 IP/30 menit, atribusi lead, rasio konten->lead)."
  - task: "A2 aturan promo sebagai DATA + endpoint meta promo-options"
    implemented: true
    working: true
    file: "backend/services/promos.py, backend/routers/content.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: "POC bagian D LOLOS. GET /api/content/meta/promo-options baru (SSOT tipe armada + layanan)."

frontend:
  - task: "A1/A3 halaman publik /packages, /packages/:slug, /promo + route /review/:token"
    implemented: true
    working: "NA"
    file: "frontend/src/App.js, features/public/{Packages,PackageDetail,Promos,ReviewSubmit}.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Route + halaman aktif; screenshot manual OK (grid paket & promo terisi data seed). BUTUH verifikasi E2E testing agent."
  - task: "CMS-06 pemilih bahasa ID/EN di situs publik (isi + label kerangka + hreflang)"
    implemented: true
    working: "NA"
    file: "frontend/src/components/public/{PublicLayout,LanguageSwitch}.jsx, hooks/useSEO.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Manual: klik EN -> ?lang=en, html lang=en, hreflang id/en/x-default, og:locale en_US, label nav Inggris. Isi DB ikut EN bila terjemahan diisi."
  - task: "CMS-05 UI: filter status, badge, tab Terbit (status+jadwal+tautan pratinjau)"
    implemented: true
    working: "NA"
    file: "frontend/src/features/app/ContentManager.jsx, components/cms/PublishControls.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Manual: tab Terbit + status select + tombol tautan pratinjau tampil. BUTUH E2E: jadwalkan artikel -> hilang dari /blog -> tautan pratinjau membukanya."
  - task: "CMS-06 UI: tab English manual per-field (copy dari ID, kosong = fallback)"
    implemented: true
    working: "NA"
    file: "frontend/src/components/cms/TranslationFields.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Daftar field diambil dari GET /api/content/meta/i18n. Badge EN muncul di daftar konten bila terjemahan tersimpan."
  - task: "CMS-09 UI: editor rich text + render aman di /blog/:slug"
    implemented: true
    working: "NA"
    file: "frontend/src/components/cms/RichTextEditor.jsx, components/public/ArticleBody.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: false
          agent: "main"
          comment: "BUG-0131: BlogDetail merender HTML sebagai teks (tag terlihat pengunjung)."
        - working: "NA"
          agent: "main"
          comment: "FIXED via ArticleBody (deteksi format). Playwright manual: h2/li/blockquote/link terender, tag tidak bocor."
  - task: "CMS-07 UI: tab Ulasan (moderasi + kirim tautan) & halaman /review/:token"
    implemented: true
    working: "NA"
    file: "frontend/src/components/app/ReviewModerationPanel.jsx, features/public/ReviewSubmit.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Panel tampil (KPI + antrean + permintaan terkirim). BUTUH E2E: buka tautan ulasan -> kirim rating -> muncul di moderasi -> setujui -> tayang."
  - task: "CMS-08 UI: tab Analitik konten + ekspor CSV"
    implemented: true
    working: "NA"
    file: "frontend/src/components/app/ContentAnalyticsPanel.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "KPI + tabel peringkat + filter jenis + CSV. Angka terisi setelah halaman konten dibuka pengunjung."
  - task: "A2 UI: form aturan promo lengkap + used_count read-only"
    implemented: true
    working: "NA"
    file: "frontend/src/features/app/ContentManager.jsx (SCHEMAS.promos), components/app/ContentFormDialog.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Field valid_from/min_days/min_amount/vehicle_types/services/weekend_only/max_uses + used_count read-only terverifikasi tampil."

metadata:
  created_by: "main_agent"
  version: "6.0"
  test_sequence: 92
  run_ui: true

test_plan:
  current_focus:
    - "CMS-05 jadwal terbit + tautan pratinjau bertoken (end-to-end di UI)"
    - "CMS-06 dua bahasa: isi EN dari CMS -> tampil di situs saat EN dipilih, fallback ID bila kosong"
    - "CMS-07 funnel ulasan end-to-end (tautan -> isi -> moderasi -> tayang)"
    - "A1/A3 halaman /packages, /packages/:slug, /promo + kode promo terbawa ke /booking"
    - "CMS-09 editor rich text -> tersimpan tersanitasi -> terender rapi di /blog/:slug"
    - "CMS-08 analitik konten mencatat tampilan & atribusi"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    - agent: "main"
      message: |
        RONDE CMS-CW2. Backend sudah dibuktikan POC (scripts/test_core_cms_cw2.py 87/87) dan
        gate.sh HIJAU (0 FAIL, 0 SKIP). Yang perlu diverifikasi = ALUR UI end-to-end.
        CATATAN ANTI BUG-PALSU (WAJIB dibaca):
        1. Login ERP di /app/login (BUKAN /login): data-testid login-email-input /
           login-password-input / login-submit-button. Akun: owner@demo.local ·
           ops@demo.local · driver@demo.local · marketing@demo.local — password demo12345
           (lihat memory/test_credentials.md).
        2. CMS ada di /app/cms dengan 8 tab: content-tab-{destinations,packages,articles,
           testimonials,promos,reviews,analytics,theme}.
        3. Semua Select adalah Radix: klik trigger lalu klik opsi ber-testid
           (mis. content-status-filter -> content-status-opt-draft; cf-status ->
           cf-status-opt-scheduled). select_option() TIDAK berlaku.
        4. Jadwal terbit memakai <input type="datetime-local"> data-testid cf-publish-at →
           gunakan page.fill dengan format "YYYY-MM-DDTHH:MM".
        5. Status terbit HANYA ada di tab "Terbit" (cf-tab-publish). Toggle
           `published`/`active` lama SUDAH DIHAPUS dari form (server menyinkronkannya) —
           itu perubahan yang disengaja, bukan field hilang.
        6. Tautan pratinjau: tombol cf-preview-token (di dialog) atau
           content-preview-token-{id} (di daftar, hanya muncul untuk konten BELUM tayang).
           Token berlaku 24 jam dan hanya membuka 1 dokumen; URL berbentuk
           /blog/<slug>?preview=<token>.
        7. Bahasa publik: lang-switch-id / lang-switch-en di bar pengumuman
           (+ public-mobile-lang di drawer). Mengganti bahasa menambahkan ?lang=en ke URL dan
           memuat ulang SEMUA data publik. Label kerangka ikut Inggris; teks halaman yang
           belum dimasukkan ke lib/i18n.js masih Indonesia (BACKLOG Fase 3 — bukan bug baru).
        8. Isi EN diisi di dialog konten tab cf-tab-en (field cf-en-<field>, tombol
           cf-en-copy-<field>). Kosong = FALLBACK Indonesia (memang dirancang begitu).
        9. Ulasan: /review/<token>. Token bisa diambil dari /app/cms tab Ulasan
           (review-copy-{id} / review-open-{id}) atau dibuat dengan review-send-{bookingId}
           pada pesanan completed. Rating <1 atau >5 dan ulasan <10 karakter WAJIB ditolak.
        10. Seed SENGAJA penuh 10–17 Agu 2026 di /booking — kalau "tidak ada unit bebas",
            GESER TANGGAL; itu BUKAN bug.
        11. MOCKED: WhatsApp Cloud / Meta Ads / Google Ads / GA4. Terjemahan AI OFF
            (endpoint translate memang 503 berpesan) — itu keputusan pemilik, bukan kerusakan.
        12. JANGAN jalankan `bash scripts/gate.sh` atau `python scripts/seed_data.py` selama
            pengujian UI (keduanya me-RESEED database → data uji Anda hilang & tampak seperti bug).
        13. Data uji yang Anda buat lewat API: awali nama dengan "Penjaga INV-" atau pakai
            nomor 0800000xxx (INV-CLEAN-01), supaya bisa dibersihkan mesin purge.
        14. JANGAN uji drag-and-drop, kamera, atau suara.
