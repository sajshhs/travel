#!/usr/bin/env python3
"""
E5 Finance Automation Backend Test Suite
=========================================
Tests all E5 finance endpoints: pl-full, reconciliation, cashflow, AR reminders, export
"""
import requests
import sys
import json
from datetime import datetime

class E5FinanceTestSuite:
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
        ops_ok = self.login("ops@demo.local", "demo12345")
        driver_ok = self.login("driver@demo.local", "demo12345")
        
        self.test("Owner login", owner_ok)
        self.test("Ops Admin login", ops_ok)
        self.test("Driver login", driver_ok)
        
        return owner_ok and ops_ok and driver_ok
    
    def test_finance_summary(self):
        """Test GET /api/finance/summary"""
        self.log("\n=== Testing Finance Summary ===", "info")
        
        try:
            url = f"{self.base_url}/api/finance/summary"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/finance/summary returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["revenue", "expenses", "profit", "outstanding_ar"]
                for field in required_fields:
                    self.test(
                        f"Summary contains {field}",
                        field in data,
                        f"{field} missing"
                    )
        except Exception as e:
            self.test("GET /api/finance/summary", False, str(e))
    
    def test_pl_full(self):
        """Test GET /api/finance/pl-full (E5 comprehensive P&L)"""
        self.log("\n=== Testing P&L Full (E5) ===", "info")
        
        try:
            url = f"{self.base_url}/api/finance/pl-full"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/finance/pl-full returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ["revenue", "operational_expenses", "maintenance_cost", 
                                 "total_cost", "profit", "margin", "per_unit", "expense_by_category"]
                for field in required_fields:
                    self.test(
                        f"P&L Full contains {field}",
                        field in data,
                        f"{field} missing"
                    )
                
                # Check per_unit is array
                self.test(
                    "P&L per_unit is array",
                    isinstance(data.get("per_unit"), list),
                    f"per_unit should be array"
                )
                
                # Check expense_by_category is array
                self.test(
                    "P&L expense_by_category is array",
                    isinstance(data.get("expense_by_category"), list),
                    f"expense_by_category should be array"
                )
                
                # Verify maintenance_cost is included in total_cost
                if "maintenance_cost" in data and "operational_expenses" in data and "total_cost" in data:
                    expected_total = data["operational_expenses"] + data["maintenance_cost"]
                    actual_total = data["total_cost"]
                    self.test(
                        "total_cost = operational_expenses + maintenance_cost",
                        abs(expected_total - actual_total) < 0.01,
                        f"Expected {expected_total}, got {actual_total}"
                    )
        except Exception as e:
            self.test("GET /api/finance/pl-full", False, str(e))
    
    def test_reconciliation(self):
        """Test GET /api/finance/reconciliation (E5)"""
        self.log("\n=== Testing Reconciliation (E5) ===", "info")
        
        try:
            url = f"{self.base_url}/api/finance/reconciliation"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/finance/reconciliation returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check structure
                self.test(
                    "Reconciliation contains items",
                    "items" in data,
                    "items missing"
                )
                
                self.test(
                    "Reconciliation contains summary",
                    "summary" in data,
                    "summary missing"
                )
                
                # Check summary fields
                if "summary" in data:
                    summary = data["summary"]
                    summary_fields = ["lunas", "sebagian", "belum", "lebih", "total_invoiced", "total_paid"]
                    for field in summary_fields:
                        self.test(
                            f"Reconciliation summary contains {field}",
                            field in summary,
                            f"{field} missing"
                        )
        except Exception as e:
            self.test("GET /api/finance/reconciliation", False, str(e))
    
    def test_reconciliation_sync(self):
        """Test POST /api/finance/reconciliation/sync (E5)"""
        self.log("\n=== Testing Reconciliation Sync (E5) ===", "info")
        
        try:
            url = f"{self.base_url}/api/finance/reconciliation/sync"
            response = requests.post(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/finance/reconciliation/sync returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test(
                    "Sync response contains updated_count",
                    "updated_count" in data,
                    "updated_count missing"
                )
                
                # Test idempotency - second call should return 0 updates
                response2 = requests.post(url, headers=self.headers("owner@demo.local"), timeout=10)
                if response2.status_code == 200:
                    data2 = response2.json()
                    self.test(
                        "Sync is idempotent (second call returns 0 updates)",
                        data2.get("updated_count") == 0,
                        f"Expected 0, got {data2.get('updated_count')}"
                    )
        except Exception as e:
            self.test("POST /api/finance/reconciliation/sync", False, str(e))
    
    def test_cashflow(self):
        """Test GET /api/finance/cashflow (E5)"""
        self.log("\n=== Testing Cashflow (E5) ===", "info")
        
        try:
            url = f"{self.base_url}/api/finance/cashflow?months=6&horizon=3"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/finance/cashflow returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check structure
                required_fields = ["months", "projection", "ending_balance"]
                for field in required_fields:
                    self.test(
                        f"Cashflow contains {field}",
                        field in data,
                        f"{field} missing"
                    )
                
                # Check months is array
                self.test(
                    "Cashflow months is array",
                    isinstance(data.get("months"), list),
                    "months should be array"
                )
                
                # Check projection is array
                self.test(
                    "Cashflow projection is array",
                    isinstance(data.get("projection"), list),
                    "projection should be array"
                )
                
                # Verify each month has required fields
                if data.get("months"):
                    month = data["months"][0]
                    month_fields = ["month", "cash_in", "cash_out", "net", "balance"]
                    for field in month_fields:
                        self.test(
                            f"Cashflow month contains {field}",
                            field in month,
                            f"{field} missing from month"
                        )
        except Exception as e:
            self.test("GET /api/finance/cashflow", False, str(e))
    
    def test_ar(self):
        """Test GET /api/finance/ar"""
        self.log("\n=== Testing Accounts Receivable ===", "info")
        
        try:
            url = f"{self.base_url}/api/finance/ar"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/finance/ar returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check structure
                self.test(
                    "AR contains items",
                    "items" in data,
                    "items missing"
                )
                
                self.test(
                    "AR contains count",
                    "count" in data,
                    "count missing"
                )
                
                self.test(
                    "AR contains total_outstanding",
                    "total_outstanding" in data,
                    "total_outstanding missing"
                )
        except Exception as e:
            self.test("GET /api/finance/ar", False, str(e))
    
    def test_ar_overdue(self):
        """Test GET /api/finance/ar/overdue (E5)"""
        self.log("\n=== Testing AR Overdue (E5) ===", "info")
        
        try:
            url = f"{self.base_url}/api/finance/ar/overdue"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/finance/ar/overdue returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                self.test(
                    "AR overdue contains items",
                    "items" in data,
                    "items missing"
                )
                
                self.test(
                    "AR overdue contains count",
                    "count" in data,
                    "count missing"
                )
        except Exception as e:
            self.test("GET /api/finance/ar/overdue", False, str(e))
    
    def test_ar_reminders(self):
        """Test AR reminder endpoints (E5 - WhatsApp mocked)"""
        self.log("\n=== Testing AR Reminders (E5 - WA Mocked) ===", "info")
        
        # Test remind-all
        try:
            url = f"{self.base_url}/api/finance/ar/remind-all"
            response = requests.post(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/finance/ar/remind-all returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test(
                    "Remind-all response contains sent count",
                    "sent" in data,
                    "sent count missing"
                )
        except Exception as e:
            self.test("POST /api/finance/ar/remind-all", False, str(e))
        
        # Test single reminder (get a booking_id first)
        try:
            ar_url = f"{self.base_url}/api/finance/ar"
            ar_response = requests.get(ar_url, headers=self.headers("owner@demo.local"), timeout=10)
            
            if ar_response.status_code == 200:
                ar_data = ar_response.json()
                if ar_data.get("items") and len(ar_data["items"]) > 0:
                    booking_id = ar_data["items"][0].get("booking_id")
                    
                    if booking_id:
                        remind_url = f"{self.base_url}/api/finance/ar/{booking_id}/remind"
                        remind_response = requests.post(remind_url, headers=self.headers("owner@demo.local"), timeout=10)
                        
                        self.test(
                            f"POST /api/finance/ar/{booking_id}/remind returns 200",
                            remind_response.status_code == 200,
                            f"Got {remind_response.status_code}"
                        )
                        
                        if remind_response.status_code == 200:
                            remind_data = remind_response.json()
                            self.test(
                                "Single reminder response contains sent flag",
                                "sent" in remind_data,
                                "sent flag missing"
                            )
        except Exception as e:
            self.test("POST /api/finance/ar/{booking_id}/remind", False, str(e))
    
    def test_export(self):
        """Test GET /api/finance/export (E5)"""
        self.log("\n=== Testing Finance Export (E5) ===", "info")
        
        # Test PDF export
        try:
            url = f"{self.base_url}/api/finance/export?format=pdf"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=15)
            
            self.test(
                "GET /api/finance/export?format=pdf returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                self.test(
                    "PDF export has correct content-type",
                    "application/pdf" in response.headers.get("Content-Type", ""),
                    f"Got {response.headers.get('Content-Type')}"
                )
                
                self.test(
                    "PDF export has content",
                    len(response.content) > 0,
                    "PDF is empty"
                )
        except Exception as e:
            self.test("GET /api/finance/export?format=pdf", False, str(e))
        
        # Test Excel export
        try:
            url = f"{self.base_url}/api/finance/export?format=excel"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=15)
            
            self.test(
                "GET /api/finance/export?format=excel returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                self.test(
                    "Excel export has correct content-type",
                    "spreadsheet" in response.headers.get("Content-Type", ""),
                    f"Got {response.headers.get('Content-Type')}"
                )
                
                self.test(
                    "Excel export has content",
                    len(response.content) > 0,
                    "Excel is empty"
                )
        except Exception as e:
            self.test("GET /api/finance/export?format=excel", False, str(e))
    
    def test_rbac(self):
        """Test RBAC: driver should get 403 on finance endpoints"""
        self.log("\n=== Testing RBAC (Driver 403) ===", "info")
        
        finance_endpoints = [
            ("GET", "/api/finance/summary"),
            ("GET", "/api/finance/pl-full"),
            ("GET", "/api/finance/reconciliation"),
            ("POST", "/api/finance/reconciliation/sync"),
            ("GET", "/api/finance/cashflow"),
            ("GET", "/api/finance/ar"),
            ("GET", "/api/finance/ar/overdue"),
            ("POST", "/api/finance/ar/remind-all"),
            ("GET", "/api/finance/export?format=pdf"),
        ]
        
        for method, endpoint in finance_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                if method == "GET":
                    response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
                elif method == "POST":
                    response = requests.post(url, headers=self.headers("driver@demo.local"), timeout=10)
                
                self.test(
                    f"Driver {method} {endpoint} returns 403",
                    response.status_code == 403,
                    f"Expected 403, got {response.status_code}"
                )
            except Exception as e:
                self.test(f"Driver {method} {endpoint}", False, str(e))
        
        # Test ops_admin should have access
        try:
            url = f"{self.base_url}/api/finance/summary"
            response = requests.get(url, headers=self.headers("ops@demo.local"), timeout=10)
            
            self.test(
                "Ops Admin GET /api/finance/summary returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
        except Exception as e:
            self.test("Ops Admin finance access", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*60, "info")
        self.log("E5 Finance Automation Backend Test Suite", "info")
        self.log("="*60, "info")
        
        if not self.test_auth():
            self.log("\n⚠️  Authentication failed. Cannot proceed.", "warn")
            return False
        
        # Run E5 finance tests
        self.test_finance_summary()
        self.test_pl_full()
        self.test_reconciliation()
        self.test_reconciliation_sync()
        self.test_cashflow()
        self.test_ar()
        self.test_ar_overdue()
        self.test_ar_reminders()
        self.test_export()
        self.test_rbac()
        
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
    tester = E5FinanceTestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
