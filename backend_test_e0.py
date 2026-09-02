#!/usr/bin/env python3
"""
Backend Test Suite for E0 (Hardening Kepercayaan)
==================================================
Tests bcrypt, rate-limiting, audit logging, last-owner guard, booking lifecycle
"""
import requests
import sys
import time
from datetime import datetime

class E0TestSuite:
    def __init__(self, base_url="https://trip-route-buttons.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.audit_endpoint = None  # Will discover /api/audit-logs or /api/audit_logs
        
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
    
    def login(self, email, password, expect_success=True):
        """Login and store token"""
        try:
            url = f"{self.base_url}/api/auth/login"
            response = requests.post(url, json={"email": email, "password": password}, timeout=10)
            
            if expect_success:
                if response.status_code == 200:
                    data = response.json()
                    token = data.get("token")
                    if token:
                        self.tokens[email] = token
                        self.log(f"Login successful: {email}", "pass")
                        return True, response
                self.log(f"Login failed for {email}: {response.status_code}", "fail")
                return False, response
            else:
                # Expecting failure
                return response.status_code != 200, response
        except Exception as e:
            self.log(f"Login error for {email}: {str(e)}", "fail")
            return False, None
    
    def headers(self, email):
        """Get auth headers for user"""
        token = self.tokens.get(email)
        if not token:
            return {"Content-Type": "application/json"}
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    
    def discover_audit_endpoint(self):
        """Discover the correct audit logs endpoint"""
        self.log("\n=== Discovering Audit Logs Endpoint ===", "info")
        
        # Try both possible endpoints
        for endpoint in ["/api/audit-logs", "/api/audit_logs"]:
            try:
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                if response.status_code == 200:
                    self.audit_endpoint = endpoint
                    self.log(f"Audit endpoint discovered: {endpoint}", "pass")
                    return True
            except Exception:
                pass
        
        self.log("Could not discover audit endpoint", "warn")
        return False
    
    def test_g7_bcrypt_login(self):
        """Test G7: bcrypt password hashing and login"""
        self.log("\n=== Testing G7: Bcrypt Login ===", "info")
        
        # Test correct credentials for all demo accounts
        accounts = [
            ("owner@demo.local", "demo12345", "owner"),
            ("ops@demo.local", "demo12345", "ops_admin"),
            ("driver@demo.local", "demo12345", "driver")
        ]
        
        for email, password, expected_role in accounts:
            success, response = self.login(email, password, expect_success=True)
            self.test(
                f"Login with correct credentials: {email}",
                success and response.status_code == 200,
                f"Expected 200, got {response.status_code if response else 'no response'}"
            )
            
            if success and response:
                data = response.json()
                self.test(
                    f"Login response contains token for {email}",
                    "token" in data and data["token"].startswith("sess_"),
                    f"Token missing or invalid format"
                )
                self.test(
                    f"Login response contains user for {email}",
                    "user" in data and data["user"].get("role") == expected_role,
                    f"User data missing or role mismatch"
                )
        
        # Test wrong password returns 401
        success, response = self.login("owner@demo.local", "wrongpassword", expect_success=False)
        self.test(
            "Login with wrong password returns 401",
            response and response.status_code == 401,
            f"Expected 401, got {response.status_code if response else 'no response'}"
        )
        
        # Test non-existent user returns 401
        success, response = self.login("nonexistent@demo.local", "demo12345", expect_success=False)
        self.test(
            "Login with non-existent user returns 401",
            response and response.status_code == 401,
            f"Expected 401, got {response.status_code if response else 'no response'}"
        )
    
    def test_g7_rate_limit(self):
        """Test G7: Rate limiting on failed login attempts"""
        self.log("\n=== Testing G7: Rate Limiting ===", "info")
        
        # Use a test email that won't lock out real accounts
        test_email = f"ratetest_{int(time.time())}@x.local"
        wrong_password = "wrongpassword123"
        
        self.log(f"Testing rate limit with email: {test_email}", "info")
        
        # Make 8 failed login attempts (should all return 401)
        for i in range(8):
            try:
                url = f"{self.base_url}/api/auth/login"
                response = requests.post(url, json={"email": test_email, "password": wrong_password}, timeout=10)
                
                self.test(
                    f"Failed login attempt {i+1}/8 returns 401",
                    response.status_code == 401,
                    f"Expected 401, got {response.status_code}"
                )
                
                # Small delay to avoid overwhelming the server
                time.sleep(0.1)
            except Exception as e:
                self.test(f"Failed login attempt {i+1}/8", False, str(e))
        
        # 9th attempt should return 429 (rate limited)
        try:
            url = f"{self.base_url}/api/auth/login"
            response = requests.post(url, json={"email": test_email, "password": wrong_password}, timeout=10)
            
            self.test(
                "9th failed login attempt returns 429 (rate limited)",
                response.status_code == 429,
                f"Expected 429, got {response.status_code}"
            )
            
            if response.status_code == 429:
                data = response.json()
                self.test(
                    "Rate limit response contains appropriate message",
                    "Terlalu banyak percobaan" in data.get("detail", ""),
                    f"Got detail: {data.get('detail')}"
                )
        except Exception as e:
            self.test("9th failed login (rate limit)", False, str(e))
        
        # Test that successful login clears the failure budget
        self.log("Testing that successful login clears failure budget...", "info")
        
        # Use a fresh test email
        test_email2 = f"ratetest2_{int(time.time())}@x.local"
        
        # Create a test user first (as owner)
        try:
            url = f"{self.base_url}/api/users"
            user_data = {
                "name": "Rate Test User",
                "email": test_email2,
                "password": "testpass123",
                "role": "driver",
                "phone": ""
            }
            response = requests.post(url, json=user_data, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                self.log(f"Created test user: {test_email2}", "info")
                
                # Make 3 failed attempts
                for i in range(3):
                    requests.post(f"{self.base_url}/api/auth/login", 
                                json={"email": test_email2, "password": "wrong"}, timeout=10)
                    time.sleep(0.1)
                
                # Now login successfully
                success_response = requests.post(f"{self.base_url}/api/auth/login",
                                               json={"email": test_email2, "password": "testpass123"}, timeout=10)
                
                self.test(
                    "Successful login after failed attempts returns 200",
                    success_response.status_code == 200,
                    f"Expected 200, got {success_response.status_code}"
                )
                
                # Now we should be able to login again immediately (budget cleared)
                success_response2 = requests.post(f"{self.base_url}/api/auth/login",
                                                json={"email": test_email2, "password": "testpass123"}, timeout=10)
                
                self.test(
                    "Subsequent successful login works (budget cleared)",
                    success_response2.status_code == 200,
                    f"Expected 200, got {success_response2.status_code}"
                )
        except Exception as e:
            self.log(f"Could not test successful login clearing budget: {str(e)}", "warn")
    
    def test_g3_audit_logging(self):
        """Test G3: Audit logging for various actions"""
        self.log("\n=== Testing G3: Audit Logging ===", "info")
        
        if not self.audit_endpoint:
            if not self.discover_audit_endpoint():
                self.log("Skipping audit tests - endpoint not found", "warn")
                return
        
        # Get initial audit log count
        try:
            url = f"{self.base_url}{self.audit_endpoint}"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                f"GET {self.audit_endpoint} returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
            
            if response.status_code == 200:
                initial_logs = response.json()
                self.log(f"Initial audit log count: {len(initial_logs)}", "info")
                
                # Check for login audit entries
                login_logs = [log for log in initial_logs if log.get("action") == "login"]
                self.test(
                    "Audit logs contain login entries",
                    len(login_logs) > 0,
                    f"Found {len(login_logs)} login entries"
                )
                
                # Check for login_failed entries
                failed_logs = [log for log in initial_logs if log.get("action") == "login_failed"]
                self.test(
                    "Audit logs contain login_failed entries",
                    len(failed_logs) > 0,
                    f"Found {len(failed_logs)} login_failed entries"
                )
                
                # Perform actions and verify audit logs
                
                # 1. Create a user
                test_user_email = f"audittest_{int(time.time())}@demo.local"
                user_data = {
                    "name": "Audit Test User",
                    "email": test_user_email,
                    "password": "testpass123",
                    "role": "driver",
                    "phone": "081234567890"
                }
                create_response = requests.post(f"{self.base_url}/api/users", 
                                              json=user_data, 
                                              headers=self.headers("owner@demo.local"), 
                                              timeout=10)
                
                if create_response.status_code == 200:
                    created_user = create_response.json()
                    user_id = created_user.get("id")
                    
                    # Wait a bit for audit log to be written
                    time.sleep(0.5)
                    
                    # Check audit logs for user create
                    audit_response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                    if audit_response.status_code == 200:
                        logs = audit_response.json()
                        user_create_log = [log for log in logs 
                                         if log.get("action") == "create" 
                                         and log.get("entity_type") == "user"
                                         and log.get("entity_id") == user_id]
                        
                        self.test(
                            "Audit log created for user creation",
                            len(user_create_log) > 0,
                            f"No audit log found for user create"
                        )
                    
                    # 2. Update the user
                    update_data = {"name": "Updated Audit Test User"}
                    update_response = requests.patch(f"{self.base_url}/api/users/{user_id}",
                                                    json=update_data,
                                                    headers=self.headers("owner@demo.local"),
                                                    timeout=10)
                    
                    if update_response.status_code == 200:
                        time.sleep(0.5)
                        
                        # Check audit logs for user update
                        audit_response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                        if audit_response.status_code == 200:
                            logs = audit_response.json()
                            user_update_log = [log for log in logs
                                             if log.get("action") == "update"
                                             and log.get("entity_type") == "user"
                                             and log.get("entity_id") == user_id]
                            
                            self.test(
                                "Audit log created for user update",
                                len(user_update_log) > 0,
                                f"No audit log found for user update"
                            )
                
                # 3. Test logout audit
                logout_response = requests.post(f"{self.base_url}/api/auth/logout",
                                              headers=self.headers("owner@demo.local"),
                                              timeout=10)
                
                if logout_response.status_code == 200:
                    time.sleep(0.5)
                    
                    # Re-login to check audit logs
                    self.login("owner@demo.local", "demo12345")
                    
                    audit_response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                    if audit_response.status_code == 200:
                        logs = audit_response.json()
                        logout_logs = [log for log in logs if log.get("action") == "logout"]
                        
                        self.test(
                            "Audit log created for logout",
                            len(logout_logs) > 0,
                            f"No audit log found for logout"
                        )
                
        except Exception as e:
            self.test("Audit logging tests", False, str(e))
    
    def test_g8_last_owner_guard(self):
        """Test G8: Last owner and self-guard protections"""
        self.log("\n=== Testing G8: Last Owner & Self Guard ===", "info")
        
        # Get owner user ID
        try:
            url = f"{self.base_url}/api/auth/me"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                owner_user = response.json()
                owner_id = owner_user.get("id")
                
                # Test 1: Cannot change own role
                self.log("Testing: Owner cannot change own role", "info")
                update_response = requests.patch(f"{self.base_url}/api/users/{owner_id}",
                                               json={"role": "ops_admin"},
                                               headers=self.headers("owner@demo.local"),
                                               timeout=10)
                
                self.test(
                    "Owner cannot change own role (returns 400)",
                    update_response.status_code == 400,
                    f"Expected 400, got {update_response.status_code}"
                )
                
                if update_response.status_code == 400:
                    data = update_response.json()
                    self.test(
                        "Error message mentions 'peran akun sendiri'",
                        "peran akun sendiri" in data.get("detail", "").lower(),
                        f"Got detail: {data.get('detail')}"
                    )
                
                # Test 2: Cannot deactivate own account
                self.log("Testing: Owner cannot deactivate own account", "info")
                update_response = requests.patch(f"{self.base_url}/api/users/{owner_id}",
                                               json={"status": "inactive"},
                                               headers=self.headers("owner@demo.local"),
                                               timeout=10)
                
                self.test(
                    "Owner cannot deactivate own account (returns 400)",
                    update_response.status_code == 400,
                    f"Expected 400, got {update_response.status_code}"
                )
                
                if update_response.status_code == 400:
                    data = update_response.json()
                    self.test(
                        "Error message mentions 'menonaktifkan akun sendiri'",
                        "menonaktifkan akun sendiri" in data.get("detail", "").lower(),
                        f"Got detail: {data.get('detail')}"
                    )
                
                # Test 3: Can create second owner, then demote/deactivate works
                self.log("Testing: Creating second owner allows demotion", "info")
                
                # Create second owner
                second_owner_email = f"owner2_{int(time.time())}@demo.local"
                owner_data = {
                    "name": "Second Owner",
                    "email": second_owner_email,
                    "password": "demo12345",
                    "role": "owner",
                    "phone": ""
                }
                create_response = requests.post(f"{self.base_url}/api/users",
                                              json=owner_data,
                                              headers=self.headers("owner@demo.local"),
                                              timeout=10)
                
                if create_response.status_code == 200:
                    second_owner = create_response.json()
                    second_owner_id = second_owner.get("id")
                    
                    self.log(f"Created second owner: {second_owner_id}", "info")
                    
                    # Now demoting the second owner should work
                    demote_response = requests.patch(f"{self.base_url}/api/users/{second_owner_id}",
                                                    json={"role": "ops_admin"},
                                                    headers=self.headers("owner@demo.local"),
                                                    timeout=10)
                    
                    self.test(
                        "Can demote second owner when multiple owners exist",
                        demote_response.status_code == 200,
                        f"Expected 200, got {demote_response.status_code}"
                    )
                    
                    # Restore to owner for next test
                    if demote_response.status_code == 200:
                        requests.patch(f"{self.base_url}/api/users/{second_owner_id}",
                                     json={"role": "owner"},
                                     headers=self.headers("owner@demo.local"),
                                     timeout=10)
                    
                    # Test deactivating second owner
                    deactivate_response = requests.patch(f"{self.base_url}/api/users/{second_owner_id}",
                                                        json={"status": "inactive"},
                                                        headers=self.headers("owner@demo.local"),
                                                        timeout=10)
                    
                    self.test(
                        "Can deactivate second owner when multiple owners exist",
                        deactivate_response.status_code == 200,
                        f"Expected 200, got {deactivate_response.status_code}"
                    )
                    
                    # Now try to demote/deactivate the first owner (should fail - only 1 active owner left)
                    demote_first_response = requests.patch(f"{self.base_url}/api/users/{owner_id}",
                                                          json={"role": "ops_admin"},
                                                          headers=self.headers("owner@demo.local"),
                                                          timeout=10)
                    
                    self.test(
                        "Cannot demote last active owner (returns 400)",
                        demote_first_response.status_code == 400,
                        f"Expected 400, got {demote_first_response.status_code}"
                    )
                    
                    if demote_first_response.status_code == 400:
                        data = demote_first_response.json()
                        self.test(
                            "Error message mentions 'minimal harus ada 1 owner aktif'",
                            "minimal" in data.get("detail", "").lower() and "owner aktif" in data.get("detail", "").lower(),
                            f"Got detail: {data.get('detail')}"
                        )
                
        except Exception as e:
            self.test("Last owner guard tests", False, str(e))
    
    def test_g2_booking_lifecycle(self):
        """Test G2: Booking lifecycle (confirmed -> ongoing -> completed)"""
        self.log("\n=== Testing G2: Booking Lifecycle ===", "info")
        
        try:
            # Get driver's trips
            url = f"{self.base_url}/api/driver/my-trips"
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "GET /api/driver/my-trips returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
            
            if response.status_code == 200:
                trips = response.json()
                self.log(f"Found {len(trips)} trips for driver", "info")
                
                # Find a trip with a booking_id
                trip_with_booking = None
                for trip in trips:
                    if trip.get("booking_id"):
                        trip_with_booking = trip
                        break
                
                if trip_with_booking:
                    booking_id = trip_with_booking.get("booking_id")
                    trip_id = trip_with_booking.get("id")
                    
                    self.log(f"Using booking_id: {booking_id}, trip_id: {trip_id}", "info")
                    
                    # Get initial booking status
                    booking_url = f"{self.base_url}/api/bookings/{booking_id}"
                    booking_response = requests.get(booking_url, 
                                                   headers=self.headers("owner@demo.local"), 
                                                   timeout=10)
                    
                    if booking_response.status_code == 200:
                        initial_booking = booking_response.json()
                        initial_status = initial_booking.get("status")
                        self.log(f"Initial booking status: {initial_status}", "info")
                        
                        # If not confirmed, we need to create a new confirmed booking
                        if initial_status != "confirmed":
                            self.log("Creating a new confirmed booking for testing...", "info")
                            
                            # Get a vehicle and customer
                            vehicles_response = requests.get(f"{self.base_url}/api/vehicles",
                                                           headers=self.headers("owner@demo.local"),
                                                           timeout=10)
                            customers_response = requests.get(f"{self.base_url}/api/customers",
                                                            headers=self.headers("owner@demo.local"),
                                                            timeout=10)
                            drivers_response = requests.get(f"{self.base_url}/api/drivers",
                                                          headers=self.headers("owner@demo.local"),
                                                          timeout=10)
                            
                            if (vehicles_response.status_code == 200 and 
                                customers_response.status_code == 200 and
                                drivers_response.status_code == 200):
                                
                                vehicles = vehicles_response.json()
                                customers = customers_response.json()
                                drivers = drivers_response.json()
                                
                                if vehicles and customers and drivers:
                                    # Find the driver that matches driver@demo.local
                                    driver_user = requests.get(f"{self.base_url}/api/auth/me",
                                                             headers=self.headers("driver@demo.local"),
                                                             timeout=10).json()
                                    
                                    test_driver = None
                                    for d in drivers:
                                        if d.get("user_id") == driver_user.get("id"):
                                            test_driver = d
                                            break
                                    
                                    if not test_driver and drivers:
                                        test_driver = drivers[0]
                                    
                                    # Create a new booking
                                    new_booking_data = {
                                        "customer_id": customers[0].get("id"),
                                        "vehicle_id": vehicles[0].get("id"),
                                        "driver_id": test_driver.get("id") if test_driver else None,
                                        "start_datetime": "2025-08-20T08:00:00Z",
                                        "end_datetime": "2025-08-20T18:00:00Z",
                                        "destination": "Test Destination",
                                        "total_amount": 1000000,
                                        "status": "confirmed"
                                    }
                                    
                                    create_booking_response = requests.post(f"{self.base_url}/api/bookings",
                                                                          json=new_booking_data,
                                                                          headers=self.headers("owner@demo.local"),
                                                                          timeout=10)
                                    
                                    if create_booking_response.status_code == 200:
                                        new_booking = create_booking_response.json()
                                        booking_id = new_booking.get("id")
                                        self.log(f"Created new confirmed booking: {booking_id}", "info")
                        
                        # Test checkin (confirmed -> ongoing)
                        self.log("Testing checkin (confirmed -> ongoing)...", "info")
                        checkin_response = requests.post(f"{self.base_url}/api/driver/checkin",
                                                        json={"booking_id": booking_id},
                                                        headers=self.headers("driver@demo.local"),
                                                        timeout=10)
                        
                        self.test(
                            "POST /api/driver/checkin returns 200",
                            checkin_response.status_code == 200,
                            f"Expected 200, got {checkin_response.status_code}"
                        )
                        
                        if checkin_response.status_code == 200:
                            trip_data = checkin_response.json()
                            trip_id = trip_data.get("id")
                            
                            # Verify booking status is now 'ongoing'
                            time.sleep(0.5)
                            booking_response = requests.get(f"{self.base_url}/api/bookings/{booking_id}",
                                                          headers=self.headers("owner@demo.local"),
                                                          timeout=10)
                            
                            if booking_response.status_code == 200:
                                booking = booking_response.json()
                                self.test(
                                    "Booking status is 'ongoing' after checkin",
                                    booking.get("status") == "ongoing",
                                    f"Expected 'ongoing', got {booking.get('status')}"
                                )
                            
                            # Test checkout (ongoing -> completed)
                            self.log("Testing checkout (ongoing -> completed)...", "info")
                            checkout_response = requests.post(f"{self.base_url}/api/driver/checkout",
                                                            json={"trip_id": trip_id},
                                                            headers=self.headers("driver@demo.local"),
                                                            timeout=10)
                            
                            self.test(
                                "POST /api/driver/checkout returns 200",
                                checkout_response.status_code == 200,
                                f"Expected 200, got {checkout_response.status_code}"
                            )
                            
                            if checkout_response.status_code == 200:
                                # Verify booking status is now 'completed' with payment_status 'selesai'
                                time.sleep(0.5)
                                booking_response = requests.get(f"{self.base_url}/api/bookings/{booking_id}",
                                                              headers=self.headers("owner@demo.local"),
                                                              timeout=10)
                                
                                if booking_response.status_code == 200:
                                    booking = booking_response.json()
                                    self.test(
                                        "Booking status is 'completed' after checkout",
                                        booking.get("status") == "completed",
                                        f"Expected 'completed', got {booking.get('status')}"
                                    )
                                    
                                    self.test(
                                        "Booking payment_status is 'selesai' after checkout",
                                        booking.get("payment_status") == "selesai",
                                        f"Expected 'selesai', got {booking.get('payment_status')}"
                                    )
                        
                        # Test dashboard active_bookings count
                        self.log("Testing dashboard active_bookings count...", "info")
                        dashboard_response = requests.get(f"{self.base_url}/api/dashboard",
                                                         headers=self.headers("owner@demo.local"),
                                                         timeout=10)
                        
                        if dashboard_response.status_code == 200:
                            dashboard = dashboard_response.json()
                            active_bookings = dashboard.get("active_bookings")
                            
                            # Count confirmed + ongoing bookings
                            bookings_response = requests.get(f"{self.base_url}/api/bookings",
                                                            headers=self.headers("owner@demo.local"),
                                                            timeout=10)
                            
                            if bookings_response.status_code == 200:
                                all_bookings = bookings_response.json()
                                expected_active = len([b for b in all_bookings 
                                                     if b.get("status") in ["confirmed", "ongoing"]])
                                
                                self.test(
                                    "Dashboard active_bookings counts confirmed+ongoing",
                                    active_bookings == expected_active,
                                    f"Expected {expected_active}, got {active_bookings}"
                                )
                else:
                    self.log("No trips with booking_id found, creating test scenario...", "warn")
                    # Could create a full test scenario here if needed
        
        except Exception as e:
            self.test("Booking lifecycle tests", False, str(e))
    
    def test_regression(self):
        """Test regression: Existing flows still work"""
        self.log("\n=== Testing Regression ===", "info")
        
        # Test logout
        try:
            url = f"{self.base_url}/api/auth/logout"
            response = requests.post(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/auth/logout returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
            
            # Re-login for subsequent tests
            self.login("owner@demo.local", "demo12345")
        except Exception as e:
            self.test("Logout regression", False, str(e))
        
        # Test dashboard
        try:
            url = f"{self.base_url}/api/dashboard"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/dashboard returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test(
                    "Dashboard contains role-aware data",
                    "role" in data and "vehicles" in data and "active_bookings" in data,
                    "Missing expected dashboard fields"
                )
        except Exception as e:
            self.test("Dashboard regression", False, str(e))
        
        # Test bookings list
        try:
            url = f"{self.base_url}/api/bookings"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/bookings returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
        except Exception as e:
            self.test("Bookings list regression", False, str(e))
        
        # Test users list (owner only)
        try:
            url = f"{self.base_url}/api/users"
            
            # Owner should get 200
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            self.test(
                "GET /api/users as owner returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
            
            # Ops admin should get 403
            response = requests.get(url, headers=self.headers("ops@demo.local"), timeout=10)
            self.test(
                "GET /api/users as ops_admin returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
            
            # Driver should get 403
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            self.test(
                "GET /api/users as driver returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("Users RBAC regression", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*60, "info")
        self.log("E0 (Hardening Kepercayaan) Backend Test Suite", "info")
        self.log("="*60, "info")
        
        # Run tests in order
        self.test_g7_bcrypt_login()
        self.test_g7_rate_limit()
        self.test_g3_audit_logging()
        self.test_g8_last_owner_guard()
        self.test_g2_booking_lifecycle()
        self.test_regression()
        
        # Print summary
        self.log("\n" + "="*60, "info")
        self.log("TEST SUMMARY", "info")
        self.log("="*60, "info")
        self.log(f"Total Tests: {self.tests_run}", "info")
        self.log(f"Passed: {self.tests_passed}", "pass")
        self.log(f"Failed: {self.tests_failed}", "fail" if self.tests_failed > 0 else "info")
        
        if self.tests_failed > 0:
            self.log("\nFailed Tests:", "fail")
            for failure in self.failures:
                self.log(f"  - {failure}", "fail")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"\nSuccess Rate: {success_rate:.1f}%", "pass" if success_rate >= 95 else "warn")
        
        return self.tests_failed == 0


def main():
    tester = E0TestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
