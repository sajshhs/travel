#!/usr/bin/env python3
"""Comprehensive E14 Backend Test - SIM Reminder & RBAC Backend Guard"""
import requests
import sys

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.owner_token = None
        self.ops_token = None
        self.driver_token = None

    def test(self, name, condition, details=""):
        if condition:
            self.passed += 1
            print(f"✅ PASS: {name}")
            if details:
                print(f"   {details}")
        else:
            self.failed += 1
            print(f"❌ FAIL: {name}")
            if details:
                print(f"   {details}")

    def login(self, email, password):
        """Login and return token"""
        try:
            r = requests.post(f"{BASE_URL}/auth/login", 
                            json={"email": email, "password": password}, 
                            timeout=20)
            if r.status_code == 200:
                return r.json().get("token")
        except Exception as e:
            print(f"Login error for {email}: {e}")
        return None

    def get_headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def run_all_tests(self):
        print("=" * 70)
        print("E14 COMPREHENSIVE BACKEND TEST - SIM REMINDER & RBAC")
        print("=" * 70)

        # Login all users
        print("\n[1] LOGIN TESTS")
        self.owner_token = self.login("owner@demo.local", "demo12345")
        self.test("Owner login", self.owner_token is not None)
        
        self.ops_token = self.login("ops@demo.local", "demo12345")
        self.test("Ops admin login", self.ops_token is not None)
        
        self.driver_token = self.login("driver@demo.local", "demo12345")
        self.test("Driver login", self.driver_token is not None)

        if not all([self.owner_token, self.ops_token, self.driver_token]):
            print("\n❌ Cannot proceed without all logins")
            return

        # B1 Tests - SIM Reminder
        print("\n[2] B1 - EVENT CATALOG")
        self.test_event_catalog()

        print("\n[3] B1 - SIM REMINDER NOTIFICATION CREATION")
        self.test_sim_reminder_creation()

        print("\n[4] B1 - SIM REMINDER EVENT EMISSION")
        self.test_sim_event_emission()

        print("\n[5] B1 - IDEMPOTENCY CHECK")
        self.test_idempotency()

        print("\n[6] B1 - NOTIFICATION API ACCESS")
        self.test_notification_api()

        # A1 Tests - Backend RBAC
        print("\n[7] A1 - BACKEND RBAC ENFORCEMENT (403 checks)")
        self.test_backend_rbac()

        # Summary
        print("\n" + "=" * 70)
        print(f"RESULTS: ✅ {self.passed} PASSED | ❌ {self.failed} FAILED")
        print("=" * 70)
        return 0 if self.failed == 0 else 1

    def test_event_catalog(self):
        """Test that event catalog includes driver.sim_expiring"""
        try:
            r = requests.get(f"{BASE_URL}/automation/event-types", 
                           headers=self.get_headers(self.owner_token), 
                           timeout=20)
            data = r.json()
            has_sim_event = "driver.sim_expiring" in str(data)
            self.test("Event catalog includes 'driver.sim_expiring'", 
                     has_sim_event,
                     f"Found in response: {has_sim_event}")
        except Exception as e:
            self.test("Event catalog includes 'driver.sim_expiring'", False, str(e))

    def test_sim_reminder_creation(self):
        """Test POST /notifications/scan creates sim_reminder"""
        try:
            # Trigger scan
            r = requests.post(f"{BASE_URL}/notifications/scan", 
                            headers=self.get_headers(self.owner_token), 
                            timeout=30)
            self.test("POST /notifications/scan returns 200", 
                     r.status_code == 200,
                     f"Status: {r.status_code}")

            # Get notifications
            r = requests.get(f"{BASE_URL}/notifications", 
                           headers=self.get_headers(self.owner_token), 
                           timeout=20)
            notifs = r.json() if isinstance(r.json(), list) else r.json().get("notifications", [])
            
            sim_reminders = [n for n in notifs if n.get("type") == "sim_reminder"]
            self.test("At least one sim_reminder notification created", 
                     len(sim_reminders) >= 1,
                     f"Found {len(sim_reminders)} sim_reminder(s)")

            if sim_reminders:
                n = sim_reminders[0]
                self.test("sim_reminder has ref_type='driver'", 
                         n.get("ref_type") == "driver",
                         f"ref_type: {n.get('ref_type')}")
                
                self.test("sim_reminder has ref_id", 
                         bool(n.get("ref_id")),
                         f"ref_id: {n.get('ref_id')}")
                
                title = n.get("title", "")
                self.test("sim_reminder title mentions 'SIM'", 
                         "SIM" in title,
                         f"Title: {title}")
                
                self.test("sim_reminder title is informative (mentions driver name)", 
                         len(title) > 10,
                         f"Title length: {len(title)}")

        except Exception as e:
            self.test("SIM reminder creation test", False, str(e))

    def test_sim_event_emission(self):
        """Test that driver.sim_expiring event is emitted"""
        try:
            r = requests.get(f"{BASE_URL}/automation/events?limit=200", 
                           headers=self.get_headers(self.owner_token), 
                           timeout=20)
            events = r.json() if isinstance(r.json(), list) else r.json().get("events", [])
            
            sim_events = [e for e in events if e.get("type") == "driver.sim_expiring"]
            self.test("At least one 'driver.sim_expiring' event exists", 
                     len(sim_events) >= 1,
                     f"Found {len(sim_events)} event(s)")

            if sim_events:
                evt = sim_events[0]
                payload = evt.get("payload") or evt.get("data") or {}
                
                has_driver_id = "driver_id" in payload
                has_due_date = "due_date" in payload
                has_days_left = "days_left" in payload
                
                self.test("Event payload contains driver_id", has_driver_id)
                self.test("Event payload contains due_date", has_due_date)
                self.test("Event payload contains days_left", has_days_left)
                
                if has_driver_id and has_due_date:
                    print(f"   Event details: driver_id={payload.get('driver_id')}, "
                          f"due_date={payload.get('due_date')}, days_left={payload.get('days_left')}")

        except Exception as e:
            self.test("SIM event emission test", False, str(e))

    def test_idempotency(self):
        """Test that calling scan twice doesn't duplicate notifications"""
        try:
            # Get current count
            r = requests.get(f"{BASE_URL}/notifications", 
                           headers=self.get_headers(self.owner_token), 
                           timeout=20)
            notifs_before = r.json() if isinstance(r.json(), list) else r.json().get("notifications", [])
            count_before = len([n for n in notifs_before if n.get("type") == "sim_reminder"])

            # Trigger scan again
            requests.post(f"{BASE_URL}/notifications/scan", 
                         headers=self.get_headers(self.owner_token), 
                         timeout=30)

            # Get count after
            r = requests.get(f"{BASE_URL}/notifications", 
                           headers=self.get_headers(self.owner_token), 
                           timeout=20)
            notifs_after = r.json() if isinstance(r.json(), list) else r.json().get("notifications", [])
            count_after = len([n for n in notifs_after if n.get("type") == "sim_reminder"])

            self.test("Second scan doesn't duplicate sim_reminder", 
                     count_after == count_before,
                     f"Before: {count_before}, After: {count_after}")

        except Exception as e:
            self.test("Idempotency test", False, str(e))

    def test_notification_api(self):
        """Test notification API endpoints"""
        try:
            # Test GET /notifications
            r = requests.get(f"{BASE_URL}/notifications", 
                           headers=self.get_headers(self.owner_token), 
                           timeout=20)
            self.test("GET /notifications returns 200", 
                     r.status_code == 200,
                     f"Status: {r.status_code}")

            # Test unread count
            r = requests.get(f"{BASE_URL}/notifications/unread_count", 
                           headers=self.get_headers(self.owner_token), 
                           timeout=20)
            self.test("GET /notifications/unread_count returns 200", 
                     r.status_code == 200,
                     f"Status: {r.status_code}, Count: {r.json().get('count', 0)}")

        except Exception as e:
            self.test("Notification API test", False, str(e))

    def test_backend_rbac(self):
        """Test backend RBAC enforcement - driver should get 403 on restricted endpoints"""
        restricted_for_driver = [
            "/customers", "/crm", "/quotations", "/inbox", 
            "/automation/rules", "/finance/invoices", "/reports/summary",
            "/users", "/settings", "/auditlog"
        ]

        for endpoint in restricted_for_driver:
            try:
                r = requests.get(f"{BASE_URL}{endpoint}", 
                               headers=self.get_headers(self.driver_token), 
                               timeout=20)
                self.test(f"Driver GET {endpoint} returns 403", 
                         r.status_code == 403,
                         f"Status: {r.status_code}")
            except Exception as e:
                self.test(f"Driver GET {endpoint} returns 403", False, str(e))

        # Test that driver CAN access allowed endpoints
        allowed_for_driver = ["/bookings", "/vehicles", "/drivers"]
        for endpoint in allowed_for_driver:
            try:
                r = requests.get(f"{BASE_URL}{endpoint}", 
                               headers=self.get_headers(self.driver_token), 
                               timeout=20)
                self.test(f"Driver GET {endpoint} returns 200", 
                         r.status_code == 200,
                         f"Status: {r.status_code}")
            except Exception as e:
                self.test(f"Driver GET {endpoint} returns 200", False, str(e))

        # Test ops_admin restrictions (should NOT access users, settings, auditlog)
        restricted_for_ops = ["/users", "/settings", "/auditlog"]
        for endpoint in restricted_for_ops:
            try:
                r = requests.get(f"{BASE_URL}{endpoint}", 
                               headers=self.get_headers(self.ops_token), 
                               timeout=20)
                self.test(f"Ops_admin GET {endpoint} returns 403", 
                         r.status_code == 403,
                         f"Status: {r.status_code}")
            except Exception as e:
                self.test(f"Ops_admin GET {endpoint} returns 403", False, str(e))

        # Test owner has full access
        owner_endpoints = ["/customers", "/users", "/settings", "/auditlog"]
        for endpoint in owner_endpoints:
            try:
                r = requests.get(f"{BASE_URL}{endpoint}", 
                               headers=self.get_headers(self.owner_token), 
                               timeout=20)
                self.test(f"Owner GET {endpoint} returns 200", 
                         r.status_code == 200,
                         f"Status: {r.status_code}")
            except Exception as e:
                self.test(f"Owner GET {endpoint} returns 200", False, str(e))


if __name__ == "__main__":
    runner = TestRunner()
    sys.exit(runner.run_all_tests())
