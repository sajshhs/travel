"""backend_rbac_test.py — E28 RBAC testing (calendar section + scope filtering).

Testing scope:
B1: Calendar endpoints - driver 403, owner/ops 200
B2: Scope filtering - driver sees only their bookings/drivers
B3: Anti over-block - driver workspace endpoints still work
B4: Regressions - owner/ops management features
B5: Error handling - no auth 401/403, invalid params no 5xx

Credentials:
- owner@demo.local / demo12345
- ops@demo.local / demo12345
- driver@demo.local / demo12345
"""
import requests
import sys

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

class RBACTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.token = None
        self.user = None
        self.failures = []

    def login(self, email, password):
        """Login and get token"""
        print(f"\n🔐 Logging in as {email}...")
        try:
            res = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password}, timeout=10)
            if res.status_code == 200:
                data = res.json()
                self.token = data.get("token")
                self.user = data.get("user", {})
                if self.token:
                    print(f"✅ Login successful - Role: {self.user.get('role')}, ID: {self.user.get('id')}")
                    return True
                else:
                    print(f"❌ Login failed - No token in response")
                    return False
            else:
                print(f"❌ Login failed - Status: {res.status_code}, Body: {res.text[:200]}")
                return False
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return False

    def test(self, name, method, endpoint, expected_status, data=None, params=None, check_fn=None, no_auth=False):
        """Run a single API test"""
        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        
        url = f"{BASE_URL}{endpoint}"
        if params:
            url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        
        req_headers = {'Content-Type': 'application/json'}
        if not no_auth and self.token:
            req_headers['Authorization'] = f'Bearer {self.token}'
        
        try:
            if method == 'GET':
                res = requests.get(url, headers=req_headers, timeout=10)
            elif method == 'POST':
                res = requests.post(url, json=data, headers=req_headers, timeout=10)
            elif method == 'PATCH':
                res = requests.patch(url, json=data, headers=req_headers, timeout=10)
            else:
                print(f"❌ Unsupported method: {method}")
                self.tests_failed += 1
                self.failures.append(f"{name}: Unsupported method {method}")
                return False, None

            # expected_status boleh:
            #   int          -> harus sama persis
            #   tuple/list   -> boleh salah satu (mis. (401, 403))
            #   None         -> status tidak dipatok; keputusan diserahkan ke check_fn
            #                   (dipakai kasus "401 ATAU 403" dan "apa pun asal bukan 5xx").
            # Sebelumnya None dibandingkan langsung dengan status code -> selalu FAIL
            # (3 false-positive di laporan iterasi 73).
            if expected_status is None:
                success = True
            elif isinstance(expected_status, (tuple, list, set)):
                success = res.status_code in expected_status
            else:
                success = res.status_code == expected_status
            response_data = None
            try:
                response_data = res.json()
            except Exception:
                pass

            if success:
                if check_fn:
                    check_result = check_fn(response_data, res)
                    if check_result is True:
                        self.tests_passed += 1
                        print(f"✅ PASS - Status: {res.status_code}")
                        return True, response_data
                    else:
                        self.tests_failed += 1
                        self.failures.append(f"{name}: {check_result}")
                        print(f"❌ FAIL - Status correct but validation failed: {check_result}")
                        return False, response_data
                else:
                    self.tests_passed += 1
                    print(f"✅ PASS - Status: {res.status_code}")
                    return True, response_data
            else:
                self.tests_failed += 1
                self.failures.append(f"{name}: Expected {expected_status}, got {res.status_code}")
                print(f"❌ FAIL - Expected {expected_status}, got {res.status_code}")
                if response_data:
                    print(f"   Response: {response_data}")
                return False, response_data

        except Exception as e:
            self.tests_failed += 1
            self.failures.append(f"{name}: Exception - {str(e)}")
            print(f"❌ FAIL - Exception: {str(e)}")
            return False, None

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print(f"📊 TEST SUMMARY")
        print("="*80)
        print(f"Total: {self.tests_run} | Passed: {self.tests_passed} | Failed: {self.tests_failed}")
        if self.failures:
            print(f"\n❌ FAILURES ({len(self.failures)}):")
            for i, failure in enumerate(self.failures, 1):
                print(f"  {i}. {failure}")
        print("="*80)
        return 0 if self.tests_failed == 0 else 1


def main():
    tester = RBACTester()
    
    # ========== B1: Calendar endpoints RBAC ==========
    print("\n" + "="*80)
    print("B1: CALENDAR ENDPOINTS - Driver 403, Owner/Ops 200")
    print("="*80)
    
    # B1.1: Driver should get 403 on calendar endpoints
    if not tester.login("driver@demo.local", "demo12345"):
        return 1
    
    tester.test(
        "B1.1a: Driver GET /api/departures/attention -> 403",
        "GET", "/departures/attention", 403,
        params={"month": "2026-08"}
    )
    
    tester.test(
        "B1.1b: Driver GET /api/bookings/calendar -> 403",
        "GET", "/bookings/calendar", 403,
        params={"month": "2026-08"}
    )
    
    tester.test(
        "B1.1c: Driver GET /api/bookings/calendar/export -> 403",
        "GET", "/bookings/calendar/export", 403,
        params={"month": "2026-08", "format": "excel"}
    )
    
    # B1.2: Owner should get 200 on calendar endpoints
    if not tester.login("owner@demo.local", "demo12345"):
        return 1
    
    tester.test(
        "B1.2a: Owner GET /api/departures/attention -> 200",
        "GET", "/departures/attention", 200,
        params={"month": "2026-08"},
        check_fn=lambda d, r: True if isinstance(d, dict) and "summary" in d else "Missing summary field"
    )
    
    tester.test(
        "B1.2b: Owner GET /api/bookings/calendar -> 200",
        "GET", "/bookings/calendar", 200,
        params={"month": "2026-08"},
        check_fn=lambda d, r: True if isinstance(d, list) else "Expected list response"
    )
    
    tester.test(
        "B1.2c: Owner GET /api/bookings/calendar/export (excel) -> 200",
        "GET", "/bookings/calendar/export", 200,
        params={"month": "2026-08", "format": "excel"},
        check_fn=lambda d, r: True if r.headers.get("content-type", "").startswith("application/vnd.openxmlformats") else f"Wrong content-type: {r.headers.get('content-type')}"
    )
    
    tester.test(
        "B1.2d: Owner GET /api/bookings/calendar/export (pdf) -> 200",
        "GET", "/bookings/calendar/export", 200,
        params={"month": "2026-08", "format": "pdf"},
        check_fn=lambda d, r: True if r.headers.get("content-type", "").startswith("application/pdf") else f"Wrong content-type: {r.headers.get('content-type')}"
    )
    
    # B1.3: Ops should get 200 on calendar endpoints
    if not tester.login("ops@demo.local", "demo12345"):
        return 1
    
    tester.test(
        "B1.3a: Ops GET /api/departures/attention -> 200",
        "GET", "/departures/attention", 200,
        params={"month": "2026-08"},
        check_fn=lambda d, r: True if isinstance(d, dict) and "summary" in d else "Missing summary field"
    )
    
    tester.test(
        "B1.3b: Ops GET /api/bookings/calendar -> 200",
        "GET", "/bookings/calendar", 200,
        params={"month": "2026-08"},
        check_fn=lambda d, r: True if isinstance(d, list) else "Expected list response"
    )
    
    tester.test(
        "B1.3c: Ops GET /api/bookings/calendar/export (excel) -> 200",
        "GET", "/bookings/calendar/export", 200,
        params={"month": "2026-08", "format": "excel"},
        check_fn=lambda d, r: True if r.headers.get("content-type", "").startswith("application/vnd.openxmlformats") else f"Wrong content-type: {r.headers.get('content-type')}"
    )
    
    # ========== B2: Scope filtering ==========
    print("\n" + "="*80)
    print("B2: SCOPE FILTERING - Driver sees only their data")
    print("="*80)
    
    # B2.1: Get owner's view first (baseline)
    if not tester.login("owner@demo.local", "demo12345"):
        return 1
    
    success, owner_bookings = tester.test(
        "B2.1a: Owner GET /api/bookings (baseline)",
        "GET", "/bookings", 200,
        check_fn=lambda d, r: True if isinstance(d, list) and len(d) > 0 else "Expected non-empty list"
    )
    owner_booking_count = len(owner_bookings) if owner_bookings else 0
    print(f"   Owner sees {owner_booking_count} bookings")
    
    success, owner_drivers = tester.test(
        "B2.1b: Owner GET /api/drivers (baseline)",
        "GET", "/drivers", 200,
        check_fn=lambda d, r: True if isinstance(d, list) and len(d) > 0 else "Expected non-empty list"
    )
    owner_driver_count = len(owner_drivers) if owner_drivers else 0
    print(f"   Owner sees {owner_driver_count} drivers")
    
    # B2.2: Driver should see only their bookings
    if not tester.login("driver@demo.local", "demo12345"):
        return 1
    
    success, driver_bookings = tester.test(
        "B2.2a: Driver GET /api/bookings (filtered)",
        "GET", "/bookings", 200,
        check_fn=lambda d, r: True if isinstance(d, list) else "Expected list response"
    )
    driver_booking_count = len(driver_bookings) if driver_bookings else 0
    print(f"   Driver sees {driver_booking_count} bookings")
    
    if driver_booking_count >= owner_booking_count:
        tester.tests_failed += 1
        tester.failures.append(f"B2.2a: Driver sees {driver_booking_count} bookings, should be less than owner's {owner_booking_count}")
        print(f"   ❌ SCOPE LEAK: Driver sees same or more bookings than owner!")
    else:
        print(f"   ✅ Scope filtering working: {driver_booking_count} < {owner_booking_count}")
    
    # B2.3: Driver should see only their profile
    success, driver_drivers = tester.test(
        "B2.3a: Driver GET /api/drivers (filtered)",
        "GET", "/drivers", 200,
        check_fn=lambda d, r: True if isinstance(d, list) and len(d) == 1 else f"Expected exactly 1 driver, got {len(d) if isinstance(d, list) else 'non-list'}"
    )
    
    # B2.4: Driver should get 403 on other driver's detail
    if owner_drivers and len(owner_drivers) >= 2:
        other_driver_id = None
        for drv in owner_drivers:
            if driver_drivers and len(driver_drivers) > 0:
                if drv.get("id") != driver_drivers[0].get("id"):
                    other_driver_id = drv.get("id")
                    break
        
        if other_driver_id:
            tester.test(
                f"B2.4a: Driver GET /api/drivers/{other_driver_id} -> 403",
                "GET", f"/drivers/{other_driver_id}", 403
            )
            
            tester.test(
                f"B2.4b: Driver GET /api/drivers/{other_driver_id}/performance -> 403",
                "GET", f"/drivers/{other_driver_id}/performance", 403
            )
    
    # B2.5: Driver should get 403 on other driver's booking
    if owner_bookings and driver_bookings:
        other_booking_id = None
        driver_booking_ids = {b.get("id") for b in driver_bookings}
        for bk in owner_bookings:
            if bk.get("id") not in driver_booking_ids:
                other_booking_id = bk.get("id")
                break
        
        if other_booking_id:
            tester.test(
                f"B2.5a: Driver GET /api/bookings/{other_booking_id} -> 403",
                "GET", f"/bookings/{other_booking_id}", 403
            )
    
    # ========== B3: Anti over-block ==========
    print("\n" + "="*80)
    print("B3: ANTI OVER-BLOCK - Driver workspace endpoints work")
    print("="*80)
    
    tester.test(
        "B3.1: Driver GET /api/driver/my-trips -> 200",
        "GET", "/driver/my-trips", 200,
        check_fn=lambda d, r: True if isinstance(d, list) else "Expected list response"
    )
    
    tester.test(
        "B3.2: Driver GET /api/driver/tasks -> 200",
        "GET", "/driver/tasks", 200,
        check_fn=lambda d, r: True if isinstance(d, list) else "Expected list response"
    )
    
    tester.test(
        "B3.3: Driver GET /api/driver/summary -> 200",
        "GET", "/driver/summary", 200,
        check_fn=lambda d, r: True if isinstance(d, dict) and "is_driver" in d else "Missing is_driver field"
    )
    
    # ========== B4: Regressions ==========
    print("\n" + "="*80)
    print("B4: REGRESSIONS - Owner/Ops management features")
    print("="*80)
    
    if not tester.login("owner@demo.local", "demo12345"):
        return 1
    
    tester.test(
        "B4.1: Owner GET /api/bookings (list) -> 200",
        "GET", "/bookings", 200,
        check_fn=lambda d, r: True if isinstance(d, list) else "Expected list response"
    )
    
    # Get a booking ID for detail test
    success, bookings = tester.test(
        "B4.2: Owner GET /api/bookings/{id} (detail) -> 200",
        "GET", "/bookings", 200
    )
    if bookings and len(bookings) > 0:
        booking_id = bookings[0].get("id")
        tester.test(
            f"B4.2b: Owner GET /api/bookings/{booking_id} -> 200",
            "GET", f"/bookings/{booking_id}", 200,
            check_fn=lambda d, r: True if isinstance(d, dict) and d.get("id") == booking_id else "Wrong booking returned"
        )
    
    tester.test(
        "B4.3: Owner GET /api/departures/attention (structure) -> 200",
        "GET", "/departures/attention", 200,
        params={"month": "2026-08"},
        check_fn=lambda d, r: (
            True if isinstance(d, dict) and "summary" in d and "items" in d and "meta" in d
            else f"Missing fields: summary={('summary' in d)}, items={('items' in d)}, meta={('meta' in d)}"
        )
    )
    
    tester.test(
        "B4.4: Owner GET /api/dispatch/today -> 200",
        "GET", "/dispatch/today", 200,
        check_fn=lambda d, r: True if isinstance(d, dict) else "Expected dict response"
    )
    
    # ========== B5: Error handling ==========
    print("\n" + "="*80)
    print("B5: ERROR HANDLING - Auth and invalid params")
    print("="*80)
    
    tester.test(
        "B5.1: No auth GET /api/departures/attention -> 401 or 403",
        "GET", "/departures/attention", None,
        params={"month": "2026-08"},
        no_auth=True,
        check_fn=lambda d, r: True if r.status_code in [401, 403] else f"Expected 401/403, got {r.status_code}"
    )
    
    if not tester.login("owner@demo.local", "demo12345"):
        return 1
    
    tester.test(
        "B5.2: Invalid month 'abcd' -> not 5xx",
        "GET", "/departures/attention", None,
        params={"month": "abcd"},
        check_fn=lambda d, r: True if r.status_code < 500 else f"Got 5xx: {r.status_code}"
    )
    
    tester.test(
        "B5.3: Invalid month '2026-13' -> not 5xx",
        "GET", "/departures/attention", None,
        params={"month": "2026-13"},
        check_fn=lambda d, r: True if r.status_code < 500 else f"Got 5xx: {r.status_code}"
    )
    
    # Print summary
    return tester.print_summary()


if __name__ == "__main__":
    sys.exit(main())
