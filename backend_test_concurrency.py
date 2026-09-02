"""backend_test_concurrency.py — RC-16 CONCURRENCY FIX VERIFICATION (anti double-booking)

PRIMARY: Fire N parallel POST /api/bookings for SAME vehicle + SAME time window.
EXPECTED: EXACTLY 1 success, all others 400/409. NO double-booking in DB.
"""
import asyncio
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List, Dict, Any

import requests

# Public endpoint from frontend/.env
BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

# Test credentials
OWNER_EMAIL = "owner@demo.local"
OWNER_PASSWORD = "demo12345"

# Test window (far future to avoid conflicts with existing bookings)
TEST_START = "2028-02-10T08:00:00+00:00"
TEST_END = "2028-02-12T18:00:00+00:00"


class ConcurrencyTester:
    def __init__(self):
        self.token = None
        self.customer_id = None
        self.vehicle_id = None
        self.tests_passed = 0
        self.tests_run = 0
        
    def log(self, msg: str, level: str = "INFO"):
        """Log with timestamp"""
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{ts}] {level:5s} | {msg}")
    
    def test(self, name: str, condition: bool, details: str = ""):
        """Record test result"""
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            self.log(f"✅ PASS: {name}", "PASS")
            if details:
                self.log(f"       {details}", "INFO")
        else:
            self.log(f"❌ FAIL: {name}", "FAIL")
            if details:
                self.log(f"       {details}", "ERROR")
        return condition
    
    def login(self) -> bool:
        """Login and get token"""
        self.log("Logging in as owner@demo.local...")
        try:
            resp = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("token")
                if self.token:
                    self.log(f"Login successful, token: {self.token[:20]}...")
                    return True
            self.log(f"Login failed: {resp.status_code} {resp.text}", "ERROR")
            return False
        except Exception as e:
            self.log(f"Login exception: {e}", "ERROR")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get auth headers"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def setup_test_data(self) -> bool:
        """Get customer and available vehicle"""
        self.log("Setting up test data...")
        
        # Get first customer
        try:
            resp = requests.get(f"{BASE_URL}/customers", headers=self.get_headers(), timeout=10)
            if resp.status_code == 200:
                customers = resp.json()
                if customers and len(customers) > 0:
                    self.customer_id = customers[0]["id"]
                    self.log(f"Using customer: {customers[0].get('name')} ({self.customer_id})")
                else:
                    self.log("No customers found", "ERROR")
                    return False
            else:
                self.log(f"Failed to get customers: {resp.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Exception getting customers: {e}", "ERROR")
            return False
        
        # Get available vehicle
        try:
            resp = requests.get(f"{BASE_URL}/vehicles", headers=self.get_headers(), timeout=10)
            if resp.status_code == 200:
                vehicles = resp.json()
                # Find an available vehicle
                for v in vehicles:
                    if v.get("status") == "available":
                        self.vehicle_id = v["id"]
                        self.log(f"Using vehicle: {v.get('name')} ({self.vehicle_id})")
                        return True
                self.log("No available vehicles found", "ERROR")
                return False
            else:
                self.log(f"Failed to get vehicles: {resp.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Exception getting vehicles: {e}", "ERROR")
            return False
    
    def create_booking_sync(self, idx: int) -> Dict[str, Any]:
        """Create booking (synchronous for ThreadPoolExecutor)"""
        try:
            payload = {
                "customer_id": self.customer_id,
                "vehicle_id": self.vehicle_id,
                "start_datetime": TEST_START,
                "end_datetime": TEST_END,
                "origin": f"Test Origin {idx}",
                "destination": f"Test Destination {idx}",
                "base_price": 1000000,
                "notes": f"Concurrency test #{idx}"
            }
            resp = requests.post(
                f"{BASE_URL}/bookings",
                json=payload,
                headers=self.get_headers(),
                timeout=15
            )
            return {
                "idx": idx,
                "status": resp.status_code,
                "success": resp.status_code in [200, 201],
                "data": resp.json() if resp.status_code in [200, 201] else None,
                "error": resp.text if resp.status_code not in [200, 201] else None
            }
        except Exception as e:
            return {
                "idx": idx,
                "status": 0,
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def test_parallel_bookings(self, n: int = 16) -> bool:
        """PRIMARY TEST: Fire N parallel bookings for same vehicle+window"""
        self.log(f"\n{'='*70}")
        self.log(f"PRIMARY TEST: {n} PARALLEL BOOKINGS (same vehicle + time)")
        self.log(f"{'='*70}")
        self.log(f"Vehicle: {self.vehicle_id}")
        self.log(f"Window: {TEST_START} to {TEST_END}")
        self.log(f"Firing {n} parallel requests...")
        
        start_time = time.time()
        
        # Use ThreadPoolExecutor for TRUE parallelism
        with ThreadPoolExecutor(max_workers=n) as executor:
            results = list(executor.map(self.create_booking_sync, range(1, n + 1)))
        
        elapsed = time.time() - start_time
        self.log(f"All {n} requests completed in {elapsed:.2f}s")
        
        # Analyze results
        successes = [r for r in results if r["success"]]
        failures_400 = [r for r in results if r["status"] == 400]
        failures_409 = [r for r in results if r["status"] == 409]
        other_failures = [r for r in results if not r["success"] and r["status"] not in [400, 409]]
        
        self.log(f"\nResults breakdown:")
        self.log(f"  ✅ Success (2xx):     {len(successes)}")
        self.log(f"  ❌ Conflict (400):    {len(failures_400)}")
        self.log(f"  ⏳ Busy (409):        {len(failures_409)}")
        self.log(f"  ⚠️  Other failures:   {len(other_failures)}")
        
        # Show sample errors
        if failures_400:
            sample = failures_400[0]
            self.log(f"  Sample 400 error: {sample['error'][:100]}")
        if failures_409:
            sample = failures_409[0]
            self.log(f"  Sample 409 error: {sample['error'][:100]}")
        
        # CRITICAL CHECK 1: Exactly 1 success
        test1 = self.test(
            "Exactly 1 request succeeded",
            len(successes) == 1,
            f"Expected 1, got {len(successes)}"
        )
        
        # CRITICAL CHECK 2: All others rejected (400 or 409)
        expected_failures = n - 1
        actual_failures = len(failures_400) + len(failures_409)
        test2 = self.test(
            "All other requests rejected (400/409)",
            actual_failures == expected_failures,
            f"Expected {expected_failures}, got {actual_failures}"
        )
        
        # CRITICAL CHECK 3: Verify DB has exactly 1 overlapping booking
        if successes:
            time.sleep(1)  # Let DB settle
            try:
                resp = requests.get(
                    f"{BASE_URL}/bookings",
                    params={"vehicle_id": self.vehicle_id},
                    headers=self.get_headers(),
                    timeout=10
                )
                if resp.status_code == 200:
                    bookings = resp.json()
                    # Count active bookings overlapping our test window
                    overlapping = []
                    for b in bookings:
                        if b.get("status") in ["hold", "confirmed", "ongoing"]:
                            b_start = b.get("start_datetime", "")
                            b_end = b.get("end_datetime", "")
                            # Simple overlap check
                            if b_start and b_end:
                                if (b_start < TEST_END and b_end > TEST_START):
                                    overlapping.append(b)
                    
                    self.log(f"\nDB verification:")
                    self.log(f"  Total bookings for vehicle: {len(bookings)}")
                    self.log(f"  Active overlapping bookings: {len(overlapping)}")
                    
                    if overlapping:
                        for b in overlapping:
                            self.log(f"    - {b.get('code')} ({b.get('status')}): {b.get('start_datetime')} to {b.get('end_datetime')}")
                    
                    test3 = self.test(
                        "DB has EXACTLY 1 overlapping active booking",
                        len(overlapping) == 1,
                        f"Expected 1, found {len(overlapping)} (DOUBLE-BOOKING!)" if len(overlapping) > 1 else ""
                    )
                    
                    return test1 and test2 and test3
                else:
                    self.log(f"Failed to verify DB: {resp.status_code}", "ERROR")
                    return False
            except Exception as e:
                self.log(f"Exception verifying DB: {e}", "ERROR")
                return False
        
        return test1 and test2
    
    def test_group_booking_concurrency(self) -> bool:
        """Test parallel group bookings with same vehicle"""
        self.log(f"\n{'='*70}")
        self.log("GROUP BOOKING CONCURRENCY TEST")
        self.log(f"{'='*70}")
        
        # Create 4 parallel group booking requests, each with 1 unit for same vehicle+window
        def create_group_sync(idx: int) -> Dict[str, Any]:
            try:
                payload = {
                    "customer_id": self.customer_id,
                    "units": [
                        {
                            "vehicle_id": self.vehicle_id,
                            "start_datetime": "2028-03-10T08:00:00+00:00",
                            "end_datetime": "2028-03-12T18:00:00+00:00",
                            "origin": f"Group Origin {idx}",
                            "destination": f"Group Dest {idx}",
                            "base_price": 1000000
                        }
                    ],
                    "note": f"Group concurrency test {idx}"
                }
                resp = requests.post(
                    f"{BASE_URL}/bookings/group",
                    json=payload,
                    headers=self.get_headers(),
                    timeout=15
                )
                return {
                    "idx": idx,
                    "status": resp.status_code,
                    "success": resp.status_code in [200, 201],
                    "error": resp.text if resp.status_code not in [200, 201] else None
                }
            except Exception as e:
                return {"idx": idx, "status": 0, "success": False, "error": str(e)}
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(create_group_sync, range(1, 5)))
        
        successes = [r for r in results if r["success"]]
        failures = [r for r in results if not r["success"]]
        
        self.log(f"Results: {len(successes)} success, {len(failures)} rejected")
        
        return self.test(
            "At most 1 group booking succeeded",
            len(successes) <= 1,
            f"Expected ≤1, got {len(successes)}"
        )
    
    def test_single_booking_regression(self) -> bool:
        """REGRESSION: Single booking on available vehicle works"""
        self.log(f"\n{'='*70}")
        self.log("REGRESSION: Single booking")
        self.log(f"{'='*70}")
        
        try:
            payload = {
                "customer_id": self.customer_id,
                "vehicle_id": self.vehicle_id,
                "start_datetime": "2028-04-10T08:00:00+00:00",
                "end_datetime": "2028-04-12T18:00:00+00:00",
                "origin": "Single Test Origin",
                "destination": "Single Test Dest",
                "base_price": 1000000,
                "notes": "Single booking regression test"
            }
            resp = requests.post(
                f"{BASE_URL}/bookings",
                json=payload,
                headers=self.get_headers(),
                timeout=10
            )
            
            success = resp.status_code in [200, 201]
            booking_id = None
            if success:
                booking_id = resp.json().get("id")
            
            test1 = self.test(
                "Single booking succeeds",
                success,
                f"Status: {resp.status_code}"
            )
            
            # Try overlapping booking (should fail)
            if booking_id:
                payload2 = {
                    "customer_id": self.customer_id,
                    "vehicle_id": self.vehicle_id,
                    "start_datetime": "2028-04-11T08:00:00+00:00",  # Overlaps
                    "end_datetime": "2028-04-13T18:00:00+00:00",
                    "origin": "Overlap Test",
                    "destination": "Overlap Dest",
                    "base_price": 1000000
                }
                resp2 = requests.post(
                    f"{BASE_URL}/bookings",
                    json=payload2,
                    headers=self.get_headers(),
                    timeout=10
                )
                
                test2 = self.test(
                    "Sequential overlapping booking rejected",
                    resp2.status_code == 400,
                    f"Status: {resp2.status_code}"
                )
                
                return test1 and test2
            
            return test1
            
        except Exception as e:
            self.log(f"Exception: {e}", "ERROR")
            return False
    
    def test_confirm_reschedule_regression(self) -> bool:
        """REGRESSION: Confirm and reschedule still work"""
        self.log(f"\n{'='*70}")
        self.log("REGRESSION: Confirm & Reschedule")
        self.log(f"{'='*70}")
        
        try:
            # Create a booking
            payload = {
                "customer_id": self.customer_id,
                "vehicle_id": self.vehicle_id,
                "start_datetime": "2028-05-10T08:00:00+00:00",
                "end_datetime": "2028-05-12T18:00:00+00:00",
                "origin": "Confirm Test",
                "destination": "Confirm Dest",
                "base_price": 1000000
            }
            resp = requests.post(
                f"{BASE_URL}/bookings",
                json=payload,
                headers=self.get_headers(),
                timeout=10
            )
            
            if resp.status_code not in [200, 201]:
                self.log(f"Failed to create booking: {resp.status_code}", "ERROR")
                return False
            
            booking_id = resp.json().get("id")
            self.log(f"Created booking: {booking_id}")
            
            # Confirm it
            resp = requests.post(
                f"{BASE_URL}/bookings/{booking_id}/confirm",
                headers=self.get_headers(),
                timeout=10
            )
            test1 = self.test(
                "Confirm booking works",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            # Reschedule to non-conflicting window
            resp = requests.post(
                f"{BASE_URL}/bookings/{booking_id}/reschedule",
                json={
                    "start_datetime": "2028-05-15T08:00:00+00:00",
                    "end_datetime": "2028-05-17T18:00:00+00:00"
                },
                headers=self.get_headers(),
                timeout=10
            )
            test2 = self.test(
                "Reschedule to non-conflicting window works",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            return test1 and test2
            
        except Exception as e:
            self.log(f"Exception: {e}", "ERROR")
            return False
    
    def test_lock_hygiene(self) -> bool:
        """LOCK HYGIENE: Subsequent bookings on different vehicles work"""
        self.log(f"\n{'='*70}")
        self.log("LOCK HYGIENE TEST")
        self.log(f"{'='*70}")
        
        try:
            # Get a different available vehicle
            resp = requests.get(f"{BASE_URL}/vehicles", headers=self.get_headers(), timeout=10)
            if resp.status_code != 200:
                self.log("Failed to get vehicles", "ERROR")
                return False
            
            vehicles = resp.json()
            other_vehicle = None
            for v in vehicles:
                if v.get("status") == "available" and v["id"] != self.vehicle_id:
                    other_vehicle = v
                    break
            
            if not other_vehicle:
                self.log("No other available vehicle found, skipping lock hygiene test", "WARN")
                return True  # Not a failure, just can't test
            
            self.log(f"Testing with different vehicle: {other_vehicle.get('name')}")
            
            # Create booking on different vehicle (should work quickly)
            start_time = time.time()
            payload = {
                "customer_id": self.customer_id,
                "vehicle_id": other_vehicle["id"],
                "start_datetime": "2028-06-10T08:00:00+00:00",
                "end_datetime": "2028-06-12T18:00:00+00:00",
                "origin": "Lock Hygiene Test",
                "destination": "Lock Hygiene Dest",
                "base_price": 1000000
            }
            resp = requests.post(
                f"{BASE_URL}/bookings",
                json=payload,
                headers=self.get_headers(),
                timeout=10
            )
            elapsed = time.time() - start_time
            
            test1 = self.test(
                "Booking on different vehicle succeeds",
                resp.status_code in [200, 201],
                f"Status: {resp.status_code}"
            )
            
            test2 = self.test(
                "Response time reasonable (no deadlock)",
                elapsed < 5.0,
                f"Took {elapsed:.2f}s"
            )
            
            return test1 and test2
            
        except Exception as e:
            self.log(f"Exception: {e}", "ERROR")
            return False
    
    def test_core_regression(self) -> bool:
        """REGRESSION: Core endpoints still work"""
        self.log(f"\n{'='*70}")
        self.log("CORE REGRESSION TEST")
        self.log(f"{'='*70}")
        
        tests = []
        
        # Dashboard
        try:
            resp = requests.get(f"{BASE_URL}/dashboard", headers=self.get_headers(), timeout=10)
            tests.append(self.test("Dashboard endpoint", resp.status_code == 200, f"Status: {resp.status_code}"))
        except Exception as e:
            self.log(f"Dashboard exception: {e}", "ERROR")
            tests.append(False)
        
        # List bookings
        try:
            resp = requests.get(f"{BASE_URL}/bookings", headers=self.get_headers(), timeout=10)
            tests.append(self.test("List bookings", resp.status_code == 200, f"Status: {resp.status_code}"))
        except Exception as e:
            self.log(f"List bookings exception: {e}", "ERROR")
            tests.append(False)
        
        return all(tests)
    
    def run_all_tests(self) -> int:
        """Run all tests and return exit code"""
        self.log("="*70)
        self.log("RC-16 CONCURRENCY FIX VERIFICATION")
        self.log("="*70)
        
        if not self.login():
            self.log("Login failed, cannot proceed", "ERROR")
            return 1
        
        if not self.setup_test_data():
            self.log("Setup failed, cannot proceed", "ERROR")
            return 1
        
        # Run tests
        self.test_parallel_bookings(16)  # PRIMARY TEST
        self.test_group_booking_concurrency()
        self.test_single_booking_regression()
        self.test_confirm_reschedule_regression()
        self.test_lock_hygiene()
        self.test_core_regression()
        
        # Summary
        self.log(f"\n{'='*70}")
        self.log(f"TEST SUMMARY")
        self.log(f"{'='*70}")
        self.log(f"Tests run:    {self.tests_run}")
        self.log(f"Tests passed: {self.tests_passed}")
        self.log(f"Tests failed: {self.tests_run - self.tests_passed}")
        
        if self.tests_passed == self.tests_run:
            self.log("\n🎉 ALL TESTS PASSED - CONCURRENCY FIX VERIFIED", "PASS")
            return 0
        else:
            self.log(f"\n❌ {self.tests_run - self.tests_passed} TEST(S) FAILED", "FAIL")
            return 1


if __name__ == "__main__":
    tester = ConcurrencyTester()
    sys.exit(tester.run_all_tests())
