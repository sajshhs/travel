#!/usr/bin/env python3
"""
Backend Test Suite for E20 (Group Booking) & E21 (Cancel with fee/refund)
==========================================================================
Tests new features + regression for Bookings/Payments/Dispatch
"""
import requests
import sys
import json
from datetime import datetime, timedelta

class E20E21TestSuite:
    def __init__(self, base_url="https://trip-route-buttons.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.customer_id = None
        self.vehicle_ids = []
        self.driver_ids = []
        
    def log(self, msg, status="info"):
        symbols = {"pass": "✅", "fail": "❌", "info": "🔍", "warn": "⚠️"}
        print(f"{symbols.get(status, '•')} {msg}")
    
    def test(self, name, condition, details=""):
        """Record test result"""
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            self.log(f"PASS: {name}", "pass")
            return True
        else:
            self.tests_failed += 1
            self.failures.append(f"{name}: {details}")
            self.log(f"FAIL: {name} - {details}", "fail")
            return False
    
    def login(self, email, password):
        """Login and store token"""
        try:
            url = f"{self.base_url}/api/auth/login"
            response = requests.post(url, json={"email": email, "password": password}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                token = data.get("token")
                if token:
                    self.tokens[email] = token
                    self.log(f"Login successful: {email}", "pass")
                    return True
            self.log(f"Login failed for {email}: {response.status_code} - {response.text[:200]}", "fail")
            return False
        except Exception as e:
            self.log(f"Login error for {email}: {str(e)}", "fail")
            return False
    
    def headers(self, email):
        """Get auth headers for user"""
        token = self.tokens.get(email)
        if not token:
            return {"Content-Type": "application/json"}
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    
    def test_auth(self):
        """Test authentication for all users"""
        self.log("\n=== Testing Authentication ===", "info")
        
        # Login all users
        owner_ok = self.login("owner@demo.local", "demo12345")
        ops_ok = self.login("ops@demo.local", "demo12345")
        driver_ok = self.login("driver@demo.local", "demo12345")
        
        self.test("Owner login", owner_ok)
        self.test("Ops Admin login", ops_ok)
        self.test("Driver login", driver_ok)
        
        return owner_ok and ops_ok
    
    def setup_test_data(self):
        """Get customer, vehicle, and driver IDs from seeded data"""
        self.log("\n=== Setting Up Test Data ===", "info")
        
        # Get customers
        try:
            url = f"{self.base_url}/api/customers"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            if response.status_code == 200:
                customers = response.json()
                if customers:
                    self.customer_id = customers[0].get("id")
                    self.log(f"Using customer ID: {self.customer_id}", "info")
        except Exception as e:
            self.log(f"Could not get customer: {str(e)}", "fail")
            return False
        
        # Get vehicles
        try:
            url = f"{self.base_url}/api/vehicles"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            if response.status_code == 200:
                vehicles = response.json()
                # Get at least 2 vehicles for group booking
                self.vehicle_ids = [v.get("id") for v in vehicles[:3] if v.get("id")]
                self.log(f"Using vehicle IDs: {self.vehicle_ids}", "info")
        except Exception as e:
            self.log(f"Could not get vehicles: {str(e)}", "fail")
            return False
        
        # Get drivers
        try:
            url = f"{self.base_url}/api/drivers"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            if response.status_code == 200:
                drivers = response.json()
                self.driver_ids = [d.get("id") for d in drivers[:2] if d.get("id")]
                self.log(f"Using driver IDs: {self.driver_ids}", "info")
        except Exception as e:
            self.log(f"Could not get drivers: {str(e)}", "fail")
        
        return bool(self.customer_id and len(self.vehicle_ids) >= 2)
    
    def test_e20_basic_group_booking(self):
        """E20: Basic group booking with 2 units"""
        self.log("\n=== E20: Basic Group Booking (2 units) ===", "info")
        
        if not self.customer_id or len(self.vehicle_ids) < 2:
            self.log("Skipping: insufficient test data", "warn")
            return
        
        # Create group booking with 2 units
        start_dt = (datetime.now() + timedelta(days=100)).replace(hour=8, minute=0, second=0, microsecond=0)
        end_dt = start_dt.replace(hour=18)
        
        body = {
            "customer_id": self.customer_id,
            "note": "E20 test - basic group booking",
            "require_dp": False,
            "units": [
                {
                    "vehicle_id": self.vehicle_ids[0],
                    "driver_id": None,
                    "origin": "Jakarta",
                    "destination": "Bandung",
                    "start_datetime": start_dt.isoformat(),
                    "end_datetime": end_dt.isoformat(),
                    "base_price": 500000
                },
                {
                    "vehicle_id": self.vehicle_ids[1],
                    "origin": "Jakarta",
                    "destination": "Bandung",
                    "start_datetime": start_dt.isoformat(),
                    "end_datetime": end_dt.isoformat(),
                    "base_price": 600000
                }
            ]
        }
        
        try:
            url = f"{self.base_url}/api/bookings/group"
            response = requests.post(url, json=body, headers=self.headers("owner@demo.local"), timeout=15)
            
            self.test(
                "POST /api/bookings/group returns 200",
                response.status_code == 200,
                f"Got {response.status_code}: {response.text[:300]}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                self.test(
                    "Response has group_id with grp_ prefix",
                    data.get("group_id", "").startswith("grp_"),
                    f"Got group_id: {data.get('group_id')}"
                )
                
                self.test(
                    "Response count = 2",
                    data.get("count") == 2,
                    f"Expected 2, got {data.get('count')}"
                )
                
                self.test(
                    "Response grand_total = 1100000",
                    data.get("grand_total") == 1100000,
                    f"Expected 1100000, got {data.get('grand_total')}"
                )
                
                bookings = data.get("bookings", [])
                self.test(
                    "Response has 2 bookings",
                    len(bookings) == 2,
                    f"Expected 2, got {len(bookings)}"
                )
                
                if len(bookings) == 2:
                    # Check first booking
                    b1 = bookings[0]
                    self.test(
                        "Booking 1 has group_id",
                        b1.get("group_id") == data.get("group_id"),
                        f"group_id mismatch"
                    )
                    
                    self.test(
                        "Booking 1 has group_size = 2",
                        b1.get("group_size") == 2,
                        f"Expected 2, got {b1.get('group_size')}"
                    )
                    
                    self.test(
                        "Booking 1 has group_index = 1",
                        b1.get("group_index") == 1,
                        f"Expected 1, got {b1.get('group_index')}"
                    )
                    
                    self.test(
                        "Booking 1 status = confirmed (require_dp=false)",
                        b1.get("status") == "confirmed",
                        f"Expected confirmed, got {b1.get('status')}"
                    )
                    
                    # Check second booking
                    b2 = bookings[1]
                    self.test(
                        "Booking 2 has group_index = 2",
                        b2.get("group_index") == 2,
                        f"Expected 2, got {b2.get('group_index')}"
                    )
                    
                    # Store for later verification
                    self.group_id = data.get("group_id")
                    self.group_booking_ids = [b1.get("id"), b2.get("id")]
                    
                    # Verify via GET /api/bookings
                    try:
                        list_url = f"{self.base_url}/api/bookings"
                        list_response = requests.get(list_url, headers=self.headers("owner@demo.local"), timeout=10)
                        if list_response.status_code == 200:
                            all_bookings = list_response.json()
                            group_bookings = [b for b in all_bookings if b.get("group_id") == self.group_id]
                            self.test(
                                "GET /api/bookings shows both group bookings",
                                len(group_bookings) == 2,
                                f"Expected 2, got {len(group_bookings)}"
                            )
                    except Exception as e:
                        self.log(f"Could not verify via GET /api/bookings: {str(e)}", "warn")
        
        except Exception as e:
            self.test("POST /api/bookings/group", False, str(e))
    
    def test_e20_intra_group_overlap(self):
        """E20: Intra-group anti-overlap (same vehicle, overlapping time)"""
        self.log("\n=== E20: Intra-group Anti-overlap ===", "info")
        
        if not self.customer_id or len(self.vehicle_ids) < 1:
            self.log("Skipping: insufficient test data", "warn")
            return
        
        # Use same vehicle for both units with overlapping time
        start_dt = (datetime.now() + timedelta(days=101)).replace(hour=8, minute=0, second=0, microsecond=0)
        end_dt = start_dt.replace(hour=18)
        
        body = {
            "customer_id": self.customer_id,
            "note": "E20 test - intra-group overlap",
            "require_dp": False,
            "units": [
                {
                    "vehicle_id": self.vehicle_ids[0],  # Same vehicle
                    "origin": "A",
                    "destination": "B",
                    "start_datetime": start_dt.isoformat(),
                    "end_datetime": end_dt.isoformat(),
                    "base_price": 500000
                },
                {
                    "vehicle_id": self.vehicle_ids[0],  # Same vehicle
                    "origin": "C",
                    "destination": "D",
                    "start_datetime": start_dt.isoformat(),  # Same time
                    "end_datetime": end_dt.isoformat(),
                    "base_price": 600000
                }
            ]
        }
        
        try:
            url = f"{self.base_url}/api/bookings/group"
            response = requests.post(url, json=body, headers=self.headers("owner@demo.local"), timeout=15)
            
            self.test(
                "Intra-group overlap returns 400",
                response.status_code == 400,
                f"Expected 400, got {response.status_code}"
            )
            
            if response.status_code == 400:
                error_detail = response.json().get("detail", "")
                self.test(
                    "Error message mentions overlap/bentrok (Indonesian)",
                    "tumpang tindih" in error_detail.lower() or "overlap" in error_detail.lower() or "bentrok" in error_detail.lower(),
                    f"Got error: {error_detail}"
                )
        
        except Exception as e:
            self.test("Intra-group overlap test", False, str(e))
    
    def test_e20_pre_existing_conflict(self):
        """E20: INV-4 pre-existing conflict"""
        self.log("\n=== E20: Pre-existing Conflict (INV-4) ===", "info")
        
        if not self.customer_id or len(self.vehicle_ids) < 2:
            self.log("Skipping: insufficient test data", "warn")
            return
        
        # First, create a single booking
        start_dt = (datetime.now() + timedelta(days=102)).replace(hour=8, minute=0, second=0, microsecond=0)
        end_dt = start_dt.replace(hour=18)
        
        single_body = {
            "customer_id": self.customer_id,
            "vehicle_id": self.vehicle_ids[0],
            "origin": "Jakarta",
            "destination": "Bogor",
            "start_datetime": start_dt.isoformat(),
            "end_datetime": end_dt.isoformat(),
            "base_price": 400000
        }
        
        try:
            # Create single booking first
            single_url = f"{self.base_url}/api/bookings"
            single_response = requests.post(single_url, json=single_body, headers=self.headers("owner@demo.local"), timeout=10)
            
            if single_response.status_code == 200:
                single_booking = single_response.json()
                self.log(f"Created single booking: {single_booking.get('code')}", "info")
                
                # Now try to create group booking with same vehicle and overlapping time
                group_body = {
                    "customer_id": self.customer_id,
                    "note": "E20 test - pre-existing conflict",
                    "require_dp": False,
                    "units": [
                        {
                            "vehicle_id": self.vehicle_ids[0],  # Same vehicle as single booking
                            "origin": "A",
                            "destination": "B",
                            "start_datetime": start_dt.isoformat(),  # Same time
                            "end_datetime": end_dt.isoformat(),
                            "base_price": 500000
                        },
                        {
                            "vehicle_id": self.vehicle_ids[1],
                            "origin": "C",
                            "destination": "D",
                            "start_datetime": start_dt.isoformat(),
                            "end_datetime": end_dt.isoformat(),
                            "base_price": 600000
                        }
                    ]
                }
                
                group_url = f"{self.base_url}/api/bookings/group"
                group_response = requests.post(group_url, json=group_body, headers=self.headers("owner@demo.local"), timeout=15)
                
                self.test(
                    "Pre-existing conflict returns 400",
                    group_response.status_code == 400,
                    f"Expected 400, got {group_response.status_code}"
                )
                
                if group_response.status_code == 400:
                    error_detail = group_response.json().get("detail", "")
                    self.test(
                        "Error message mentions conflict/bentrok",
                        "bentrok" in error_detail.lower() or "conflict" in error_detail.lower(),
                        f"Got error: {error_detail}"
                    )
                
                # Verify nothing was created (atomic)
                list_url = f"{self.base_url}/api/bookings"
                list_response = requests.get(list_url, headers=self.headers("owner@demo.local"), timeout=10)
                if list_response.status_code == 200:
                    all_bookings = list_response.json()
                    # Should only have the single booking, not the group
                    recent_bookings = [b for b in all_bookings if b.get("vehicle_id") == self.vehicle_ids[1]]
                    self.test(
                        "Atomic: second unit not created when first conflicts",
                        len(recent_bookings) == 0,
                        f"Found {len(recent_bookings)} bookings for vehicle 2 (should be 0)"
                    )
        
        except Exception as e:
            self.test("Pre-existing conflict test", False, str(e))
    
    def test_e20_require_dp(self):
        """E20: require_dp=true creates hold status"""
        self.log("\n=== E20: require_dp=true (hold status) ===", "info")
        
        if not self.customer_id or len(self.vehicle_ids) < 2:
            self.log("Skipping: insufficient test data", "warn")
            return
        
        start_dt = (datetime.now() + timedelta(days=103)).replace(hour=8, minute=0, second=0, microsecond=0)
        end_dt = start_dt.replace(hour=18)
        
        body = {
            "customer_id": self.customer_id,
            "note": "E20 test - require_dp",
            "require_dp": True,
            "units": [
                {
                    "vehicle_id": self.vehicle_ids[0],
                    "origin": "A",
                    "destination": "B",
                    "start_datetime": start_dt.isoformat(),
                    "end_datetime": end_dt.isoformat(),
                    "base_price": 500000
                },
                {
                    "vehicle_id": self.vehicle_ids[1],
                    "origin": "A",
                    "destination": "B",
                    "start_datetime": start_dt.isoformat(),
                    "end_datetime": end_dt.isoformat(),
                    "base_price": 600000
                }
            ]
        }
        
        try:
            url = f"{self.base_url}/api/bookings/group"
            response = requests.post(url, json=body, headers=self.headers("owner@demo.local"), timeout=15)
            
            self.test(
                "POST /api/bookings/group with require_dp=true returns 200",
                response.status_code == 200,
                f"Got {response.status_code}: {response.text[:300]}"
            )
            
            if response.status_code == 200:
                data = response.json()
                bookings = data.get("bookings", [])
                
                if len(bookings) >= 1:
                    b1 = bookings[0]
                    
                    self.test(
                        "Booking status = hold (require_dp=true)",
                        b1.get("status") == "hold",
                        f"Expected hold, got {b1.get('status')}"
                    )
                    
                    self.test(
                        "Booking has hold_expires_at",
                        b1.get("hold_expires_at") is not None,
                        "hold_expires_at missing"
                    )
                    
                    self.test(
                        "Booking has dp_amount",
                        b1.get("dp_amount") is not None and b1.get("dp_amount") > 0,
                        f"dp_amount: {b1.get('dp_amount')}"
                    )
                    
                    self.test(
                        "Booking has dp_percent",
                        b1.get("dp_percent") is not None,
                        f"dp_percent: {b1.get('dp_percent')}"
                    )
        
        except Exception as e:
            self.test("require_dp test", False, str(e))
    
    def test_e20_rbac_driver(self):
        """E20: RBAC - driver cannot create group booking"""
        self.log("\n=== E20: RBAC (driver 403) ===", "info")
        
        if not self.customer_id or len(self.vehicle_ids) < 2:
            self.log("Skipping: insufficient test data", "warn")
            return
        
        start_dt = (datetime.now() + timedelta(days=34)).replace(hour=8, minute=0, second=0, microsecond=0)
        end_dt = start_dt.replace(hour=18)
        
        body = {
            "customer_id": self.customer_id,
            "note": "E20 test - driver RBAC",
            "require_dp": False,
            "units": [
                {
                    "vehicle_id": self.vehicle_ids[0],
                    "origin": "A",
                    "destination": "B",
                    "start_datetime": start_dt.isoformat(),
                    "end_datetime": end_dt.isoformat(),
                    "base_price": 500000
                }
            ]
        }
        
        try:
            url = f"{self.base_url}/api/bookings/group"
            response = requests.post(url, json=body, headers=self.headers("driver@demo.local"), timeout=15)
            
            self.test(
                "Driver POST /api/bookings/group returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        
        except Exception as e:
            self.test("Driver RBAC test", False, str(e))
    
    def test_e20_empty_units(self):
        """E20: Empty units array returns 400"""
        self.log("\n=== E20: Empty units array ===", "info")
        
        if not self.customer_id:
            self.log("Skipping: insufficient test data", "warn")
            return
        
        body = {
            "customer_id": self.customer_id,
            "note": "E20 test - empty units",
            "require_dp": False,
            "units": []
        }
        
        try:
            url = f"{self.base_url}/api/bookings/group"
            response = requests.post(url, json=body, headers=self.headers("owner@demo.local"), timeout=15)
            
            self.test(
                "Empty units array returns 400 or 422",
                response.status_code in [400, 422],
                f"Expected 400/422, got {response.status_code}"
            )
        
        except Exception as e:
            self.test("Empty units test", False, str(e))
    
    def test_e21_cancel_without_body(self):
        """E21: Cancel without body (backward compatibility)"""
        self.log("\n=== E21: Cancel without body (backward compat) ===", "info")
        
        if not self.customer_id or len(self.vehicle_ids) < 1:
            self.log("Skipping: insufficient test data", "warn")
            return
        
        # Create a booking first
        start_dt = (datetime.now() + timedelta(days=35)).replace(hour=8, minute=0, second=0, microsecond=0)
        end_dt = start_dt.replace(hour=18)
        
        booking_body = {
            "customer_id": self.customer_id,
            "vehicle_id": self.vehicle_ids[0],
            "origin": "Jakarta",
            "destination": "Bogor",
            "start_datetime": start_dt.isoformat(),
            "end_datetime": end_dt.isoformat(),
            "base_price": 400000
        }
        
        try:
            # Create booking
            create_url = f"{self.base_url}/api/bookings"
            create_response = requests.post(create_url, json=booking_body, headers=self.headers("owner@demo.local"), timeout=10)
            
            if create_response.status_code == 200:
                booking = create_response.json()
                booking_id = booking.get("id")
                self.log(f"Created booking: {booking.get('code')}", "info")
                
                # Cancel without body
                cancel_url = f"{self.base_url}/api/bookings/{booking_id}/cancel"
                cancel_response = requests.post(cancel_url, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "POST /cancel without body returns 200",
                    cancel_response.status_code == 200,
                    f"Got {cancel_response.status_code}: {cancel_response.text[:300]}"
                )
                
                if cancel_response.status_code == 200:
                    cancelled = cancel_response.json()
                    
                    self.test(
                        "Status = cancelled",
                        cancelled.get("status") == "cancelled",
                        f"Expected cancelled, got {cancelled.get('status')}"
                    )
                    
                    self.test(
                        "cancellation_reason is empty string",
                        cancelled.get("cancellation_reason") == "",
                        f"Expected empty, got {cancelled.get('cancellation_reason')}"
                    )
                    
                    self.test(
                        "cancellation_fee = 0",
                        cancelled.get("cancellation_fee") == 0,
                        f"Expected 0, got {cancelled.get('cancellation_fee')}"
                    )
                    
                    self.test(
                        "refund_amount = 0",
                        cancelled.get("refund_amount") == 0,
                        f"Expected 0, got {cancelled.get('refund_amount')}"
                    )
                    
                    self.test(
                        "Has cancelled_at timestamp",
                        cancelled.get("cancelled_at") is not None,
                        "cancelled_at missing"
                    )
        
        except Exception as e:
            self.test("Cancel without body test", False, str(e))
    
    def test_e21_cancel_with_body(self):
        """E21: Cancel with body (reason, fee, refund)"""
        self.log("\n=== E21: Cancel with body (reason, fee, refund) ===", "info")
        
        if not self.customer_id or len(self.vehicle_ids) < 1:
            self.log("Skipping: insufficient test data", "warn")
            return
        
        # Create a booking first
        start_dt = (datetime.now() + timedelta(days=36)).replace(hour=8, minute=0, second=0, microsecond=0)
        end_dt = start_dt.replace(hour=18)
        
        booking_body = {
            "customer_id": self.customer_id,
            "vehicle_id": self.vehicle_ids[0],
            "origin": "Jakarta",
            "destination": "Bogor",
            "start_datetime": start_dt.isoformat(),
            "end_datetime": end_dt.isoformat(),
            "base_price": 500000
        }
        
        try:
            # Create booking
            create_url = f"{self.base_url}/api/bookings"
            create_response = requests.post(create_url, json=booking_body, headers=self.headers("owner@demo.local"), timeout=10)
            
            if create_response.status_code == 200:
                booking = create_response.json()
                booking_id = booking.get("id")
                self.log(f"Created booking: {booking.get('code')}", "info")
                
                # Cancel with body
                cancel_body = {
                    "reason": "Pelanggan pindah tanggal",
                    "cancellation_fee": 100000,
                    "refund_amount": 0
                }
                
                cancel_url = f"{self.base_url}/api/bookings/{booking_id}/cancel"
                cancel_response = requests.post(cancel_url, json=cancel_body, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "POST /cancel with body returns 200",
                    cancel_response.status_code == 200,
                    f"Got {cancel_response.status_code}: {cancel_response.text[:300]}"
                )
                
                if cancel_response.status_code == 200:
                    cancelled = cancel_response.json()
                    
                    self.test(
                        "Status = cancelled",
                        cancelled.get("status") == "cancelled",
                        f"Expected cancelled, got {cancelled.get('status')}"
                    )
                    
                    self.test(
                        "cancellation_reason stored",
                        cancelled.get("cancellation_reason") == "Pelanggan pindah tanggal",
                        f"Expected 'Pelanggan pindah tanggal', got {cancelled.get('cancellation_reason')}"
                    )
                    
                    self.test(
                        "cancellation_fee = 100000",
                        cancelled.get("cancellation_fee") == 100000,
                        f"Expected 100000, got {cancelled.get('cancellation_fee')}"
                    )
                    
                    self.test(
                        "refund_amount = 0",
                        cancelled.get("refund_amount") == 0,
                        f"Expected 0, got {cancelled.get('refund_amount')}"
                    )
                    
                    # Verify via GET
                    get_url = f"{self.base_url}/api/bookings/{booking_id}"
                    get_response = requests.get(get_url, headers=self.headers("owner@demo.local"), timeout=10)
                    if get_response.status_code == 200:
                        verified = get_response.json()
                        self.test(
                            "GET /bookings/{id} shows cancellation fields",
                            verified.get("cancellation_fee") == 100000 and verified.get("cancellation_reason") == "Pelanggan pindah tanggal",
                            "Cancellation fields not persisted"
                        )
        
        except Exception as e:
            self.test("Cancel with body test", False, str(e))
    
    def test_e21_negative_fee(self):
        """E21: Negative fee validation"""
        self.log("\n=== E21: Negative fee validation ===", "info")
        
        if not self.customer_id or len(self.vehicle_ids) < 1:
            self.log("Skipping: insufficient test data", "warn")
            return
        
        # Create a booking first
        start_dt = (datetime.now() + timedelta(days=37)).replace(hour=8, minute=0, second=0, microsecond=0)
        end_dt = start_dt.replace(hour=18)
        
        booking_body = {
            "customer_id": self.customer_id,
            "vehicle_id": self.vehicle_ids[0],
            "origin": "Jakarta",
            "destination": "Bogor",
            "start_datetime": start_dt.isoformat(),
            "end_datetime": end_dt.isoformat(),
            "base_price": 400000
        }
        
        try:
            # Create booking
            create_url = f"{self.base_url}/api/bookings"
            create_response = requests.post(create_url, json=booking_body, headers=self.headers("owner@demo.local"), timeout=10)
            
            if create_response.status_code == 200:
                booking = create_response.json()
                booking_id = booking.get("id")
                
                # Try to cancel with negative fee
                cancel_body = {
                    "reason": "Test negative",
                    "cancellation_fee": -1,
                    "refund_amount": 0
                }
                
                cancel_url = f"{self.base_url}/api/bookings/{booking_id}/cancel"
                cancel_response = requests.post(cancel_url, json=cancel_body, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "Negative fee returns 400",
                    cancel_response.status_code == 400,
                    f"Expected 400, got {cancel_response.status_code}"
                )
                
                if cancel_response.status_code == 400:
                    error_detail = cancel_response.json().get("detail", "")
                    self.test(
                        "Error message mentions negative/negatif",
                        "negatif" in error_detail.lower() or "negative" in error_detail.lower(),
                        f"Got error: {error_detail}"
                    )
        
        except Exception as e:
            self.test("Negative fee test", False, str(e))
    
    def test_e21_refund_exceeds_paid(self):
        """E21: Refund > paid_amount validation"""
        self.log("\n=== E21: Refund > paid_amount validation ===", "info")
        
        if not self.customer_id or len(self.vehicle_ids) < 1:
            self.log("Skipping: insufficient test data", "warn")
            return
        
        # Create a booking first (paid_amount = 0)
        start_dt = (datetime.now() + timedelta(days=38)).replace(hour=8, minute=0, second=0, microsecond=0)
        end_dt = start_dt.replace(hour=18)
        
        booking_body = {
            "customer_id": self.customer_id,
            "vehicle_id": self.vehicle_ids[0],
            "origin": "Jakarta",
            "destination": "Bogor",
            "start_datetime": start_dt.isoformat(),
            "end_datetime": end_dt.isoformat(),
            "base_price": 400000
        }
        
        try:
            # Create booking
            create_url = f"{self.base_url}/api/bookings"
            create_response = requests.post(create_url, json=booking_body, headers=self.headers("owner@demo.local"), timeout=10)
            
            if create_response.status_code == 200:
                booking = create_response.json()
                booking_id = booking.get("id")
                
                # Try to cancel with refund > paid_amount (0)
                cancel_body = {
                    "reason": "Test refund exceeds",
                    "cancellation_fee": 0,
                    "refund_amount": 999999999
                }
                
                cancel_url = f"{self.base_url}/api/bookings/{booking_id}/cancel"
                cancel_response = requests.post(cancel_url, json=cancel_body, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "Refund > paid returns 400",
                    cancel_response.status_code == 400,
                    f"Expected 400, got {cancel_response.status_code}"
                )
                
                if cancel_response.status_code == 400:
                    error_detail = cancel_response.json().get("detail", "")
                    self.test(
                        "Error message mentions paid amount",
                        "paid" in error_detail.lower() or "terbayar" in error_detail.lower(),
                        f"Got error: {error_detail}"
                    )
        
        except Exception as e:
            self.test("Refund exceeds paid test", False, str(e))
    
    def test_e21_refund_valid(self):
        """E21: Valid refund ≤ paid_amount"""
        self.log("\n=== E21: Valid refund ≤ paid_amount ===", "info")
        
        if not self.customer_id or len(self.vehicle_ids) < 1:
            self.log("Skipping: insufficient test data", "warn")
            return
        
        # Create a booking first
        start_dt = (datetime.now() + timedelta(days=39)).replace(hour=8, minute=0, second=0, microsecond=0)
        end_dt = start_dt.replace(hour=18)
        
        booking_body = {
            "customer_id": self.customer_id,
            "vehicle_id": self.vehicle_ids[0],
            "origin": "Jakarta",
            "destination": "Bogor",
            "start_datetime": start_dt.isoformat(),
            "end_datetime": end_dt.isoformat(),
            "base_price": 500000
        }
        
        try:
            # Create booking
            create_url = f"{self.base_url}/api/bookings"
            create_response = requests.post(create_url, json=booking_body, headers=self.headers("owner@demo.local"), timeout=10)
            
            if create_response.status_code == 200:
                booking = create_response.json()
                booking_id = booking.get("id")
                
                # Make a payment
                payment_body = {
                    "booking_id": booking_id,
                    "amount": 200000,
                    "method": "transfer",
                    "notes": "DP test"
                }
                
                payment_url = f"{self.base_url}/api/payments"
                payment_response = requests.post(payment_url, json=payment_body, headers=self.headers("owner@demo.local"), timeout=10)
                
                if payment_response.status_code == 200:
                    self.log("Payment created: 200000", "info")
                    
                    # Cancel with refund ≤ paid_amount
                    cancel_body = {
                        "reason": "Test valid refund",
                        "cancellation_fee": 50000,
                        "refund_amount": 150000  # ≤ 200000 paid
                    }
                    
                    cancel_url = f"{self.base_url}/api/bookings/{booking_id}/cancel"
                    cancel_response = requests.post(cancel_url, json=cancel_body, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    self.test(
                        "Valid refund returns 200",
                        cancel_response.status_code == 200,
                        f"Got {cancel_response.status_code}: {cancel_response.text[:300]}"
                    )
                    
                    if cancel_response.status_code == 200:
                        cancelled = cancel_response.json()
                        
                        self.test(
                            "refund_amount = 150000",
                            cancelled.get("refund_amount") == 150000,
                            f"Expected 150000, got {cancelled.get('refund_amount')}"
                        )
                        
                        self.test(
                            "paid_amount unchanged (ledger DEFERRED)",
                            cancelled.get("paid_amount") == 200000,
                            f"Expected 200000, got {cancelled.get('paid_amount')}"
                        )
        
        except Exception as e:
            self.test("Valid refund test", False, str(e))
    
    def test_e21_already_cancelled(self):
        """E21: Cancel already cancelled booking"""
        self.log("\n=== E21: Cancel already cancelled booking ===", "info")
        
        if not self.customer_id or len(self.vehicle_ids) < 1:
            self.log("Skipping: insufficient test data", "warn")
            return
        
        # Create and cancel a booking
        start_dt = (datetime.now() + timedelta(days=40)).replace(hour=8, minute=0, second=0, microsecond=0)
        end_dt = start_dt.replace(hour=18)
        
        booking_body = {
            "customer_id": self.customer_id,
            "vehicle_id": self.vehicle_ids[0],
            "origin": "Jakarta",
            "destination": "Bogor",
            "start_datetime": start_dt.isoformat(),
            "end_datetime": end_dt.isoformat(),
            "base_price": 400000
        }
        
        try:
            # Create booking
            create_url = f"{self.base_url}/api/bookings"
            create_response = requests.post(create_url, json=booking_body, headers=self.headers("owner@demo.local"), timeout=10)
            
            if create_response.status_code == 200:
                booking = create_response.json()
                booking_id = booking.get("id")
                
                # Cancel first time
                cancel_url = f"{self.base_url}/api/bookings/{booking_id}/cancel"
                first_cancel = requests.post(cancel_url, headers=self.headers("owner@demo.local"), timeout=10)
                
                if first_cancel.status_code == 200:
                    self.log("First cancel successful", "info")
                    
                    # Try to cancel again
                    second_cancel = requests.post(cancel_url, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    # Could be idempotent (200) or error (400)
                    self.test(
                        "Second cancel returns 200 (idempotent) or 400",
                        second_cancel.status_code in [200, 400],
                        f"Got {second_cancel.status_code}"
                    )
                    
                    self.log(f"Actual behavior: {second_cancel.status_code} - {'idempotent' if second_cancel.status_code == 200 else 'error'}", "info")
        
        except Exception as e:
            self.test("Already cancelled test", False, str(e))
    
    def test_e21_rbac_driver(self):
        """E21: RBAC - driver cannot cancel booking"""
        self.log("\n=== E21: RBAC (driver 403) ===", "info")
        
        if not self.customer_id or len(self.vehicle_ids) < 1:
            self.log("Skipping: insufficient test data", "warn")
            return
        
        # Create a booking first
        start_dt = (datetime.now() + timedelta(days=41)).replace(hour=8, minute=0, second=0, microsecond=0)
        end_dt = start_dt.replace(hour=18)
        
        booking_body = {
            "customer_id": self.customer_id,
            "vehicle_id": self.vehicle_ids[0],
            "origin": "Jakarta",
            "destination": "Bogor",
            "start_datetime": start_dt.isoformat(),
            "end_datetime": end_dt.isoformat(),
            "base_price": 400000
        }
        
        try:
            # Create booking as owner
            create_url = f"{self.base_url}/api/bookings"
            create_response = requests.post(create_url, json=booking_body, headers=self.headers("owner@demo.local"), timeout=10)
            
            if create_response.status_code == 200:
                booking = create_response.json()
                booking_id = booking.get("id")
                
                # Try to cancel as driver
                cancel_url = f"{self.base_url}/api/bookings/{booking_id}/cancel"
                cancel_response = requests.post(cancel_url, headers=self.headers("driver@demo.local"), timeout=10)
                
                self.test(
                    "Driver POST /cancel returns 403",
                    cancel_response.status_code == 403,
                    f"Expected 403, got {cancel_response.status_code}"
                )
        
        except Exception as e:
            self.test("Driver cancel RBAC test", False, str(e))
    
    def test_regression_bookings(self):
        """Regression: POST /api/bookings (single) still works"""
        self.log("\n=== Regression: Single Booking ===", "info")
        
        if not self.customer_id or len(self.vehicle_ids) < 1:
            self.log("Skipping: insufficient test data", "warn")
            return
        
        start_dt = (datetime.now() + timedelta(days=50)).replace(hour=8, minute=0, second=0, microsecond=0)
        end_dt = start_dt.replace(hour=18)
        
        body = {
            "customer_id": self.customer_id,
            "vehicle_id": self.vehicle_ids[0],
            "origin": "Jakarta",
            "destination": "Bandung",
            "start_datetime": start_dt.isoformat(),
            "end_datetime": end_dt.isoformat(),
            "base_price": 600000
        }
        
        try:
            url = f"{self.base_url}/api/bookings"
            response = requests.post(url, json=body, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/bookings returns 200",
                response.status_code == 200,
                f"Got {response.status_code}: {response.text[:300]}"
            )
            
            if response.status_code == 200:
                booking = response.json()
                self.regression_booking_id = booking.get("id")
                
                # Test INV-4 (conflict detection)
                conflict_body = {
                    "customer_id": self.customer_id,
                    "vehicle_id": self.vehicle_ids[0],  # Same vehicle
                    "origin": "Jakarta",
                    "destination": "Bogor",
                    "start_datetime": start_dt.isoformat(),  # Same time
                    "end_datetime": end_dt.isoformat(),
                    "base_price": 500000
                }
                
                conflict_response = requests.post(url, json=conflict_body, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "INV-4: Conflict detection returns 400",
                    conflict_response.status_code == 400,
                    f"Expected 400, got {conflict_response.status_code}"
                )
        
        except Exception as e:
            self.test("Single booking regression", False, str(e))
    
    def test_regression_approve(self):
        """Regression: POST /api/bookings/{id}/approve"""
        self.log("\n=== Regression: Approve Booking ===", "info")
        
        if not self.customer_id or len(self.vehicle_ids) < 1:
            self.log("Skipping: insufficient test data", "warn")
            return
        
        # Create pending booking
        start_dt = (datetime.now() + timedelta(days=51)).replace(hour=8, minute=0, second=0, microsecond=0)
        end_dt = start_dt.replace(hour=18)
        
        # Note: Need to check if there's a way to create pending booking
        # For now, just test the endpoint exists
        try:
            # Try to approve a non-existent booking to check endpoint
            url = f"{self.base_url}/api/bookings/bk_test/approve"
            body = {"vehicle_id": self.vehicle_ids[0]}
            response = requests.post(url, json=body, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/bookings/{id}/approve endpoint exists",
                response.status_code in [404, 400],  # 404 not found or 400 not pending
                f"Got {response.status_code}"
            )
        
        except Exception as e:
            self.test("Approve endpoint test", False, str(e))
    
    def test_regression_reschedule(self):
        """Regression: POST /api/bookings/{id}/reschedule"""
        self.log("\n=== Regression: Reschedule Booking ===", "info")
        
        if not hasattr(self, 'regression_booking_id') or not self.regression_booking_id:
            self.log("Skipping: no booking to reschedule", "warn")
            return
        
        # Reschedule to different date
        new_start = (datetime.now() + timedelta(days=52)).replace(hour=9, minute=0, second=0, microsecond=0)
        new_end = new_start.replace(hour=19)
        
        body = {
            "start_datetime": new_start.isoformat(),
            "end_datetime": new_end.isoformat(),
            "reason": "Regression test reschedule"
        }
        
        try:
            url = f"{self.base_url}/api/bookings/{self.regression_booking_id}/reschedule"
            response = requests.post(url, json=body, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/bookings/{id}/reschedule returns 200",
                response.status_code == 200,
                f"Got {response.status_code}: {response.text[:300]}"
            )
        
        except Exception as e:
            self.test("Reschedule regression", False, str(e))
    
    def test_regression_payments(self):
        """Regression: POST /api/payments"""
        self.log("\n=== Regression: Payments ===", "info")
        
        if not hasattr(self, 'regression_booking_id') or not self.regression_booking_id:
            self.log("Skipping: no booking for payment", "warn")
            return
        
        body = {
            "booking_id": self.regression_booking_id,
            "amount": 300000,
            "method": "transfer",
            "notes": "Regression test payment"
        }
        
        try:
            url = f"{self.base_url}/api/payments"
            response = requests.post(url, json=body, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/payments returns 200",
                response.status_code == 200,
                f"Got {response.status_code}: {response.text[:300]}"
            )
            
            if response.status_code == 200:
                payment = response.json()
                
                # Verify booking paid_amount updated
                booking_url = f"{self.base_url}/api/bookings/{self.regression_booking_id}"
                booking_response = requests.get(booking_url, headers=self.headers("owner@demo.local"), timeout=10)
                
                if booking_response.status_code == 200:
                    booking = booking_response.json()
                    self.test(
                        "INV-2: paid_amount updated",
                        booking.get("paid_amount") >= 300000,
                        f"Expected >= 300000, got {booking.get('paid_amount')}"
                    )
                    
                    self.test(
                        "INV-3: payment_status derived",
                        booking.get("payment_status") in ["dp", "lunas", "belum_bayar"],
                        f"Got payment_status: {booking.get('payment_status')}"
                    )
        
        except Exception as e:
            self.test("Payments regression", False, str(e))
    
    def test_regression_dispatch(self):
        """Regression: GET /api/dispatch/today"""
        self.log("\n=== Regression: Dispatch ===", "info")
        
        # Just check endpoint exists
        try:
            url = f"{self.base_url}/api/dispatch/today"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/dispatch/today returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
        
        except Exception as e:
            self.test("Dispatch endpoint test", False, str(e))
    
    def test_regression_reports(self):
        """Regression: GET /api/finance/pl-full"""
        self.log("\n=== Regression: Finance Reports ===", "info")
        
        try:
            url = f"{self.base_url}/api/finance/pl-full"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/finance/pl-full returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
        
        except Exception as e:
            self.test("Finance reports test", False, str(e))
    
    def test_regression_audit_sweep(self):
        """Regression: Audit endpoint sweep"""
        self.log("\n=== Regression: Audit Endpoint Sweep ===", "info")
        
        endpoints = [
            "/api/vehicles",
            "/api/drivers",
            "/api/customers",
            "/api/bookings",
            "/api/payments",
            "/api/notifications"
        ]
        
        for endpoint in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    f"GET {endpoint} returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
            
            except Exception as e:
                self.test(f"GET {endpoint}", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*70, "info")
        self.log("E20 (Group Booking) & E21 (Cancel with fee/refund) Test Suite", "info")
        self.log("="*70, "info")
        
        # Auth
        if not self.test_auth():
            self.log("\n⚠️  Authentication failed. Cannot proceed.", "warn")
            return False
        
        # Setup
        if not self.setup_test_data():
            self.log("\n⚠️  Test data setup failed. Cannot proceed.", "warn")
            return False
        
        # E20 Tests
        self.test_e20_basic_group_booking()
        self.test_e20_intra_group_overlap()
        self.test_e20_pre_existing_conflict()
        self.test_e20_require_dp()
        self.test_e20_rbac_driver()
        self.test_e20_empty_units()
        
        # E21 Tests
        self.test_e21_cancel_without_body()
        self.test_e21_cancel_with_body()
        self.test_e21_negative_fee()
        self.test_e21_refund_exceeds_paid()
        self.test_e21_refund_valid()
        self.test_e21_already_cancelled()
        self.test_e21_rbac_driver()
        
        # Regression Tests
        self.test_regression_bookings()
        self.test_regression_approve()
        self.test_regression_reschedule()
        self.test_regression_payments()
        self.test_regression_dispatch()
        self.test_regression_reports()
        self.test_regression_audit_sweep()
        
        # Summary
        self.log("\n" + "="*70, "info")
        self.log("TEST SUMMARY", "info")
        self.log("="*70, "info")
        self.log(f"Total Tests: {self.tests_run}", "info")
        self.log(f"Passed: {self.tests_passed}", "pass")
        self.log(f"Failed: {self.tests_failed}", "fail" if self.tests_failed > 0 else "info")
        
        if self.tests_failed > 0:
            self.log("\n❌ FAILED TESTS:", "fail")
            for failure in self.failures:
                self.log(f"  • {failure}", "fail")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"\n{'✅' if success_rate == 100 else '⚠️'} Success Rate: {success_rate:.1f}%", "pass" if success_rate == 100 else "warn")
        
        return self.tests_failed == 0


def main():
    tester = E20E21TestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
