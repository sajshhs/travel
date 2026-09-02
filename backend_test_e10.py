#!/usr/bin/env python3
"""
Backend Test Suite for Phase A (E10): Service Types & Vehicle Service History
==============================================================================
Tests Service Types CRUD, Vehicle Maintenance History, RBAC
"""
import requests
import sys
import json
from datetime import datetime

class E10TestSuite:
    def __init__(self, base_url="https://trip-route-buttons.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.created_service_type_id = None
        
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
    
    def test_list_service_types(self):
        """Test GET /api/service-types"""
        self.log("\n=== Testing List Service Types (GET /api/service-types) ===", "info")
        
        # Test as owner
        try:
            url = f"{self.base_url}/api/service-types"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/service-types as owner returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test(
                    "Service types list is array",
                    isinstance(data, list),
                    f"Expected list, got {type(data)}"
                )
                
                # Check for seeded service types
                if isinstance(data, list):
                    names = [st.get("name") for st in data]
                    self.log(f"Found service types: {names}", "info")
                    
                    expected_types = ["Ganti Ban", "Ganti Oli", "Spooring & Balancing"]
                    for expected in expected_types:
                        found = any(expected in name for name in names)
                        self.test(
                            f"Seeded service type '{expected}' exists",
                            found,
                            f"Not found in {names}"
                        )
                    
                    # Store a service type ID for later tests
                    if data:
                        self.existing_service_type = data[0]
        except Exception as e:
            self.test("GET /api/service-types as owner", False, str(e))
        
        # Test as driver (should work - read access)
        try:
            url = f"{self.base_url}/api/service-types"
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "GET /api/service-types as driver returns 200 (read access)",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
        except Exception as e:
            self.test("GET /api/service-types as driver", False, str(e))
    
    def test_create_service_type(self):
        """Test POST /api/service-types"""
        self.log("\n=== Testing Create Service Type (POST /api/service-types) ===", "info")
        
        # Test as owner
        service_type_data = {
            "name": "Ganti Kampas Rem",
            "default_interval_km": 30000,
            "default_interval_days": 365,
            "active": True
        }
        
        try:
            url = f"{self.base_url}/api/service-types"
            response = requests.post(url, json=service_type_data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/service-types as owner returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                created = response.json()
                
                # Check ID prefix
                self.test(
                    "Service type ID has svt_ prefix",
                    created.get("id", "").startswith("svt_"),
                    f"Got ID: {created.get('id')}"
                )
                
                # Check key is slugified
                self.test(
                    "Service type has key field",
                    "key" in created,
                    "key field missing"
                )
                
                # Check name
                self.test(
                    "Service type name matches",
                    created.get("name") == "Ganti Kampas Rem",
                    f"Expected 'Ganti Kampas Rem', got {created.get('name')}"
                )
                
                # Check intervals
                self.test(
                    "Service type default_interval_km matches",
                    created.get("default_interval_km") == 30000,
                    f"Expected 30000, got {created.get('default_interval_km')}"
                )
                
                self.test(
                    "Service type default_interval_days matches",
                    created.get("default_interval_days") == 365,
                    f"Expected 365, got {created.get('default_interval_days')}"
                )
                
                # Check active
                self.test(
                    "Service type active is True",
                    created.get("active") == True,
                    f"Expected True, got {created.get('active')}"
                )
                
                # Store for later tests
                self.created_service_type_id = created.get("id")
                self.created_service_type_key = created.get("key")
        except Exception as e:
            self.test("POST /api/service-types as owner", False, str(e))
        
        # Test duplicate name (should fail with 400)
        try:
            url = f"{self.base_url}/api/service-types"
            response = requests.post(url, json=service_type_data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST duplicate service type returns 400",
                response.status_code == 400,
                f"Expected 400, got {response.status_code}"
            )
            
            if response.status_code == 400:
                error = response.json()
                self.test(
                    "Error message mentions duplicate",
                    "duplikat" in error.get("detail", "").lower() or "sudah ada" in error.get("detail", "").lower(),
                    f"Got error: {error.get('detail')}"
                )
        except Exception as e:
            self.test("POST duplicate service type", False, str(e))
        
        # Test builtin collision (should fail with 400)
        builtin_data = {
            "name": "Servis",
            "default_interval_km": 5000,
            "default_interval_days": 90,
            "active": True
        }
        
        try:
            url = f"{self.base_url}/api/service-types"
            response = requests.post(url, json=builtin_data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST builtin name collision returns 400",
                response.status_code == 400,
                f"Expected 400, got {response.status_code}"
            )
        except Exception as e:
            self.test("POST builtin collision", False, str(e))
        
        # Test as driver (should fail with 403)
        try:
            url = f"{self.base_url}/api/service-types"
            driver_data = {
                "name": "Driver Test",
                "default_interval_km": 1000,
                "default_interval_days": 30,
                "active": True
            }
            response = requests.post(url, json=driver_data, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "POST /api/service-types as driver returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("POST /api/service-types as driver", False, str(e))
    
    def test_update_service_type(self):
        """Test PATCH /api/service-types/{id}"""
        self.log("\n=== Testing Update Service Type (PATCH /api/service-types/{id}) ===", "info")
        
        if not self.created_service_type_id:
            self.log("No service type ID available, skipping update tests", "warn")
            return
        
        # Test as owner
        update_data = {
            "default_interval_km": 40000,
            "default_interval_days": 400
        }
        
        try:
            url = f"{self.base_url}/api/service-types/{self.created_service_type_id}"
            response = requests.patch(url, json=update_data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "PATCH /api/service-types/{id} as owner returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                updated = response.json()
                
                # Check intervals updated
                self.test(
                    "Service type default_interval_km updated",
                    updated.get("default_interval_km") == 40000,
                    f"Expected 40000, got {updated.get('default_interval_km')}"
                )
                
                self.test(
                    "Service type default_interval_days updated",
                    updated.get("default_interval_days") == 400,
                    f"Expected 400, got {updated.get('default_interval_days')}"
                )
                
                # Check name preserved
                self.test(
                    "Service type name preserved",
                    updated.get("name") == "Ganti Kampas Rem",
                    f"Name should be preserved"
                )
        except Exception as e:
            self.test("PATCH /api/service-types/{id} as owner", False, str(e))
        
        # Test as driver (should fail with 403)
        try:
            url = f"{self.base_url}/api/service-types/{self.created_service_type_id}"
            response = requests.patch(url, json={"active": False}, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "PATCH /api/service-types/{id} as driver returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("PATCH /api/service-types/{id} as driver", False, str(e))
        
        # Test non-existent ID (should return 404)
        try:
            url = f"{self.base_url}/api/service-types/svt_nonexistent"
            response = requests.patch(url, json={"active": False}, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "PATCH non-existent service type returns 404",
                response.status_code == 404,
                f"Expected 404, got {response.status_code}"
            )
        except Exception as e:
            self.test("PATCH non-existent service type", False, str(e))
    
    def test_maintenance_with_custom_types(self):
        """Test POST /api/maintenance with custom service types"""
        self.log("\n=== Testing Maintenance with Custom Service Types ===", "info")
        
        # Get a vehicle ID first
        try:
            url = f"{self.base_url}/api/vehicles"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                vehicles = response.json()
                if vehicles:
                    vehicle_id = vehicles[0].get("id")
                    self.log(f"Using vehicle ID: {vehicle_id}", "info")
                    
                    # Create maintenance record with custom service type
                    if self.created_service_type_key:
                        maintenance_data = {
                            "vehicle_id": vehicle_id,
                            "type": self.created_service_type_key,
                            "title": "Test Custom Service Type",
                            "description": "Testing custom service type integration",
                            "scheduled_date": "2025-09-01",
                            "odometer": 50000,
                            "cost": 500000,
                            "status": "scheduled"
                        }
                        
                        url = f"{self.base_url}/api/maintenance"
                        response = requests.post(url, json=maintenance_data, headers=self.headers("owner@demo.local"), timeout=10)
                        
                        self.test(
                            "POST /api/maintenance with custom service type returns 200",
                            response.status_code == 200,
                            f"Got {response.status_code}"
                        )
                        
                        if response.status_code == 200:
                            created = response.json()
                            
                            # Check type matches custom key
                            self.test(
                                "Maintenance record type matches custom service type key",
                                created.get("type") == self.created_service_type_key,
                                f"Expected {self.created_service_type_key}, got {created.get('type')}"
                            )
                            
                            self.created_maintenance_id = created.get("id")
        except Exception as e:
            self.test("POST /api/maintenance with custom type", False, str(e))
    
    def test_vehicle_maintenance_history(self):
        """Test GET /api/vehicles/{id}/maintenance"""
        self.log("\n=== Testing Vehicle Maintenance History ===", "info")
        
        # Get a vehicle ID
        try:
            url = f"{self.base_url}/api/vehicles"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                vehicles = response.json()
                if vehicles:
                    vehicle_id = vehicles[0].get("id")
                    vehicle_code = vehicles[0].get("code")
                    self.log(f"Testing maintenance history for vehicle: {vehicle_code}", "info")
                    
                    # Get maintenance history
                    url = f"{self.base_url}/api/vehicles/{vehicle_id}/maintenance"
                    response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    self.test(
                        "GET /api/vehicles/{id}/maintenance returns 200",
                        response.status_code == 200,
                        f"Got {response.status_code}"
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Check structure
                        self.test(
                            "Response has 'totals' field",
                            "totals" in data,
                            "totals field missing"
                        )
                        
                        self.test(
                            "Response has 'records' field",
                            "records" in data,
                            "records field missing"
                        )
                        
                        # Check totals structure
                        if "totals" in data:
                            totals = data["totals"]
                            required_fields = ["count", "total_cost", "done", "next_service_date", "last_service_date"]
                            for field in required_fields:
                                self.test(
                                    f"Totals has '{field}' field",
                                    field in totals,
                                    f"{field} missing from totals"
                                )
                        
                        # Check records is array
                        if "records" in data:
                            self.test(
                                "Records is array",
                                isinstance(data["records"], list),
                                f"Expected list, got {type(data['records'])}"
                            )
                            
                            # If we created a maintenance record, check it's in the list
                            if hasattr(self, 'created_maintenance_id') and data["records"]:
                                found = any(r.get("id") == self.created_maintenance_id for r in data["records"])
                                self.test(
                                    "Created maintenance record appears in vehicle history",
                                    found,
                                    "Created record not found in history"
                                )
        except Exception as e:
            self.test("GET /api/vehicles/{id}/maintenance", False, str(e))
        
        # Test as driver (should work - read access)
        try:
            url = f"{self.base_url}/api/vehicles"
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            if response.status_code == 200:
                vehicles = response.json()
                if vehicles:
                    vehicle_id = vehicles[0].get("id")
                    
                    url = f"{self.base_url}/api/vehicles/{vehicle_id}/maintenance"
                    response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
                    
                    self.test(
                        "GET /api/vehicles/{id}/maintenance as driver returns 200 (read access)",
                        response.status_code == 200,
                        f"Got {response.status_code}"
                    )
        except Exception as e:
            self.test("GET /api/vehicles/{id}/maintenance as driver", False, str(e))
    
    def test_delete_service_type(self):
        """Test DELETE /api/service-types/{id}"""
        self.log("\n=== Testing Delete Service Type (DELETE /api/service-types/{id}) ===", "info")
        
        if not self.created_service_type_id:
            self.log("No service type ID available, skipping delete tests", "warn")
            return
        
        # Test as driver (should fail with 403)
        try:
            url = f"{self.base_url}/api/service-types/{self.created_service_type_id}"
            response = requests.delete(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "DELETE /api/service-types/{id} as driver returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("DELETE /api/service-types/{id} as driver", False, str(e))
        
        # Test as owner
        try:
            url = f"{self.base_url}/api/service-types/{self.created_service_type_id}"
            response = requests.delete(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "DELETE /api/service-types/{id} as owner returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                result = response.json()
                self.test(
                    "DELETE returns deleted: true",
                    result.get("deleted") == True,
                    f"Expected {{deleted: true}}, got {result}"
                )
                
                # Verify deleted (GET should return 404 or not in list)
                list_url = f"{self.base_url}/api/service-types"
                list_response = requests.get(list_url, headers=self.headers("owner@demo.local"), timeout=10)
                if list_response.status_code == 200:
                    items = list_response.json()
                    deleted_found = any(item.get("id") == self.created_service_type_id for item in items)
                    self.test(
                        "Deleted service type not in list",
                        not deleted_found,
                        "Deleted item still appears in list"
                    )
        except Exception as e:
            self.test("DELETE /api/service-types/{id} as owner", False, str(e))
        
        # Test delete non-existent ID (should return 404)
        try:
            url = f"{self.base_url}/api/service-types/svt_nonexistent"
            response = requests.delete(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "DELETE non-existent service type returns 404",
                response.status_code == 404,
                f"Expected 404, got {response.status_code}"
            )
        except Exception as e:
            self.test("DELETE non-existent service type", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*60, "info")
        self.log("Phase A (E10): Service Types & Vehicle Service History", "info")
        self.log("="*60, "info")
        
        # Run tests in order
        if not self.test_auth():
            self.log("\n⚠️  Authentication failed. Cannot proceed with other tests.", "warn")
            return False
        
        self.test_list_service_types()
        self.test_create_service_type()
        self.test_update_service_type()
        self.test_maintenance_with_custom_types()
        self.test_vehicle_maintenance_history()
        self.test_delete_service_type()
        
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
    tester = E10TestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
