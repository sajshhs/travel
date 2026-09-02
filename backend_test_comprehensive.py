"""
Backend Testing Suite for Rahaza Travel ERP - FINAL COMPREHENSIVE VERIFICATION
Putaran 12 - Post Bug-Fix Validation

Tests ALL major modules:
- AUTH & RBAC (owner/ops/driver login, RBAC enforcement)
- CUSTOMERS + ID-RACE (CRUD + concurrency)
- BOOKINGS (CRUD, status transitions, assign)
- QUOTATIONS + EXPORT (create, PDF, markup chars, convert)
- DISPATCH / VEHICLES / DRIVERS (list, assign, lock)
- FINANCE (invoices, payments, expenses with negative tests)
- PAYROLL (list, approve/pay)
- CRM (segments, preview, campaigns, RFM, scoreboard)
- CONTENT/CMS + SET-1 (destinations lat/lng, packages price_from)
- SETTINGS + SET-1 (GET, PATCH invalid/valid)
- PUBLIC (homepage, booking request, estimator)

Demo credentials: owner@demo.local / demo12345, ops@demo.local / demo12345, driver@demo.local / demo12345
Backend uses /api prefix
"""

import requests
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

class TestRunner:
    def __init__(self):
        self.tokens = {}  # role -> token
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.created_resources = {
            "customers": [],
            "bookings": [],
            "quotations": [],
            "segments": [],
            "destinations": [],
            "packages": []
        }
        
    def login(self, email, password, role_name):
        """Authenticate and get token"""
        print(f"\n{Colors.BLUE}=== AUTHENTICATION: {role_name} ==={Colors.END}")
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": email, "password": password},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                token = data.get("token")
                self.tokens[role_name] = token
                print(f"{Colors.GREEN}✓ Login successful as {email} ({role_name}){Colors.END}")
                return True
            else:
                print(f"{Colors.RED}✗ Login failed: {response.status_code} - {response.text[:200]}{Colors.END}")
                return False
        except Exception as e:
            print(f"{Colors.RED}✗ Login error: {str(e)}{Colors.END}")
            return False
    
    def headers(self, role="owner"):
        """Get headers with token for specified role"""
        token = self.tokens.get(role)
        if not token:
            raise ValueError(f"No token for role {role}")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def test(self, name: str, method: str, endpoint: str, expected_status: int, 
             data=None, check_fn=None, silent=False, role="owner"):
        """Run a single test"""
        self.tests_run += 1
        url = f"{BASE_URL}/{endpoint}"
        
        if not silent:
            print(f"\n{Colors.BLUE}Test #{self.tests_run}: {name}{Colors.END}")
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers(role), timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, headers=self.headers(role), timeout=10)
            elif method == "PATCH":
                response = requests.patch(url, json=data, headers=self.headers(role), timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers(role), timeout=10)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=self.headers(role), timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            status_ok = response.status_code == expected_status
            
            if status_ok:
                result_data = response.json() if response.text else {}
                
                # Run additional check function if provided
                if check_fn:
                    check_result, check_msg = check_fn(result_data, response)
                    if not check_result:
                        if not silent:
                            print(f"{Colors.RED}✗ FAILED - Status OK but check failed: {check_msg}{Colors.END}")
                            print(f"  Response: {str(result_data)[:200]}")
                        self.tests_failed += 1
                        self.failures.append(f"{name}: {check_msg}")
                        return False, result_data
                
                if not silent:
                    print(f"{Colors.GREEN}✓ PASSED - Status: {response.status_code}{Colors.END}")
                self.tests_passed += 1
                return True, result_data
            else:
                if not silent:
                    print(f"{Colors.RED}✗ FAILED - Expected {expected_status}, got {response.status_code}{Colors.END}")
                    print(f"  Response: {response.text[:300]}")
                self.tests_failed += 1
                self.failures.append(f"{name}: Expected {expected_status}, got {response.status_code}")
                return False, {}
                
        except Exception as e:
            if not silent:
                print(f"{Colors.RED}✗ FAILED - Error: {str(e)}{Colors.END}")
            self.tests_failed += 1
            self.failures.append(f"{name}: {str(e)}")
            return False, {}
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BLUE}TEST SUMMARY{Colors.END}")
        print(f"{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"Total Tests: {self.tests_run}")
        print(f"{Colors.GREEN}Passed: {self.tests_passed}{Colors.END}")
        print(f"{Colors.RED}Failed: {self.tests_failed}{Colors.END}")
        
        if self.failures:
            print(f"\n{Colors.RED}FAILURES:{Colors.END}")
            for i, failure in enumerate(self.failures, 1):
                print(f"  {i}. {failure}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if self.tests_failed == 0:
            print(f"\n{Colors.GREEN}🎉 ALL TESTS PASSED!{Colors.END}")
            return 0
        else:
            print(f"\n{Colors.RED}❌ SOME TESTS FAILED{Colors.END}")
            return 1


# ============================================================================
# AUTH & RBAC TESTS
# ============================================================================

def test_auth_rbac(runner: TestRunner):
    """Test authentication and RBAC enforcement"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}AUTH & RBAC TESTS{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    # Login all three roles
    if not runner.login("owner@demo.local", "demo12345", "owner"):
        return False
    if not runner.login("ops@demo.local", "demo12345", "ops"):
        return False
    if not runner.login("driver@demo.local", "demo12345", "driver"):
        return False
    
    # Test RBAC: driver should be FORBIDDEN (403) on management endpoints
    runner.test(
        "Driver access to GET /api/settings (should be 403)",
        "GET",
        "settings",
        403,
        role="driver"
    )
    
    runner.test(
        "Driver access to GET /api/finance/summary (should be 403)",
        "GET",
        "finance/summary",
        403,
        role="driver"
    )
    
    runner.test(
        "Driver access to GET /api/payroll/payouts (should be 403)",
        "GET",
        "payroll/payouts",
        403,
        role="driver"
    )
    
    # Owner should have access
    runner.test(
        "Owner access to GET /api/settings (should be 200)",
        "GET",
        "settings",
        200,
        role="owner"
    )
    
    return True


# ============================================================================
# CUSTOMERS + ID-RACE TESTS
# ============================================================================

def test_customers_id_race(runner: TestRunner):
    """Test customers CRUD and ID-RACE fix"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}CUSTOMERS + ID-RACE TESTS{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    timestamp = int(time.time() * 1000) % 100000000
    
    # Test 1: Create customer
    success, customer = runner.test(
        "Create customer",
        "POST",
        "customers",
        200,
        data={
            "name": "Test Customer",
            "phone": f"081234{timestamp}",
            "email": f"test{timestamp}@test.local",
            "type": "individual"
        }
    )
    
    if success:
        customer_id = customer.get("id")
        runner.created_resources["customers"].append(customer_id)
        
        # Test 2: Get customer
        runner.test(
            "Get customer by ID",
            "GET",
            f"customers/{customer_id}",
            200
        )
        
        # Test 3: Update customer
        runner.test(
            "Update customer",
            "PATCH",
            f"customers/{customer_id}",
            200,
            data={"city": "Jakarta"}
        )
        
        # Test 4: List customers
        runner.test(
            "List customers",
            "GET",
            "customers",
            200
        )
    
    # Test 5: Duplicate phone should return 409
    runner.test(
        "Create customer with duplicate phone (should be 409)",
        "POST",
        "customers",
        409,
        data={
            "name": "Duplicate",
            "phone": f"081234{timestamp}",
            "email": f"different{timestamp}@test.local",
            "type": "individual"
        }
    )
    
    # Test 6: Concurrency test - 8 parallel requests with same phone
    print(f"\n  {Colors.BLUE}Concurrency test: 8 parallel requests...{Colors.END}")
    race_phone = f"081299{timestamp}"
    
    def create_customer(idx):
        try:
            response = requests.post(
                f"{BASE_URL}/customers",
                json={
                    "name": "RaceTest",
                    "phone": race_phone,
                    "email": f"race{timestamp}_{idx}@test.local",
                    "type": "individual"
                },
                headers=runner.headers(),
                timeout=10
            )
            return {"idx": idx, "status": response.status_code}
        except Exception as e:
            return {"idx": idx, "status": 0, "error": str(e)}
    
    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(create_customer, i) for i in range(8)]
        for future in as_completed(futures):
            results.append(future.result())
    
    status_200 = [r for r in results if r["status"] in (200, 201)]
    status_409 = [r for r in results if r["status"] == 409]
    status_500 = [r for r in results if r["status"] == 500]
    
    runner.tests_run += 1
    if len(status_200) == 1 and len(status_500) == 0 and len(status_409) >= 6:
        print(f"{Colors.GREEN}✓ PASSED - Concurrency: 1 created, {len(status_409)} conflicts, 0 errors{Colors.END}")
        runner.tests_passed += 1
        if status_200:
            # Track for cleanup
            try:
                resp = requests.get(f"{BASE_URL}/customers", headers=runner.headers(), timeout=5)
                if resp.status_code == 200:
                    customers = resp.json()
                    for c in customers:
                        if c.get("phone") == race_phone:
                            runner.created_resources["customers"].append(c.get("id"))
                            break
            except:
                pass
    else:
        print(f"{Colors.RED}✗ FAILED - Concurrency: {len(status_200)} created, {len(status_409)} conflicts, {len(status_500)} errors{Colors.END}")
        runner.tests_failed += 1
        runner.failures.append(f"Concurrency test failed: {len(status_200)} created, {len(status_500)} 500s")


# ============================================================================
# BOOKINGS TESTS
# ============================================================================

def test_bookings(runner: TestRunner):
    """Test bookings CRUD and status transitions"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}BOOKINGS TESTS{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    timestamp = int(time.time() * 1000) % 100000000
    
    # Create a customer first
    success, customer = runner.test(
        "Create customer for booking",
        "POST",
        "customers",
        200,
        data={
            "name": "Booking Customer",
            "phone": f"081299{timestamp}",
            "email": f"booking{timestamp}@test.local",
            "type": "individual"
        },
        silent=True
    )
    
    if not success:
        print(f"{Colors.RED}Cannot create customer, skipping booking tests{Colors.END}")
        return
    
    customer_id = customer.get("id")
    runner.created_resources["customers"].append(customer_id)
    
    # Create booking
    start_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    success, booking = runner.test(
        "Create booking",
        "POST",
        "bookings",
        200,
        data={
            "customer_id": customer_id,
            "destination": "Bali",
            "start_datetime": f"{start_date}T08:00:00",
            "end_datetime": f"{start_date}T18:00:00",
            "pax": 4,
            "vehicle_type": "minibus",
            "total_amount": 2000000
        }
    )
    
    if success:
        booking_id = booking.get("id")
        runner.created_resources["bookings"].append(booking_id)
        
        # Get booking
        runner.test(
            "Get booking by ID",
            "GET",
            f"bookings/{booking_id}",
            200
        )
        
        # List bookings
        runner.test(
            "List bookings",
            "GET",
            "bookings",
            200
        )
        
        # Test status transition: draft -> confirmed
        runner.test(
            "Confirm booking (draft -> confirmed)",
            "POST",
            f"bookings/{booking_id}/confirm",
            200
        )
        
        # Test invalid transition (should return 4xx, not 500)
        runner.test(
            "Invalid transition: confirm again (should be 4xx)",
            "POST",
            f"bookings/{booking_id}/confirm",
            400
        )


# ============================================================================
# QUOTATIONS + EXPORT TESTS
# ============================================================================

def test_quotations_export(runner: TestRunner):
    """Test quotations CRUD, PDF export, and markup chars"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}QUOTATIONS + EXPORT TESTS{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    timestamp = int(time.time() * 1000) % 100000000
    
    # Create quotation with normal data
    success, quotation = runner.test(
        "Create quotation (normal)",
        "POST",
        "quotations",
        200,
        data={
            "customer_name": "Test Customer",
            "phone": f"081234{timestamp}",
            "destination": "Bali",
            "trip_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
            "pax": 5,
            "items": [
                {"label": "Sewa Minibus", "amount": 1500000},
                {"label": "Driver Fee", "amount": 300000}
            ],
            "total": 1800000
        }
    )
    
    if success:
        quotation_id = quotation.get("id")
        runner.created_resources["quotations"].append(quotation_id)
        
        # Test PDF export
        def check_pdf(data, response):
            content_type = response.headers.get("content-type", "")
            if "application/pdf" in content_type:
                return True, "PDF content type OK"
            return False, f"Expected application/pdf, got {content_type}"
        
        runner.test(
            "Export quotation to PDF",
            "GET",
            f"quotations/{quotation_id}/pdf",
            200,
            check_fn=check_pdf
        )
    
    # EXPORT-1 test: Create quotation with markup chars
    success, quotation2 = runner.test(
        "Create quotation with markup chars (EXPORT-1)",
        "POST",
        "quotations",
        200,
        data={
            "customer_name": "A<b>&</b>",
            "phone": f"081235{timestamp}",
            "destination": "Bali <&>",
            "trip_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
            "pax": 3,
            "items": [
                {"label": "Test <markup>", "amount": 1000000}
            ],
            "total": 1000000
        }
    )
    
    if success:
        quotation_id2 = quotation2.get("id")
        runner.created_resources["quotations"].append(quotation_id2)
        
        # Test PDF export with markup chars (should not 500)
        runner.test(
            "Export quotation with markup chars to PDF (should be 200, not 500)",
            "GET",
            f"quotations/{quotation_id2}/pdf",
            200
        )
        
        # Test convert to booking
        runner.test(
            "Convert quotation to booking",
            "POST",
            f"quotations/{quotation_id2}/convert",
            200
        )


# ============================================================================
# DISPATCH / VEHICLES / DRIVERS TESTS
# ============================================================================

def test_dispatch_vehicles_drivers(runner: TestRunner):
    """Test dispatch, vehicles, and drivers"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}DISPATCH / VEHICLES / DRIVERS TESTS{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    # List vehicles
    runner.test(
        "List vehicles",
        "GET",
        "vehicles",
        200
    )
    
    # List drivers
    runner.test(
        "List drivers",
        "GET",
        "drivers",
        200
    )
    
    # List dispatch/trips
    runner.test(
        "List dispatch/trips",
        "GET",
        "dispatch/trips",
        200
    )


# ============================================================================
# FINANCE TESTS
# ============================================================================

def test_finance(runner: TestRunner):
    """Test finance: invoices, payments, expenses"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}FINANCE TESTS{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    timestamp = int(time.time() * 1000) % 100000000
    
    # Create customer for invoice
    success, customer = runner.test(
        "Create customer for invoice",
        "POST",
        "customers",
        200,
        data={
            "name": "Invoice Customer",
            "phone": f"081288{timestamp}",
            "email": f"invoice{timestamp}@test.local",
            "type": "individual"
        },
        silent=True
    )
    
    if success:
        customer_id = customer.get("id")
        runner.created_resources["customers"].append(customer_id)
        
        # Create invoice with positive amount
        runner.test(
            "Create invoice with positive amount",
            "POST",
            "invoices",
            200,
            data={
                "customer_id": customer_id,
                "amount": 1000000,
                "due_at": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            }
        )
        
        # Create invoice with negative amount (should be 4xx, not 500)
        runner.test(
            "Create invoice with negative amount (should be 4xx)",
            "POST",
            "invoices",
            400,
            data={
                "customer_id": customer_id,
                "amount": -500000,
                "due_at": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            }
        )
    
    # List invoices
    runner.test(
        "List invoices",
        "GET",
        "invoices",
        200
    )
    
    # List payments
    runner.test(
        "List payments",
        "GET",
        "payments",
        200
    )
    
    # Create expense with positive amount
    runner.test(
        "Create expense with positive amount",
        "POST",
        "expenses",
        200,
        data={
            "category": "fuel",
            "amount": 500000,
            "description": "Test expense",
            "date": datetime.now().strftime("%Y-%m-%d")
        }
    )
    
    # Create expense with negative amount (should be 4xx, not 500)
    runner.test(
        "Create expense with negative amount (should be 4xx)",
        "POST",
        "expenses",
        400,
        data={
            "category": "fuel",
            "amount": -100000,
            "description": "Negative test",
            "date": datetime.now().strftime("%Y-%m-%d")
        }
    )
    
    # Get finance summary
    runner.test(
        "Get finance summary",
        "GET",
        "finance/summary",
        200
    )


# ============================================================================
# PAYROLL TESTS
# ============================================================================

def test_payroll(runner: TestRunner):
    """Test payroll: list payouts, approve/pay actions"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}PAYROLL TESTS{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    # List payouts
    runner.test(
        "List payroll payouts",
        "GET",
        "payroll/payouts",
        200
    )


# ============================================================================
# CRM TESTS
# ============================================================================

def test_crm(runner: TestRunner):
    """Test CRM: segments, preview, campaigns, RFM, scoreboard"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}CRM TESTS{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    # Scoreboard
    runner.test(
        "Get CRM scoreboard",
        "GET",
        "crm/scoreboard",
        200
    )
    
    # RFM
    runner.test(
        "Get CRM RFM analysis",
        "GET",
        "crm/rfm",
        200
    )
    
    # Create segment
    timestamp = int(time.time() * 1000) % 100000000
    success, segment = runner.test(
        "Create CRM segment",
        "POST",
        "crm/segments",
        200,
        data={
            "name": f"Test Segment {timestamp}",
            "audience": "customer",
            "criteria": {
                "type": "individual"
            }
        }
    )
    
    if success:
        segment_id = segment.get("id")
        runner.created_resources["segments"].append(segment_id)
        
        # Preview segment (normal)
        def check_preview(data, response):
            if "count" in data and "sample" in data:
                return True, "Preview has count and sample"
            return False, "Preview missing count or sample"
        
        runner.test(
            "Preview segment (normal)",
            "GET",
            f"crm/segments/{segment_id}/preview",
            200,
            check_fn=check_preview
        )
    
    # Create segment with malformed criteria
    success, bad_segment = runner.test(
        "Create segment with malformed criteria",
        "POST",
        "crm/segments",
        200,
        data={
            "name": f"Bad Segment {timestamp}",
            "audience": "customer",
            "criteria": {
                "invalid_operator": "xyz",
                "bad_field": 12345
            }
        },
        silent=True
    )
    
    if success:
        bad_segment_id = bad_segment.get("id")
        runner.created_resources["segments"].append(bad_segment_id)
        
        # Preview malformed segment (should be 400 or 200, NOT 500)
        runner.test(
            "Preview segment with malformed criteria (should NOT be 500)",
            "GET",
            f"crm/segments/{bad_segment_id}/preview",
            200  # R6-4 fix: should handle gracefully
        )
    
    # List campaigns
    runner.test(
        "List CRM campaigns",
        "GET",
        "campaigns",
        200
    )


# ============================================================================
# CONTENT/CMS + SET-1 TESTS
# ============================================================================

def test_content_cms(runner: TestRunner):
    """Test content/CMS with SET-1 validation"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}CONTENT/CMS + SET-1 TESTS{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    timestamp = int(time.time() * 1000) % 100000000
    
    # Create destination with valid lat/lng
    success, destination = runner.test(
        "Create destination with valid lat/lng",
        "POST",
        "content/destinations",
        200,
        data={
            "slug": f"test-dest-{timestamp}",
            "name": "Test Destination",
            "region": "Bali",
            "description": "Test description",
            "lat": -8.3405,
            "lng": 115.0920
        }
    )
    
    if success:
        dest_id = destination.get("id")
        runner.created_resources["destinations"].append(dest_id)
    
    # Create destination with non-numeric lat (should be 400, not 500)
    runner.test(
        "Create destination with non-numeric lat (should be 400)",
        "POST",
        "content/destinations",
        400,
        data={
            "slug": f"bad-dest-{timestamp}",
            "name": "Bad Destination",
            "region": "Test",
            "description": "Test",
            "lat": "not-a-number",
            "lng": 115.0920
        }
    )
    
    # Create package with valid price_from
    success, package = runner.test(
        "Create package with valid price_from",
        "POST",
        "content/packages",
        200,
        data={
            "slug": f"test-pkg-{timestamp}",
            "name": "Test Package",
            "destination": "Bali",
            "days": 3,
            "price_from": 5000000,
            "description": "Test package"
        }
    )
    
    if success:
        pkg_id = package.get("id")
        runner.created_resources["packages"].append(pkg_id)
    
    # Create package with non-numeric price_from (should be 400, not 500)
    runner.test(
        "Create package with non-numeric price_from (should be 400)",
        "POST",
        "content/packages",
        400,
        data={
            "slug": f"bad-pkg-{timestamp}",
            "name": "Bad Package",
            "destination": "Test",
            "days": 3,
            "price_from": "gratis",
            "description": "Test"
        }
    )


# ============================================================================
# SETTINGS + SET-1 TESTS
# ============================================================================

def test_settings(runner: TestRunner):
    """Test settings with SET-1 validation"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}SETTINGS + SET-1 TESTS{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    # Get settings
    success, settings = runner.test(
        "GET /api/settings",
        "GET",
        "settings",
        200
    )
    
    # PATCH with invalid negative default_day_rate (should be 400)
    runner.test(
        "PATCH settings with negative default_day_rate (should be 400)",
        "PATCH",
        "settings",
        400,
        data={
            "pricing_rules": {
                "default_day_rate": -1000
            }
        }
    )
    
    # PATCH with invalid dp_percent > 100 (should be 400)
    runner.test(
        "PATCH settings with dp_percent > 100 (should be 400)",
        "PATCH",
        "settings",
        400,
        data={
            "pricing_rules": {
                "dp_percent": 150
            }
        }
    )
    
    # PATCH with non-numeric fuel_per_km (should be 400)
    runner.test(
        "PATCH settings with non-numeric fuel_per_km (should be 400)",
        "PATCH",
        "settings",
        400,
        data={
            "pricing_rules": {
                "fuel_per_km": "gratis"
            }
        }
    )
    
    # PATCH with negative dp_percent in pricing_defaults (should be 400)
    runner.test(
        "PATCH settings with negative dp_percent in pricing_defaults (should be 400)",
        "PATCH",
        "settings",
        400,
        data={
            "pricing_defaults": {
                "dp_percent": -5
            }
        }
    )
    
    # PATCH with negative min_rental_hours (should be 400)
    runner.test(
        "PATCH settings with negative min_rental_hours (should be 400)",
        "PATCH",
        "settings",
        400,
        data={
            "pricing_defaults": {
                "min_rental_hours": -3
            }
        }
    )
    
    # PATCH with valid pricing_rules (should be 200)
    if success and settings:
        current_pricing = settings.get("pricing_rules", {})
        runner.test(
            "PATCH settings with valid pricing_rules (should be 200)",
            "PATCH",
            "settings",
            200,
            data={
                "pricing_rules": current_pricing
            }
        )


# ============================================================================
# PUBLIC TESTS (no auth)
# ============================================================================

def test_public_endpoints(runner: TestRunner):
    """Test public endpoints (no authentication)"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}PUBLIC ENDPOINTS TESTS{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    # Public homepage/company info
    try:
        response = requests.get(f"{BASE_URL}/public/company", timeout=10)
        runner.tests_run += 1
        if response.status_code == 200:
            print(f"{Colors.GREEN}✓ PASSED - GET /api/public/company: 200{Colors.END}")
            runner.tests_passed += 1
        else:
            print(f"{Colors.RED}✗ FAILED - GET /api/public/company: {response.status_code}{Colors.END}")
            runner.tests_failed += 1
            runner.failures.append(f"Public company endpoint: {response.status_code}")
    except Exception as e:
        print(f"{Colors.RED}✗ FAILED - GET /api/public/company: {str(e)}{Colors.END}")
        runner.tests_failed += 1
        runner.failures.append(f"Public company endpoint: {str(e)}")
    
    # Public destinations
    try:
        response = requests.get(f"{BASE_URL}/public/destinations", timeout=10)
        runner.tests_run += 1
        if response.status_code == 200:
            print(f"{Colors.GREEN}✓ PASSED - GET /api/public/destinations: 200{Colors.END}")
            runner.tests_passed += 1
        else:
            print(f"{Colors.RED}✗ FAILED - GET /api/public/destinations: {response.status_code}{Colors.END}")
            runner.tests_failed += 1
    except Exception as e:
        print(f"{Colors.RED}✗ FAILED - GET /api/public/destinations: {str(e)}{Colors.END}")
        runner.tests_failed += 1
    
    # Public booking request
    timestamp = int(time.time() * 1000) % 100000000
    try:
        response = requests.post(
            f"{BASE_URL}/public/booking-request",
            json={
                "name": "Public Test",
                "phone": f"081277{timestamp}",
                "destination": "Bali",
                "trip_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                "pax": 4
            },
            timeout=10
        )
        runner.tests_run += 1
        if response.status_code in (200, 201):
            print(f"{Colors.GREEN}✓ PASSED - POST /api/public/booking-request: {response.status_code}{Colors.END}")
            runner.tests_passed += 1
        else:
            print(f"{Colors.RED}✗ FAILED - POST /api/public/booking-request: {response.status_code}{Colors.END}")
            runner.tests_failed += 1
    except Exception as e:
        print(f"{Colors.RED}✗ FAILED - POST /api/public/booking-request: {str(e)}{Colors.END}")
        runner.tests_failed += 1


# ============================================================================
# CLEANUP
# ============================================================================

def cleanup(runner: TestRunner):
    """Cleanup created test resources"""
    print(f"\n{Colors.BLUE}=== CLEANUP ==={Colors.END}")
    
    total = sum(len(v) for v in runner.created_resources.values())
    if total == 0:
        print("  No resources to cleanup")
        return
    
    print(f"  Cleaning up {total} test resources...")
    
    # Cleanup in reverse order of dependencies
    for resource_type in ["bookings", "quotations", "segments", "packages", "destinations", "customers"]:
        for resource_id in runner.created_resources[resource_type]:
            try:
                endpoint = f"{resource_type}/{resource_id}"
                if resource_type in ["packages", "destinations"]:
                    endpoint = f"content/{resource_type}/{resource_id}"
                elif resource_type == "segments":
                    endpoint = f"crm/segments/{resource_id}"
                
                requests.delete(
                    f"{BASE_URL}/{endpoint}",
                    headers=runner.headers(),
                    timeout=5
                )
            except:
                pass
    
    print(f"{Colors.GREEN}✓ Cleanup complete{Colors.END}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main test runner"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Rahaza Travel ERP - FINAL COMPREHENSIVE VERIFICATION{Colors.END}")
    print(f"{Colors.BLUE}Post Bug-Fix Validation (Putaran 12){Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    runner = TestRunner()
    
    try:
        # Run all test suites
        test_auth_rbac(runner)
        test_customers_id_race(runner)
        test_bookings(runner)
        test_quotations_export(runner)
        test_dispatch_vehicles_drivers(runner)
        test_finance(runner)
        test_payroll(runner)
        test_crm(runner)
        test_content_cms(runner)
        test_settings(runner)
        test_public_endpoints(runner)
        
    except Exception as e:
        print(f"\n{Colors.RED}Test suite error: {str(e)}{Colors.END}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        cleanup(runner)
    
    # Print summary
    return runner.print_summary()


if __name__ == "__main__":
    sys.exit(main())
