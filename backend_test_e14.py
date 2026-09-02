#!/usr/bin/env python3
"""
Backend Test Suite for E14 Verification + Regression
====================================================
Tests E14-B1 (SIM reminder notifications) + RBAC + critical endpoint regression
"""
import requests
import sys
import json
from datetime import datetime

class E14TestSuite:
    def __init__(self, base_url="https://trip-route-buttons.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        
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
                if token and token.startswith("sess_"):
                    self.tokens[email] = token
                    user = data.get("user", {})
                    self.log(f"Login successful: {email} (role: {user.get('role')})", "pass")
                    return True, data
                else:
                    self.log(f"Login failed for {email}: token format incorrect", "fail")
                    return False, None
            self.log(f"Login failed for {email}: {response.status_code} - {response.text[:200]}", "fail")
            return False, None
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
    
    def test_auth(self):
        """Test authentication for all 3 roles"""
        self.log("\n=== Testing Authentication (3 Roles) ===", "info")
        
        # Login all users
        owner_ok, owner_data = self.login("owner@demo.local", "demo12345")
        ops_ok, ops_data = self.login("ops@demo.local", "demo12345")
        driver_ok, driver_data = self.login("driver@demo.local", "demo12345")
        
        # Verify token format
        self.test("Owner login returns token with sess_ prefix", 
                  owner_ok and owner_data and owner_data.get("token", "").startswith("sess_"),
                  f"Token: {owner_data.get('token', '')[:20] if owner_data else 'None'}...")
        
        self.test("Ops Admin login returns token with sess_ prefix", 
                  ops_ok and ops_data and ops_data.get("token", "").startswith("sess_"),
                  f"Token: {ops_data.get('token', '')[:20] if ops_data else 'None'}...")
        
        self.test("Driver login returns token with sess_ prefix", 
                  driver_ok and driver_data and driver_data.get("token", "").startswith("sess_"),
                  f"Token: {driver_data.get('token', '')[:20] if driver_data else 'None'}...")
        
        # Verify user object returned
        self.test("Owner login returns user object",
                  owner_ok and owner_data and "user" in owner_data,
                  "user object missing")
        
        self.test("Ops Admin login returns user object",
                  ops_ok and ops_data and "user" in ops_data,
                  "user object missing")
        
        self.test("Driver login returns user object",
                  driver_ok and driver_data and "user" in driver_data,
                  "user object missing")
        
        return owner_ok and ops_ok and driver_ok
    
    def test_e14_b1_notifications(self):
        """Test E14-B1: SIM reminder notifications"""
        self.log("\n=== Testing E14-B1: SIM Reminder Notifications ===", "info")
        
        # Step 1: Trigger notification scan as owner
        try:
            url = f"{self.base_url}/api/notifications/scan"
            response = requests.post(url, headers=self.headers("owner@demo.local"), timeout=15)
            
            self.test(
                "POST /api/notifications/scan as owner returns 200",
                response.status_code == 200,
                f"Got {response.status_code}: {response.text[:200]}"
            )
            
            if response.status_code == 200:
                scan_result = response.json()
                self.log(f"Scan created {scan_result.get('created', 0)} notifications", "info")
        except Exception as e:
            self.test("POST /api/notifications/scan", False, str(e))
        
        # Step 2: Get notifications as owner
        try:
            url = f"{self.base_url}/api/notifications"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/notifications as owner returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                notifications = response.json()
                self.log(f"Found {len(notifications)} total notifications", "info")
                
                # Find sim_reminder notifications
                sim_reminders = [n for n in notifications if n.get("type") == "sim_reminder"]
                
                self.test(
                    "Notifications include sim_reminder type",
                    len(sim_reminders) > 0,
                    f"Found {len(sim_reminders)} sim_reminder notifications"
                )
                
                if sim_reminders:
                    # Check first sim_reminder structure
                    sim = sim_reminders[0]
                    self.log(f"SIM reminder: {sim.get('title')}", "info")
                    
                    self.test(
                        "sim_reminder has title field",
                        "title" in sim and sim.get("title"),
                        f"Title: {sim.get('title', 'missing')}"
                    )
                    
                    self.test(
                        "sim_reminder has body field",
                        "body" in sim and sim.get("body"),
                        f"Body: {sim.get('body', 'missing')[:50]}"
                    )
                    
                    self.test(
                        "sim_reminder target_role is 'manager'",
                        sim.get("target_role") == "manager",
                        f"Got target_role: {sim.get('target_role')}"
                    )
                    
                    self.test(
                        "sim_reminder ref_type is 'driver'",
                        sim.get("ref_type") == "driver",
                        f"Got ref_type: {sim.get('ref_type')}"
                    )
        except Exception as e:
            self.test("GET /api/notifications", False, str(e))
        
        # Step 3: Check unread count
        try:
            url = f"{self.base_url}/api/notifications/unread_count"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/notifications/unread_count returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                count_data = response.json()
                unread_count = count_data.get("count", 0)
                self.log(f"Unread count: {unread_count}", "info")
                
                self.test(
                    "Unread count is a number",
                    isinstance(unread_count, int),
                    f"Got type: {type(unread_count)}"
                )
        except Exception as e:
            self.test("GET /api/notifications/unread_count", False, str(e))
        
        # Step 4: Test as ops_admin (should also see manager notifications)
        try:
            url = f"{self.base_url}/api/notifications"
            response = requests.get(url, headers=self.headers("ops@demo.local"), timeout=10)
            
            self.test(
                "GET /api/notifications as ops_admin returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                ops_notifications = response.json()
                ops_sim_reminders = [n for n in ops_notifications if n.get("type") == "sim_reminder"]
                
                self.test(
                    "Ops admin can see sim_reminder notifications (target_role=manager)",
                    len(ops_sim_reminders) > 0,
                    f"Found {len(ops_sim_reminders)} sim_reminder notifications"
                )
        except Exception as e:
            self.test("GET /api/notifications as ops_admin", False, str(e))
    
    def test_regression_endpoints(self):
        """Test regression: critical endpoints return data (not just 200)"""
        self.log("\n=== Testing Regression: Critical Endpoints ===", "info")
        
        critical_endpoints = [
            ("/api/vehicles", "vehicles"),
            ("/api/drivers", "drivers"),
            ("/api/customers", "customers"),
            ("/api/bookings", "bookings"),
            ("/api/dashboard", "dashboard"),
            ("/api/leads/pipeline", "leads pipeline"),
            ("/api/reports/summary", "reports summary"),
            ("/api/finance/pl-full", "P&L full"),
            ("/api/payroll/summary", "payroll summary"),
            ("/api/dispatch/today", "dispatch today"),
        ]
        
        for endpoint, name in critical_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                
                # Check no 5xx errors
                self.test(
                    f"GET {endpoint} returns non-5xx status",
                    response.status_code < 500,
                    f"Got {response.status_code}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check data is not empty
                    has_data = False
                    if isinstance(data, list):
                        has_data = len(data) > 0
                    elif isinstance(data, dict):
                        has_data = len(data) > 0
                    
                    self.test(
                        f"GET {endpoint} returns data (not empty)",
                        has_data,
                        f"Got {type(data).__name__} with {len(data) if isinstance(data, (list, dict)) else 0} items/keys"
                    )
                    
                    self.log(f"  {name}: {len(data) if isinstance(data, (list, dict)) else 'N/A'} items/keys", "info")
            except Exception as e:
                self.test(f"GET {endpoint}", False, str(e))
    
    def test_rbac_driver(self):
        """Test RBAC: driver gets 403 on manager-only endpoints"""
        self.log("\n=== Testing RBAC: Driver Access Control ===", "info")
        
        manager_only_endpoints = [
            ("/api/finance/pl-full", "GET"),
            ("/api/reports/summary", "GET"),
            ("/api/customers", "GET"),
            ("/api/customers", "POST"),
            ("/api/settings", "GET"),
            ("/api/users", "GET"),
            ("/api/leads/pipeline", "GET"),
            ("/api/dispatch/today", "GET"),
            ("/api/payroll/summary", "GET"),
        ]
        
        for endpoint, method in manager_only_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                
                if method == "GET":
                    response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
                elif method == "POST":
                    response = requests.post(url, json={"test": "data"}, headers=self.headers("driver@demo.local"), timeout=10)
                
                self.test(
                    f"Driver {method} {endpoint} returns 403",
                    response.status_code == 403,
                    f"Expected 403, got {response.status_code}"
                )
            except Exception as e:
                self.test(f"Driver {method} {endpoint}", False, str(e))
        
        # Test driver CAN access allowed endpoints
        driver_allowed_endpoints = [
            "/api/dashboard",
            "/api/bookings",
            "/api/vehicles",
            "/api/drivers",
        ]
        
        for endpoint in driver_allowed_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
                
                self.test(
                    f"Driver GET {endpoint} returns 200 (allowed)",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
            except Exception as e:
                self.test(f"Driver GET {endpoint}", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*70, "info")
        self.log("E14 Verification + Regression Backend Test Suite", "info")
        self.log("="*70, "info")
        
        # Run tests in order
        if not self.test_auth():
            self.log("\n⚠️  Authentication failed. Cannot proceed with other tests.", "warn")
            return False
        
        # E14-B1: SIM reminder notifications
        self.test_e14_b1_notifications()
        
        # Regression: critical endpoints
        self.test_regression_endpoints()
        
        # RBAC: driver access control
        self.test_rbac_driver()
        
        # Print summary
        self.log("\n" + "="*70, "info")
        self.log("TEST SUMMARY", "info")
        self.log("="*70, "info")
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
    tester = E14TestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
