"""
Backend Testing for RONDE 2 - Rahaza Travel ERP
Focus: BUG-0119 RBAC fixes + booking flow verification
Tests all priority scenarios from review request.
"""
import requests
import sys
from datetime import datetime, timedelta

# Use public endpoint
BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

# Test dates: >= 20 days from now (seed data full Aug 10-17, 2026)
TODAY = datetime.utcnow()
START_DATE = (TODAY + timedelta(days=22)).strftime("%Y-%m-%dT10:00:00Z")
END_DATE = (TODAY + timedelta(days=24)).strftime("%Y-%m-%dT10:00:00Z")

class TestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.tokens = {}
        self.errors = []

    def log(self, msg: str, level: str = "INFO"):
        prefix = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(level, "•")
        print(f"{prefix} {msg}")

    def test(self, name: str, condition: bool, error_msg: str = ""):
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            self.log(f"{name}: PASS", "PASS")
            return True
        else:
            self.tests_failed += 1
            self.log(f"{name}: FAIL - {error_msg}", "FAIL")
            self.errors.append(f"{name}: {error_msg}")
            return False

    def login(self, email: str, password: str):
        """Login and store token"""
        try:
            resp = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password}, timeout=10)
            if resp.status_code == 200:
                token = resp.json().get("token")
                if token:
                    self.tokens[email] = token
                    self.log(f"Login successful: {email}", "PASS")
                    return True
            self.log(f"Login failed: {email} - {resp.status_code}", "FAIL")
            return False
        except Exception as e:
            self.log(f"Login exception: {email} - {e}", "FAIL")
            return False

    def get(self, endpoint: str, email: str = None, params: dict = None):
        """GET request with optional auth"""
        headers = {}
        if email and email in self.tokens:
            headers["Authorization"] = f"Bearer {self.tokens[email]}"
        return requests.get(f"{BASE_URL}/{endpoint}", headers=headers, params=params, timeout=10)

    def post(self, endpoint: str, email: str = None, data: dict = None):
        """POST request with optional auth"""
        headers = {}
        if email and email in self.tokens:
            headers["Authorization"] = f"Bearer {self.tokens[email]}"
        return requests.post(f"{BASE_URL}/{endpoint}", headers=headers, json=data, timeout=10)

    def test_priority2_rbac_marketing_blocked(self):
        """PRIORITY 2: Verify BUG-0119 fix - marketing_admin should get 403 on 8 endpoints"""
        self.log("\n=== PRIORITY 2: RBAC - Marketing Admin BLOCKED Endpoints ===", "INFO")
        
        marketing = "marketing@demo.local"
        if marketing not in self.tokens:
            self.log("Marketing not logged in, skipping", "WARN")
            return
        
        # List of endpoints that should be 403 for marketing_admin
        blocked_endpoints = [
            ("GET", "bookings", "Bookings list"),
            ("GET", "bookings/availability", "Bookings availability"),
            ("GET", "vehicles", "Vehicles list"),
            ("GET", "drivers", "Drivers list"),
            ("GET", "maintenance", "Maintenance list"),
            ("GET", "gps/live", "GPS live"),
            ("GET", "quotations", "Quotations list"),
            ("GET", "driver/my-trips", "Driver my-trips"),
            ("GET", "driver/tasks", "Driver tasks"),
            ("GET", "driver/summary", "Driver summary"),
        ]
        
        for method, endpoint, desc in blocked_endpoints:
            resp = self.get(endpoint, email=marketing)
            self.test(f"Marketing 403 on {desc}", resp.status_code == 403,
                     f"Expected 403, got {resp.status_code} for {endpoint}")

    def test_priority2_rbac_owner_ops_allowed(self):
        """PRIORITY 2: Verify owner & ops_admin still have access (no over-block)"""
        self.log("\n=== PRIORITY 2: RBAC - Owner & Ops Admin ALLOWED ===", "INFO")
        
        owner = "owner@demo.local"
        ops = "ops@demo.local"
        
        if owner not in self.tokens or ops not in self.tokens:
            self.log("Owner or ops not logged in, skipping", "WARN")
            return
        
        # Endpoints that owner & ops should access
        allowed_endpoints = [
            ("bookings", "Bookings"),
            ("bookings/availability", "Availability"),
            ("vehicles", "Vehicles"),
            ("drivers", "Drivers"),
            ("maintenance", "Maintenance"),
            ("gps/live", "GPS"),
        ]
        
        for endpoint, desc in allowed_endpoints:
            # Test owner
            resp = self.get(endpoint, email=owner)
            self.test(f"Owner 200 on {desc}", resp.status_code == 200,
                     f"Expected 200, got {resp.status_code} for {endpoint}")
            
            # Test ops
            resp = self.get(endpoint, email=ops)
            self.test(f"Ops 200 on {desc}", resp.status_code == 200,
                     f"Expected 200, got {resp.status_code} for {endpoint}")

    def test_priority2_rbac_driver_allowed(self):
        """PRIORITY 2: Verify driver still has access to allowed endpoints"""
        self.log("\n=== PRIORITY 2: RBAC - Driver ALLOWED Endpoints ===", "INFO")
        
        driver = "driver@demo.local"
        if driver not in self.tokens:
            self.log("Driver not logged in, skipping", "WARN")
            return
        
        # Driver should have access to these
        allowed_endpoints = [
            ("vehicles", "Vehicles"),
            ("maintenance", "Maintenance"),
            ("gps/live", "GPS"),
            ("bookings", "Bookings (scoped)"),
            ("driver/my-trips", "My trips"),
            ("driver/tasks", "Tasks"),
            ("driver/summary", "Summary"),
        ]
        
        for endpoint, desc in allowed_endpoints:
            resp = self.get(endpoint, email=driver)
            self.test(f"Driver 200 on {desc}", resp.status_code == 200,
                     f"Expected 200, got {resp.status_code} for {endpoint}")

    def test_priority2_rbac_marketing_allowed(self):
        """PRIORITY 2: Verify marketing_admin can access their own endpoints"""
        self.log("\n=== PRIORITY 2: RBAC - Marketing Admin ALLOWED Endpoints ===", "INFO")
        
        marketing = "marketing@demo.local"
        if marketing not in self.tokens:
            self.log("Marketing not logged in, skipping", "WARN")
            return
        
        # Marketing should have access to these
        allowed_endpoints = [
            ("leads", "Leads"),
            ("customers", "Customers"),
            ("media", "Media"),
            ("landing/pages", "Landing pages"),
            ("ads/overview", "Ads overview"),
            ("content/destinations", "Content destinations"),
            ("dashboard", "Dashboard"),
        ]
        
        for endpoint, desc in allowed_endpoints:
            resp = self.get(endpoint, email=marketing)
            self.test(f"Marketing 200 on {desc}", resp.status_code == 200,
                     f"Expected 200, got {resp.status_code} for {endpoint}")

    def test_priority1_booking_config(self):
        """PRIORITY 1: Verify /api/public/booking/config works"""
        self.log("\n=== PRIORITY 1: Booking Config ===", "INFO")
        
        resp = self.get("public/booking/config")
        self.test("Config returns 200", resp.status_code == 200,
                 f"Got {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            self.test("Config has services", "services" in data and len(data["services"]) > 0,
                     "No services")
            self.test("Config has vehicle_types", "vehicle_types" in data,
                     "No vehicle_types")
            self.test("Config has dp_percent", "dp_percent" in data,
                     "No dp_percent")
            return data
        return {}

    def test_priority1_booking_search(self):
        """PRIORITY 1: Verify booking search works"""
        self.log("\n=== PRIORITY 1: Booking Search ===", "INFO")
        
        resp = self.post("public/booking/search", data={
            "service": "daily_rental",
            "start_datetime": START_DATE,
            "end_datetime": END_DATE,
            "pax": 4
        })
        
        self.test("Search returns 200", resp.status_code == 200,
                 f"Got {resp.status_code}: {resp.text[:200]}")
        
        if resp.status_code == 200:
            data = resp.json()
            options = data.get("options", [])
            self.test("Search has options", len(options) > 0,
                     f"Found {len(options)} vehicles")
            
            if options:
                vehicle = options[0]["vehicle"]
                self.log(f"Found vehicle: {vehicle.get('name')}")
                return vehicle
        return None

    def test_batas_teks(self):
        """REGRESI: BUG-0114 - Test text length limits"""
        self.log("\n=== REGRESI: Text Length Limits (BUG-0114) ===", "INFO")
        
        owner = "owner@demo.local"
        if owner not in self.tokens:
            self.log("Owner not logged in, skipping", "WARN")
            return
        
        # Test 1: 60,000 character name should be rejected
        long_name = "A" * 60000
        resp = self.post("customers", email=owner, data={
            "name": long_name,
            "phone": "081234567890",
            "source": "website"
        })
        self.test("60k char name rejected", resp.status_code == 422,
                 f"Expected 422, got {resp.status_code}")
        
        # Test 2: Normal name should work
        resp = self.post("customers", email=owner, data={
            "name": "Normal Customer Name",
            "phone": f"0812{datetime.utcnow().strftime('%H%M%S')}",
            "source": "website"
        })
        self.test("Normal name accepted", resp.status_code == 200,
                 f"Expected 200, got {resp.status_code}")

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60, "INFO")
        self.log(f"TESTS RUN: {self.tests_run}", "INFO")
        self.log(f"PASSED: {self.tests_passed}", "PASS")
        self.log(f"FAILED: {self.tests_failed}", "FAIL" if self.tests_failed > 0 else "INFO")
        
        if self.errors:
            self.log("\nFailed Tests:", "FAIL")
            for error in self.errors:
                self.log(f"  - {error}", "FAIL")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"\nSUCCESS RATE: {success_rate:.1f}%", "INFO")
        self.log("="*60, "INFO")
        
        return 0 if self.tests_failed == 0 else 1

def main():
    runner = TestRunner()
    
    # Login all users
    runner.log("=== LOGGING IN USERS ===", "INFO")
    runner.login("owner@demo.local", "demo12345")
    runner.login("ops@demo.local", "demo12345")
    runner.login("marketing@demo.local", "demo12345")
    runner.login("driver@demo.local", "demo12345")
    
    # PRIORITY 2: RBAC tests (BUG-0119 verification)
    runner.test_priority2_rbac_marketing_blocked()
    runner.test_priority2_rbac_owner_ops_allowed()
    runner.test_priority2_rbac_driver_allowed()
    runner.test_priority2_rbac_marketing_allowed()
    
    # PRIORITY 1: Basic booking flow
    runner.test_priority1_booking_config()
    runner.test_priority1_booking_search()
    
    # REGRESSION: Text limits
    runner.test_batas_teks()
    
    return runner.print_summary()

if __name__ == "__main__":
    sys.exit(main())
