#!/usr/bin/env python3
"""backend_test_e13.py — E13 Driver Leaderboard + Revenue-per-Trip API Testing.

Tests:
1. GET /api/reports/drivers?period=YYYY-MM as owner → 200 with correct structure
2. Aggregate consistency (fleet totals match sum of drivers)
3. GET /api/reports/summary includes 'drivers_report' key
4. GET /api/reports/drivers/export?format=excel → xlsx file
5. GET /api/reports/drivers/export?format=pdf → PDF file
6. Period filter with old date (2020-01) → empty results
7. RBAC: driver token → 403 on all driver report endpoints
"""
import sys
import requests
from datetime import datetime

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com"

class E13APITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.owner_token = None
        self.ops_token = None
        self.driver_token = None
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, token=None, data=None, check_content_type=None, check_size=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                # Additional checks
                if check_content_type:
                    content_type = response.headers.get('content-type', '')
                    if check_content_type not in content_type:
                        print(f"❌ Failed - Expected content-type to contain '{check_content_type}', got '{content_type}'")
                        return False, {}
                
                if check_size:
                    size = len(response.content)
                    if size < check_size:
                        print(f"❌ Failed - Expected size > {check_size}, got {size}")
                        return False, {}
                
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                
                # Return JSON if possible
                if 'application/json' in response.headers.get('content-type', ''):
                    return True, response.json()
                return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.status_code >= 400:
                    try:
                        print(f"   Error: {response.json()}")
                    except:
                        print(f"   Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def login(self, email, password):
        """Login and get token"""
        print(f"\n🔐 Logging in as {email}...")
        success, response = self.run_test(
            f"Login {email}",
            "POST",
            "/api/auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'token' in response:
            print(f"✅ Login successful")
            return response['token']
        print(f"❌ Login failed")
        return None

    def test_drivers_report_structure(self):
        """Test 1: GET /api/reports/drivers structure"""
        print("\n" + "="*60)
        print("TEST 1: Driver Report Structure")
        print("="*60)
        
        success, data = self.run_test(
            "GET /api/reports/drivers",
            "GET",
            "/api/reports/drivers",
            200,
            token=self.owner_token
        )
        
        if not success:
            return False
        
        # Check top-level structure
        required_keys = ['period', 'fleet', 'drivers']
        for key in required_keys:
            if key in data:
                print(f"✅ Has key '{key}'")
                self.tests_passed += 1
            else:
                print(f"❌ Missing key '{key}'")
            self.tests_run += 1
        
        # Check fleet structure
        fleet = data.get('fleet', {})
        fleet_keys = ['trips', 'completed', 'completion_rate', 'km', 'revenue', 
                      'revenue_per_trip', 'avg_km_per_trip', 'active_drivers']
        print(f"\n📊 Fleet data: {fleet}")
        for key in fleet_keys:
            if key in fleet:
                print(f"✅ Fleet has '{key}': {fleet[key]}")
                self.tests_passed += 1
            else:
                print(f"❌ Fleet missing '{key}'")
            self.tests_run += 1
        
        # Check drivers structure
        drivers = data.get('drivers', [])
        print(f"\n👥 Found {len(drivers)} drivers")
        if drivers:
            driver_keys = ['rank', 'driver_id', 'driver_name', 'trips', 'completed', 
                          'completion_rate', 'km', 'revenue', 'revenue_per_trip', 'avg_km_per_trip']
            d0 = drivers[0]
            print(f"   First driver: {d0.get('driver_name')} (rank {d0.get('rank')})")
            for key in driver_keys:
                if key in d0:
                    print(f"✅ Driver has '{key}': {d0[key]}")
                    self.tests_passed += 1
                else:
                    print(f"❌ Driver missing '{key}'")
                self.tests_run += 1
        
        return data

    def test_aggregate_consistency(self, data):
        """Test 2: Aggregate consistency checks"""
        print("\n" + "="*60)
        print("TEST 2: Aggregate Consistency")
        print("="*60)
        
        fleet = data.get('fleet', {})
        drivers = data.get('drivers', [])
        
        if not drivers:
            print("⚠️  No drivers in current period - skipping consistency checks")
            return True
        
        # Sum of driver trips should equal fleet trips
        sum_trips = sum(int(d['trips']) for d in drivers)
        fleet_trips = int(fleet.get('trips', 0))
        self.tests_run += 1
        if sum_trips == fleet_trips:
            print(f"✅ Fleet trips ({fleet_trips}) == Sum of driver trips ({sum_trips})")
            self.tests_passed += 1
        else:
            print(f"❌ Fleet trips ({fleet_trips}) != Sum of driver trips ({sum_trips})")
        
        # Sum of driver revenue should equal fleet revenue
        sum_revenue = round(sum(float(d['revenue']) for d in drivers), 2)
        fleet_revenue = round(float(fleet.get('revenue', 0)), 2)
        self.tests_run += 1
        if abs(sum_revenue - fleet_revenue) < 1:
            print(f"✅ Fleet revenue ({fleet_revenue}) == Sum of driver revenue ({sum_revenue})")
            self.tests_passed += 1
        else:
            print(f"❌ Fleet revenue ({fleet_revenue}) != Sum of driver revenue ({sum_revenue})")
        
        # Revenue per trip calculation
        expected_rpt = round(fleet_revenue / fleet_trips, 2) if fleet_trips else 0.0
        actual_rpt = round(float(fleet.get('revenue_per_trip', 0)), 2)
        self.tests_run += 1
        if abs(expected_rpt - actual_rpt) < 1:
            print(f"✅ Fleet revenue_per_trip ({actual_rpt}) == revenue/trips ({expected_rpt})")
            self.tests_passed += 1
        else:
            print(f"❌ Fleet revenue_per_trip ({actual_rpt}) != revenue/trips ({expected_rpt})")
        
        # Leaderboard sorted by revenue descending
        revenues = [float(d['revenue']) for d in drivers]
        self.tests_run += 1
        if revenues == sorted(revenues, reverse=True):
            print(f"✅ Leaderboard sorted by revenue (descending)")
            self.tests_passed += 1
        else:
            print(f"❌ Leaderboard NOT sorted by revenue")
            print(f"   Actual: {revenues}")
            print(f"   Expected: {sorted(revenues, reverse=True)}")
        
        # Rank sequential 1..N
        ranks = [d['rank'] for d in drivers]
        expected_ranks = list(range(1, len(drivers) + 1))
        self.tests_run += 1
        if ranks == expected_ranks:
            print(f"✅ Ranks sequential 1..{len(drivers)}")
            self.tests_passed += 1
        else:
            print(f"❌ Ranks not sequential")
            print(f"   Actual: {ranks}")
            print(f"   Expected: {expected_ranks}")
        
        # Per-driver revenue_per_trip calculation
        d0 = drivers[0]
        expected_d0_rpt = round(float(d0['revenue']) / int(d0['trips']), 2) if d0['trips'] else 0.0
        actual_d0_rpt = round(float(d0['revenue_per_trip']), 2)
        self.tests_run += 1
        if abs(expected_d0_rpt - actual_d0_rpt) < 1:
            print(f"✅ Driver revenue_per_trip correct ({actual_d0_rpt})")
            self.tests_passed += 1
        else:
            print(f"❌ Driver revenue_per_trip incorrect ({actual_d0_rpt} vs {expected_d0_rpt})")
        
        return True

    def test_summary_includes_drivers_report(self):
        """Test 3: /api/reports/summary includes drivers_report"""
        print("\n" + "="*60)
        print("TEST 3: Summary Includes Drivers Report")
        print("="*60)
        
        success, data = self.run_test(
            "GET /api/reports/summary",
            "GET",
            "/api/reports/summary",
            200,
            token=self.owner_token
        )
        
        if not success:
            return False
        
        self.tests_run += 1
        if 'drivers_report' in data:
            print(f"✅ Summary includes 'drivers_report' key")
            self.tests_passed += 1
            
            dr = data['drivers_report']
            self.tests_run += 1
            if isinstance(dr.get('drivers'), list):
                print(f"✅ drivers_report.drivers is a list ({len(dr['drivers'])} items)")
                self.tests_passed += 1
            else:
                print(f"❌ drivers_report.drivers is not a list")
        else:
            print(f"❌ Summary missing 'drivers_report' key")
        
        return True

    def test_export_excel(self):
        """Test 4: Export Excel"""
        print("\n" + "="*60)
        print("TEST 4: Export Excel")
        print("="*60)
        
        success, _ = self.run_test(
            "GET /api/reports/drivers/export?format=excel",
            "GET",
            "/api/reports/drivers/export?format=excel",
            200,
            token=self.owner_token,
            check_content_type="spreadsheet",
            check_size=800
        )
        
        return success

    def test_export_pdf(self):
        """Test 5: Export PDF"""
        print("\n" + "="*60)
        print("TEST 5: Export PDF")
        print("="*60)
        
        success, _ = self.run_test(
            "GET /api/reports/drivers/export?format=pdf",
            "GET",
            "/api/reports/drivers/export?format=pdf",
            200,
            token=self.owner_token,
            check_content_type="application/pdf",
            check_size=800
        )
        
        return success

    def test_period_filter(self):
        """Test 6: Period filter"""
        print("\n" + "="*60)
        print("TEST 6: Period Filter (Old Date)")
        print("="*60)
        
        success, data = self.run_test(
            "GET /api/reports/drivers?period=2020-01",
            "GET",
            "/api/reports/drivers?period=2020-01",
            200,
            token=self.owner_token
        )
        
        if not success:
            return False
        
        self.tests_run += 1
        if data.get('period') == '2020-01':
            print(f"✅ Period parameter applied (2020-01)")
            self.tests_passed += 1
        else:
            print(f"❌ Period parameter not applied (got {data.get('period')})")
        
        fleet = data.get('fleet', {})
        drivers = data.get('drivers', [])
        
        self.tests_run += 1
        if fleet.get('trips', 0) == 0 and drivers == []:
            print(f"✅ Old period returns empty (fleet.trips=0, drivers=[])")
            self.tests_passed += 1
        else:
            print(f"❌ Old period should be empty (fleet.trips={fleet.get('trips')}, drivers={len(drivers)})")
        
        return True

    def test_rbac_driver(self):
        """Test 7: RBAC - driver should get 403"""
        print("\n" + "="*60)
        print("TEST 7: RBAC - Driver Access")
        print("="*60)
        
        success1, _ = self.run_test(
            "Driver GET /api/reports/drivers (should be 403)",
            "GET",
            "/api/reports/drivers",
            403,
            token=self.driver_token
        )
        
        success2, _ = self.run_test(
            "Driver GET /api/reports/drivers/export (should be 403)",
            "GET",
            "/api/reports/drivers/export?format=excel",
            403,
            token=self.driver_token
        )
        
        return success1 and success2

    def run_all_tests(self):
        """Run all E13 tests"""
        print("\n" + "="*70)
        print("E13 DRIVER LEADERBOARD + REVENUE-PER-TRIP API TESTS")
        print("="*70)
        
        # Login
        self.owner_token = self.login("owner@demo.local", "demo12345")
        self.ops_token = self.login("ops@demo.local", "demo12345")
        self.driver_token = self.login("driver@demo.local", "demo12345")
        
        if not self.owner_token or not self.driver_token:
            print("\n❌ Login failed - cannot proceed with tests")
            return 1
        
        # Test 1: Structure
        data = self.test_drivers_report_structure()
        if not data:
            print("\n❌ Structure test failed - cannot proceed with consistency checks")
            return 1
        
        # Test 2: Consistency
        self.test_aggregate_consistency(data)
        
        # Test 3: Summary
        self.test_summary_includes_drivers_report()
        
        # Test 4: Export Excel
        self.test_export_excel()
        
        # Test 5: Export PDF
        self.test_export_pdf()
        
        # Test 6: Period filter
        self.test_period_filter()
        
        # Test 7: RBAC
        self.test_rbac_driver()
        
        # Summary
        print("\n" + "="*70)
        print(f"RESULTS: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*70)
        
        if self.tests_passed == self.tests_run:
            print("✅ ALL TESTS PASSED")
            return 0
        else:
            print(f"❌ {self.tests_run - self.tests_passed} tests failed")
            return 1

def main():
    tester = E13APITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())
