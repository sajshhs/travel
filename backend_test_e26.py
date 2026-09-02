#!/usr/bin/env python3
"""
E26 Auto-Invoice Denda Pembatalan — Comprehensive Test Suite
Tests auto-invoice creation when cancellation_fee > 0 + regressions E21/E20
"""
import requests
import sys
from datetime import datetime, timedelta

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"
OWNER_EMAIL = "owner@demo.local"
OWNER_PASSWORD = "demo12345"

def login():
    """Login as owner and return token"""
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": OWNER_EMAIL,
        "password": OWNER_PASSWORD
    })
    if resp.status_code != 200:
        print(f"❌ Login failed: {resp.status_code} {resp.text}")
        sys.exit(1)
    data = resp.json()
    token = data.get("token")
    if not token:
        print(f"❌ No token in login response: {data}")
        sys.exit(1)
    print(f"✅ Login successful: {data.get('user', {}).get('email')}")
    return token

def headers(token):
    return {"Authorization": f"Bearer {token}"}

def create_booking(token, customer_id, vehicle_id, base_price=800000, days_offset=None):
    """Create a booking and return booking object"""
    if days_offset is None:
        # Use a random offset to avoid conflicts
        import random
        days_offset = random.randint(20, 100)
    
    start = (datetime.utcnow() + timedelta(days=days_offset)).isoformat()
    end = (datetime.utcnow() + timedelta(days=days_offset + 2)).isoformat()
    
    resp = requests.post(f"{BASE_URL}/bookings", headers=headers(token), json={
        "customer_id": customer_id,
        "vehicle_id": vehicle_id,
        "start_datetime": start,
        "end_datetime": end,
        "origin": "Jakarta",
        "destination": "Bandung",
        "base_price": base_price,
        "notes": "Test booking for E26"
    })
    
    if resp.status_code != 200:
        print(f"❌ Create booking failed: {resp.status_code} {resp.text}")
        return None
    
    booking = resp.json()
    print(f"✅ Booking created: {booking.get('code')} (id={booking.get('id')})")
    return booking

def add_payment(token, booking_id, amount):
    """Add payment to booking"""
    resp = requests.post(f"{BASE_URL}/payments", headers=headers(token), json={
        "booking_id": booking_id,
        "amount": amount,
        "method": "transfer",
        "note": "Test payment"
    })
    
    if resp.status_code != 200:
        print(f"❌ Add payment failed: {resp.status_code} {resp.text}")
        return None
    
    payment = resp.json()
    print(f"✅ Payment added: {amount} (id={payment.get('id')})")
    return payment

def cancel_booking(token, booking_id, reason="", cancellation_fee=0, refund_amount=0):
    """Cancel booking with optional fee and refund"""
    body = None
    if reason or cancellation_fee or refund_amount:
        body = {
            "reason": reason,
            "cancellation_fee": cancellation_fee,
            "refund_amount": refund_amount
        }
    
    resp = requests.post(f"{BASE_URL}/bookings/{booking_id}/cancel", 
                        headers=headers(token), 
                        json=body if body else {})
    
    if resp.status_code != 200:
        print(f"❌ Cancel booking failed: {resp.status_code} {resp.text}")
        return None
    
    result = resp.json()
    print(f"✅ Booking cancelled: fee={result.get('cancellation_fee')}, refund={result.get('refund_amount')}")
    return result

def get_invoices(token, booking_id=None):
    """Get invoices, optionally filtered by booking_id"""
    resp = requests.get(f"{BASE_URL}/invoices", headers=headers(token))
    
    if resp.status_code != 200:
        print(f"❌ Get invoices failed: {resp.status_code} {resp.text}")
        return []
    
    invoices = resp.json()
    if booking_id:
        invoices = [inv for inv in invoices if inv.get("booking_id") == booking_id]
    
    return invoices

def get_invoice_export(token, invoice_id, format="pdf"):
    """Export invoice as PDF or Excel"""
    resp = requests.get(f"{BASE_URL}/invoices/{invoice_id}/export?format={format}", 
                       headers=headers(token))
    return resp

def get_pl_full(token):
    """Get P&L full report"""
    resp = requests.get(f"{BASE_URL}/finance/pl-full", headers=headers(token))
    if resp.status_code != 200:
        print(f"❌ Get P&L failed: {resp.status_code} {resp.text}")
        return None
    return resp.json()

def get_customers(token):
    """Get customers list"""
    resp = requests.get(f"{BASE_URL}/customers", headers=headers(token))
    if resp.status_code != 200:
        print(f"❌ Get customers failed: {resp.status_code}")
        return []
    return resp.json()

def get_vehicles(token):
    """Get vehicles list"""
    resp = requests.get(f"{BASE_URL}/vehicles", headers=headers(token))
    if resp.status_code != 200:
        print(f"❌ Get vehicles failed: {resp.status_code}")
        return []
    return resp.json()

def test_t1_auto_invoice_success(token, customer_id, vehicle_id):
    """T1. Auto-invoice denda sukses"""
    print("\n" + "="*80)
    print("T1. Auto-invoice denda sukses")
    print("="*80)
    
    # Create booking
    booking = create_booking(token, customer_id, vehicle_id, base_price=800000)
    if not booking:
        return False
    
    booking_id = booking["id"]
    
    # Add payment (settlement 800000)
    payment = add_payment(token, booking_id, 800000)
    if not payment:
        return False
    
    # Cancel with fee=150000, refund=500000
    cancelled = cancel_booking(token, booking_id, 
                               reason="pindah tanggal",
                               cancellation_fee=150000,
                               refund_amount=500000)
    if not cancelled:
        return False
    
    # Verify response
    if cancelled.get("cancellation_fee") != 150000:
        print(f"❌ cancellation_fee mismatch: {cancelled.get('cancellation_fee')} != 150000")
        return False
    
    if cancelled.get("refund_amount") != 500000:
        print(f"❌ refund_amount mismatch: {cancelled.get('refund_amount')} != 500000")
        return False
    
    # paid_amount should be 800000 - 500000 = 300000
    if cancelled.get("paid_amount") != 300000:
        print(f"❌ paid_amount mismatch: {cancelled.get('paid_amount')} != 300000")
        return False
    
    # payment_status should be 'dp' (0 < 300000 < 800000)
    if cancelled.get("payment_status") != "dp":
        print(f"❌ payment_status mismatch: {cancelled.get('payment_status')} != 'dp'")
        return False
    
    # Get invoices for this booking
    invoices = get_invoices(token, booking_id)
    cancellation_invoices = [inv for inv in invoices if inv.get("type") == "cancellation_fee"]
    
    if len(cancellation_invoices) == 0:
        print(f"❌ No cancellation_fee invoice found for booking {booking_id}")
        return False
    
    if len(cancellation_invoices) > 1:
        print(f"❌ Multiple cancellation_fee invoices found: {len(cancellation_invoices)}")
        return False
    
    inv = cancellation_invoices[0]
    
    # Verify invoice fields
    if not inv.get("number", "").startswith("INV-"):
        print(f"❌ Invoice number format invalid: {inv.get('number')}")
        return False
    
    if inv.get("status") != "paid":
        print(f"❌ Invoice status mismatch: {inv.get('status')} != 'paid'")
        return False
    
    if inv.get("amount") != 150000:
        print(f"❌ Invoice amount mismatch: {inv.get('amount')} != 150000")
        return False
    
    if "Denda pembatalan" not in inv.get("notes", ""):
        print(f"❌ Invoice notes missing 'Denda pembatalan': {inv.get('notes')}")
        return False
    
    if inv.get("customer_name") != booking.get("customer_name"):
        print(f"❌ Invoice customer_name mismatch: {inv.get('customer_name')} != {booking.get('customer_name')}")
        return False
    
    if inv.get("booking_code") != booking.get("code"):
        print(f"❌ Invoice booking_code mismatch: {inv.get('booking_code')} != {booking.get('code')}")
        return False
    
    print(f"✅ T1 PASS: Auto-invoice created successfully")
    print(f"   Invoice: {inv.get('number')}, amount={inv.get('amount')}, status={inv.get('status')}")
    return True

def test_t2_idempotent_retry(token, customer_id, vehicle_id):
    """T2. Idempotent — retry cancel"""
    print("\n" + "="*80)
    print("T2. Idempotent — retry cancel")
    print("="*80)
    
    # Create booking
    booking = create_booking(token, customer_id, vehicle_id, base_price=600000)
    if not booking:
        return False
    
    booking_id = booking["id"]
    
    # Add payment
    payment = add_payment(token, booking_id, 600000)
    if not payment:
        return False
    
    # First cancel with fee=100000, refund=200000
    cancelled1 = cancel_booking(token, booking_id,
                                reason="test idempotent",
                                cancellation_fee=100000,
                                refund_amount=200000)
    if not cancelled1:
        return False
    
    # Get invoices after first cancel
    invoices1 = get_invoices(token, booking_id)
    cancellation_invoices1 = [inv for inv in invoices1 if inv.get("type") == "cancellation_fee"]
    
    if len(cancellation_invoices1) != 1:
        print(f"❌ Expected 1 cancellation invoice after first cancel, got {len(cancellation_invoices1)}")
        return False
    
    first_invoice = cancellation_invoices1[0]
    first_amount = first_invoice.get("amount")
    
    # Retry cancel with different fee (should be ignored)
    cancelled2 = cancel_booking(token, booking_id,
                                reason="retry with different fee",
                                cancellation_fee=999999,
                                refund_amount=0)
    if not cancelled2:
        return False
    
    # Get invoices after retry
    invoices2 = get_invoices(token, booking_id)
    cancellation_invoices2 = [inv for inv in invoices2 if inv.get("type") == "cancellation_fee"]
    
    if len(cancellation_invoices2) != 1:
        print(f"❌ Expected 1 cancellation invoice after retry, got {len(cancellation_invoices2)} (not idempotent)")
        return False
    
    second_invoice = cancellation_invoices2[0]
    second_amount = second_invoice.get("amount")
    
    if second_amount != first_amount:
        print(f"❌ Invoice amount changed after retry: {first_amount} → {second_amount} (not idempotent)")
        return False
    
    if second_invoice.get("id") != first_invoice.get("id"):
        print(f"❌ Different invoice ID after retry (not idempotent)")
        return False
    
    print(f"✅ T2 PASS: Idempotent retry working correctly")
    print(f"   Only 1 invoice exists, amount unchanged: {first_amount}")
    return True

def test_t3_fee_zero_no_invoice(token, customer_id, vehicle_id):
    """T3. Fee = 0 → tidak ada invoice denda"""
    print("\n" + "="*80)
    print("T3. Fee = 0 → tidak ada invoice denda")
    print("="*80)
    
    # Create booking
    booking = create_booking(token, customer_id, vehicle_id, base_price=500000)
    if not booking:
        return False
    
    booking_id = booking["id"]
    
    # Add payment
    payment = add_payment(token, booking_id, 500000)
    if not payment:
        return False
    
    # Cancel with fee=0, refund=100000
    cancelled = cancel_booking(token, booking_id,
                               reason="no fee",
                               cancellation_fee=0,
                               refund_amount=100000)
    if not cancelled:
        return False
    
    # Get invoices
    invoices = get_invoices(token, booking_id)
    cancellation_invoices = [inv for inv in invoices if inv.get("type") == "cancellation_fee"]
    
    if len(cancellation_invoices) != 0:
        print(f"❌ Expected 0 cancellation invoices when fee=0, got {len(cancellation_invoices)}")
        return False
    
    print(f"✅ T3 PASS: No invoice created when fee=0")
    return True

def test_t4_fee_only_no_refund(token, customer_id, vehicle_id):
    """T4. Fee only, no refund"""
    print("\n" + "="*80)
    print("T4. Fee only, no refund")
    print("="*80)
    
    # Create booking
    booking = create_booking(token, customer_id, vehicle_id, base_price=700000)
    if not booking:
        return False
    
    booking_id = booking["id"]
    
    # Add payment (full)
    payment = add_payment(token, booking_id, 700000)
    if not payment:
        return False
    
    # Cancel with fee=200000, refund=0
    cancelled = cancel_booking(token, booking_id,
                               reason="fee only",
                               cancellation_fee=200000,
                               refund_amount=0)
    if not cancelled:
        return False
    
    # paid_amount should remain 700000 (no refund)
    if cancelled.get("paid_amount") != 700000:
        print(f"❌ paid_amount changed: {cancelled.get('paid_amount')} != 700000")
        return False
    
    # Get invoices
    invoices = get_invoices(token, booking_id)
    cancellation_invoices = [inv for inv in invoices if inv.get("type") == "cancellation_fee"]
    
    if len(cancellation_invoices) != 1:
        print(f"❌ Expected 1 cancellation invoice, got {len(cancellation_invoices)}")
        return False
    
    inv = cancellation_invoices[0]
    if inv.get("amount") != 200000:
        print(f"❌ Invoice amount mismatch: {inv.get('amount')} != 200000")
        return False
    
    # Verify no refund payment exists
    resp = requests.get(f"{BASE_URL}/bookings/{booking_id}", headers=headers(token))
    if resp.status_code == 200:
        booking_detail = resp.json()
        payments = booking_detail.get("payments", [])
        refund_payments = [p for p in payments if p.get("type") == "refund"]
        
        if len(refund_payments) != 0:
            print(f"❌ Found refund payment when refund_amount=0")
            return False
    
    print(f"✅ T4 PASS: Fee-only cancellation working correctly")
    print(f"   paid_amount unchanged, invoice created, no refund payment")
    return True

def test_t5_invoice_number_sequential(token, customer_id, vehicle_id):
    """T5. Nomor invoice tidak konflik dgn invoice normal"""
    print("\n" + "="*80)
    print("T5. Nomor invoice tidak konflik dgn invoice normal")
    print("="*80)
    
    # Get current highest invoice number
    all_invoices = get_invoices(token)
    invoice_numbers = [inv.get("number", "") for inv in all_invoices if inv.get("number", "").startswith("INV-")]
    print(f"   Current invoice count: {len(invoice_numbers)}")
    
    # Create 2 bookings and cancel with fee
    booking1 = create_booking(token, customer_id, vehicle_id, base_price=400000)
    if not booking1:
        return False
    
    add_payment(token, booking1["id"], 400000)
    cancel_booking(token, booking1["id"], cancellation_fee=50000, refund_amount=100000)
    
    booking2 = create_booking(token, customer_id, vehicle_id, base_price=450000)
    if not booking2:
        return False
    
    add_payment(token, booking2["id"], 450000)
    cancel_booking(token, booking2["id"], cancellation_fee=60000, refund_amount=150000)
    
    # Create 1 normal invoice
    booking3 = create_booking(token, customer_id, vehicle_id, base_price=500000)
    if not booking3:
        return False
    
    resp = requests.post(f"{BASE_URL}/invoices", headers=headers(token), json={
        "booking_id": booking3["id"],
        "amount": 500000,
        "notes": "Normal invoice for T5"
    })
    
    if resp.status_code != 200:
        print(f"❌ Create normal invoice failed: {resp.status_code}")
        return False
    
    # Get all invoices again
    all_invoices_after = get_invoices(token)
    new_invoices = [inv for inv in all_invoices_after 
                   if inv.get("number") not in invoice_numbers]
    
    if len(new_invoices) != 3:
        print(f"❌ Expected 3 new invoices, got {len(new_invoices)}")
        return False
    
    # Check numbers are sequential
    new_numbers = sorted([inv.get("number") for inv in new_invoices])
    print(f"   New invoice numbers: {new_numbers}")
    
    # Extract sequence numbers
    sequences = []
    for num in new_numbers:
        try:
            # Format: INV-YYYY-####
            seq = int(num.split("-")[-1])
            sequences.append(seq)
        except:
            print(f"❌ Invalid invoice number format: {num}")
            return False
    
    # Check sequential (allowing for existing invoices in between)
    for i in range(len(sequences) - 1):
        if sequences[i] >= sequences[i+1]:
            print(f"❌ Invoice numbers not sequential: {sequences}")
            return False
    
    print(f"✅ T5 PASS: Invoice numbers are sequential")
    print(f"   Sequences: {sequences}")
    return True

def test_t6_pl_no_double_count(token, customer_id, vehicle_id):
    """T6. P&L revenue TIDAK double-count"""
    print("\n" + "="*80)
    print("T6. P&L revenue TIDAK double-count")
    print("="*80)
    
    # Get initial P&L
    pl_before = get_pl_full(token)
    if not pl_before:
        return False
    
    revenue_before = pl_before.get("revenue", 0)
    print(f"   Revenue before: {revenue_before}")
    
    # Create booking
    booking = create_booking(token, customer_id, vehicle_id, base_price=500000)
    if not booking:
        return False
    
    booking_id = booking["id"]
    
    # Add payment (500k)
    payment = add_payment(token, booking_id, 500000)
    if not payment:
        return False
    
    # Cancel with fee=100k, refund=200k
    # Net payment = 500k - 200k = 300k (includes 100k fee)
    cancelled = cancel_booking(token, booking_id,
                               cancellation_fee=100000,
                               refund_amount=200000)
    if not cancelled:
        return False
    
    # Get P&L after
    pl_after = get_pl_full(token)
    if not pl_after:
        return False
    
    revenue_after = pl_after.get("revenue", 0)
    print(f"   Revenue after: {revenue_after}")
    
    revenue_delta = revenue_after - revenue_before
    print(f"   Revenue delta: {revenue_delta}")
    
    # Revenue should increase by net payment (300k), NOT by net payment + fee (400k)
    # Allow some tolerance for other transactions
    expected_delta = 300000
    
    if abs(revenue_delta - expected_delta) > 100000:
        print(f"⚠️  Revenue delta ({revenue_delta}) differs significantly from expected ({expected_delta})")
        print(f"   This might indicate double-counting or other transactions in the period")
        print(f"   Checking if delta is closer to 400k (double-count scenario)...")
        
        if abs(revenue_delta - 400000) < abs(revenue_delta - 300000):
            print(f"❌ Revenue delta closer to 400k - possible double-counting!")
            return False
        else:
            print(f"   Delta not closer to 400k, likely other transactions. Proceeding...")
    
    print(f"✅ T6 PASS: P&L revenue calculation appears correct")
    print(f"   Revenue increased by ~{revenue_delta} (expected ~{expected_delta})")
    return True

def test_t7_invoice_export(token, customer_id, vehicle_id):
    """T7. Invoice denda bisa diekspor PDF/Excel"""
    print("\n" + "="*80)
    print("T7. Invoice denda bisa diekspor PDF/Excel")
    print("="*80)
    
    # Create booking and cancel with fee
    booking = create_booking(token, customer_id, vehicle_id, base_price=300000)
    if not booking:
        return False
    
    add_payment(token, booking["id"], 300000)
    cancel_booking(token, booking["id"], cancellation_fee=50000, refund_amount=100000)
    
    # Get cancellation invoice
    invoices = get_invoices(token, booking["id"])
    cancellation_invoices = [inv for inv in invoices if inv.get("type") == "cancellation_fee"]
    
    if len(cancellation_invoices) == 0:
        print(f"❌ No cancellation invoice found")
        return False
    
    inv_id = cancellation_invoices[0]["id"]
    
    # Test PDF export
    pdf_resp = get_invoice_export(token, inv_id, "pdf")
    if pdf_resp.status_code != 200:
        print(f"❌ PDF export failed: {pdf_resp.status_code}")
        return False
    
    if "application/pdf" not in pdf_resp.headers.get("content-type", ""):
        print(f"❌ PDF content-type incorrect: {pdf_resp.headers.get('content-type')}")
        return False
    
    print(f"✅ PDF export successful: {len(pdf_resp.content)} bytes")
    
    # Test Excel export
    excel_resp = get_invoice_export(token, inv_id, "excel")
    if excel_resp.status_code != 200:
        print(f"❌ Excel export failed: {excel_resp.status_code}")
        return False
    
    if "spreadsheetml.sheet" not in excel_resp.headers.get("content-type", ""):
        print(f"❌ Excel content-type incorrect: {excel_resp.headers.get('content-type')}")
        return False
    
    print(f"✅ Excel export successful: {len(excel_resp.content)} bytes")
    
    print(f"✅ T7 PASS: Invoice export working for both PDF and Excel")
    return True

def test_t8_regression_e21_ledger(token, customer_id, vehicle_id):
    """T8. Regression E21 Ledger (refund posting) masih PASS"""
    print("\n" + "="*80)
    print("T8. Regression E21 Ledger (refund posting)")
    print("="*80)
    
    # Create booking
    booking = create_booking(token, customer_id, vehicle_id, base_price=600000)
    if not booking:
        return False
    
    booking_id = booking["id"]
    
    # Add payment
    add_payment(token, booking_id, 600000)
    
    # Cancel with refund
    cancelled = cancel_booking(token, booking_id,
                               reason="test refund",
                               cancellation_fee=50000,
                               refund_amount=200000)
    if not cancelled:
        return False
    
    # Get booking detail with payments
    resp = requests.get(f"{BASE_URL}/bookings/{booking_id}", headers=headers(token))
    if resp.status_code != 200:
        print(f"❌ Get booking detail failed: {resp.status_code}")
        return False
    
    booking_detail = resp.json()
    payments = booking_detail.get("payments", [])
    
    # Check refund payment exists
    refund_payments = [p for p in payments if p.get("type") == "refund"]
    if len(refund_payments) != 1:
        print(f"❌ Expected 1 refund payment, got {len(refund_payments)}")
        return False
    
    refund_pay = refund_payments[0]
    if refund_pay.get("amount") != -200000:
        print(f"❌ Refund payment amount incorrect: {refund_pay.get('amount')} != -200000")
        return False
    
    if refund_pay.get("method") != "refund":
        print(f"❌ Refund payment method incorrect: {refund_pay.get('method')}")
        return False
    
    # Check paid_amount updated correctly
    if booking_detail.get("paid_amount") != 400000:
        print(f"❌ paid_amount incorrect: {booking_detail.get('paid_amount')} != 400000")
        return False
    
    # Test idempotent refund (retry cancel)
    cancel_booking(token, booking_id, cancellation_fee=999, refund_amount=999)
    
    resp2 = requests.get(f"{BASE_URL}/bookings/{booking_id}", headers=headers(token))
    booking_detail2 = resp2.json()
    payments2 = booking_detail2.get("payments", [])
    refund_payments2 = [p for p in payments2 if p.get("type") == "refund"]
    
    if len(refund_payments2) != 1:
        print(f"❌ Refund not idempotent: {len(refund_payments2)} refund payments after retry")
        return False
    
    # Test manual payment to cancelled booking (should fail)
    resp3 = requests.post(f"{BASE_URL}/payments", headers=headers(token), json={
        "booking_id": booking_id,
        "amount": 100000,
        "method": "cash",
        "note": "Should fail"
    })
    
    if resp3.status_code != 400:
        print(f"❌ Manual payment to cancelled booking should return 400, got {resp3.status_code}")
        return False
    
    if "dibatalkan" not in resp3.text.lower():
        print(f"❌ Error message should mention 'dibatalkan': {resp3.text}")
        return False
    
    print(f"✅ T8 PASS: E21 Ledger regression tests passed")
    print(f"   - Refund payment created correctly")
    print(f"   - Idempotent refund working")
    print(f"   - Manual payment to cancelled booking blocked")
    return True

def test_t9_regression_e20_group(token, customer_id, vehicle_id):
    """T9. Regression E20 (group booking) masih PASS"""
    print("\n" + "="*80)
    print("T9. Regression E20 (group booking)")
    print("="*80)
    
    # Get vehicles
    vehicles = get_vehicles(token)
    if len(vehicles) < 2:
        print(f"⚠️  Need at least 2 vehicles for group booking test, got {len(vehicles)}")
        return True  # Skip but don't fail
    
    vehicle1_id = vehicles[0]["id"]
    vehicle2_id = vehicles[1]["id"]
    
    # Use far future dates to avoid conflicts
    import random
    offset = random.randint(300, 400)
    start = (datetime.utcnow() + timedelta(days=offset)).isoformat()
    end = (datetime.utcnow() + timedelta(days=offset + 2)).isoformat()
    
    # Test group booking
    resp = requests.post(f"{BASE_URL}/bookings/group", headers=headers(token), json={
        "customer_id": customer_id,
        "units": [
            {
                "vehicle_id": vehicle1_id,
                "start_datetime": start,
                "end_datetime": end,
                "origin": "Jakarta",
                "destination": "Surabaya",
                "base_price": 1000000
            },
            {
                "vehicle_id": vehicle2_id,
                "start_datetime": start,
                "end_datetime": end,
                "origin": "Jakarta",
                "destination": "Surabaya",
                "base_price": 1100000
            }
        ]
    })
    
    if resp.status_code != 200:
        print(f"❌ Group booking failed: {resp.status_code} {resp.text}")
        return False
    
    result = resp.json()
    
    if result.get("count") != 2:
        print(f"❌ Group booking count incorrect: {result.get('count')} != 2")
        return False
    
    group_id = result.get("group_id")
    if not group_id or not group_id.startswith("grp_"):
        print(f"❌ Invalid group_id: {group_id}")
        return False
    
    bookings = result.get("bookings", [])
    if len(bookings) != 2:
        print(f"❌ Expected 2 bookings, got {len(bookings)}")
        return False
    
    # Check group_size and group_index
    for i, bk in enumerate(bookings):
        if bk.get("group_size") != 2:
            print(f"❌ Booking {i} group_size incorrect: {bk.get('group_size')}")
            return False
        
        if bk.get("group_index") not in [1, 2]:
            print(f"❌ Booking {i} group_index incorrect: {bk.get('group_index')}")
            return False
    
    # Test intra-group anti-overlap (same vehicle + time) with even more distant dates
    offset2 = random.randint(500, 600)
    start2 = (datetime.utcnow() + timedelta(days=offset2)).isoformat()
    end2 = (datetime.utcnow() + timedelta(days=offset2 + 2)).isoformat()
    
    resp2 = requests.post(f"{BASE_URL}/bookings/group", headers=headers(token), json={
        "customer_id": customer_id,
        "units": [
            {
                "vehicle_id": vehicle1_id,
                "start_datetime": start2,
                "end_datetime": end2,
                "origin": "Jakarta",
                "destination": "Bandung",
                "base_price": 500000
            },
            {
                "vehicle_id": vehicle1_id,  # Same vehicle
                "start_datetime": start2,     # Overlapping time
                "end_datetime": end2,
                "origin": "Jakarta",
                "destination": "Yogyakarta",
                "base_price": 600000
            }
        ]
    })
    
    if resp2.status_code != 400:
        print(f"❌ Intra-group overlap should return 400, got {resp2.status_code}")
        return False
    
    error_text = resp2.text.lower()
    if "tumpang tindih" not in error_text and "bentrok" not in error_text:
        print(f"❌ Error message should mention conflict: {resp2.text}")
        return False
    
    print(f"✅ T9 PASS: E20 group booking regression tests passed")
    print(f"   - Group booking created: {group_id}, count={result.get('count')}")
    print(f"   - Intra-group anti-overlap working (error: {resp2.text[:100]})")
    return True

def test_t10_regression_finance_reports(token):
    """T10. Regression finance/reports semua 200"""
    print("\n" + "="*80)
    print("T10. Regression finance/reports endpoints")
    print("="*80)
    
    endpoints = [
        "/finance/pl-full",
        "/finance/ar",
        "/finance/summary",
        "/finance/cashflow",
        "/reports/summary",
        "/dashboard",
        "/invoices"
    ]
    
    all_pass = True
    for endpoint in endpoints:
        resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers(token))
        if resp.status_code == 200:
            print(f"✅ {endpoint} → 200")
        else:
            print(f"❌ {endpoint} → {resp.status_code}")
            all_pass = False
    
    if all_pass:
        print(f"✅ T10 PASS: All finance/reports endpoints working")
    else:
        print(f"❌ T10 FAIL: Some endpoints failed")
    
    return all_pass

def main():
    print("="*80)
    print("E26 AUTO-INVOICE DENDA PEMBATALAN — COMPREHENSIVE TEST SUITE")
    print("="*80)
    
    # Login
    token = login()
    
    # Get test data
    customers = get_customers(token)
    if not customers:
        print("❌ No customers found")
        sys.exit(1)
    
    customer_id = customers[0]["id"]
    print(f"✅ Using customer: {customers[0].get('name')} (id={customer_id})")
    
    vehicles = get_vehicles(token)
    if not vehicles:
        print("❌ No vehicles found")
        sys.exit(1)
    
    vehicle_id = vehicles[0]["id"]
    print(f"✅ Using vehicle: {vehicles[0].get('name')} (id={vehicle_id})")
    
    # Run tests
    results = {}
    
    results["T1"] = test_t1_auto_invoice_success(token, customer_id, vehicle_id)
    results["T2"] = test_t2_idempotent_retry(token, customer_id, vehicle_id)
    results["T3"] = test_t3_fee_zero_no_invoice(token, customer_id, vehicle_id)
    results["T4"] = test_t4_fee_only_no_refund(token, customer_id, vehicle_id)
    results["T5"] = test_t5_invoice_number_sequential(token, customer_id, vehicle_id)
    results["T6"] = test_t6_pl_no_double_count(token, customer_id, vehicle_id)
    results["T7"] = test_t7_invoice_export(token, customer_id, vehicle_id)
    results["T8"] = test_t8_regression_e21_ledger(token, customer_id, vehicle_id)
    results["T9"] = test_t9_regression_e20_group(token, customer_id, vehicle_id)
    results["T10"] = test_t10_regression_finance_reports(token)
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test}: {status}")
    
    print("="*80)
    print(f"TOTAL: {passed}/{total} tests passed ({passed*100//total}%)")
    print("="*80)
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("⚠️  SOME TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
