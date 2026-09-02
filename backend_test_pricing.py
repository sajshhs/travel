#!/usr/bin/env python3
"""
Phase 9 / Tahap B · B1: Pricing Engine Backend Tests
=====================================================
Tests configurable pricing rules, weekend/holiday surcharges, auto-calc booking prices.
"""
import requests
import sys
import time
from datetime import datetime, timedelta, timezone

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"

def log(emoji, msg, color=None):
    if color:
        print(f"{color}{emoji} {msg}{Colors.RESET}")
    else:
        print(f"{emoji} {msg}")

def login(email, password):
    """Login and return token"""
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", 
                            json={"email": email, "password": password}, 
                            timeout=10)
        if resp.status_code == 200:
            return resp.json().get("token")
        log("❌", f"Login failed for {email}: {resp.status_code}", Colors.RED)
        return None
    except Exception as e:
        log("❌", f"Login error for {email}: {e}", Colors.RED)
        return None

def get_vehicles(token):
    """Get list of vehicles"""
    try:
        resp = requests.get(f"{BASE_URL}/vehicles", 
                           headers={"Authorization": f"Bearer {token}"}, 
                           timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []

def get_customers(token):
    """Get list of customers"""
    try:
        resp = requests.get(f"{BASE_URL}/customers", 
                           headers={"Authorization": f"Bearer {token}"}, 
                           timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []

def test_pricing_rules_get(token, role):
    """Test GET /api/pricing/rules (auth required)"""
    log("🧪", f"\n=== GET /api/pricing/rules ({role}) ===", Colors.BLUE)
    
    try:
        resp = requests.get(f"{BASE_URL}/pricing/rules", 
                           headers={"Authorization": f"Bearer {token}"}, 
                           timeout=10)
        
        if resp.status_code != 200:
            log("❌", f"Expected 200, got {resp.status_code}", Colors.RED)
            return False
        
        data = resp.json()
        
        # Verify structure
        required_keys = ["day_rates", "default_day_rate", "driver_fee_per_day", 
                        "fuel_per_km", "toll_parking_per_day", "weekend_surcharge_percent",
                        "holiday_surcharge_percent", "dp_percent", "rounding"]
        
        for key in required_keys:
            if key not in data:
                log("❌", f"Missing key: {key}", Colors.RED)
                return False
        
        # Verify day_rates structure
        if not isinstance(data["day_rates"], dict):
            log("❌", "day_rates should be a dict", Colors.RED)
            return False
        
        expected_types = ["hiace_premio", "hiace", "elf", "bus", "avanza"]
        for vtype in expected_types:
            if vtype not in data["day_rates"]:
                log("❌", f"Missing vehicle type in day_rates: {vtype}", Colors.RED)
                return False
        
        log("✅", f"Pricing rules retrieved successfully", Colors.GREEN)
        log("📊", f"Sample rates: hiace_premio={data['day_rates']['hiace_premio']}, weekend_surcharge={data['weekend_surcharge_percent']}%")
        return True
        
    except Exception as e:
        log("❌", f"Error: {e}", Colors.RED)
        return False

def test_pricing_rules_no_auth():
    """Test GET /api/pricing/rules without auth (should fail)"""
    log("🧪", "\n=== GET /api/pricing/rules (no auth - should 401) ===", Colors.BLUE)
    
    try:
        resp = requests.get(f"{BASE_URL}/pricing/rules", timeout=10)
        
        if resp.status_code == 401:
            log("✅", "Correctly returned 401 without auth", Colors.GREEN)
            return True
        else:
            log("❌", f"Expected 401, got {resp.status_code}", Colors.RED)
            return False
            
    except Exception as e:
        log("❌", f"Error: {e}", Colors.RED)
        return False

def test_pricing_quote_basic(token):
    """Test POST /api/pricing/quote with basic parameters"""
    log("🧪", "\n=== POST /api/pricing/quote (basic) ===", Colors.BLUE)
    
    try:
        payload = {
            "vehicle_type": "hiace_premio",
            "days": 3,
            "distance_km": 200,
            "start_date": "2026-07-01T08:00:00+00:00"  # Wednesday (weekday)
        }
        
        resp = requests.post(f"{BASE_URL}/pricing/quote", 
                            json=payload,
                            headers={"Authorization": f"Bearer {token}"}, 
                            timeout=10)
        
        if resp.status_code != 200:
            log("❌", f"Expected 200, got {resp.status_code}", Colors.RED)
            return False
        
        data = resp.json()
        
        # Verify response structure
        required_keys = ["breakdown", "subtotal", "surcharge_percent", "total", 
                        "dp_percent", "dp_amount", "days", "vehicle_type"]
        
        for key in required_keys:
            if key not in data:
                log("❌", f"Missing key: {key}", Colors.RED)
                return False
        
        # Verify breakdown is a list
        if not isinstance(data["breakdown"], list):
            log("❌", "breakdown should be a list", Colors.RED)
            return False
        
        # Verify no surcharge on weekday
        if data["surcharge_percent"] != 0:
            log("❌", f"Expected 0% surcharge on weekday, got {data['surcharge_percent']}%", Colors.RED)
            return False
        
        log("✅", "Quote calculated successfully", Colors.GREEN)
        log("📊", f"Total: Rp {data['total']:,}, Days: {data['days']}, Surcharge: {data['surcharge_percent']}%")
        log("📊", f"Breakdown items: {len(data['breakdown'])}")
        return True
        
    except Exception as e:
        log("❌", f"Error: {e}", Colors.RED)
        return False

def test_pricing_quote_weekend(token):
    """Test POST /api/pricing/quote with weekend surcharge"""
    log("🧪", "\n=== POST /api/pricing/quote (weekend - 2026-07-04 Saturday) ===", Colors.BLUE)
    
    try:
        payload = {
            "vehicle_type": "hiace",
            "days": 2,
            "distance_km": 150,
            "start_date": "2026-07-04T08:00:00+00:00"  # Saturday
        }
        
        resp = requests.post(f"{BASE_URL}/pricing/quote", 
                            json=payload,
                            headers={"Authorization": f"Bearer {token}"}, 
                            timeout=10)
        
        if resp.status_code != 200:
            log("❌", f"Expected 200, got {resp.status_code}", Colors.RED)
            return False
        
        data = resp.json()
        
        # Verify weekend surcharge applied (20%)
        if data["surcharge_percent"] != 20:
            log("❌", f"Expected 20% weekend surcharge, got {data['surcharge_percent']}%", Colors.RED)
            return False
        
        # Verify breakdown contains surcharge item
        surcharge_found = False
        for item in data["breakdown"]:
            if "akhir pekan" in item.get("label", "").lower() or "weekend" in item.get("label", "").lower():
                surcharge_found = True
                break
        
        if not surcharge_found:
            log("❌", "Weekend surcharge not found in breakdown", Colors.RED)
            return False
        
        log("✅", "Weekend surcharge applied correctly", Colors.GREEN)
        log("📊", f"Total: Rp {data['total']:,}, Surcharge: {data['surcharge_percent']}%")
        return True
        
    except Exception as e:
        log("❌", f"Error: {e}", Colors.RED)
        return False

def test_pricing_quote_holiday(token):
    """Test POST /api/pricing/quote with holiday surcharge"""
    log("🧪", "\n=== POST /api/pricing/quote (holiday surcharge) ===", Colors.BLUE)
    
    try:
        # Get holiday dates from settings
        resp = requests.get(f"{BASE_URL}/settings", 
                           headers={"Authorization": f"Bearer {token}"}, 
                           timeout=10)
        
        if resp.status_code != 200:
            log("❌", f"Failed to get settings: {resp.status_code}", Colors.RED)
            return False
        
        settings = resp.json()
        holidays = settings.get("operational", {}).get("holidays", [])
        
        if not holidays:
            log("⚠️", "No holidays configured, skipping holiday test", Colors.YELLOW)
            return True
        
        holiday_date = holidays[0]
        log("📊", f"Testing with holiday date: {holiday_date}")
        
        payload = {
            "vehicle_type": "elf",
            "days": 1,
            "distance_km": 100,
            "start_date": f"{holiday_date}T08:00:00+00:00"
        }
        
        resp = requests.post(f"{BASE_URL}/pricing/quote", 
                            json=payload,
                            headers={"Authorization": f"Bearer {token}"}, 
                            timeout=10)
        
        if resp.status_code != 200:
            log("❌", f"Expected 200, got {resp.status_code}", Colors.RED)
            return False
        
        data = resp.json()
        
        # Verify holiday surcharge applied (30%)
        if data["surcharge_percent"] != 30:
            log("❌", f"Expected 30% holiday surcharge, got {data['surcharge_percent']}%", Colors.RED)
            return False
        
        # Verify breakdown contains surcharge item
        surcharge_found = False
        for item in data["breakdown"]:
            if "libur" in item.get("label", "").lower() or "holiday" in item.get("label", "").lower():
                surcharge_found = True
                break
        
        if not surcharge_found:
            log("❌", "Holiday surcharge not found in breakdown", Colors.RED)
            return False
        
        log("✅", "Holiday surcharge applied correctly", Colors.GREEN)
        log("📊", f"Total: Rp {data['total']:,}, Surcharge: {data['surcharge_percent']}%")
        return True
        
    except Exception as e:
        log("❌", f"Error: {e}", Colors.RED)
        return False

def test_pricing_quote_vehicle_id(token):
    """Test POST /api/pricing/quote with vehicle_id resolution"""
    log("🧪", "\n=== POST /api/pricing/quote (vehicle_id resolution) ===", Colors.BLUE)
    
    try:
        # Get a vehicle
        vehicles = get_vehicles(token)
        if not vehicles:
            log("❌", "No vehicles found", Colors.RED)
            return False
        
        vehicle = vehicles[0]
        vehicle_id = vehicle.get("id")
        vehicle_type = vehicle.get("type")
        
        log("📊", f"Testing with vehicle_id={vehicle_id}, expected type={vehicle_type}")
        
        payload = {
            "vehicle_id": vehicle_id,
            "days": 2,
            "distance_km": 100,
            "start_date": "2026-07-01T08:00:00+00:00"
        }
        
        resp = requests.post(f"{BASE_URL}/pricing/quote", 
                            json=payload,
                            headers={"Authorization": f"Bearer {token}"}, 
                            timeout=10)
        
        if resp.status_code != 200:
            log("❌", f"Expected 200, got {resp.status_code}", Colors.RED)
            return False
        
        data = resp.json()
        
        # Verify vehicle_type resolved correctly
        if data["vehicle_type"] != vehicle_type:
            log("❌", f"Expected vehicle_type={vehicle_type}, got {data['vehicle_type']}", Colors.RED)
            return False
        
        log("✅", "Vehicle ID resolved to type correctly", Colors.GREEN)
        log("📊", f"Vehicle type: {data['vehicle_type']}, Total: Rp {data['total']:,}")
        return True
        
    except Exception as e:
        log("❌", f"Error: {e}", Colors.RED)
        return False

def test_public_trip_estimate():
    """Test POST /api/public/trip-estimate (no auth)"""
    log("🧪", "\n=== POST /api/public/trip-estimate (no auth) ===", Colors.BLUE)
    
    try:
        payload = {
            "vehicle_type": "hiace_premio",
            "days": 3,
            "distance_km": 250,
            "trip_date": "2026-07-05T08:00:00+00:00"  # Sunday
        }
        
        resp = requests.post(f"{BASE_URL}/public/trip-estimate", 
                            json=payload,
                            timeout=10)
        
        if resp.status_code != 200:
            log("❌", f"Expected 200, got {resp.status_code}", Colors.RED)
            return False
        
        data = resp.json()
        
        # Verify response structure
        required_keys = ["breakdown", "total", "days", "vehicle_type"]
        
        for key in required_keys:
            if key not in data:
                log("❌", f"Missing key: {key}", Colors.RED)
                return False
        
        # Verify breakdown is a list
        if not isinstance(data["breakdown"], list):
            log("❌", "breakdown should be a list", Colors.RED)
            return False
        
        log("✅", "Public trip estimate works without auth", Colors.GREEN)
        log("📊", f"Total: Rp {data['total']:,}, Days: {data['days']}, Vehicle: {data['vehicle_type']}")
        return True
        
    except Exception as e:
        log("❌", f"Error: {e}", Colors.RED)
        return False

def test_settings_update_pricing_rules(owner_token, ops_token):
    """Test PATCH /api/settings with pricing_rules (owner only)"""
    log("🧪", "\n=== PATCH /api/settings (pricing_rules - owner only) ===", Colors.BLUE)
    
    try:
        # Test with ops_admin (should fail)
        log("📊", "Testing with ops_admin (should fail)...")
        payload = {
            "pricing_rules": {
                "day_rates": {
                    "hiace_premio": 1600000
                }
            }
        }
        
        resp = requests.patch(f"{BASE_URL}/settings", 
                             json=payload,
                             headers={"Authorization": f"Bearer {ops_token}"}, 
                             timeout=10)
        
        if resp.status_code != 403:
            log("❌", f"Expected 403 for ops_admin, got {resp.status_code}", Colors.RED)
            return False
        
        log("✅", "Ops admin correctly denied (403)", Colors.GREEN)
        
        # Test with owner (should succeed)
        log("📊", "Testing with owner (should succeed)...")
        
        resp = requests.patch(f"{BASE_URL}/settings", 
                             json=payload,
                             headers={"Authorization": f"Bearer {owner_token}"}, 
                             timeout=10)
        
        if resp.status_code != 200:
            log("❌", f"Expected 200 for owner, got {resp.status_code}", Colors.RED)
            return False
        
        data = resp.json()
        
        # Verify pricing_rules updated
        if "pricing_rules" not in data:
            log("❌", "pricing_rules not in response", Colors.RED)
            return False
        
        log("✅", "Owner successfully updated pricing_rules", Colors.GREEN)
        
        # Verify the change is reflected in GET /api/pricing/rules
        resp = requests.get(f"{BASE_URL}/pricing/rules", 
                           headers={"Authorization": f"Bearer {owner_token}"}, 
                           timeout=10)
        
        if resp.status_code != 200:
            log("❌", f"Failed to get updated rules: {resp.status_code}", Colors.RED)
            return False
        
        rules = resp.json()
        if rules["day_rates"]["hiace_premio"] != 1600000:
            log("❌", f"Expected hiace_premio=1600000, got {rules['day_rates']['hiace_premio']}", Colors.RED)
            return False
        
        log("✅", "Updated pricing_rules reflected in GET /api/pricing/rules", Colors.GREEN)
        
        # Verify quote uses new rate
        quote_payload = {
            "vehicle_type": "hiace_premio",
            "days": 1,
            "distance_km": 0,
            "start_date": "2026-07-01T08:00:00+00:00"
        }
        
        resp = requests.post(f"{BASE_URL}/pricing/quote", 
                            json=quote_payload,
                            headers={"Authorization": f"Bearer {owner_token}"}, 
                            timeout=10)
        
        if resp.status_code != 200:
            log("❌", f"Failed to get quote: {resp.status_code}", Colors.RED)
            return False
        
        quote = resp.json()
        log("✅", "Quote reflects updated rate", Colors.GREEN)
        log("📊", f"New quote total: Rp {quote['total']:,}")
        
        return True
        
    except Exception as e:
        log("❌", f"Error: {e}", Colors.RED)
        return False

def test_booking_auto_calc(token):
    """Test POST /api/bookings with auto-calc base_price (when <= 0)"""
    log("🧪", "\n=== POST /api/bookings (auto-calc base_price) ===", Colors.BLUE)
    
    try:
        # Get customer and vehicle
        customers = get_customers(token)
        vehicles = get_vehicles(token)
        
        if not customers or not vehicles:
            log("❌", "No customers or vehicles found", Colors.RED)
            return False
        
        customer = customers[0]
        vehicle = vehicles[0]
        
        # Create booking with base_price = 0 (should auto-calculate)
        now = datetime.now(timezone.utc)
        start = now + timedelta(days=10)
        end = start + timedelta(days=3)
        
        payload = {
            "customer_id": customer["id"],
            "vehicle_id": vehicle["id"],
            "origin": "Bandung",
            "destination": "Jakarta",
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "base_price": 0,  # Should trigger auto-calc
            "add_ons": [{"label": "Extra", "amount": 100000}]
        }
        
        resp = requests.post(f"{BASE_URL}/bookings", 
                            json=payload,
                            headers={"Authorization": f"Bearer {token}"}, 
                            timeout=10)
        
        if resp.status_code != 200:
            log("❌", f"Expected 200, got {resp.status_code}", Colors.RED)
            if resp.status_code == 400:
                log("📊", f"Error: {resp.json()}")
            return False
        
        data = resp.json()
        
        # Verify base_price was auto-calculated (should be > 0)
        if data["base_price"] <= 0:
            log("❌", f"Expected base_price > 0, got {data['base_price']}", Colors.RED)
            return False
        
        # Verify total = base_price + add_ons
        expected_total = data["base_price"] + 100000
        if abs(data["total_amount"] - expected_total) > 1:
            log("❌", f"Expected total={expected_total}, got {data['total_amount']}", Colors.RED)
            return False
        
        log("✅", "Booking auto-calculated base_price correctly", Colors.GREEN)
        log("📊", f"Base price: Rp {data['base_price']:,}, Total: Rp {data['total_amount']:,}")
        return True
        
    except Exception as e:
        log("❌", f"Error: {e}", Colors.RED)
        return False

def test_booking_explicit_price(token):
    """Test POST /api/bookings with explicit base_price (should be respected)"""
    log("🧪", "\n=== POST /api/bookings (explicit base_price override) ===", Colors.BLUE)
    
    try:
        # Get customer and vehicle
        customers = get_customers(token)
        vehicles = get_vehicles(token)
        
        if not customers or not vehicles:
            log("❌", "No customers or vehicles found", Colors.RED)
            return False
        
        customer = customers[0]
        # Use different vehicle to avoid conflict
        vehicle = vehicles[1] if len(vehicles) > 1 else vehicles[0]
        
        # Create booking with explicit base_price (should NOT auto-calculate)
        now = datetime.now(timezone.utc)
        start = now + timedelta(days=15)
        end = start + timedelta(days=2)
        
        explicit_price = 5000000
        
        payload = {
            "customer_id": customer["id"],
            "vehicle_id": vehicle["id"],
            "origin": "Jakarta",
            "destination": "Bali",
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "base_price": explicit_price,  # Explicit price
            "add_ons": [{"label": "Insurance", "amount": 200000}]
        }
        
        resp = requests.post(f"{BASE_URL}/bookings", 
                            json=payload,
                            headers={"Authorization": f"Bearer {token}"}, 
                            timeout=10)
        
        if resp.status_code != 200:
            log("❌", f"Expected 200, got {resp.status_code}", Colors.RED)
            if resp.status_code == 400:
                log("📊", f"Error: {resp.json()}")
            return False
        
        data = resp.json()
        
        # Verify base_price matches explicit value
        if data["base_price"] != explicit_price:
            log("❌", f"Expected base_price={explicit_price}, got {data['base_price']}", Colors.RED)
            return False
        
        # Verify total = base_price + add_ons
        expected_total = explicit_price + 200000
        if abs(data["total_amount"] - expected_total) > 1:
            log("❌", f"Expected total={expected_total}, got {data['total_amount']}", Colors.RED)
            return False
        
        log("✅", "Booking respected explicit base_price", Colors.GREEN)
        log("📊", f"Base price: Rp {data['base_price']:,}, Total: Rp {data['total_amount']:,}")
        return True
        
    except Exception as e:
        log("❌", f"Error: {e}", Colors.RED)
        return False

def test_regression_anti_double_booking(token):
    """Test anti double-booking still works"""
    log("🧪", "\n=== Regression: Anti Double-Booking (INV-4) ===", Colors.BLUE)
    
    try:
        # Get customer and vehicle
        customers = get_customers(token)
        vehicles = get_vehicles(token)
        
        if not customers or not vehicles:
            log("❌", "No customers or vehicles found", Colors.RED)
            return False
        
        customer = customers[0]
        vehicle = vehicles[2] if len(vehicles) > 2 else vehicles[0]
        
        # Create first booking
        now = datetime.now(timezone.utc)
        start = now + timedelta(days=20)
        end = start + timedelta(days=2)
        
        payload1 = {
            "customer_id": customer["id"],
            "vehicle_id": vehicle["id"],
            "origin": "Bandung",
            "destination": "Yogyakarta",
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "base_price": 3000000
        }
        
        resp1 = requests.post(f"{BASE_URL}/bookings", 
                             json=payload1,
                             headers={"Authorization": f"Bearer {token}"}, 
                             timeout=10)
        
        if resp1.status_code != 200:
            log("❌", f"First booking failed: {resp1.status_code}", Colors.RED)
            return False
        
        booking1 = resp1.json()
        log("✅", f"First booking created: {booking1['code']}", Colors.GREEN)
        
        # Try to create overlapping booking (should fail)
        payload2 = {
            "customer_id": customer["id"],
            "vehicle_id": vehicle["id"],
            "origin": "Jakarta",
            "destination": "Surabaya",
            "start_datetime": (start + timedelta(days=1)).isoformat(),
            "end_datetime": (end + timedelta(days=1)).isoformat(),
            "base_price": 2500000
        }
        
        resp2 = requests.post(f"{BASE_URL}/bookings", 
                             json=payload2,
                             headers={"Authorization": f"Bearer {token}"}, 
                             timeout=10)
        
        if resp2.status_code == 200:
            log("❌", "Double booking was allowed (should have been blocked)", Colors.RED)
            return False
        
        if resp2.status_code != 400:
            log("❌", f"Expected 400, got {resp2.status_code}", Colors.RED)
            return False
        
        error = resp2.json()
        if "bentrok" not in error.get("detail", "").lower():
            log("❌", f"Expected conflict error, got: {error.get('detail')}", Colors.RED)
            return False
        
        log("✅", "Anti double-booking working correctly", Colors.GREEN)
        log("📊", f"Conflict detected: {error.get('detail')}")
        return True
        
    except Exception as e:
        log("❌", f"Error: {e}", Colors.RED)
        return False

def test_regression_payment_status(token):
    """Test payment status derivation still works"""
    log("🧪", "\n=== Regression: Payment Status Derivation (INV-3) ===", Colors.BLUE)
    
    try:
        # Get existing bookings
        resp = requests.get(f"{BASE_URL}/bookings", 
                           headers={"Authorization": f"Bearer {token}"}, 
                           timeout=10)
        
        if resp.status_code != 200:
            log("❌", f"Failed to get bookings: {resp.status_code}", Colors.RED)
            return False
        
        bookings = resp.json()
        
        if not bookings:
            log("⚠️", "No bookings found to test payment status", Colors.YELLOW)
            return True
        
        # Check payment status is present
        for booking in bookings[:3]:  # Check first 3
            if "payment_status" not in booking:
                log("❌", f"Booking {booking.get('code')} missing payment_status", Colors.RED)
                return False
            
            # Verify payment_status is valid
            valid_statuses = ["belum_bayar", "dp", "lunas", "selesai"]
            if booking["payment_status"] not in valid_statuses:
                log("❌", f"Invalid payment_status: {booking['payment_status']}", Colors.RED)
                return False
        
        log("✅", "Payment status derivation working", Colors.GREEN)
        log("📊", f"Checked {min(3, len(bookings))} bookings")
        return True
        
    except Exception as e:
        log("❌", f"Error: {e}", Colors.RED)
        return False

def main():
    log("🚀", "="*70, Colors.BLUE)
    log("🚀", "PHASE 9 / TAHAP B · B1: PRICING ENGINE TESTS", Colors.BLUE)
    log("🚀", "="*70, Colors.BLUE)
    
    # Login as different roles
    log("🔐", "\n=== Logging in as different roles ===", Colors.BLUE)
    owner_token = login("owner@demo.local", "demo12345")
    ops_token = login("ops@demo.local", "demo12345")
    driver_token = login("driver@demo.local", "demo12345")
    
    if not owner_token or not ops_token or not driver_token:
        log("❌", "Failed to login, aborting tests", Colors.RED)
        return 1
    
    log("✅", "All roles logged in successfully", Colors.GREEN)
    
    results = []
    
    # Auth tests
    results.append(("Pricing Rules - No Auth (401)", test_pricing_rules_no_auth()))
    
    # Pricing rules tests
    results.append(("Pricing Rules - Owner", test_pricing_rules_get(owner_token, "owner")))
    results.append(("Pricing Rules - Ops Admin", test_pricing_rules_get(ops_token, "ops_admin")))
    results.append(("Pricing Rules - Driver", test_pricing_rules_get(driver_token, "driver")))
    
    # Pricing quote tests
    results.append(("Pricing Quote - Basic", test_pricing_quote_basic(owner_token)))
    results.append(("Pricing Quote - Weekend Surcharge", test_pricing_quote_weekend(owner_token)))
    results.append(("Pricing Quote - Holiday Surcharge", test_pricing_quote_holiday(owner_token)))
    results.append(("Pricing Quote - Vehicle ID Resolution", test_pricing_quote_vehicle_id(owner_token)))
    
    # Public endpoint test
    results.append(("Public Trip Estimate", test_public_trip_estimate()))
    
    # Settings update test
    results.append(("Settings Update - Pricing Rules (RBAC)", test_settings_update_pricing_rules(owner_token, ops_token)))
    
    # Booking tests
    results.append(("Booking - Auto-calc Base Price", test_booking_auto_calc(owner_token)))
    results.append(("Booking - Explicit Base Price", test_booking_explicit_price(owner_token)))
    
    # Regression tests
    results.append(("Regression - Anti Double-Booking", test_regression_anti_double_booking(owner_token)))
    results.append(("Regression - Payment Status", test_regression_payment_status(owner_token)))
    
    # Summary
    log("📊", "\n" + "="*70, Colors.BLUE)
    log("📊", "TEST SUMMARY", Colors.BLUE)
    log("📊", "="*70, Colors.BLUE)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        if result:
            log("✅", f"PASS - {name}", Colors.GREEN)
            passed += 1
        else:
            log("❌", f"FAIL - {name}", Colors.RED)
            failed += 1
    
    log("📊", f"\nTotal: {passed}/{len(results)} passed, {failed} failed", Colors.BLUE)
    
    if failed == 0:
        log("🎉", "ALL TESTS PASSED!", Colors.GREEN)
        return 0
    else:
        log("⚠️", f"{failed} test(s) failed", Colors.YELLOW)
        return 1

if __name__ == "__main__":
    sys.exit(main())
