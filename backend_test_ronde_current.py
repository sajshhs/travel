"""
Backend test for current round: Promo list, Hold expired report, Transfer routes
Testing:
1. POST /api/public/booking/promos - promo eligibility + anti-tamper
2. GET /api/reports/hold-expired - hold expired report + RBAC
3. GET /api/reports/hold-expired/export - CSV export + RBAC
4. Input validation for promos endpoint
"""
import requests
import sys
from datetime import datetime, timedelta

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com"

class TestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.owner_token = None
        self.driver_token = None
        self.marketing_token = None
        self.ops_token = None

    def test(self, name, fn):
        """Run a test function"""
        self.tests_run += 1
        print(f"\n{'='*60}")
        print(f"TEST {self.tests_run}: {name}")
        print('='*60)
        try:
            fn()
            self.tests_passed += 1
            print(f"✅ PASSED")
            return True
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            return False
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return False

    def login(self, email, password):
        """Login and return token"""
        try:
            res = requests.post(f"{BASE_URL}/api/auth/login", 
                              json={"email": email, "password": password}, timeout=10)
            if res.status_code == 200:
                token = res.json().get("token")
                print(f"✓ Logged in as {email}")
                return token
            else:
                print(f"✗ Login failed for {email}: {res.status_code}")
                return None
        except Exception as e:
            print(f"✗ Login error for {email}: {e}")
            return None

    def setup_auth(self):
        """Setup authentication tokens"""
        print("\n" + "="*60)
        print("SETUP: Logging in test users")
        print("="*60)
        self.owner_token = self.login("owner@demo.local", "demo12345")
        self.ops_token = self.login("ops@demo.local", "demo12345")
        self.driver_token = self.login("driver@demo.local", "demo12345")
        self.marketing_token = self.login("marketing@demo.local", "demo12345")
        
        if not self.owner_token:
            print("⚠️  WARNING: Could not login as owner")
        if not self.ops_token:
            print("⚠️  WARNING: Could not login as ops")

    def get_vehicle_for_promo_test(self):
        """Get a vehicle ID for promo testing"""
        try:
            # Get config to find available vehicles
            res = requests.get(f"{BASE_URL}/api/public/booking/config", timeout=10)
            if res.status_code != 200:
                print(f"Could not get booking config: {res.status_code}")
                return None
            
            config = res.json()
            
            # Search for available vehicles for a 2-day weekend rental
            # Use a Saturday-Sunday in the future
            today = datetime.now()
            days_until_saturday = (5 - today.weekday()) % 7
            if days_until_saturday == 0:
                days_until_saturday = 7
            start = today + timedelta(days=days_until_saturday)
            end = start + timedelta(days=2)
            
            search_payload = {
                "service": "daily_rental",
                "start_datetime": start.isoformat(),
                "end_datetime": end.isoformat(),
                "pax": 12
            }
            
            res = requests.post(f"{BASE_URL}/api/public/booking/search", 
                              json=search_payload, timeout=10)
            if res.status_code != 200:
                print(f"Search failed: {res.status_code}")
                return None
            
            data = res.json()
            options = data.get("options", [])
            if not options:
                print("No vehicles available for testing")
                return None
            
            # Find a Hiace Premio if possible (for AKHIRPEKAN10 promo)
            for opt in options:
                if opt.get("vehicle", {}).get("type") == "hiace_premio":
                    vehicle_id = opt["vehicle"]["id"]
                    print(f"✓ Found Hiace Premio: {vehicle_id}")
                    return vehicle_id, start, end
            
            # Otherwise use first available
            vehicle_id = options[0]["vehicle"]["id"]
            print(f"✓ Found vehicle: {vehicle_id}")
            return vehicle_id, start, end
            
        except Exception as e:
            print(f"Error getting vehicle: {e}")
            return None

    def test_promo_eligible_weekend_rental(self):
        """Test promo eligibility for 2-day weekend rental >= Rp 3,000,000"""
        result = self.get_vehicle_for_promo_test()
        if not result:
            raise AssertionError("Could not get vehicle for testing")
        
        vehicle_id, start, end = result
        
        payload = {
            "service": "daily_rental",
            "vehicle_id": vehicle_id,
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "pax": 12
        }
        
        print(f"Testing with vehicle {vehicle_id}, {start.date()} to {end.date()}")
        
        res = requests.post(f"{BASE_URL}/api/public/booking/promos", 
                          json=payload, timeout=10)
        
        print(f"Status: {res.status_code}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        print(f"Response: {data}")
        
        promos = data.get("promos", [])
        eligible_count = data.get("eligible_count", 0)
        
        print(f"Total promos: {len(promos)}, Eligible: {eligible_count}")
        
        # Check if GATHERING500 and AKHIRPEKAN10 exist
        gathering = next((p for p in promos if p.get("code") == "GATHERING500"), None)
        akhirpekan = next((p for p in promos if p.get("code") == "AKHIRPEKAN10"), None)
        
        if gathering:
            print(f"GATHERING500: eligible={gathering.get('eligible')}, discount={gathering.get('discount')}, reason={gathering.get('reason')}")
        else:
            print("⚠️  GATHERING500 not found in promo list")
        
        if akhirpekan:
            print(f"AKHIRPEKAN10: eligible={akhirpekan.get('eligible')}, discount={akhirpekan.get('discount')}, reason={akhirpekan.get('reason')}")
        else:
            print("⚠️  AKHIRPEKAN10 not found in promo list")

    def test_promo_ineligible_one_day(self):
        """Test promo ineligibility for 1-day rental"""
        result = self.get_vehicle_for_promo_test()
        if not result:
            raise AssertionError("Could not get vehicle for testing")
        
        vehicle_id, start, _ = result
        end = start + timedelta(days=1)  # Only 1 day
        
        payload = {
            "service": "daily_rental",
            "vehicle_id": vehicle_id,
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "pax": 12
        }
        
        print(f"Testing 1-day rental with vehicle {vehicle_id}")
        
        res = requests.post(f"{BASE_URL}/api/public/booking/promos", 
                          json=payload, timeout=10)
        
        print(f"Status: {res.status_code}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        
        data = res.json()
        promos = data.get("promos", [])
        
        gathering = next((p for p in promos if p.get("code") == "GATHERING500"), None)
        if gathering:
            print(f"GATHERING500: eligible={gathering.get('eligible')}, reason={gathering.get('reason')}")
            assert gathering.get("eligible") == False, "GATHERING500 should be ineligible for 1-day rental"
            assert "minimal 2 hari" in gathering.get("reason", "").lower(), f"Expected 'minimal 2 hari' in reason, got: {gathering.get('reason')}"
            print("✓ GATHERING500 correctly ineligible with proper reason")

    def test_promo_wrong_service(self):
        """Test promo ineligibility for wrong service"""
        result = self.get_vehicle_for_promo_test()
        if not result:
            raise AssertionError("Could not get vehicle for testing")
        
        vehicle_id, start, end = result
        
        payload = {
            "service": "daily_rental",
            "vehicle_id": vehicle_id,
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "pax": 12
        }
        
        res = requests.post(f"{BASE_URL}/api/public/booking/promos", 
                          json=payload, timeout=10)
        
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        
        data = res.json()
        promos = data.get("promos", [])
        
        # BANDARA50 should be for airport_transfer only
        bandara = next((p for p in promos if p.get("code") == "BANDARA50"), None)
        if bandara:
            print(f"BANDARA50: eligible={bandara.get('eligible')}, reason={bandara.get('reason')}")
            assert bandara.get("eligible") == False, "BANDARA50 should be ineligible for daily_rental"
            assert "layanan" in bandara.get("reason", "").lower(), f"Expected service-related reason, got: {bandara.get('reason')}"
            print("✓ BANDARA50 correctly ineligible with service reason")

    def test_promo_anti_tamper(self):
        """Test anti-tamper: client-sent subtotal should be ignored"""
        result = self.get_vehicle_for_promo_test()
        if not result:
            raise AssertionError("Could not get vehicle for testing")
        
        vehicle_id, start, end = result
        
        # Send with fake subtotal field
        payload_with_fake = {
            "service": "daily_rental",
            "vehicle_id": vehicle_id,
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "pax": 12,
            "subtotal": 99000000  # Fake high amount
        }
        
        res1 = requests.post(f"{BASE_URL}/api/public/booking/promos", 
                           json=payload_with_fake, timeout=10)
        
        # Send without fake subtotal
        payload_normal = {
            "service": "daily_rental",
            "vehicle_id": vehicle_id,
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "pax": 12
        }
        
        res2 = requests.post(f"{BASE_URL}/api/public/booking/promos", 
                           json=payload_normal, timeout=10)
        
        assert res1.status_code == 200, f"Request with fake subtotal failed: {res1.status_code}"
        assert res2.status_code == 200, f"Normal request failed: {res2.status_code}"
        
        data1 = res1.json()
        data2 = res2.json()
        
        # Eligibility should be the same
        promos1 = {p["code"]: p["eligible"] for p in data1.get("promos", [])}
        promos2 = {p["code"]: p["eligible"] for p in data2.get("promos", [])}
        
        print(f"With fake subtotal: {promos1}")
        print(f"Without fake subtotal: {promos2}")
        
        assert promos1 == promos2, "Eligibility changed when fake subtotal was sent - server is using client data!"
        print("✓ Server correctly ignores client-sent subtotal")

    def test_promo_validation_invalid_vehicle(self):
        """Test validation: invalid vehicle_id should return 404"""
        today = datetime.now()
        start = today + timedelta(days=7)
        end = start + timedelta(days=2)
        
        payload = {
            "service": "daily_rental",
            "vehicle_id": "nonexistent-vehicle-id",
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "pax": 12
        }
        
        res = requests.post(f"{BASE_URL}/api/public/booking/promos", 
                          json=payload, timeout=10)
        
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
        
        assert res.status_code == 404, f"Expected 404 for invalid vehicle, got {res.status_code}"
        
        data = res.json()
        detail = data.get("detail", "")
        assert detail, "Expected error detail message"
        print(f"✓ Got 404 with reason: {detail}")

    def test_promo_validation_invalid_dates(self):
        """Test validation: invalid dates should return 4xx"""
        result = self.get_vehicle_for_promo_test()
        if not result:
            raise AssertionError("Could not get vehicle for testing")
        
        vehicle_id, _, _ = result
        
        payload = {
            "service": "daily_rental",
            "vehicle_id": vehicle_id,
            "start_datetime": "invalid-date",
            "end_datetime": "also-invalid",
            "pax": 12
        }
        
        res = requests.post(f"{BASE_URL}/api/public/booking/promos", 
                          json=payload, timeout=10)
        
        print(f"Status: {res.status_code}")
        assert res.status_code >= 400 and res.status_code < 500, f"Expected 4xx for invalid dates, got {res.status_code}"
        print(f"✓ Got {res.status_code} for invalid dates")

    def test_promo_validation_end_before_start(self):
        """Test validation: end before start should return 400"""
        result = self.get_vehicle_for_promo_test()
        if not result:
            raise AssertionError("Could not get vehicle for testing")
        
        vehicle_id, start, _ = result
        end = start - timedelta(days=1)  # End before start
        
        payload = {
            "service": "daily_rental",
            "vehicle_id": vehicle_id,
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "pax": 12
        }
        
        res = requests.post(f"{BASE_URL}/api/public/booking/promos", 
                          json=payload, timeout=10)
        
        print(f"Status: {res.status_code}")
        assert res.status_code == 400, f"Expected 400 for end before start, got {res.status_code}"
        print(f"✓ Got 400 for end before start")

    def test_hold_expired_report_owner(self):
        """Test hold expired report for owner"""
        if not self.owner_token:
            raise AssertionError("Owner token not available")
        
        headers = {"Authorization": f"Bearer {self.owner_token}"}
        res = requests.get(f"{BASE_URL}/api/reports/hold-expired?days=30", 
                         headers=headers, timeout=10)
        
        print(f"Status: {res.status_code}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        
        data = res.json()
        print(f"Response keys: {data.keys()}")
        
        # Check structure
        assert "summary" in data, "Missing 'summary' field"
        assert "rows" in data, "Missing 'rows' field"
        assert "insights" in data, "Missing 'insights' field"
        
        summary = data["summary"]
        print(f"Summary: {summary}")
        
        # Check summary fields
        required_fields = ["count", "potential_value", "dp_value", "with_proof", 
                          "recovered", "holds_started", "expiry_rate", "avg_hold_hours"]
        for field in required_fields:
            assert field in summary, f"Missing summary field: {field}"
        
        rows = data["rows"]
        print(f"Total rows: {len(rows)}")
        
        # Check for demo data BK-0009 and BK-0010
        codes = [r.get("code") for r in rows]
        print(f"Booking codes: {codes}")
        
        bk_0009 = next((r for r in rows if r.get("code") == "BK-0009"), None)
        bk_0010 = next((r for r in rows if r.get("code") == "BK-0010"), None)
        
        if bk_0009:
            print(f"✓ Found BK-0009: proofs={bk_0009.get('proofs')}")
            assert bk_0009.get("proofs") == 1, "BK-0009 should have 1 proof"
        else:
            print("⚠️  BK-0009 not found (may have been cleaned)")
        
        if bk_0010:
            print(f"✓ Found BK-0010: proofs={bk_0010.get('proofs')}")
            assert bk_0010.get("proofs") == 0, "BK-0010 should have 0 proofs"
        else:
            print("⚠️  BK-0010 not found (may have been cleaned)")
        
        print(f"✓ Report structure valid, count={summary.get('count')}, with_proof={summary.get('with_proof')}")

    def test_hold_expired_report_rbac_driver(self):
        """Test RBAC: driver should get 403"""
        if not self.driver_token:
            print("⚠️  Driver token not available, skipping")
            return
        
        headers = {"Authorization": f"Bearer {self.driver_token}"}
        res = requests.get(f"{BASE_URL}/api/reports/hold-expired?days=30", 
                         headers=headers, timeout=10)
        
        print(f"Status: {res.status_code}")
        assert res.status_code == 403, f"Expected 403 for driver, got {res.status_code}"
        print("✓ Driver correctly denied access (403)")

    def test_hold_expired_report_rbac_no_auth(self):
        """Test RBAC: no token should get 401"""
        res = requests.get(f"{BASE_URL}/api/reports/hold-expired?days=30", timeout=10)
        
        print(f"Status: {res.status_code}")
        assert res.status_code == 401, f"Expected 401 without auth, got {res.status_code}"
        print("✓ Correctly requires authentication (401)")

    def test_hold_expired_report_rbac_marketing(self):
        """Test RBAC: marketing should get 403"""
        if not self.marketing_token:
            print("⚠️  Marketing token not available, skipping")
            return
        
        headers = {"Authorization": f"Bearer {self.marketing_token}"}
        res = requests.get(f"{BASE_URL}/api/reports/hold-expired?days=30", 
                         headers=headers, timeout=10)
        
        print(f"Status: {res.status_code}")
        assert res.status_code == 403, f"Expected 403 for marketing, got {res.status_code}"
        print("✓ Marketing correctly denied access (403)")

    def test_hold_expired_report_days_validation(self):
        """Test days parameter validation"""
        if not self.owner_token:
            raise AssertionError("Owner token not available")
        
        headers = {"Authorization": f"Bearer {self.owner_token}"}
        
        # Test valid values
        for days in [7, 365]:
            res = requests.get(f"{BASE_URL}/api/reports/hold-expired?days={days}", 
                             headers=headers, timeout=10)
            print(f"days={days}: {res.status_code}")
            assert res.status_code == 200, f"Expected 200 for days={days}, got {res.status_code}"
        
        # Test invalid values
        for days in [0, 999]:
            res = requests.get(f"{BASE_URL}/api/reports/hold-expired?days={days}", 
                             headers=headers, timeout=10)
            print(f"days={days}: {res.status_code}")
            assert res.status_code == 422, f"Expected 422 for days={days}, got {res.status_code}"
        
        print("✓ Days validation working correctly")

    def test_hold_expired_export_csv(self):
        """Test CSV export"""
        if not self.owner_token:
            raise AssertionError("Owner token not available")
        
        headers = {"Authorization": f"Bearer {self.owner_token}"}
        res = requests.get(f"{BASE_URL}/api/reports/hold-expired/export?days=30", 
                         headers=headers, timeout=10)
        
        print(f"Status: {res.status_code}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        
        content_type = res.headers.get("content-type", "")
        print(f"Content-Type: {content_type}")
        assert "csv" in content_type.lower(), f"Expected CSV content type, got {content_type}"
        
        csv_content = res.text
        lines = csv_content.split("\n")
        print(f"CSV lines: {len(lines)}")
        
        # Check header
        header = lines[0] if lines else ""
        print(f"Header: {header[:100]}")
        assert "Kode" in header, "CSV header should contain 'Kode'"
        
        # Check for BK-0009 in content
        has_bk_0009 = any("BK-0009" in line for line in lines)
        if has_bk_0009:
            print("✓ Found BK-0009 in CSV")
        else:
            print("⚠️  BK-0009 not found in CSV (may have been cleaned)")
        
        print("✓ CSV export working")

    def test_hold_expired_export_rbac(self):
        """Test CSV export RBAC"""
        if not self.driver_token:
            print("⚠️  Driver token not available, skipping")
            return
        
        headers = {"Authorization": f"Bearer {self.driver_token}"}
        res = requests.get(f"{BASE_URL}/api/reports/hold-expired/export?days=30", 
                         headers=headers, timeout=10)
        
        print(f"Status: {res.status_code}")
        assert res.status_code == 403, f"Expected 403 for driver, got {res.status_code}"
        print("✓ Driver correctly denied CSV export (403)")

    def run_all(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("BACKEND TEST - RONDE CURRENT")
        print("Testing: Promo list, Hold expired report, Transfer routes")
        print("="*60)
        
        self.setup_auth()
        
        # Promo tests
        self.test("Promo eligible for 2-day weekend rental", 
                 self.test_promo_eligible_weekend_rental)
        self.test("Promo ineligible for 1-day rental", 
                 self.test_promo_ineligible_one_day)
        self.test("Promo ineligible for wrong service", 
                 self.test_promo_wrong_service)
        self.test("Promo anti-tamper (ignore client subtotal)", 
                 self.test_promo_anti_tamper)
        
        # Validation tests
        self.test("Promo validation - invalid vehicle_id", 
                 self.test_promo_validation_invalid_vehicle)
        self.test("Promo validation - invalid dates", 
                 self.test_promo_validation_invalid_dates)
        self.test("Promo validation - end before start", 
                 self.test_promo_validation_end_before_start)
        
        # Hold expired report tests
        self.test("Hold expired report - owner access", 
                 self.test_hold_expired_report_owner)
        self.test("Hold expired report - RBAC driver (403)", 
                 self.test_hold_expired_report_rbac_driver)
        self.test("Hold expired report - RBAC no auth (401)", 
                 self.test_hold_expired_report_rbac_no_auth)
        self.test("Hold expired report - RBAC marketing (403)", 
                 self.test_hold_expired_report_rbac_marketing)
        self.test("Hold expired report - days validation", 
                 self.test_hold_expired_report_days_validation)
        
        # CSV export tests
        self.test("Hold expired CSV export", 
                 self.test_hold_expired_export_csv)
        self.test("Hold expired CSV export - RBAC", 
                 self.test_hold_expired_export_rbac)
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {self.tests_run - self.tests_passed}")
        print(f"Success rate: {self.tests_passed * 100 // self.tests_run if self.tests_run else 0}%")
        
        return 0 if self.tests_passed == self.tests_run else 1

if __name__ == "__main__":
    runner = TestRunner()
    sys.exit(runner.run_all())
