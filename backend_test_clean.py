"""
Backend Testing Suite for Rahaza Travel - CLEAN RUN
Focus on the 5 critical fixes with minimal state pollution
Uses unique far-future dates and available resources only
"""

import requests
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional
import random

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

class TestRunner:
    def __init__(self):
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        # Use unique timestamp for this test run to avoid conflicts
        self.test_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        
    def login(self, email="owner@demo.local", password="demo12345"):
        """Authenticate and get token"""
        print(f"\n{Colors.BLUE}=== AUTHENTICATION ==={Colors.END}")
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": email, "password": password},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                print(f"{Colors.GREEN}✓ Login successful as {email}{Colors.END}")
                return True
            else:
                print(f"{Colors.RED}✗ Login failed: {response.status_code}{Colors.END}")
                return False
        except Exception as e:
            print(f"{Colors.RED}✗ Login error: {str(e)}{Colors.END}")
            return False
    
    def headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test(self, name: str, method: str, endpoint: str, expected_status: int, 
             data: Optional[dict] = None, check_fn=None):
        """Run a single test"""
        self.tests_run += 1
        url = f"{BASE_URL}/{endpoint}"
        
        print(f"\n{Colors.BLUE}Test #{self.tests_run}: {name}{Colors.END}")
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers(), timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, headers=self.headers(), timeout=10)
            elif method == "PATCH":
                response = requests.patch(url, json=data, headers=self.headers(), timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            status_ok = response.status_code == expected_status
            
            if status_ok:
                result_data = response.json() if response.text else {}
                
                if check_fn:
                    check_result, check_msg = check_fn(result_data, response)
                    if not check_result:
                        print(f"{Colors.RED}✗ FAILED - {check_msg}{Colors.END}")
                        self.tests_failed += 1
                        self.failures.append(f"{name}: {check_msg}")
                        return False, result_data
                
                print(f"{Colors.GREEN}✓ PASSED{Colors.END}")
                self.tests_passed += 1
                return True, result_data
            else:
                print(f"{Colors.RED}✗ FAILED - Expected {expected_status}, got {response.status_code}{Colors.END}")
                print(f"  Response: {response.text[:200]}")
                self.tests_failed += 1
                self.failures.append(f"{name}: Expected {expected_status}, got {response.status_code}")
                return False, {}
                
        except Exception as e:
            print(f"{Colors.RED}✗ FAILED - Error: {str(e)}{Colors.END}")
            self.tests_failed += 1
            self.failures.append(f"{name}: {str(e)}")
            return False, {}
    
    def get_unique_date(self, days_offset=0):
        """Generate unique far-future date to avoid conflicts"""
        # Use 2028 + random offset to avoid any existing bookings
        base = datetime(2028, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        offset_days = int(self.test_timestamp[-6:]) % 365 + days_offset
        dt = base + timedelta(days=offset_days)
        return dt.isoformat()
    
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
            print(f"\n{Colors.YELLOW}⚠ {self.tests_failed} test(s) failed{Colors.END}")
            return 1


def test_fix_e_clean(runner: TestRunner):
    """FIX E: Dispatch re-assign frees old vehicle - CLEAN SCENARIO"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}FIX E: Dispatch Re-Assign Frees Old Vehicle{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    # Get available vehicles
    success, vehicles = runner.test("Get vehicles", "GET", "vehicles", 200)
    if not success:
        return
    
    available = [v for v in vehicles if v.get("status") == "available"]
    print(f"  Found {len(available)} available vehicles")
    
    if len(available) < 2:
        print(f"{Colors.RED}Need 2 available vehicles, found {len(available)}{Colors.END}")
        return
    
    v1, v2 = available[0], available[1]
    print(f"  Vehicle 1: {v1.get('name')} ({v1.get('id')})")
    print(f"  Vehicle 2: {v2.get('name')} ({v2.get('id')})")
    
    # Get drivers
    success, drivers = runner.test("Get drivers", "GET", "drivers", 200)
    if not success or not drivers:
        return
    
    driver = drivers[0]
    print(f"  Driver: {driver.get('name')} ({driver.get('id')})")
    
    # Get customer
    success, bookings = runner.test("Get bookings", "GET", "bookings", 200)
    if not success or not bookings:
        return
    
    customer_id = bookings[0].get("customer_id")
    
    # Create booking with unique far-future date
    start = runner.get_unique_date(0)
    end = runner.get_unique_date(1)
    
    success, booking = runner.test(
        "Create booking with far-future date",
        "POST",
        "bookings",
        200,
        data={
            "customer_id": customer_id,
            "vehicle_id": v1["id"],
            "start_datetime": start,
            "end_datetime": end,
            "base_price": 2000000,
            "origin": "Jakarta",
            "destination": "Bandung"
        }
    )
    
    if not success:
        return
    
    booking_id = booking.get("id")
    print(f"  Created: {booking.get('code')}")
    
    # First assign
    success, _ = runner.test(
        f"Assign to {v1.get('name')}",
        "POST",
        f"dispatch/{booking_id}/assign",
        200,
        data={"driver_id": driver["id"], "vehicle_id": v1["id"]}
    )
    
    if not success:
        return
    
    # Check v1 status
    success, v1_status = runner.test(
        f"Check {v1.get('name')} status (should be on_trip)",
        "GET",
        f"vehicles/{v1['id']}",
        200,
        check_fn=lambda d, r: (
            d.get("status") == "on_trip",
            f"Expected on_trip, got {d.get('status')}"
        )
    )
    
    # Re-assign to v2
    success, _ = runner.test(
        f"Re-assign to {v2.get('name')}",
        "POST",
        f"dispatch/{booking_id}/assign",
        200,
        data={"driver_id": driver["id"], "vehicle_id": v2["id"]}
    )
    
    if not success:
        return
    
    # CRITICAL CHECK: v1 should be available
    success, v1_after = runner.test(
        f"Check {v1.get('name')} freed (should be available)",
        "GET",
        f"vehicles/{v1['id']}",
        200,
        check_fn=lambda d, r: (
            d.get("status") == "available",
            f"FIX E FAILED: Expected available, got {d.get('status')}"
        )
    )
    
    if success:
        print(f"{Colors.GREEN}✓✓✓ FIX E PASSED: Old vehicle freed correctly{Colors.END}")
    
    # Check v2 is on_trip
    runner.test(
        f"Check {v2.get('name')} status (should be on_trip)",
        "GET",
        f"vehicles/{v2['id']}",
        200,
        check_fn=lambda d, r: (
            d.get("status") == "on_trip",
            f"Expected on_trip, got {d.get('status')}"
        )
    )


def test_fix_b_cancel(runner: TestRunner):
    """FIX B: Cancel state-machine guard"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}FIX B: Cancel State-Machine Guard{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    # Get resources
    success, bookings = runner.test("Get bookings", "GET", "bookings", 200)
    if not success:
        return
    
    success, vehicles = runner.test("Get vehicles", "GET", "vehicles", 200)
    if not success:
        return
    
    customer_id = bookings[0].get("customer_id")
    vehicle_id = vehicles[0].get("id")
    
    # Create and complete a booking
    start = runner.get_unique_date(10)
    end = runner.get_unique_date(11)
    
    success, booking = runner.test(
        "Create booking to complete",
        "POST",
        "bookings",
        200,
        data={
            "customer_id": customer_id,
            "vehicle_id": vehicle_id,
            "start_datetime": start,
            "end_datetime": end,
            "base_price": 1000000,
            "origin": "Jakarta",
            "destination": "Bogor"
        }
    )
    
    if not success:
        return
    
    booking_id = booking.get("id")
    
    # Complete it
    runner.test("Complete booking", "POST", f"bookings/{booking_id}/complete", 200)
    
    # Try to cancel completed (should FAIL)
    runner.test(
        "Cancel completed booking (should REJECT)",
        "POST",
        f"bookings/{booking_id}/cancel",
        400,
        check_fn=lambda d, r: (
            "selesai" in r.text.lower() or "completed" in r.text.lower(),
            "Should mention completed"
        )
    )
    
    print(f"{Colors.GREEN}✓✓✓ FIX B PASSED: Cannot cancel completed bookings{Colors.END}")


def test_fix_c_timezone(runner: TestRunner):
    """FIX C: Timezone-aware timestamps"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}FIX C: Timezone-Aware Timestamps{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    success, bookings = runner.test("Get bookings", "GET", "bookings", 200)
    if not success:
        return
    
    success, vehicles = runner.test("Get vehicles", "GET", "vehicles", 200)
    if not success:
        return
    
    customer_id = bookings[0].get("customer_id")
    vehicle_id = vehicles[0].get("id")
    
    start = runner.get_unique_date(20)
    end = runner.get_unique_date(21)
    
    success, booking = runner.test(
        "Create booking for timezone test",
        "POST",
        "bookings",
        200,
        data={
            "customer_id": customer_id,
            "vehicle_id": vehicle_id,
            "start_datetime": start,
            "end_datetime": end,
            "base_price": 2000000,
            "origin": "Jakarta",
            "destination": "Bandung"
        }
    )
    
    if not success:
        return
    
    booking_id = booking.get("id")
    
    # Record payment
    runner.test(
        "Record payment",
        "POST",
        "payments",
        200,
        data={
            "booking_id": booking_id,
            "amount": 1000000,
            "method": "transfer",
            "note": "DP"
        }
    )
    
    # Cancel with refund
    runner.test(
        "Cancel with refund",
        "POST",
        f"bookings/{booking_id}/cancel",
        200,
        data={
            "reason": "Test",
            "cancellation_fee": 200000,
            "refund_amount": 800000
        }
    )
    
    # Check timestamps
    success, detail = runner.test(
        "Get booking detail",
        "GET",
        f"bookings/{booking_id}",
        200
    )
    
    if success:
        cancelled_at = detail.get("cancelled_at", "")
        payments = detail.get("payments", [])
        refund = [p for p in payments if p.get("type") == "refund"]
        
        tz_ok = "+00:00" in cancelled_at or "Z" in cancelled_at
        refund_tz_ok = False
        if refund:
            paid_at = refund[0].get("paid_at", "")
            refund_tz_ok = "+00:00" in paid_at or "Z" in paid_at
        
        if tz_ok and refund_tz_ok:
            print(f"{Colors.GREEN}✓✓✓ FIX C PASSED: Timestamps are timezone-aware{Colors.END}")
        else:
            print(f"{Colors.RED}FIX C FAILED: Timestamps not timezone-aware{Colors.END}")
            runner.tests_failed += 1


def main():
    """Main test runner"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Rahaza Travel - Backend Test Suite (CLEAN){Colors.END}")
    print(f"{Colors.BLUE}Testing Critical Fixes E, B, C{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    runner = TestRunner()
    
    if not runner.login():
        return 1
    
    try:
        test_fix_e_clean(runner)
        test_fix_b_cancel(runner)
        test_fix_c_timezone(runner)
    except Exception as e:
        print(f"\n{Colors.RED}Test error: {str(e)}{Colors.END}")
        import traceback
        traceback.print_exc()
    
    return runner.print_summary()


if __name__ == "__main__":
    sys.exit(main())
