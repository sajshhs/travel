#!/usr/bin/env python3
"""
Backend Test Suite for E11 Driver Payroll / HR Lite
====================================================
Tests compensation config, payout generation, approve/pay workflow, RBAC, slip export
"""
import requests
import sys
import json
from datetime import datetime, timedelta

class E11PayrollTestSuite:
    def __init__(self, base_url="https://trip-route-buttons.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.driver_id = None
        self.payout_id = None
        
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
    
    def test_get_driver(self):
        """Get a driver ID for testing"""
        self.log("\n=== Getting Driver for Testing ===", "info")
        
        try:
            url = f"{self.base_url}/api/drivers"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                drivers = response.json()
                if drivers:
                    self.driver_id = drivers[0].get("id")
                    self.driver_name = drivers[0].get("name")
                    self.log(f"Using driver: {self.driver_name} ({self.driver_id})", "info")
                    return True
            
            self.log("No drivers found", "fail")
            return False
        except Exception as e:
            self.log(f"Error getting drivers: {str(e)}", "fail")
            return False
    
    def test_compensation_rbac(self):
        """Test compensation RBAC - driver should get 403"""
        self.log("\n=== Testing Compensation RBAC ===", "info")
        
        if not self.driver_id:
            self.log("No driver ID, skipping RBAC tests", "warn")
            return
        
        # Test driver GET compensation (should be 403)
        try:
            url = f"{self.base_url}/api/drivers/{self.driver_id}/compensation"
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "Driver GET compensation returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("Driver GET compensation", False, str(e))
        
        # Test driver PATCH compensation (should be 403)
        try:
            url = f"{self.base_url}/api/drivers/{self.driver_id}/compensation"
            payload = {"base_salary_monthly": 5000000}
            response = requests.patch(url, json=payload, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "Driver PATCH compensation returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("Driver PATCH compensation", False, str(e))
        
        # Test owner GET compensation (should be 200)
        try:
            url = f"{self.base_url}/api/drivers/{self.driver_id}/compensation"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "Owner GET compensation returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test(
                    "Compensation response has comp field",
                    "comp" in data,
                    "comp field missing"
                )
                self.test(
                    "Compensation response has driver_id",
                    data.get("driver_id") == self.driver_id,
                    f"Expected {self.driver_id}, got {data.get('driver_id')}"
                )
        except Exception as e:
            self.test("Owner GET compensation", False, str(e))
        
        # Test ops_admin GET compensation (should be 200)
        try:
            url = f"{self.base_url}/api/drivers/{self.driver_id}/compensation"
            response = requests.get(url, headers=self.headers("ops@demo.local"), timeout=10)
            
            self.test(
                "Ops Admin GET compensation returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
        except Exception as e:
            self.test("Ops Admin GET compensation", False, str(e))
    
    def test_compensation_update(self):
        """Test updating driver compensation"""
        self.log("\n=== Testing Compensation Update ===", "info")
        
        if not self.driver_id:
            self.log("No driver ID, skipping compensation update", "warn")
            return
        
        try:
            url = f"{self.base_url}/api/drivers/{self.driver_id}/compensation"
            payload = {
                "base_salary_monthly": 4500000,
                "commission_per_trip": 75000,
                "commission_pct_revenue": 8.5,
                "allowance_per_km": 600,
                "revenue_base": "trip",
                "enable_base": True,
                "enable_commission_trip": True,
                "enable_commission_pct": True,
                "enable_allowance_km": True
            }
            
            response = requests.patch(url, json=payload, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "PATCH compensation returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                comp = data.get("comp", {})
                
                self.test(
                    "Compensation base_salary_monthly updated",
                    comp.get("base_salary_monthly") == 4500000,
                    f"Expected 4500000, got {comp.get('base_salary_monthly')}"
                )
                
                self.test(
                    "Compensation commission_per_trip updated",
                    comp.get("commission_per_trip") == 75000,
                    f"Expected 75000, got {comp.get('commission_per_trip')}"
                )
                
                self.test(
                    "Compensation commission_pct_revenue updated",
                    comp.get("commission_pct_revenue") == 8.5,
                    f"Expected 8.5, got {comp.get('commission_pct_revenue')}"
                )
                
                self.test(
                    "Compensation allowance_per_km updated",
                    comp.get("allowance_per_km") == 600,
                    f"Expected 600, got {comp.get('allowance_per_km')}"
                )
                
                self.test(
                    "Compensation revenue_base updated",
                    comp.get("revenue_base") == "trip",
                    f"Expected 'trip', got {comp.get('revenue_base')}"
                )
        except Exception as e:
            self.test("PATCH compensation", False, str(e))
        
        # Test invalid revenue_base (should be 400)
        try:
            url = f"{self.base_url}/api/drivers/{self.driver_id}/compensation"
            payload = {"revenue_base": "invalid"}
            response = requests.patch(url, json=payload, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "PATCH compensation with invalid revenue_base returns 400",
                response.status_code == 400,
                f"Expected 400, got {response.status_code}"
            )
        except Exception as e:
            self.test("PATCH compensation invalid revenue_base", False, str(e))
    
    def test_payroll_summary(self):
        """Test GET /api/payroll/summary"""
        self.log("\n=== Testing Payroll Summary ===", "info")
        
        try:
            url = f"{self.base_url}/api/payroll/summary"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/payroll/summary returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                self.test(
                    "Summary has count field",
                    "count" in data,
                    "count field missing"
                )
                
                self.test(
                    "Summary has by_status field",
                    "by_status" in data,
                    "by_status field missing"
                )
                
                self.test(
                    "Summary has accrued_total field",
                    "accrued_total" in data,
                    "accrued_total field missing"
                )
                
                self.test(
                    "Summary has paid_total field",
                    "paid_total" in data,
                    "paid_total field missing"
                )
        except Exception as e:
            self.test("GET /api/payroll/summary", False, str(e))
        
        # Test driver access (should be 403)
        try:
            url = f"{self.base_url}/api/payroll/summary"
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "Driver GET /api/payroll/summary returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("Driver GET /api/payroll/summary", False, str(e))
    
    def test_list_payouts(self):
        """Test GET /api/payroll/payouts with filters"""
        self.log("\n=== Testing List Payouts ===", "info")
        
        # Test list all payouts
        try:
            url = f"{self.base_url}/api/payroll/payouts"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/payroll/payouts returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test(
                    "Payouts list is array",
                    isinstance(data, list),
                    f"Expected list, got {type(data)}"
                )
        except Exception as e:
            self.test("GET /api/payroll/payouts", False, str(e))
        
        # Test filter by status
        try:
            url = f"{self.base_url}/api/payroll/payouts?status=draft"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/payroll/payouts?status=draft returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
        except Exception as e:
            self.test("GET /api/payroll/payouts with status filter", False, str(e))
        
        # Test filter by driver_id
        if self.driver_id:
            try:
                url = f"{self.base_url}/api/payroll/payouts?driver_id={self.driver_id}"
                response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "GET /api/payroll/payouts?driver_id returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
            except Exception as e:
                self.test("GET /api/payroll/payouts with driver_id filter", False, str(e))
        
        # Test driver access (should be 403)
        try:
            url = f"{self.base_url}/api/payroll/payouts"
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "Driver GET /api/payroll/payouts returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("Driver GET /api/payroll/payouts", False, str(e))
    
    def test_generate_payout(self):
        """Test POST /api/payroll/payouts/generate"""
        self.log("\n=== Testing Generate Payout ===", "info")
        
        if not self.driver_id:
            self.log("No driver ID, skipping payout generation", "warn")
            return
        
        # Calculate period (current month)
        now = datetime.now()
        period_start = f"{now.year}-{now.month:02d}-01"
        period_end = f"{now.year}-{now.month:02d}-{now.day:02d}"
        
        try:
            url = f"{self.base_url}/api/payroll/payouts/generate"
            payload = {
                "driver_id": self.driver_id,
                "period_type": "monthly",
                "period_start": period_start,
                "period_end": period_end
            }
            
            response = requests.post(url, json=payload, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/payroll/payouts/generate returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                self.test(
                    "Generated payout has ID with dpo_ prefix",
                    data.get("id", "").startswith("dpo_"),
                    f"Got ID: {data.get('id')}"
                )
                
                self.test(
                    "Generated payout has status draft",
                    data.get("status") == "draft",
                    f"Expected 'draft', got {data.get('status')}"
                )
                
                self.test(
                    "Generated payout has driver_id",
                    data.get("driver_id") == self.driver_id,
                    f"Expected {self.driver_id}, got {data.get('driver_id')}"
                )
                
                self.test(
                    "Generated payout has period_type",
                    data.get("period_type") == "monthly",
                    f"Expected 'monthly', got {data.get('period_type')}"
                )
                
                self.test(
                    "Generated payout has total field",
                    "total" in data,
                    "total field missing"
                )
                
                self.test(
                    "Generated payout has gross field",
                    "gross" in data,
                    "gross field missing"
                )
                
                # Store payout ID for later tests
                self.payout_id = data.get("id")
                self.log(f"Generated payout ID: {self.payout_id}", "info")
        except Exception as e:
            self.test("POST /api/payroll/payouts/generate", False, str(e))
        
        # Test duplicate generation (should be 400)
        try:
            url = f"{self.base_url}/api/payroll/payouts/generate"
            payload = {
                "driver_id": self.driver_id,
                "period_type": "monthly",
                "period_start": period_start,
                "period_end": period_end
            }
            
            response = requests.post(url, json=payload, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "Duplicate payout generation returns 400",
                response.status_code == 400,
                f"Expected 400, got {response.status_code}"
            )
        except Exception as e:
            self.test("Duplicate payout generation", False, str(e))
        
        # Test invalid period (should be 400)
        try:
            url = f"{self.base_url}/api/payroll/payouts/generate"
            payload = {
                "driver_id": self.driver_id,
                "period_type": "monthly",
                "period_start": "2024-12-31",
                "period_end": "2024-12-01"  # End before start
            }
            
            response = requests.post(url, json=payload, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "Invalid period (end < start) returns 400",
                response.status_code == 400,
                f"Expected 400, got {response.status_code}"
            )
        except Exception as e:
            self.test("Invalid period generation", False, str(e))
        
        # Test driver access (should be 403)
        try:
            url = f"{self.base_url}/api/payroll/payouts/generate"
            payload = {
                "driver_id": self.driver_id,
                "period_type": "weekly",
                "period_start": period_start,
                "period_end": period_end
            }
            
            response = requests.post(url, json=payload, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "Driver POST /api/payroll/payouts/generate returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("Driver POST /api/payroll/payouts/generate", False, str(e))
    
    def test_get_payout(self):
        """Test GET /api/payroll/payouts/{id}"""
        self.log("\n=== Testing Get Payout ===", "info")
        
        if not self.payout_id:
            self.log("No payout ID, skipping get payout test", "warn")
            return
        
        try:
            url = f"{self.base_url}/api/payroll/payouts/{self.payout_id}"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/payroll/payouts/{id} returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                self.test(
                    "Payout has correct ID",
                    data.get("id") == self.payout_id,
                    f"Expected {self.payout_id}, got {data.get('id')}"
                )
                
                self.test(
                    "Payout has bonuses field",
                    "bonuses" in data,
                    "bonuses field missing"
                )
                
                self.test(
                    "Payout has deductions field",
                    "deductions" in data,
                    "deductions field missing"
                )
        except Exception as e:
            self.test("GET /api/payroll/payouts/{id}", False, str(e))
        
        # Test non-existent payout (should be 404)
        try:
            url = f"{self.base_url}/api/payroll/payouts/dpo_nonexistent"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET non-existent payout returns 404",
                response.status_code == 404,
                f"Expected 404, got {response.status_code}"
            )
        except Exception as e:
            self.test("GET non-existent payout", False, str(e))
    
    def test_update_payout_draft(self):
        """Test PATCH /api/payroll/payouts/{id} (draft only)"""
        self.log("\n=== Testing Update Payout Draft ===", "info")
        
        if not self.payout_id:
            self.log("No payout ID, skipping update payout test", "warn")
            return
        
        try:
            url = f"{self.base_url}/api/payroll/payouts/{self.payout_id}"
            payload = {
                "bonuses": [
                    {"label": "Bonus Kinerja", "amount": 500000},
                    {"label": "Bonus Kehadiran", "amount": 250000}
                ],
                "deductions": [
                    {"label": "Potongan Kasbon", "amount": 300000}
                ],
                "notes": "Test payout dengan bonus dan potongan"
            }
            
            response = requests.patch(url, json=payload, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "PATCH /api/payroll/payouts/{id} returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                self.test(
                    "Payout bonuses updated",
                    len(data.get("bonuses", [])) == 2,
                    f"Expected 2 bonuses, got {len(data.get('bonuses', []))}"
                )
                
                self.test(
                    "Payout deductions updated",
                    len(data.get("deductions", [])) == 1,
                    f"Expected 1 deduction, got {len(data.get('deductions', []))}"
                )
                
                self.test(
                    "Payout notes updated",
                    data.get("notes") == "Test payout dengan bonus dan potongan",
                    f"Notes not updated correctly"
                )
                
                self.test(
                    "Payout bonus_total calculated",
                    data.get("bonus_total") == 750000,
                    f"Expected 750000, got {data.get('bonus_total')}"
                )
                
                self.test(
                    "Payout deduction_total calculated",
                    data.get("deduction_total") == 300000,
                    f"Expected 300000, got {data.get('deduction_total')}"
                )
                
                # Total should be gross + bonus - deduction
                expected_total = data.get("gross", 0) + 750000 - 300000
                self.test(
                    "Payout total recalculated correctly",
                    data.get("total") == expected_total,
                    f"Expected {expected_total}, got {data.get('total')}"
                )
        except Exception as e:
            self.test("PATCH /api/payroll/payouts/{id}", False, str(e))
    
    def test_approve_payout(self):
        """Test POST /api/payroll/payouts/{id}/approve"""
        self.log("\n=== Testing Approve Payout ===", "info")
        
        if not self.payout_id:
            self.log("No payout ID, skipping approve payout test", "warn")
            return
        
        try:
            url = f"{self.base_url}/api/payroll/payouts/{self.payout_id}/approve"
            response = requests.post(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/payroll/payouts/{id}/approve returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                self.test(
                    "Payout status changed to approved",
                    data.get("status") == "approved",
                    f"Expected 'approved', got {data.get('status')}"
                )
                
                self.test(
                    "Payout has approver_id",
                    data.get("approver_id") is not None,
                    "approver_id missing"
                )
                
                self.test(
                    "Payout has approver_name",
                    data.get("approver_name") is not None,
                    "approver_name missing"
                )
                
                self.test(
                    "Payout has approved_at",
                    data.get("approved_at") is not None,
                    "approved_at missing"
                )
                
                self.test(
                    "Payout has expense_id (Finance integration)",
                    data.get("expense_id") is not None,
                    "expense_id missing - Finance integration failed"
                )
                
                # Store expense_id for verification
                self.expense_id = data.get("expense_id")
        except Exception as e:
            self.test("POST /api/payroll/payouts/{id}/approve", False, str(e))
        
        # Verify expense created in Finance
        if hasattr(self, 'expense_id') and self.expense_id:
            try:
                url = f"{self.base_url}/api/expenses"
                response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                
                if response.status_code == 200:
                    expenses = response.json()
                    expense = next((e for e in expenses if e.get("id") == self.expense_id), None)
                    
                    self.test(
                        "Finance expense created for payout",
                        expense is not None,
                        f"Expense {self.expense_id} not found"
                    )
                    
                    if expense:
                        self.test(
                            "Expense category is gaji_driver",
                            expense.get("category") == "gaji_driver",
                            f"Expected 'gaji_driver', got {expense.get('category')}"
                        )
                        
                        self.test(
                            "Expense paid is False (akrual)",
                            expense.get("paid") == False,
                            f"Expected False, got {expense.get('paid')}"
                        )
            except Exception as e:
                self.test("Verify Finance expense", False, str(e))
    
    def test_pay_payout(self):
        """Test POST /api/payroll/payouts/{id}/pay"""
        self.log("\n=== Testing Pay Payout ===", "info")
        
        if not self.payout_id:
            self.log("No payout ID, skipping pay payout test", "warn")
            return
        
        try:
            url = f"{self.base_url}/api/payroll/payouts/{self.payout_id}/pay"
            response = requests.post(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/payroll/payouts/{id}/pay returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                self.test(
                    "Payout status changed to paid",
                    data.get("status") == "paid",
                    f"Expected 'paid', got {data.get('status')}"
                )
                
                self.test(
                    "Payout has paid_at",
                    data.get("paid_at") is not None,
                    "paid_at missing"
                )
        except Exception as e:
            self.test("POST /api/payroll/payouts/{id}/pay", False, str(e))
        
        # Verify expense marked as paid
        if hasattr(self, 'expense_id') and self.expense_id:
            try:
                url = f"{self.base_url}/api/expenses"
                response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                
                if response.status_code == 200:
                    expenses = response.json()
                    expense = next((e for e in expenses if e.get("id") == self.expense_id), None)
                    
                    if expense:
                        self.test(
                            "Expense marked as paid (realisasi kas)",
                            expense.get("paid") == True,
                            f"Expected True, got {expense.get('paid')}"
                        )
            except Exception as e:
                self.test("Verify expense paid", False, str(e))
    
    def test_delete_payout(self):
        """Test DELETE /api/payroll/payouts/{id} (draft only)"""
        self.log("\n=== Testing Delete Payout ===", "info")
        
        # Try to delete paid payout (should be 400)
        if self.payout_id:
            try:
                url = f"{self.base_url}/api/payroll/payouts/{self.payout_id}"
                response = requests.delete(url, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "DELETE paid payout returns 400",
                    response.status_code == 400,
                    f"Expected 400, got {response.status_code}"
                )
            except Exception as e:
                self.test("DELETE paid payout", False, str(e))
        
        # Create a new draft payout and delete it
        if self.driver_id:
            try:
                # Generate new draft payout
                now = datetime.now()
                period_start = f"{now.year}-{now.month:02d}-15"
                period_end = f"{now.year}-{now.month:02d}-{now.day:02d}"
                
                gen_url = f"{self.base_url}/api/payroll/payouts/generate"
                gen_payload = {
                    "driver_id": self.driver_id,
                    "period_type": "weekly",
                    "period_start": period_start,
                    "period_end": period_end
                }
                
                gen_response = requests.post(gen_url, json=gen_payload, headers=self.headers("owner@demo.local"), timeout=10)
                
                if gen_response.status_code == 200:
                    draft_payout = gen_response.json()
                    draft_id = draft_payout.get("id")
                    
                    # Delete draft payout
                    del_url = f"{self.base_url}/api/payroll/payouts/{draft_id}"
                    del_response = requests.delete(del_url, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    self.test(
                        "DELETE draft payout returns 200",
                        del_response.status_code == 200,
                        f"Got {del_response.status_code}"
                    )
                    
                    if del_response.status_code == 200:
                        result = del_response.json()
                        self.test(
                            "DELETE returns deleted: true",
                            result.get("deleted") == True,
                            f"Expected deleted: true"
                        )
            except Exception as e:
                self.test("DELETE draft payout", False, str(e))
    
    def test_slip_export(self):
        """Test GET /api/payroll/payouts/{id}/slip (PDF and Excel)"""
        self.log("\n=== Testing Slip Export ===", "info")
        
        if not self.payout_id:
            self.log("No payout ID, skipping slip export test", "warn")
            return
        
        # Test PDF export
        try:
            url = f"{self.base_url}/api/payroll/payouts/{self.payout_id}/slip?format=pdf"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET slip?format=pdf returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                self.test(
                    "PDF response has correct content-type",
                    "application/pdf" in response.headers.get("content-type", ""),
                    f"Got content-type: {response.headers.get('content-type')}"
                )
        except Exception as e:
            self.test("GET slip PDF", False, str(e))
        
        # Test Excel export
        try:
            url = f"{self.base_url}/api/payroll/payouts/{self.payout_id}/slip?format=excel"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET slip?format=excel returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                self.test(
                    "Excel response has correct content-type",
                    "spreadsheetml" in response.headers.get("content-type", ""),
                    f"Got content-type: {response.headers.get('content-type')}"
                )
        except Exception as e:
            self.test("GET slip Excel", False, str(e))
        
        # Test driver access (should be 403)
        try:
            url = f"{self.base_url}/api/payroll/payouts/{self.payout_id}/slip?format=pdf"
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "Driver GET slip returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("Driver GET slip", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*60, "info")
        self.log("E11 Driver Payroll / HR Lite Backend Test Suite", "info")
        self.log("="*60, "info")
        
        # Run tests in order
        if not self.test_auth():
            self.log("\n⚠️  Authentication failed. Cannot proceed with other tests.", "warn")
            return False
        
        if not self.test_get_driver():
            self.log("\n⚠️  No driver found. Cannot proceed with payroll tests.", "warn")
            return False
        
        # Run all E11 tests
        self.test_compensation_rbac()
        self.test_compensation_update()
        self.test_payroll_summary()
        self.test_list_payouts()
        self.test_generate_payout()
        self.test_get_payout()
        self.test_update_payout_draft()
        self.test_approve_payout()
        self.test_pay_payout()
        self.test_delete_payout()
        self.test_slip_export()
        
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
    tester = E11PayrollTestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
