#!/usr/bin/env python3
"""
Backend Test Suite for E8: Driver Workspace + Fleet Management
===============================================================
Tests Workshops CRUD, Preventive Maintenance, Driver Workspace APIs
"""
import requests
import sys
from datetime import datetime

class E8TestSuite:
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
    
    def login(self, email, password="demo12345"):
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
        
        owner_ok = self.login("owner@demo.local")
        ops_ok = self.login("ops@demo.local")
        driver_ok = self.login("driver@demo.local")
        
        self.test("Owner login", owner_ok)
        self.test("Ops Admin login", ops_ok)
        self.test("Driver login", driver_ok)
        
        return owner_ok and ops_ok and driver_ok
    
    def test_workshops_crud(self):
        """Test Workshops CRUD + RBAC"""
        self.log("\n=== Testing Workshops CRUD ===", "info")
        
        # GET /api/workshops
        try:
            url = f"{self.base_url}/api/workshops"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/workshops returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                workshops = response.json()
                self.test(
                    "GET /api/workshops returns >=3 workshops",
                    len(workshops) >= 3,
                    f"Expected >=3, got {len(workshops)}"
                )
                
                # Check ID prefix
                all_have_prefix = all(w.get("id", "").startswith("wsh_") for w in workshops)
                self.test(
                    "All workshop IDs start with 'wsh_'",
                    all_have_prefix,
                    f"Some IDs don't have wsh_ prefix"
                )
                
                # Store for later tests
                self.workshops = workshops
        except Exception as e:
            self.test("GET /api/workshops", False, str(e))
        
        # POST /api/workshops (create)
        try:
            url = f"{self.base_url}/api/workshops"
            data = {
                "name": "Bengkel Test E8",
                "city": "Jakarta",
                "specialties": ["servis", "perbaikan"],
                "phone": "021-12345678",
                "address": "Jl. Test No. 123"
            }
            response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/workshops returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                created = response.json()
                self.test(
                    "Created workshop has wsh_ prefix",
                    created.get("id", "").startswith("wsh_"),
                    f"Got ID: {created.get('id')}"
                )
                
                self.test(
                    "Created workshop has correct name",
                    created.get("name") == "Bengkel Test E8",
                    f"Expected 'Bengkel Test E8', got {created.get('name')}"
                )
                
                self.test(
                    "Created workshop is active by default",
                    created.get("active") == True,
                    f"Expected True, got {created.get('active')}"
                )
                
                # Store for later tests
                self.created_workshop_id = created.get("id")
        except Exception as e:
            self.test("POST /api/workshops", False, str(e))
        
        # PATCH /api/workshops/{id} (deactivate)
        if hasattr(self, 'created_workshop_id'):
            try:
                url = f"{self.base_url}/api/workshops/{self.created_workshop_id}"
                data = {"active": False}
                response = requests.patch(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "PATCH /api/workshops/{id} returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
                
                if response.status_code == 200:
                    updated = response.json()
                    self.test(
                        "Workshop active set to False",
                        updated.get("active") == False,
                        f"Expected False, got {updated.get('active')}"
                    )
            except Exception as e:
                self.test("PATCH /api/workshops/{id}", False, str(e))
        
        # DELETE /api/workshops/{id}
        if hasattr(self, 'created_workshop_id'):
            try:
                url = f"{self.base_url}/api/workshops/{self.created_workshop_id}"
                response = requests.delete(url, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "DELETE /api/workshops/{id} returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.test(
                        "DELETE returns deleted: true",
                        result.get("deleted") == True,
                        f"Expected deleted: true, got {result}"
                    )
            except Exception as e:
                self.test("DELETE /api/workshops/{id}", False, str(e))
        
        # RBAC: Driver should get 403 on POST
        try:
            url = f"{self.base_url}/api/workshops"
            data = {"name": "Test", "city": "Test"}
            response = requests.post(url, json=data, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "Driver POST /api/workshops returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("Driver POST /api/workshops RBAC", False, str(e))
    
    def test_preventive_maintenance(self):
        """Test Preventive Maintenance endpoints"""
        self.log("\n=== Testing Preventive Maintenance ===", "info")
        
        # GET /api/maintenance/preventive
        try:
            url = f"{self.base_url}/api/maintenance/preventive"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/maintenance/preventive returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                summary = data.get("summary", {})
                
                self.test(
                    "Preventive response has items array",
                    isinstance(items, list),
                    f"Expected list, got {type(items)}"
                )
                
                self.test(
                    "Preventive response has summary",
                    isinstance(summary, dict),
                    f"Expected dict, got {type(summary)}"
                )
                
                # Check for expected seed data
                overdue_items = [i for i in items if i.get("status") == "overdue"]
                due_soon_items = [i for i in items if i.get("status") == "due_soon"]
                ok_items = [i for i in items if i.get("status") == "ok"]
                
                self.test(
                    "Has at least 1 OVERDUE vehicle (Hiace Premio 01)",
                    len(overdue_items) >= 1,
                    f"Expected >=1 overdue, got {len(overdue_items)}"
                )
                
                self.test(
                    "Has at least 1 DUE_SOON vehicle (Hiace Premio 02)",
                    len(due_soon_items) >= 1,
                    f"Expected >=1 due_soon, got {len(due_soon_items)}"
                )
                
                self.test(
                    "Has at least 1 OK vehicle (Isuzu Elf Long 01)",
                    len(ok_items) >= 1,
                    f"Expected >=1 ok, got {len(ok_items)}"
                )
                
                # Check item structure
                if items:
                    sample = items[0]
                    required_fields = ["vehicle_id", "vehicle_name", "odometer", "status"]
                    has_all_fields = all(field in sample for field in required_fields)
                    self.test(
                        "Preventive item has required fields",
                        has_all_fields,
                        f"Missing fields in: {sample.keys()}"
                    )
                    
                    # Check km or date basis exists
                    has_basis = sample.get("km") or sample.get("date")
                    self.test(
                        "Preventive item has km or date basis",
                        has_basis,
                        f"No km or date basis found"
                    )
                
                # Check summary consistency
                self.test(
                    "Summary total matches items count",
                    summary.get("total") == len(items),
                    f"Summary total {summary.get('total')} != items count {len(items)}"
                )
                
                # Store for schedule test
                self.preventive_items = items
        except Exception as e:
            self.test("GET /api/maintenance/preventive", False, str(e))
        
        # POST /api/maintenance/preventive/{vehicle_id}/schedule
        if hasattr(self, 'preventive_items') and self.preventive_items:
            vehicle_id = self.preventive_items[0].get("vehicle_id")
            try:
                url = f"{self.base_url}/api/maintenance/preventive/{vehicle_id}/schedule"
                response = requests.post(url, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "POST /api/maintenance/preventive/{id}/schedule returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
                
                if response.status_code == 200:
                    created = response.json()
                    self.test(
                        "Scheduled maintenance has type='servis'",
                        created.get("type") == "servis",
                        f"Expected 'servis', got {created.get('type')}"
                    )
                    
                    self.test(
                        "Scheduled maintenance has status='scheduled'",
                        created.get("status") == "scheduled",
                        f"Expected 'scheduled', got {created.get('status')}"
                    )
            except Exception as e:
                self.test("POST preventive schedule", False, str(e))
        
        # RBAC: Driver can GET (read-only)
        try:
            url = f"{self.base_url}/api/maintenance/preventive"
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "Driver GET /api/maintenance/preventive returns 200 (read-only)",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
        except Exception as e:
            self.test("Driver GET preventive", False, str(e))
        
        # RBAC: Driver cannot POST schedule
        if hasattr(self, 'preventive_items') and self.preventive_items:
            vehicle_id = self.preventive_items[0].get("vehicle_id")
            try:
                url = f"{self.base_url}/api/maintenance/preventive/{vehicle_id}/schedule"
                response = requests.post(url, headers=self.headers("driver@demo.local"), timeout=10)
                
                self.test(
                    "Driver POST preventive schedule returns 403",
                    response.status_code == 403,
                    f"Expected 403, got {response.status_code}"
                )
            except Exception as e:
                self.test("Driver POST preventive schedule RBAC", False, str(e))
    
    def test_maintenance_workshop_integration(self):
        """Test maintenance creation with workshop_id auto-resolve"""
        self.log("\n=== Testing Maintenance + Workshop Integration ===", "info")
        
        # Find an Auto2000 workshop
        auto2000_workshop = None
        if hasattr(self, 'workshops'):
            for w in self.workshops:
                if "Auto2000" in w.get("name", ""):
                    auto2000_workshop = w
                    break
        
        if not auto2000_workshop:
            self.log("No Auto2000 workshop found, skipping integration test", "warn")
            return
        
        # Get a vehicle ID
        try:
            url = f"{self.base_url}/api/vehicles"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            if response.status_code == 200:
                vehicles = response.json()
                if vehicles:
                    vehicle_id = vehicles[0].get("id")
                else:
                    self.log("No vehicles found", "warn")
                    return
            else:
                self.log("Could not get vehicles", "warn")
                return
        except Exception as e:
            self.log(f"Error getting vehicles: {str(e)}", "warn")
            return
        
        # Create maintenance with workshop_id
        try:
            url = f"{self.base_url}/api/maintenance"
            data = {
                "vehicle_id": vehicle_id,
                "type": "servis",
                "title": "Servis Test E8",
                "workshop_id": auto2000_workshop.get("id"),
                "scheduled_date": "2025-09-01"
            }
            response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/maintenance with workshop_id returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                created = response.json()
                
                self.test(
                    "Maintenance workshop_id is set",
                    created.get("workshop_id") == auto2000_workshop.get("id"),
                    f"Expected {auto2000_workshop.get('id')}, got {created.get('workshop_id')}"
                )
                
                self.test(
                    "Maintenance workshop name auto-resolved",
                    created.get("workshop") == auto2000_workshop.get("name"),
                    f"Expected '{auto2000_workshop.get('name')}', got '{created.get('workshop')}'"
                )
        except Exception as e:
            self.test("POST maintenance with workshop_id", False, str(e))
    
    def test_driver_workspace(self):
        """Test Driver Workspace APIs"""
        self.log("\n=== Testing Driver Workspace ===", "info")
        
        # GET /api/driver/summary
        try:
            url = f"{self.base_url}/api/driver/summary"
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "GET /api/driver/summary returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                summary = response.json()
                
                self.test(
                    "Driver summary has is_driver=true",
                    summary.get("is_driver") == True,
                    f"Expected True, got {summary.get('is_driver')}"
                )
                
                required_fields = ["total", "active", "completed", "need_pod"]
                has_all_fields = all(field in summary for field in required_fields)
                self.test(
                    "Driver summary has all required fields",
                    has_all_fields,
                    f"Missing fields in: {summary.keys()}"
                )
        except Exception as e:
            self.test("GET /api/driver/summary", False, str(e))
        
        # GET /api/driver/tasks
        try:
            url = f"{self.base_url}/api/driver/tasks"
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "GET /api/driver/tasks returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                tasks = response.json()
                
                self.test(
                    "Driver tasks is an array",
                    isinstance(tasks, list),
                    f"Expected list, got {type(tasks)}"
                )
                
                self.test(
                    "Driver has at least 1 task (seed data)",
                    len(tasks) >= 1,
                    f"Expected >=1, got {len(tasks)}"
                )
                
                if tasks:
                    task = tasks[0]
                    required_fields = ["trip_id", "code", "customer_name", "origin", "destination", 
                                     "trip_status", "acknowledged", "has_pod"]
                    has_all_fields = all(field in task for field in required_fields)
                    self.test(
                        "Driver task has all required fields",
                        has_all_fields,
                        f"Missing fields in: {task.keys()}"
                    )
                    
                    # Store for later tests
                    self.driver_task = task
        except Exception as e:
            self.test("GET /api/driver/tasks", False, str(e))
        
        # POST /api/driver/tasks/{trip_id}/ack
        if hasattr(self, 'driver_task'):
            trip_id = self.driver_task.get("trip_id")
            try:
                url = f"{self.base_url}/api/driver/tasks/{trip_id}/ack"
                response = requests.post(url, headers=self.headers("driver@demo.local"), timeout=10)
                
                self.test(
                    "POST /api/driver/tasks/{id}/ack returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
                
                if response.status_code == 200:
                    updated = response.json()
                    self.test(
                        "Trip has driver_ack_at after ack",
                        updated.get("driver_ack_at") is not None,
                        f"driver_ack_at is None"
                    )
            except Exception as e:
                self.test("POST driver ack", False, str(e))
        
        # POST /api/driver/tasks/{trip_id}/arrived
        if hasattr(self, 'driver_task'):
            trip_id = self.driver_task.get("trip_id")
            try:
                url = f"{self.base_url}/api/driver/tasks/{trip_id}/arrived"
                response = requests.post(url, headers=self.headers("driver@demo.local"), timeout=10)
                
                self.test(
                    "POST /api/driver/tasks/{id}/arrived returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
                
                if response.status_code == 200:
                    updated = response.json()
                    self.test(
                        "Trip has arrived_at after arrived",
                        updated.get("arrived_at") is not None,
                        f"arrived_at is None"
                    )
            except Exception as e:
                self.test("POST driver arrived", False, str(e))
        
        # POST /api/driver/tasks/{trip_id}/pod (NO file, just recipient_name + note)
        if hasattr(self, 'driver_task'):
            trip_id = self.driver_task.get("trip_id")
            try:
                url = f"{self.base_url}/api/driver/tasks/{trip_id}/pod"
                # Use form data (not JSON) as per the endpoint signature
                data = {
                    "recipient_name": "Pak Budi Test",
                    "note": "Diterima dengan baik"
                }
                response = requests.post(url, data=data, headers={"Authorization": f"Bearer {self.tokens.get('driver@demo.local')}"}, timeout=10)
                
                self.test(
                    "POST /api/driver/tasks/{id}/pod returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
                
                if response.status_code == 200:
                    updated = response.json()
                    self.test(
                        "Trip has pod after upload",
                        updated.get("pod") is not None,
                        f"pod is None"
                    )
                    
                    if updated.get("pod"):
                        pod = updated.get("pod")
                        self.test(
                            "POD has recipient_name",
                            pod.get("recipient_name") == "Pak Budi Test",
                            f"Expected 'Pak Budi Test', got {pod.get('recipient_name')}"
                        )
            except Exception as e:
                self.test("POST driver pod", False, str(e))
    
    def test_driver_workspace_rbac(self):
        """Test Driver Workspace RBAC and ownership"""
        self.log("\n=== Testing Driver Workspace RBAC ===", "info")
        
        # Owner (not a driver) should get empty tasks
        try:
            url = f"{self.base_url}/api/driver/tasks"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "Owner GET /api/driver/tasks returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                tasks = response.json()
                self.test(
                    "Owner (not driver) gets empty tasks array",
                    len(tasks) == 0,
                    f"Expected empty array, got {len(tasks)} tasks"
                )
        except Exception as e:
            self.test("Owner GET driver tasks", False, str(e))
        
        # Owner should get 403 on driver actions
        if hasattr(self, 'driver_task'):
            trip_id = self.driver_task.get("trip_id")
            try:
                url = f"{self.base_url}/api/driver/tasks/{trip_id}/ack"
                response = requests.post(url, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "Owner POST driver ack returns 403",
                    response.status_code == 403,
                    f"Expected 403, got {response.status_code}"
                )
            except Exception as e:
                self.test("Owner POST driver ack RBAC", False, str(e))
        
        # Non-existent trip should return 404
        try:
            url = f"{self.base_url}/api/driver/tasks/trp_nonexistent/ack"
            response = requests.post(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "Driver ack non-existent trip returns 404",
                response.status_code == 404,
                f"Expected 404, got {response.status_code}"
            )
        except Exception as e:
            self.test("Driver ack non-existent trip", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*60, "info")
        self.log("E8 Backend Test Suite: Driver Workspace + Fleet", "info")
        self.log("="*60, "info")
        
        # Run tests in order
        if not self.test_auth():
            self.log("\n⚠️  Authentication failed. Cannot proceed with other tests.", "warn")
            return False
        
        self.test_workshops_crud()
        self.test_preventive_maintenance()
        self.test_maintenance_workshop_integration()
        self.test_driver_workspace()
        self.test_driver_workspace_rbac()
        
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
    tester = E8TestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
