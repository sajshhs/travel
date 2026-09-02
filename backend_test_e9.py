#!/usr/bin/env python3
"""
Backend Test Suite for Phase E9: Fleet↔Driver Trip/KM & Odometer
=================================================================
Tests driver odometer flow, distance computation, and performance/trip history endpoints
"""
import requests
import sys
import json
from datetime import datetime

class E9TestSuite:
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
        """Test authentication"""
        self.log("\n=== Testing Authentication ===", "info")
        
        owner_ok = self.login("owner@demo.local")
        driver_ok = self.login("driver@demo.local")
        
        self.test("Owner login", owner_ok)
        self.test("Driver login", driver_ok)
        
        return owner_ok and driver_ok
    
    def test_driver_tasks(self):
        """Test GET /api/driver/tasks"""
        self.log("\n=== Testing Driver Tasks Endpoint ===", "info")
        
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
                    "Driver has tasks",
                    isinstance(tasks, list) and len(tasks) > 0,
                    f"Expected list with tasks, got {len(tasks) if isinstance(tasks, list) else 'not a list'}"
                )
                
                if tasks:
                    task = tasks[0]
                    required_fields = ["trip_id", "booking_id", "code", "trip_status", "vehicle_id", "vehicle_odometer"]
                    for field in required_fields:
                        self.test(
                            f"Task has {field} field",
                            field in task,
                            f"Missing {field}"
                        )
                    
                    # Store task info for later tests
                    self.test_task = next((t for t in tasks if t.get("trip_status") in ("standby", "assigned")), tasks[0] if tasks else None)
                    if self.test_task:
                        self.log(f"Found test task: {self.test_task.get('code')} (status: {self.test_task.get('trip_status')})", "info")
                        return True
            return False
        except Exception as e:
            self.test("GET /api/driver/tasks", False, str(e))
            return False
    
    def test_driver_odometer_flow(self):
        """Test driver checkin/checkout with odometer"""
        self.log("\n=== Testing Driver Odometer Flow ===", "info")
        
        if not hasattr(self, 'test_task'):
            self.log("No test task available, skipping odometer flow", "warn")
            return False
        
        trip_id = self.test_task.get("trip_id")
        vehicle_id = self.test_task.get("vehicle_id")
        
        # Get initial vehicle odometer
        try:
            url = f"{self.base_url}/api/vehicles/{vehicle_id}"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            if response.status_code == 200:
                vehicle = response.json()
                initial_odometer = float(vehicle.get("odometer", 0))
                self.log(f"Initial vehicle odometer: {initial_odometer} km", "info")
            else:
                initial_odometer = 0
        except Exception as e:
            self.log(f"Could not get initial odometer: {str(e)}", "warn")
            initial_odometer = 0
        
        # Test checkin with odometer_start
        odometer_start = initial_odometer + 10
        try:
            url = f"{self.base_url}/api/driver/checkin"
            payload = {
                "trip_id": trip_id,
                "odometer_start": odometer_start
            }
            response = requests.post(url, json=payload, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "POST /api/driver/checkin with odometer_start returns 200",
                response.status_code == 200,
                f"Got {response.status_code}: {response.text if response.status_code != 200 else ''}"
            )
            
            if response.status_code == 200:
                trip = response.json()
                self.test(
                    "Trip has odometer_start after checkin",
                    trip.get("odometer_start") == odometer_start,
                    f"Expected {odometer_start}, got {trip.get('odometer_start')}"
                )
        except Exception as e:
            self.test("POST /api/driver/checkin", False, str(e))
            return False
        
        # Test checkout with odometer_end
        odometer_end = odometer_start + 250
        try:
            url = f"{self.base_url}/api/driver/checkout"
            payload = {
                "trip_id": trip_id,
                "odometer_end": odometer_end
            }
            response = requests.post(url, json=payload, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "POST /api/driver/checkout with odometer_end returns 200",
                response.status_code == 200,
                f"Got {response.status_code}: {response.text if response.status_code != 200 else ''}"
            )
            
            if response.status_code == 200:
                trip = response.json()
                
                self.test(
                    "Trip has odometer_end after checkout",
                    trip.get("odometer_end") == odometer_end,
                    f"Expected {odometer_end}, got {trip.get('odometer_end')}"
                )
                
                distance_km = trip.get("distance_km")
                self.test(
                    "Trip distance_km calculated correctly",
                    distance_km == 250.0,
                    f"Expected 250.0, got {distance_km}"
                )
                
                self.test(
                    "Trip distance_basis is 'odometer'",
                    trip.get("distance_basis") == "odometer",
                    f"Expected 'odometer', got {trip.get('distance_basis')}"
                )
                
                # Verify vehicle odometer updated
                try:
                    url = f"{self.base_url}/api/vehicles/{vehicle_id}"
                    response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                    if response.status_code == 200:
                        vehicle = response.json()
                        updated_odometer = float(vehicle.get("odometer", 0))
                        self.test(
                            "Vehicle odometer updated after checkout",
                            updated_odometer >= odometer_end,
                            f"Expected >= {odometer_end}, got {updated_odometer}"
                        )
                        self.log(f"Vehicle odometer updated to: {updated_odometer} km", "info")
                except Exception as e:
                    self.test("Vehicle odometer update verification", False, str(e))
                
                return True
        except Exception as e:
            self.test("POST /api/driver/checkout", False, str(e))
            return False
    
    def test_checkout_without_odometer(self):
        """Test checkout without odometer (fallback to OSRM or graceful handling)"""
        self.log("\n=== Testing Checkout Without Odometer (Fallback) ===", "info")
        
        # Get another task if available
        try:
            url = f"{self.base_url}/api/driver/tasks"
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            if response.status_code == 200:
                tasks = response.json()
                # Find a task that's not completed
                fallback_task = next((t for t in tasks if t.get("trip_status") in ("standby", "assigned", "to_pickup", "on_trip")), None)
                
                if not fallback_task:
                    self.log("No available task for fallback test, skipping", "warn")
                    return True  # Not a failure, just no task available
                
                trip_id = fallback_task.get("trip_id")
                
                # Checkin without odometer
                url = f"{self.base_url}/api/driver/checkin"
                payload = {"trip_id": trip_id}
                response = requests.post(url, json=payload, headers=self.headers("driver@demo.local"), timeout=10)
                
                self.test(
                    "POST /api/driver/checkin without odometer returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
                
                # Checkout without odometer
                url = f"{self.base_url}/api/driver/checkout"
                payload = {"trip_id": trip_id}
                response = requests.post(url, json=payload, headers=self.headers("driver@demo.local"), timeout=10)
                
                self.test(
                    "POST /api/driver/checkout without odometer returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}: {response.text if response.status_code != 200 else ''}"
                )
                
                if response.status_code == 200:
                    trip = response.json()
                    distance_basis = trip.get("distance_basis")
                    
                    # Should be 'osrm' if est_distance_km exists, or None if gracefully handled
                    self.test(
                        "Checkout without odometer handles gracefully",
                        distance_basis in ("osrm", None),
                        f"Expected 'osrm' or None, got {distance_basis}"
                    )
                    
                    if distance_basis == "osrm":
                        self.log("Fallback to OSRM estimate working", "pass")
                    else:
                        self.log("Graceful handling of missing odometer (distance_km=0)", "pass")
                
                return True
        except Exception as e:
            self.test("Checkout without odometer", False, str(e))
            return False
    
    def test_driver_performance(self):
        """Test GET /api/drivers/{driver_id}/performance"""
        self.log("\n=== Testing Driver Performance Endpoint ===", "info")
        
        # Get driver list
        try:
            url = f"{self.base_url}/api/drivers"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                drivers = response.json()
                if not drivers:
                    self.log("No drivers found", "warn")
                    return False
                
                driver = drivers[0]
                driver_id = driver.get("id")
                self.log(f"Testing performance for driver: {driver.get('name')} ({driver_id})", "info")
                
                # Test performance endpoint
                url = f"{self.base_url}/api/drivers/{driver_id}/performance"
                response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "GET /api/drivers/{id}/performance returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    self.test(
                        "Performance response has 'stats' field",
                        "stats" in data,
                        "Missing 'stats' field"
                    )
                    
                    self.test(
                        "Performance response has 'trips' field",
                        "trips" in data,
                        "Missing 'trips' field"
                    )
                    
                    if "stats" in data:
                        stats = data["stats"]
                        required_stats = ["total_trips", "completed", "completion_rate", "total_km", "total_revenue", "last_trip_at"]
                        for stat in required_stats:
                            self.test(
                                f"Stats has {stat} field",
                                stat in stats,
                                f"Missing {stat}"
                            )
                        
                        self.log(f"Driver stats: {stats.get('total_trips')} trips, {stats.get('total_km')} km, {stats.get('completion_rate')}% completion", "info")
                    
                    if "trips" in data:
                        trips = data["trips"]
                        self.test(
                            "Performance trips is a list",
                            isinstance(trips, list),
                            f"Expected list, got {type(trips)}"
                        )
                
                # Test non-existent driver (should return 404)
                url = f"{self.base_url}/api/drivers/drv_nonexistent/performance"
                response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "GET /api/drivers/{nonexistent}/performance returns 404",
                    response.status_code == 404,
                    f"Expected 404, got {response.status_code}"
                )
                
                return True
        except Exception as e:
            self.test("GET /api/drivers/{id}/performance", False, str(e))
            return False
    
    def test_vehicle_trips(self):
        """Test GET /api/vehicles/{vehicle_id}/trips"""
        self.log("\n=== Testing Vehicle Trips Endpoint ===", "info")
        
        # Get vehicle list
        try:
            url = f"{self.base_url}/api/vehicles"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                vehicles = response.json()
                if not vehicles:
                    self.log("No vehicles found", "warn")
                    return False
                
                vehicle = vehicles[0]
                vehicle_id = vehicle.get("id")
                self.log(f"Testing trips for vehicle: {vehicle.get('name')} ({vehicle_id})", "info")
                
                # Test vehicle trips endpoint
                url = f"{self.base_url}/api/vehicles/{vehicle_id}/trips"
                response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "GET /api/vehicles/{id}/trips returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    self.test(
                        "Vehicle trips response has 'totals' field",
                        "totals" in data,
                        "Missing 'totals' field"
                    )
                    
                    self.test(
                        "Vehicle trips response has 'trips' field",
                        "trips" in data,
                        "Missing 'trips' field"
                    )
                    
                    if "totals" in data:
                        totals = data["totals"]
                        required_totals = ["trips", "completed", "distance_km", "revenue"]
                        for total in required_totals:
                            self.test(
                                f"Totals has {total} field",
                                total in totals,
                                f"Missing {total}"
                            )
                        
                        self.log(f"Vehicle totals: {totals.get('trips')} trips, {totals.get('distance_km')} km, Rp {totals.get('revenue')}", "info")
                    
                    if "trips" in data:
                        trips = data["trips"]
                        self.test(
                            "Vehicle trips is a list",
                            isinstance(trips, list),
                            f"Expected list, got {type(trips)}"
                        )
                
                # Test non-existent vehicle (should return 404)
                url = f"{self.base_url}/api/vehicles/veh_nonexistent/trips"
                response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "GET /api/vehicles/{nonexistent}/trips returns 404",
                    response.status_code == 404,
                    f"Expected 404, got {response.status_code}"
                )
                
                return True
        except Exception as e:
            self.test("GET /api/vehicles/{id}/trips", False, str(e))
            return False
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*60, "info")
        self.log("Phase E9: Fleet↔Driver Trip/KM & Odometer Backend Tests", "info")
        self.log("="*60, "info")
        
        # Run tests in order
        if not self.test_auth():
            self.log("\n⚠️  Authentication failed. Cannot proceed with other tests.", "warn")
            return False
        
        # E9 specific tests
        self.test_driver_tasks()
        self.test_driver_odometer_flow()
        self.test_checkout_without_odometer()
        self.test_driver_performance()
        self.test_vehicle_trips()
        
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
    tester = E9TestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
