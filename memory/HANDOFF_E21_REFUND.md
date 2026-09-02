# HANDOFF — E21 Refund Ledger Posting  (UPDATE: DONE untuk refund; denda tetap MEMO)

Tanggal awal: 2026-07-03 — dibuat sbg defer.
Update: 2026-07-03 — **refund posting DONE via payments negatif**; denda tetap memo.

## Ringkasan implementasi
- **Refund → payments negatif method="refund"** (rekomendasi HANDOFF v1 dipilih).
  Saat `POST /api/bookings/{id}/cancel` dgn `refund_amount > 0`:
  1. Insert dokumen `payments` dgn `amount = -refund_amount`, `type="refund"`,
     `method="refund"`, `note = "Refund pembatalan: <reason>"`.
  2. **Idempotent**: kalau sudah ada payment `type=refund` utk booking itu, tidak insert lagi
     (retry cancel aman; tidak duplikasi refund).
  3. Panggil `services.finance.recompute_booking_payment(db, booking_id)` supaya
     `paid_amount` di-recompute = Σ payments (termasuk negatif) dan `payment_status`
     diturunkan ulang lewat `derive_payment_status(paid, total)`.
- **Denda (cancellation_fee) tetap MEMO** disimpan di `bookings.cancellation_fee` — tidak diposting
  jurnal terpisah. Ops boleh buat invoice manual bila perlu pengakuan pendapatan denda.

## Invarian yang tetap terjaga
- **INV-2** `paid_amount == Σ payments[booking].amount` — refund adalah baris payments (nilai
  negatif), jadi identitas tetap.
- **INV-3** `payment_status = derive(paid, total)` — setelah refund:
  - `paid == 0` → `belum_bayar`
  - `0 < paid < total` → `dp`
  - `paid >= total` → `lunas` (mustahil setelah refund kecuali fully paid & refund=0)
- **RC-04** cancel tetap melepaskan armada (INV-4) via `_release_booking_resources`.
- **RC-05** pembayaran normal (POST /api/payments) tetap ditolak utk booking `cancelled`
  → refund yg diposting oleh cancel endpoint TIDAK melewati route publik `/payments`
  (insert langsung ke koleksi), jadi tidak konflik.

## Verifikasi (curl)
```bash
# Booking BID sudah paid=3.0M lunas → cancel dgn fee=50k, refund=200k
curl -X POST /api/bookings/$BID/cancel \
  -d '{"reason":"customer minta","cancellation_fee":50000,"refund_amount":200000}'
# → 200; paid_amount=2800000; payment_status="dp"; cancellation_fee=50000
# → GET /api/payments?booking_id=$BID: 2 records → settlement +3.0M, refund -200k
# → Retry cancel dgn refund=99999 → tidak menambah refund baru (idempotent)
```

## Efek ke laporan finansial
- `finance/pl-full`, `finance/ar`, `finance/summary`, `finance/cashflow`, `reports/summary`,
  `dashboard` — semua **200** setelah patch (regresi HIJAU).
- Revenue diakui berbasis `paid_amount` atau `Σ payments (positif+negatif)` → berkurang otomatis
  sebesar refund. **Denda tidak muncul di revenue** kecuali ops membuat invoice denda manual.

## Yang MASIH manual / tidak di-otomasi
- **Metode kas refund**: `method="refund"` (generic). Jika perlu mencatat kanal (transfer/tunai),
  perlu perluasan schema atau tambahan field.
- **Rekonsiliasi bank utk refund out-flow**: jika ada modul reconciliation kas keluar,
  refund payment negatif ini bisa dimasukkan sbg baris kas keluar. Belum di-wire.

## UPDATE E26 (2026-07-03) — Denda Auto-Invoice (Paper Trail)
Status: **DONE**. Rekomendasi HANDOFF v1 ("denda tidak posting jurnal terpisah") direvisi:
denda tetap tidak menaikkan revenue di P&L (revenue dari Σ payments), tapi **auto-invoice
paper trail** dibuat supaya:
- Ada nomor invoice formal (INV-YYYY-####) utk denda pembatalan.
- Muncul di list `/api/invoices` (filter `type=cancellation_fee`).
- Bisa diekspor PDF/Excel via endpoint invoice yg ada.

**Implementasi** (di `cancel_booking`, blok E26):
- Bila `cancellation_fee > 0`: insert `invoices` dgn `type="cancellation_fee"`,
  `status="paid"`, `amount=cancellation_fee`, notes berisi alasan.
- **Idempotent**: cek invoice existing dgn `booking_id + type=cancellation_fee`; skip bila sudah ada.
- **TIDAK double-count** di P&L: revenue tetap `Σ payments`; denda sudah tercakup di
  residual `paid_amount - refund_amount` (net payments).

## Endpoint & data model
- `POST /api/bookings/{id}/cancel` — body opsional `CancelBooking{reason, cancellation_fee, refund_amount}`.
- `bookings.{cancellation_reason, cancellation_fee, refund_amount, cancelled_at, cancelled_by}`
- `payments.{type="refund", method="refund", amount<0}` — kolom baru enum value.

## Cross-ref
- `backend/routers/bookings.py :: cancel_booking` (blok E21-Ledger)
- `backend/services/finance.py :: recompute_booking_payment` (dipakai untuk sinkron paid_amount)
- `backend/schemas.py :: CancelBooking`
- `frontend/src/components/app/CancelBookingDialog.jsx`
- `docs/03_DATA_MODEL.md` §bookings + §payments
