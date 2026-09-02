#!/usr/bin/env python3
"""
Backend API quick check for Round 3 testing
Tests critical endpoints before frontend testing
"""
import requests
import sys
from datetime import datetime, timedelta

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

class QuickAPICheck:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tokens = {}
    
    def test(self, name, method, endpoint, expected_status, **kwargs):
        """Run a single API test"""
        url = f"{BASE_URL}/{endpoint}"
        print(f"\n🔍 {name}")
        try:
            if method == "GET":
                resp = requests.get(url, **kwargs)
            elif method == "POST":
                resp = requests.post(url, **kwargs)
            elif method == "PUT":
                resp = requests.put(url, **kwargs)
            elif method == "DELETE":
                resp = requests.delete(url, **kwargs)
            
            if resp.status_code == expected_status:
                print(f"✅ PASS - Status {resp.status_code}")
                self.passed += 1
                return True, resp
            else:
                print(f"❌ FAIL - Expected {expected_status}, got {resp.status_code}")
                print(f"   Response: {resp.text[:200]}")
                self.failed += 1
                return False, resp
        except Exception as e:
            print(f"❌ ERROR - {str(e)}")
            self.failed += 1
            return False, None
    
    def login(self, email, password):
        """Login and store token"""
        success, resp = self.test(
            f"Login as {email}",
            "POST",
            "auth/login",
            200,
            json={"email": email, "password": password}
        )
        if success and resp:
            data = resp.json()
            self.tokens[email] = data.get("access_token")
            return True
        return False
    
    def headers(self, email):
        """Get auth headers for user"""
        return {"Authorization": f"Bearer {self.tokens.get(email, '')}"}

def main():
    checker = QuickAPICheck()
    
    print("=" * 60)
    print("ROUND 3 - Backend API Quick Check")
    print("=" * 60)
    
    # Test 1: Public booking config
    checker.test(
        "GET /public/booking/config",
        "GET",
        "public/booking/config",
        200
    )
    
    # Test 2: Login as owner
    if not checker.login("owner@demo.local", "demo12345"):
        print("\n❌ CRITICAL: Owner login failed, stopping tests")
        return 1
    
    # Test 3: Login as ops
    checker.login("ops@demo.local", "demo12345")
    
    # Test 4: Login as driver
    checker.login("driver@demo.local", "demo12345")
    
    # Test 5: Get vehicles (owner)
    checker.test(
        "GET /vehicles (owner)",
        "GET",
        "vehicles",
        200,
        headers=checker.headers("owner@demo.local")
    )
    
    # Test 6: Get bookings (owner)
    checker.test(
        "GET /bookings (owner)",
        "GET",
        "bookings",
        200,
        headers=checker.headers("owner@demo.local")
    )
    
    # Test 7: Get settings (owner)
    checker.test(
        "GET /settings (owner)",
        "GET",
        "settings",
        200,
        headers=checker.headers("owner@demo.local")
    )
    
    # Test 8: Get promos (public)
    checker.test(
        "GET /public/promos",
        "GET",
        "public/promos",
        200
    )
    
    # Test 9: Search units (future date)
    future_date = datetime.now() + timedelta(days=25)
    start = future_date.replace(hour=8, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=2)
    
    checker.test(
        "POST /public/booking/search (25 days ahead)",
        "POST",
        "public/booking/search",
        200,
        json={
            "service": "daily_rental",
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "pax": 10,
            "vehicle_type": "hiace_premio",
            "origin": "Bandung",
            "destination": "Yogyakarta"
        }
    )
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {checker.passed} passed, {checker.failed} failed")
    print("=" * 60)
    
    if checker.failed > 0:
        print("\n⚠️  Some backend APIs are failing. Frontend tests may be affected.")
        return 1
    else:
        print("\n✅ All backend APIs working. Proceeding to frontend tests.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
