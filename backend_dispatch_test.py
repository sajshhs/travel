"""
Backend API Test - ALUR E: Dispatch → Trip → Completion Flow
Tests the complete dispatch workflow from assignment to driver check-out
"""
import requests
import sys
from datetime import datetime, timedelta

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

class DispatchFlowTester:
    def __init__(self):
        self.token = None
        self.driver_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.test_data = {
            "booking_id": None,
            "booking_code": None,
            "trip_id": None,
            "driver_id": None,
            "vehicle_id": None,
            "odometer_start": None,
            "odometer_end": None
        }

    def login(self, email="ops@demo.local", password="demo12345"):
        """Login and get auth token"""
        print(f"\n🔐 Logging in as {email}...")
        try:
            response = requests.post(f"{BASE_URL}/auth/login", 
                                   json={"email": email, "password": password})
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token") or data.get("token")
                print(f"✅ Login successful - Token: {token[:20]}...")
                return token
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return None

    def headers(self, token=None):
        t = token or self.token
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {t}'
        }

    def test(self, name, method, endpoint, expected_status, data=None, token=None, check_fn=None):
        """Run a single API test"""
        url = f"{BASE_URL}/{endpoint}"
        self.tests_run += 1
        print(f"\n🔍 Test #{self.tests_run}: {name}")
        
        try:
            headers = self.headers(token)
            
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers)
            
            status_ok = response.status_code == expected_status
            
            # Get response data
            response_data = None
            try:
                response_data = response.json()
            except Exception:
                response_data = None
            
            # Run custom check function if provided
            check_ok = True
            check_msg = ""
            if status_ok and check_fn:
                check_ok, check_msg = check_fn(response_data)
            
            success = status_ok and check_ok
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASS - Status: {response.status_code}")
                if check_msg:
                    print(f"   ✓ {check_msg}")
            else:
                self.tests_failed += 1
                self.failures.append({
                    'test': name,
                    'expected': expected_status,
                    'got': response.status_code,
                    'response': response.text[:200],
                    'check_msg': check_msg if not check_ok else ""
                })
                print(f"❌ FAIL - Expected {expected_status}, got {response.status_code}")
                if not check_ok:
                    print(f"   ✗ Check failed: {check_msg}")
                print(f"   Response: {response.text[:300]}")
            
            return success, response_data
        
        except Exception as e:
            self.tests_failed += 1
            self.failures.append({
                'test': name,
                'error': str(e)
            })
            print(f"❌ ERROR: {str(e)}")
            return False, None

    def run_tests(self):
        print("\n" + "="*80)
        print("ALUR E: DISPATCH → TRIP → COMPLETION FLOW TEST")
        print("="*80)
        
        # Login as ops
        self.token = self.login("ops@demo.local", "demo12345")
        if not self.token:
            print("\n❌ Cannot proceed without ops login")
            return False
        
        # Login as driver
        self.driver_token = self.login("driver@demo.local", "demo12345")
        if not self.driver_token:
            print("\n❌ Cannot proceed without driver login")
            return False
        
        # E.1 - ASSIGN: Find confirmed booking and assign driver + vehicle
        print("\n" + "="*80)
        print("ALUR E.1 - ASSIGN DRIVER + VEHICLE")
        print("="*80)
        
        # Get list of bookings to find a confirmed one
        success, bookings = self.test(
            "E.1.1 - Get bookings list",
            "GET",
            "bookings",
            200,
            token=self.token,
            check_fn=lambda d: (isinstance(d, list), f"Found {len(d) if isinstance(d, list) else 0} bookings")
        )
        
        if not success or not bookings:
            print("\n❌ Cannot find bookings")
            return False
        
        # Find a confirmed booking (prefer BK-0001, BK-0002, BK-0005, or any confirmed)
        confirmed_booking = None
        for bk in bookings:
            if bk.get("status") == "confirmed":
                confirmed_booking = bk
                # Prefer specific booking codes if available
                if bk.get("code") in ["BK-0001", "BK-0002", "BK-0005"]:
                    break
        
        if not confirmed_booking:
            print("\n❌ No confirmed booking found. Please confirm a booking first.")
            return False
        
        self.test_data["booking_id"] = confirmed_booking["id"]
        self.test_data["booking_code"] = confirmed_booking.get("code")
        print(f"\n📋 Using booking: {self.test_data['booking_code']} (ID: {self.test_data['booking_id']})")
        
        # Get drivers list
        success, drivers = self.test(
            "E.1.2 - Get drivers list",
            "GET",
            "drivers",
            200,
            token=self.token,
            check_fn=lambda d: (isinstance(d, list) and len(d) > 0, f"Found {len(d) if isinstance(d, list) else 0} drivers")
        )
        
        if not success or not drivers:
            print("\n❌ Cannot find drivers")
            return False
        
        # Find driver linked to driver@demo.local account (Driver Satu)
        driver_for_test = None
        for drv in drivers:
            if drv.get("user_id"):  # Driver with user_id is linked to an account
                driver_for_test = drv
                break
        
        if not driver_for_test:
            # Fallback to first driver
            driver_for_test = drivers[0]
        
        self.test_data["driver_id"] = driver_for_test["id"]
        print(f"   Using driver: {driver_for_test.get('name')} (ID: {self.test_data['driver_id']})")
        
        # Get vehicles list
        success, vehicles = self.test(
            "E.1.3 - Get vehicles list",
            "GET",
            "vehicles",
            200,
            token=self.token,
            check_fn=lambda d: (isinstance(d, list) and len(d) > 0, f"Found {len(d) if isinstance(d, list) else 0} vehicles")
        )
        
        if not success or not vehicles:
            print("\n❌ Cannot find vehicles")
            return False
        
        # Use first available vehicle
        self.test_data["vehicle_id"] = vehicles[0]["id"]
        print(f"   Using vehicle: {vehicles[0].get('name')} (ID: {self.test_data['vehicle_id']})")
        
        # Assign driver + vehicle to booking
        success, assign_result = self.test(
            "E.1.4 - Assign driver + vehicle to booking",
            "POST",
            f"dispatch/{self.test_data['booking_id']}/assign",
            200,
            data={
                "driver_id": self.test_data["driver_id"],
                "vehicle_id": self.test_data["vehicle_id"]
            },
            token=self.token,
            check_fn=lambda d: (
                d and d.get("trip") and d["trip"].get("id"),
                f"Trip created: {d.get('trip', {}).get('id') if d else 'N/A'}"
            )
        )
        
        if not success or not assign_result:
            print("\n❌ Assignment failed")
            return False
        
        self.test_data["trip_id"] = assign_result["trip"]["id"]
        print(f"\n✅ Assignment successful - Trip ID: {self.test_data['trip_id']}")
        
        # E.2 - STATUS TRANSITIONS
        print("\n" + "="*80)
        print("ALUR E.2 - STATUS TRANSITIONS (CONFIRM → ENROUTE → ARRIVED)")
        print("="*80)
        
        # Confirm departure
        success, _ = self.test(
            "E.2.1 - Confirm departure",
            "POST",
            f"dispatch/{self.test_data['booking_id']}/confirm-departure",
            200,
            token=self.token,
            check_fn=lambda d: (
                d and d.get("booking") and d["booking"].get("departure_confirmed_at"),
                "Departure confirmed"
            )
        )
        
        if not success:
            print("\n⚠️  Departure confirmation failed, but continuing...")
        
        # Mark enroute
        success, _ = self.test(
            "E.2.2 - Mark trip as enroute",
            "POST",
            f"dispatch/trips/{self.test_data['trip_id']}/enroute",
            200,
            token=self.token,
            check_fn=lambda d: (
                d and d.get("status") == "to_pickup" and d.get("enroute_at"),
                "Trip marked as enroute"
            )
        )
        
        if not success:
            print("\n⚠️  Enroute transition failed, but continuing...")
        
        # Mark arrived
        success, _ = self.test(
            "E.2.3 - Mark trip as arrived",
            "POST",
            f"dispatch/trips/{self.test_data['trip_id']}/arrived",
            200,
            token=self.token,
            check_fn=lambda d: (
                d and d.get("arrived_at"),
                "Trip marked as arrived"
            )
        )
        
        if not success:
            print("\n⚠️  Arrived transition failed, but continuing...")
        
        # E.3 - DRIVER CHECK-IN/CHECK-OUT
        print("\n" + "="*80)
        print("ALUR E.3 - DRIVER CHECK-IN/CHECK-OUT WITH ODOMETER")
        print("="*80)
        
        # Get driver tasks
        success, tasks = self.test(
            "E.3.1 - Get driver tasks",
            "GET",
            "driver/tasks",
            200,
            token=self.driver_token,
            check_fn=lambda d: (
                isinstance(d, list),
                f"Driver has {len(d) if isinstance(d, list) else 0} tasks"
            )
        )
        
        if not success:
            print("\n⚠️  Cannot get driver tasks")
        
        # Check if our trip is in the driver's task list
        trip_found = False
        if tasks:
            for task in tasks:
                if task.get("trip_id") == self.test_data["trip_id"]:
                    trip_found = True
                    print(f"   ✓ Trip {self.test_data['trip_id']} found in driver's tasks")
                    break
        
        if not trip_found:
            print(f"\n⚠️  Trip {self.test_data['trip_id']} NOT found in driver's tasks")
            print(f"   This might be because the trip is assigned to a different driver.")
            print(f"   Driver tasks: {[t.get('trip_id') for t in (tasks or [])]}")
        
        # Driver check-in with odometer start
        self.test_data["odometer_start"] = 84000
        success, checkin_result = self.test(
            "E.3.2 - Driver check-in with odometer start",
            "POST",
            "driver/checkin",
            200,
            data={
                "trip_id": self.test_data["trip_id"],
                "odometer_start": self.test_data["odometer_start"]
            },
            token=self.driver_token,
            check_fn=lambda d: (
                d and d.get("odometer_start") == self.test_data["odometer_start"],
                f"Check-in successful with odometer: {self.test_data['odometer_start']} km"
            )
        )
        
        if not success:
            print("\n⚠️  Driver check-in failed")
        
        # Driver check-out with odometer end
        self.test_data["odometer_end"] = 84260
        expected_distance = self.test_data["odometer_end"] - self.test_data["odometer_start"]
        
        success, checkout_result = self.test(
            "E.3.3 - Driver check-out with odometer end",
            "POST",
            "driver/checkout",
            200,
            data={
                "trip_id": self.test_data["trip_id"],
                "odometer_end": self.test_data["odometer_end"]
            },
            token=self.driver_token,
            check_fn=lambda d: (
                d and d.get("status") == "completed" and d.get("distance_km") == expected_distance,
                f"Check-out successful - Distance: {d.get('distance_km') if d else 'N/A'} km (expected: {expected_distance} km)"
            )
        )
        
        if not success:
            print("\n⚠️  Driver check-out failed")
        else:
            print(f"\n✅ Trip completed successfully!")
            print(f"   Odometer start: {self.test_data['odometer_start']} km")
            print(f"   Odometer end: {self.test_data['odometer_end']} km")
            print(f"   Distance traveled: {expected_distance} km")
        
        # E.4 - POST-COMPLETION VERIFICATION
        print("\n" + "="*80)
        print("ALUR E.4 - POST-COMPLETION VERIFICATION")
        print("="*80)
        
        # Login as owner to check reports
        owner_token = self.login("owner@demo.local", "demo12345")
        if not owner_token:
            print("\n⚠️  Cannot login as owner for post-completion checks")
        else:
            # Check if booking is completed
            success, booking = self.test(
                "E.4.1 - Verify booking status is completed",
                "GET",
                f"bookings/{self.test_data['booking_id']}",
                200,
                token=owner_token,
                check_fn=lambda d: (
                    d and d.get("status") == "completed",
                    f"Booking status: {d.get('status') if d else 'N/A'}"
                )
            )
            
            # Check driver reports
            success, _ = self.test(
                "E.4.2 - Check driver reports page",
                "GET",
                "reports/drivers",
                200,
                token=owner_token,
                check_fn=lambda d: (
                    d and "drivers" in d,
                    "Driver reports accessible"
                )
            )
            
            # Check finance page
            success, _ = self.test(
                "E.4.3 - Check finance summary",
                "GET",
                "finance/summary",
                200,
                token=owner_token,
                check_fn=lambda d: (
                    d is not None,
                    "Finance summary accessible"
                )
            )
        
        # Print summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        print("\n" + "="*80)
        print("TEST DATA USED (for cleanup)")
        print("="*80)
        for key, value in self.test_data.items():
            print(f"{key}: {value}")
        
        if self.failures:
            print("\n" + "="*80)
            print("FAILED TESTS")
            print("="*80)
            for i, failure in enumerate(self.failures, 1):
                print(f"\n{i}. {failure.get('test')}")
                if 'error' in failure:
                    print(f"   Error: {failure['error']}")
                else:
                    print(f"   Expected: {failure.get('expected')}, Got: {failure.get('got')}")
                    if failure.get('check_msg'):
                        print(f"   Check: {failure['check_msg']}")
                    if failure.get('response'):
                        print(f"   Response: {failure['response']}")
        
        return self.tests_failed == 0

def main():
    tester = DispatchFlowTester()
    success = tester.run_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
