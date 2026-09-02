#!/usr/bin/env python3
"""
Backend Test Suite for E12 Payroll Enhancements
================================================
Tests:
1. Rekap Payroll API (GET /api/reports/payroll)
2. Export Rekap Payroll (GET /api/reports/payroll/export?format=excel|pdf)
3. Generate Payout MASSAL (POST /api/payroll/payouts/generate-bulk)
4. Otomasi/pengingat Payroll (POST /api/notifications/scan, GET /api/automation/*)
5. RBAC E12 (driver should get 403 on reports/payroll & generate-bulk)
6. Regresi (GET /api/reports/summary should include payroll key)
"""
import requests
import sys
from datetime import datetime

class E12TestSuite:
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
                if token:
                    self.tokens[email] = token
                    self.log(f"Login successful: {email}", "pass")
                    return True
            self.log(f"Login failed for {email}: {response.status_code}", "fail")
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
        
        owner_ok = self.login("owner@demo.local", "demo12345")
        driver_ok = self.login("driver@demo.local", "demo12345")
        
        self.test("Owner login", owner_ok)
        self.test("Driver login", driver_ok)
        
        return owner_ok and driver_ok
    
    def test_rekap_payroll_api(self):
        """Test GET /api/reports/payroll"""
        self.log("\n=== Testing Rekap Payroll API ===", "info")
        
        # Test owner can access
        try:
            url = f"{self.base_url}/api/reports/payroll"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/reports/payroll (owner) returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ["period", "count", "by_status", "total_gross", "total_bonus", 
                                 "total_deduction", "total_net", "per_driver", "sdm_vs_revenue"]
                for field in required_fields:
                    self.test(
                        f"Payroll report has '{field}' field",
                        field in data,
                        f"Missing field: {field}"
                    )
                
                # Check by_status structure
                if "by_status" in data:
                    by_status = data["by_status"]
                    self.test(
                        "by_status has draft/approved/paid keys",
                        "draft" in by_status and "approved" in by_status and "paid" in by_status,
                        f"Missing status keys in by_status"
                    )
                
                # Check sdm_vs_revenue structure
                if "sdm_vs_revenue" in data:
                    svr = data["sdm_vs_revenue"]
                    self.test(
                        "sdm_vs_revenue has payroll_cost/revenue/ratio_pct",
                        "payroll_cost" in svr and "revenue" in svr and "ratio_pct" in svr,
                        f"Missing keys in sdm_vs_revenue"
                    )
                
                # Check per_driver structure
                if "per_driver" in data and len(data["per_driver"]) > 0:
                    driver_row = data["per_driver"][0]
                    driver_fields = ["driver_id", "driver_name", "trips", "km", "gross", 
                                   "bonus", "deduction", "total", "ytd", "statuses"]
                    for field in driver_fields:
                        self.test(
                            f"per_driver row has '{field}' field",
                            field in driver_row,
                            f"Missing field: {field}"
                        )
                
                self.payroll_data = data
        except Exception as e:
            self.test("GET /api/reports/payroll (owner)", False, str(e))
    
    def test_export_payroll(self):
        """Test GET /api/reports/payroll/export"""
        self.log("\n=== Testing Export Rekap Payroll ===", "info")
        
        # Test Excel export
        try:
            url = f"{self.base_url}/api/reports/payroll/export?format=excel"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/reports/payroll/export?format=excel returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "")
                self.test(
                    "Excel export has correct content-type",
                    "spreadsheetml" in content_type or "excel" in content_type,
                    f"Got content-type: {content_type}"
                )
                
                self.test(
                    "Excel export has content",
                    len(response.content) > 0,
                    f"Empty response"
                )
        except Exception as e:
            self.test("GET /api/reports/payroll/export?format=excel", False, str(e))
        
        # Test PDF export
        try:
            url = f"{self.base_url}/api/reports/payroll/export?format=pdf"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/reports/payroll/export?format=pdf returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "")
                self.test(
                    "PDF export has correct content-type",
                    "pdf" in content_type,
                    f"Got content-type: {content_type}"
                )
                
                self.test(
                    "PDF export has content",
                    len(response.content) > 0,
                    f"Empty response"
                )
        except Exception as e:
            self.test("GET /api/reports/payroll/export?format=pdf", False, str(e))
    
    def test_generate_bulk(self):
        """Test POST /api/payroll/payouts/generate-bulk"""
        self.log("\n=== Testing Generate Payout MASSAL ===", "info")
        
        # Use a unique past period to avoid conflicts
        unique_period = {
            "period_type": "monthly",
            "period_start": "2015-08-01",
            "period_end": "2015-08-31"
        }
        
        try:
            url = f"{self.base_url}/api/payroll/payouts/generate-bulk"
            response = requests.post(url, json=unique_period, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/payroll/payouts/generate-bulk returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["created", "skipped", "created_count", "skipped_count"]
                for field in required_fields:
                    self.test(
                        f"Bulk generate response has '{field}' field",
                        field in data,
                        f"Missing field: {field}"
                    )
                
                created_count = data.get("created_count", 0)
                skipped_count = data.get("skipped_count", 0)
                
                self.log(f"Bulk generate: {created_count} created, {skipped_count} skipped", "info")
                
                # Test duplicate prevention: run again with same period
                response2 = requests.post(url, json=unique_period, headers=self.headers("owner@demo.local"), timeout=10)
                
                if response2.status_code == 200:
                    data2 = response2.json()
                    new_created = data2.get("created_count", 0)
                    new_skipped = data2.get("skipped_count", 0)
                    
                    self.test(
                        "Duplicate bulk generate skips all payouts",
                        new_created == 0 and new_skipped > 0,
                        f"Expected 0 created, got {new_created} created and {new_skipped} skipped"
                    )
                    
                    self.log(f"Duplicate prevention: {new_created} created, {new_skipped} skipped", "info")
        except Exception as e:
            self.test("POST /api/payroll/payouts/generate-bulk", False, str(e))
    
    def test_payroll_automation(self):
        """Test payroll automation and notifications"""
        self.log("\n=== Testing Payroll Automation & Notifications ===", "info")
        
        # Test notifications scan
        try:
            url = f"{self.base_url}/api/notifications/scan"
            response = requests.post(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/notifications/scan returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test(
                    "Notifications scan returns created count",
                    "created" in data,
                    f"Missing 'created' field"
                )
        except Exception as e:
            self.test("POST /api/notifications/scan", False, str(e))
        
        # Test GET /api/notifications for payroll_reminder
        try:
            url = f"{self.base_url}/api/notifications"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/notifications returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                notifications = response.json()
                payroll_notifs = [n for n in notifications if n.get("type") == "payroll_reminder" or n.get("ref_type") == "payroll"]
                
                self.test(
                    "Notifications include payroll_reminder type",
                    len(payroll_notifs) > 0,
                    f"No payroll notifications found"
                )
                
                if len(payroll_notifs) > 0:
                    self.log(f"Found {len(payroll_notifs)} payroll notifications", "info")
        except Exception as e:
            self.test("GET /api/notifications", False, str(e))
        
        # Test GET /api/automation/event-types
        try:
            url = f"{self.base_url}/api/automation/event-types"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/automation/event-types returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                event_keys = [e.get("key") for e in events]
                
                self.test(
                    "Event types include 'payroll.period_due'",
                    "payroll.period_due" in event_keys,
                    f"Missing payroll.period_due"
                )
                
                self.test(
                    "Event types include 'payroll.payout_pending'",
                    "payroll.payout_pending" in event_keys,
                    f"Missing payroll.payout_pending"
                )
        except Exception as e:
            self.test("GET /api/automation/event-types", False, str(e))
        
        # Test GET /api/automation/events
        try:
            url = f"{self.base_url}/api/automation/events"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/automation/events returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                events = response.json()
                payroll_events = [e for e in events if e.get("type", "").startswith("payroll.")]
                
                self.test(
                    "Events include payroll.* events",
                    len(payroll_events) > 0,
                    f"No payroll events found"
                )
                
                if len(payroll_events) > 0:
                    self.log(f"Found {len(payroll_events)} payroll events", "info")
        except Exception as e:
            self.test("GET /api/automation/events", False, str(e))
    
    def test_rbac_e12(self):
        """Test RBAC for E12 endpoints"""
        self.log("\n=== Testing RBAC E12 ===", "info")
        
        # Driver should get 403 on GET /api/reports/payroll
        try:
            url = f"{self.base_url}/api/reports/payroll"
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "Driver GET /api/reports/payroll returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("Driver GET /api/reports/payroll", False, str(e))
        
        # Driver should get 403 on POST /api/payroll/payouts/generate-bulk
        try:
            url = f"{self.base_url}/api/payroll/payouts/generate-bulk"
            bulk_data = {
                "period_type": "monthly",
                "period_start": "2015-09-01",
                "period_end": "2015-09-30"
            }
            response = requests.post(url, json=bulk_data, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "Driver POST /api/payroll/payouts/generate-bulk returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("Driver POST /api/payroll/payouts/generate-bulk", False, str(e))
    
    def test_regression(self):
        """Test regression: GET /api/reports/summary should include payroll key"""
        self.log("\n=== Testing Regression ===", "info")
        
        try:
            url = f"{self.base_url}/api/reports/summary"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/reports/summary returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                self.test(
                    "Reports summary includes 'payroll' key",
                    "payroll" in data,
                    f"Missing 'payroll' key in summary"
                )
                
                if "payroll" in data:
                    payroll = data["payroll"]
                    self.test(
                        "Payroll in summary has required fields",
                        "period" in payroll and "total_net" in payroll,
                        f"Missing fields in payroll summary"
                    )
        except Exception as e:
            self.test("GET /api/reports/summary", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*60, "info")
        self.log("E12 Payroll Enhancements Backend Test Suite", "info")
        self.log("="*60, "info")
        
        if not self.test_auth():
            self.log("\n⚠️  Authentication failed. Cannot proceed with other tests.", "warn")
            return False
        
        # Run E12 tests
        self.test_rekap_payroll_api()
        self.test_export_payroll()
        self.test_generate_bulk()
        self.test_payroll_automation()
        self.test_rbac_e12()
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
        self.log(f"\nSuccess Rate: {success_rate:.1f}%", "pass" if success_rate == 100 else "warn")
        
        return self.tests_failed == 0


def main():
    tester = E12TestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
