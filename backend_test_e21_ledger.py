#!/usr/bin/env python3
"""
Regression test E21 Refund Ledger Posting — auto-post refund sbg payment negatif.

Skenario:
R1. Refund posting sukses (payment negatif tercatat, paid_amount berkurang)
R2. Idempotent — retry cancel tidak duplikat refund payment
R3. Refund = 0 → tidak ada payment refund
R4. Refund = full paid (semua uang dikembalikan, paid_amount=0)
R5. INV-2 & INV-3 tetap konsisten
R6. Finance reports masih 200
R7. RC-05 tidak konflik (manual payment ke cancelled booking → 400)
R8. E20 & E21 base scenarios masih PASS
"""
import os
import sys
import requests
from datetime import datetime, timedelta

# Base URL dari frontend/.env
BASE_URL = os.getenv("REACT_APP_BACKEND_URL", "https://trip-route-buttons.preview.emergentagent.com")
API_URL = f"{BASE_URL}/api"

# Test credentials
OWNER_EMAIL = "owner@demo.local"
OWNER_PASSWORD = "demo12345"

session = requests.Session()
token = None


def login():
    """Login sebagai owner untuk mendapatkan token."""
    global token
    resp = session.post(f"{API_URL}/auth/login", json={
        "email": OWNER_EMAIL,
        "password": OWNER_PASSWORD
    })
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    data = resp.json()
    token = data.get("token")
    assert token, "No token in login response"
    session.headers.update({"Authorization": f"Bearer {token}"})
    print(f"✓ Logged in as {OWNER_EMAIL}")
    return data


def create_booking(base_price=500000, customer_id=None, vehicle_id=None):
    """Buat booking baru untuk testing."""
    # Get customer & vehicle if not provided
    if not customer_id:
        customers = session.get(f"{API_URL}/customers").json()
        customer_id = customers[0]["id"] if customers else None
    if not vehicle_id:
        vehicles = session.get(f"{API_URL}/vehicles").json()
        vehicle_id = vehicles[0]["id"] if vehicles else None
    
    assert customer_id and vehicle_id, "Need customer & vehicle"
    
    start = (datetime.utcnow() + timedelta(days=7)).isoformat()
    end = (datetime.utcnow() + timedelta(days=8)).isoformat()
    
    resp = session.post(f"{API_URL}/bookings", json={
        "customer_id": customer_id,
        "vehicle_id": vehicle_id,
        "start_datetime": start,
        "end_datetime": end,
        "base_price": base_price,
        "origin": "Jakarta",
        "destination": "Bandung"
    })
    assert resp.status_code == 200, f"Create booking failed: {resp.status_code} {resp.text}"
    return resp.json()


def create_payment(booking_id, amount, payment_type="dp"):
    """Catat pembayaran untuk booking."""
    resp = session.post(f"{API_URL}/payments", json={
        "booking_id": booking_id,
        "amount": amount,
        "type": payment_type,
        "method": "transfer"
    })
    assert resp.status_code == 200, f"Create payment failed: {resp.status_code} {resp.text}"
    return resp.json()


def cancel_booking(booking_id, reason="", cancellation_fee=0, refund_amount=0):
    """Cancel booking dengan body CancelBooking."""
    body = {
        "reason": reason,
        "cancellation_fee": cancellation_fee,
        "refund_amount": refund_amount
    }
    resp = session.post(f"{API_URL}/bookings/{booking_id}/cancel", json=body)
    return resp


def get_booking(booking_id):
    """Get booking detail."""
    resp = session.get(f"{API_URL}/bookings/{booking_id}")
    assert resp.status_code == 200, f"Get booking failed: {resp.status_code} {resp.text}"
    return resp.json()


def get_payments(booking_id):
    """Get payments untuk booking."""
    resp = session.get(f"{API_URL}/payments", params={"booking_id": booking_id})
    assert resp.status_code == 200, f"Get payments failed: {resp.status_code} {resp.text}"
    return resp.json()


def test_r1_refund_posting_success():
    """R1. Refund posting sukses — payment negatif tercatat, paid_amount berkurang."""
    print("\n=== R1: Refund posting sukses ===")
    
    # 1. Buat booking baru dgn base_price=500000
    booking = create_booking(base_price=500000)
    booking_id = booking["id"]
    print(f"✓ Created booking {booking['code']} (total={booking['total_amount']})")
    
    # 2. POST payment dgn amount=300000, type=dp
    payment = create_payment(booking_id, 300000, "dp")
    print(f"✓ Created payment {payment['id']} (amount=300000)")
    
    # Verify paid_amount=300000, payment_status=dp
    booking = get_booking(booking_id)
    assert booking["paid_amount"] == 300000, f"Expected paid_amount=300000, got {booking['paid_amount']}"
    assert booking["payment_status"] == "dp", f"Expected payment_status=dp, got {booking['payment_status']}"
    print(f"✓ Verified: paid_amount=300000, payment_status=dp")
    
    # 3. POST cancel dgn refund_amount=200000
    resp = cancel_booking(booking_id, reason="customer minta", cancellation_fee=50000, refund_amount=200000)
    assert resp.status_code == 200, f"Cancel failed: {resp.status_code} {resp.text}"
    print(f"✓ Cancelled booking with refund=200000, fee=50000")
    
    # 4. Verifikasi booking
    booking = get_booking(booking_id)
    assert booking["status"] == "cancelled", f"Expected status=cancelled, got {booking['status']}"
    assert booking["cancellation_fee"] == 50000, f"Expected fee=50000, got {booking['cancellation_fee']}"
    assert booking["refund_amount"] == 200000, f"Expected refund=200000, got {booking['refund_amount']}"
    assert booking["paid_amount"] == 100000, f"Expected paid_amount=100000 (300k-200k), got {booking['paid_amount']}"
    assert booking["payment_status"] == "dp", f"Expected payment_status=dp (0<paid<total), got {booking['payment_status']}"
    print(f"✓ Verified: status=cancelled, paid_amount=100000, payment_status=dp")
    
    # 5. Verifikasi payments — harus ada 2 records (settlement +300k & refund -200k)
    payments = get_payments(booking_id)
    assert len(payments) == 2, f"Expected 2 payments, got {len(payments)}"
    
    # Find refund payment
    refund_payment = next((p for p in payments if p["type"] == "refund"), None)
    assert refund_payment is not None, "Refund payment not found"
    assert refund_payment["amount"] == -200000, f"Expected refund amount=-200000, got {refund_payment['amount']}"
    assert refund_payment["method"] == "refund", f"Expected method=refund, got {refund_payment['method']}"
    assert "Refund pembatalan" in refund_payment["note"], f"Expected note to contain 'Refund pembatalan', got {refund_payment['note']}"
    print(f"✓ Verified: 2 payments (settlement +300k, refund -200k)")
    
    print("✅ R1 PASS: Refund posting sukses")
    return booking_id


def test_r2_idempotent_retry_cancel(booking_id):
    """R2. Idempotent — retry cancel tidak menambah refund payment baru."""
    print("\n=== R2: Idempotent retry cancel ===")
    
    # Get current payments count
    payments_before = get_payments(booking_id)
    refund_count_before = len([p for p in payments_before if p["type"] == "refund"])
    paid_before = get_booking(booking_id)["paid_amount"]
    
    # Retry cancel dengan refund_amount yang VALID (≤ paid_before)
    # Idempotent guard akan mencegah duplikasi payment refund
    retry_refund = min(50000, paid_before)  # Use valid amount
    resp = cancel_booking(booking_id, reason="retry test", cancellation_fee=0, refund_amount=retry_refund)
    assert resp.status_code == 200, f"Retry cancel failed: {resp.status_code} {resp.text}"
    print(f"✓ Retry cancel with refund={retry_refund}")
    
    # Verifikasi: masih hanya 1 payment type=refund (tidak duplikat)
    payments_after = get_payments(booking_id)
    refund_count_after = len([p for p in payments_after if p["type"] == "refund"])
    assert refund_count_after == refund_count_before, f"Expected {refund_count_before} refund payment, got {refund_count_after} (duplicate detected!)"
    print(f"✓ Verified: Still only {refund_count_after} refund payment (no duplicate)")
    
    # paid_amount tetap (refund tidak berubah karena idempotent guard)
    booking = get_booking(booking_id)
    assert booking["paid_amount"] == paid_before, f"Expected paid_amount={paid_before}, got {booking['paid_amount']} (should not change)"
    print(f"✓ Verified: paid_amount unchanged ({paid_before})")
    
    # Field refund_amount di booking BOLEH ter-update (metadata booking)
    # tapi kas ledger TIDAK berubah karena idempotent guard
    print(f"  Note: booking.refund_amount={booking['refund_amount']} (metadata may update, but ledger unchanged)")
    
    print("✅ R2 PASS: Idempotent retry cancel")


def test_r3_refund_zero_no_payment():
    """R3. Refund = 0 → tidak ada payment refund."""
    print("\n=== R3: Refund = 0 → no payment refund ===")
    
    # 1. Buat booking baru + bayar sebagian
    booking = create_booking(base_price=400000)
    booking_id = booking["id"]
    create_payment(booking_id, 150000, "dp")
    print(f"✓ Created booking {booking['code']} with payment 150000")
    
    # 2. Cancel dgn refund_amount=0
    resp = cancel_booking(booking_id, reason="test zero refund", cancellation_fee=0, refund_amount=0)
    assert resp.status_code == 200, f"Cancel failed: {resp.status_code} {resp.text}"
    print(f"✓ Cancelled with refund=0")
    
    # 3. Verifikasi: TIDAK ADA payment type=refund
    payments = get_payments(booking_id)
    refund_payments = [p for p in payments if p["type"] == "refund"]
    assert len(refund_payments) == 0, f"Expected 0 refund payments, got {len(refund_payments)}"
    print(f"✓ Verified: No refund payment created")
    
    # 4. paid_amount TIDAK berkurang (tetap 150000)
    booking = get_booking(booking_id)
    assert booking["paid_amount"] == 150000, f"Expected paid_amount=150000, got {booking['paid_amount']}"
    print(f"✓ Verified: paid_amount unchanged (150000)")
    
    print("✅ R3 PASS: Refund = 0 → no payment refund")


def test_r4_refund_full_paid():
    """R4. Refund = full paid (semua uang dikembalikan, paid_amount=0)."""
    print("\n=== R4: Refund = full paid ===")
    
    # 1. Buat booking + bayar full
    booking = create_booking(base_price=500000)
    booking_id = booking["id"]
    total = booking["total_amount"]
    create_payment(booking_id, total, "settlement")
    print(f"✓ Created booking {booking['code']} with full payment {total}")
    
    # Verify lunas
    booking = get_booking(booking_id)
    assert booking["payment_status"] == "lunas", f"Expected payment_status=lunas, got {booking['payment_status']}"
    print(f"✓ Verified: payment_status=lunas")
    
    # 2. Cancel dgn refund_amount=full paid
    resp = cancel_booking(booking_id, reason="full refund", cancellation_fee=0, refund_amount=total)
    assert resp.status_code == 200, f"Cancel failed: {resp.status_code} {resp.text}"
    print(f"✓ Cancelled with refund={total} (full paid)")
    
    # 3. Verifikasi: paid_amount == 0
    booking = get_booking(booking_id)
    assert booking["paid_amount"] == 0, f"Expected paid_amount=0, got {booking['paid_amount']}"
    print(f"✓ Verified: paid_amount=0")
    
    # 4. payment_status == "belum_bayar" (paid <= 0)
    assert booking["payment_status"] == "belum_bayar", f"Expected payment_status=belum_bayar, got {booking['payment_status']}"
    print(f"✓ Verified: payment_status=belum_bayar")
    
    # 5. Refund payment tercatat -total
    payments = get_payments(booking_id)
    refund_payment = next((p for p in payments if p["type"] == "refund"), None)
    assert refund_payment is not None, "Refund payment not found"
    assert refund_payment["amount"] == -total, f"Expected refund amount=-{total}, got {refund_payment['amount']}"
    print(f"✓ Verified: Refund payment -{total} recorded")
    
    print("✅ R4 PASS: Refund = full paid")


def test_r5_inv2_inv3_consistency(booking_id):
    """R5. INV-2 & INV-3 tetap konsisten setelah refund."""
    print("\n=== R5: INV-2 & INV-3 consistency ===")
    
    # Get booking & payments
    booking = get_booking(booking_id)
    payments = get_payments(booking_id)
    
    # INV-2: Σ payments == paid_amount
    sum_payments = sum(p["amount"] for p in payments)
    assert sum_payments == booking["paid_amount"], f"INV-2 violated: Σ payments={sum_payments}, paid_amount={booking['paid_amount']}"
    print(f"✓ INV-2: Σ payments = {sum_payments} == paid_amount = {booking['paid_amount']}")
    
    # INV-3: payment_status derived correctly
    paid = booking["paid_amount"]
    total = booking["total_amount"]
    expected_status = "belum_bayar" if paid <= 0 else ("lunas" if paid >= total else "dp")
    assert booking["payment_status"] == expected_status, f"INV-3 violated: expected {expected_status}, got {booking['payment_status']}"
    print(f"✓ INV-3: payment_status = {booking['payment_status']} (derived from paid={paid}, total={total})")
    
    print("✅ R5 PASS: INV-2 & INV-3 consistent")


def test_r6_finance_reports_200():
    """R6. Finance reports masih 200."""
    print("\n=== R6: Finance reports 200 ===")
    
    endpoints = [
        "/finance/pl-full",
        "/finance/ar",
        "/finance/summary",
        "/finance/cashflow",
        "/reports/summary",
        "/dashboard"
    ]
    
    for endpoint in endpoints:
        resp = session.get(f"{API_URL}{endpoint}")
        assert resp.status_code == 200, f"{endpoint} failed: {resp.status_code} {resp.text}"
        # Verify valid JSON
        data = resp.json()
        assert isinstance(data, (dict, list)), f"{endpoint} returned invalid JSON"
        print(f"✓ {endpoint} → 200")
    
    # Verify pl-full mencerminkan refund (revenue berkurang)
    pl = session.get(f"{API_URL}/finance/pl-full").json()
    assert "revenue" in pl, "pl-full missing 'revenue' field"
    print(f"  pl-full revenue: {pl.get('revenue', 0)}")
    
    print("✅ R6 PASS: Finance reports 200")


def test_r7_rc05_no_conflict():
    """R7. RC-05 tidak konflik — manual payment ke cancelled booking → 400."""
    print("\n=== R7: RC-05 no conflict ===")
    
    # Buat booking + cancel
    booking = create_booking(base_price=300000)
    booking_id = booking["id"]
    resp = cancel_booking(booking_id, reason="test rc05", cancellation_fee=0, refund_amount=0)
    assert resp.status_code == 200, f"Cancel failed: {resp.status_code} {resp.text}"
    print(f"✓ Cancelled booking {booking['code']}")
    
    # Coba POST payment manual (bukan via cancel) → HARUS 400
    resp = session.post(f"{API_URL}/payments", json={
        "booking_id": booking_id,
        "amount": 100000,
        "type": "dp",
        "method": "transfer"
    })
    assert resp.status_code == 400, f"Expected 400 for payment to cancelled booking, got {resp.status_code}"
    assert "dibatalkan" in resp.text.lower() or "cancelled" in resp.text.lower(), f"Expected error message about cancelled booking, got: {resp.text}"
    print(f"✓ Verified: Manual payment to cancelled booking → 400 'Booking dibatalkan'")
    
    print("✅ R7 PASS: RC-05 no conflict")


def test_r8_e20_e21_base_scenarios():
    """R8. E20 & E21 base scenarios masih PASS."""
    print("\n=== R8: E20 & E21 base scenarios ===")
    
    # E20: POST /bookings/group 2 unit → 200 + group_id
    customers = session.get(f"{API_URL}/customers").json()
    vehicles = session.get(f"{API_URL}/vehicles").json()
    customer_id = customers[0]["id"]
    vehicle1_id = vehicles[0]["id"]
    vehicle2_id = vehicles[1]["id"] if len(vehicles) > 1 else vehicles[0]["id"]
    
    start1 = (datetime.utcnow() + timedelta(days=10)).isoformat()
    end1 = (datetime.utcnow() + timedelta(days=11)).isoformat()
    start2 = (datetime.utcnow() + timedelta(days=12)).isoformat()
    end2 = (datetime.utcnow() + timedelta(days=13)).isoformat()
    
    resp = session.post(f"{API_URL}/bookings/group", json={
        "customer_id": customer_id,
        "units": [
            {
                "vehicle_id": vehicle1_id,
                "start_datetime": start1,
                "end_datetime": end1,
                "base_price": 500000,
                "origin": "Jakarta",
                "destination": "Bandung"
            },
            {
                "vehicle_id": vehicle2_id,
                "start_datetime": start2,
                "end_datetime": end2,
                "base_price": 600000,
                "origin": "Jakarta",
                "destination": "Surabaya"
            }
        ]
    })
    assert resp.status_code == 200, f"Group booking failed: {resp.status_code} {resp.text}"
    group_data = resp.json()
    assert "group_id" in group_data, "Missing group_id in response"
    assert group_data["count"] == 2, f"Expected count=2, got {group_data['count']}"
    print(f"✓ E20: Group booking 2 units → 200, group_id={group_data['group_id']}")
    
    # E21: POST /cancel tanpa body → 200 (backward compat)
    booking = create_booking(base_price=300000)
    booking_id = booking["id"]
    resp = session.post(f"{API_URL}/bookings/{booking_id}/cancel")
    assert resp.status_code == 200, f"Cancel without body failed: {resp.status_code} {resp.text}"
    booking = get_booking(booking_id)
    assert booking["status"] == "cancelled", f"Expected status=cancelled, got {booking['status']}"
    assert booking.get("cancellation_reason", "") == "", "Expected empty reason"
    assert booking.get("cancellation_fee", 0) == 0, "Expected fee=0"
    assert booking.get("refund_amount", 0) == 0, "Expected refund=0"
    print(f"✓ E21: Cancel without body → 200 (backward compat)")
    
    # E21: POST /cancel dgn refund > paid → 400
    booking = create_booking(base_price=400000)
    booking_id = booking["id"]
    create_payment(booking_id, 100000, "dp")
    resp = cancel_booking(booking_id, reason="test", cancellation_fee=0, refund_amount=200000)
    assert resp.status_code == 400, f"Expected 400 for refund > paid, got {resp.status_code}"
    assert "melebihi" in resp.text.lower() or "exceed" in resp.text.lower(), f"Expected error about exceeding paid, got: {resp.text}"
    print(f"✓ E21: Cancel with refund > paid → 400 'melebihi terbayar'")
    
    print("✅ R8 PASS: E20 & E21 base scenarios")


def main():
    print("=" * 80)
    print("E21 LEDGER REFUND POSTING — REGRESSION TEST")
    print("=" * 80)
    
    try:
        # Login
        login()
        
        # Run tests
        booking_id_r1 = test_r1_refund_posting_success()
        test_r2_idempotent_retry_cancel(booking_id_r1)
        test_r3_refund_zero_no_payment()
        test_r4_refund_full_paid()
        test_r5_inv2_inv3_consistency(booking_id_r1)
        test_r6_finance_reports_200()
        test_r7_rc05_no_conflict()
        test_r8_e20_e21_base_scenarios()
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED (8/8)")
        print("=" * 80)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
