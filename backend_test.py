"""
Backend API Test - Travel ERP Public APIs & Brand Rename
Tests public endpoints and brand consistency for iteration_86+
"""
import requests
import sys
from datetime import datetime, timedelta

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

class APITester:
    def __init__(self):
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []

    def login(self, email="owner@demo.local", password="demo12345"):
        """Login and get auth token"""
        print(f"\n🔐 Logging in as {email}...")
        try:
            response = requests.post(f"{BASE_URL}/auth/login", 
                                   json={"email": email, "password": password})
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token") or data.get("token")
                print(f"✅ Login successful")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return False

    def headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }

    def test(self, name, method, endpoint, expected_status, data=None, 
             should_contain=None, auth=False):
        """Run a single API test"""
        url = f"{BASE_URL}/{endpoint}"
        self.tests_run += 1
        print(f"\n🔍 Test #{self.tests_run}: {name}")
        
        try:
            headers = self.headers() if auth else {'Content-Type': 'application/json'}
            
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers)
            
            status_ok = response.status_code == expected_status
            
            # Check response content
            content_ok = True
            response_data = None
            if status_ok:
                try:
                    response_data = response.json()
                except Exception:
                    response_data = None
                    
                if should_contain:
                    response_text = response.text.lower()
                    if isinstance(should_contain, list):
                        for keyword in should_contain:
                            if keyword.lower() not in response_text:
                                content_ok = False
                                print(f"   ⚠️  Expected keyword '{keyword}' not found in response")
                    else:
                        if should_contain.lower() not in response_text:
                            content_ok = False
                            print(f"   ⚠️  Expected keyword '{should_contain}' not found in response")
            
            success = status_ok and content_ok
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASS - Status: {response.status_code}")
                if should_contain:
                    print(f"   ✓ Response contains expected keywords")
            else:
                self.tests_failed += 1
                self.failures.append({
                    'test': name,
                    'expected': expected_status,
                    'got': response.status_code,
                    'response': response.text[:200]
                })
                print(f"❌ FAIL - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:300]}")
            
            return success, response_data
            
        except Exception as e:
            self.tests_failed += 1
            self.failures.append({'test': name, 'error': str(e)})
            print(f"❌ FAIL - Error: {str(e)}")
            return False, None

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100) if self.tests_run > 0 else 0:.1f}%")
        
        if self.failures:
            print("\n❌ FAILED TESTS:")
            for i, failure in enumerate(self.failures, 1):
                print(f"\n{i}. {failure.get('test', 'Unknown')}")
                if 'error' in failure:
                    print(f"   Error: {failure['error']}")
                else:
                    print(f"   Expected: {failure.get('expected')}, Got: {failure.get('got')}")
                    print(f"   Response: {failure.get('response', '')[:150]}")
        
        print("\n" + "="*70)


def main():
    tester = APITester()
    
    print("\n" + "="*70)
    print("🧪 SECTION 1: BRAND RENAME - Company Info")
    print("="*70)
    
    # Test 1: Company info has RahazaTrans
    success, data = tester.test(
        "GET /api/public/company - brand name is 'RahazaTrans'",
        "GET", "public/company",
        200,
        should_contain="RahazaTrans"
    )
    if success and data:
        company_name = data.get('name', '')
        if company_name == "RahazaTrans":
            print(f"   ✓ Company name is exactly 'RahazaTrans'")
        else:
            print(f"   ⚠️  Company name is '{company_name}' (expected 'RahazaTrans')")
    
    print("\n" + "="*70)
    print("🧪 SECTION 2: PUBLIC FLEET API")
    print("="*70)
    
    # Test 2: Fleet list
    success, fleet_data = tester.test(
        "GET /api/public/fleet - returns vehicles",
        "GET", "public/fleet",
        200
    )
    if success and fleet_data:
        fleet_count = len(fleet_data) if isinstance(fleet_data, list) else 0
        print(f"   ✓ Fleet count: {fleet_count}")
        if fleet_count > 0:
            first_vehicle = fleet_data[0]
            print(f"   ✓ First vehicle: {first_vehicle.get('name', 'N/A')} ({first_vehicle.get('type', 'N/A')})")
    
    print("\n" + "="*70)
    print("🧪 SECTION 3: BOOKING CONFIG (vehicle_types, dp_percent, routes)")
    print("="*70)
    
    # Test 3: Booking config
    success, config_data = tester.test(
        "GET /api/public/booking/config - returns config",
        "GET", "public/booking/config",
        200
    )
    if success and config_data:
        vehicle_types = config_data.get('vehicle_types', [])
        dp_percent = config_data.get('dp_percent', 0)
        hold_hours = config_data.get('hold_hours', 0)
        routes = config_data.get('routes', [])
        
        print(f"   ✓ Vehicle types count: {len(vehicle_types)}")
        print(f"   ✓ DP percent: {dp_percent}%")
        print(f"   ✓ Hold hours: {hold_hours}")
        print(f"   ✓ Airport routes count: {len(routes)}")
        
        if len(vehicle_types) > 0:
            for vt in vehicle_types[:3]:
                print(f"      - {vt.get('label', 'N/A')}: from {vt.get('from_price', 0)} (capacity: {vt.get('max_capacity', 0)})")
        
        if len(routes) > 0:
            for route in routes[:3]:
                print(f"      - {route.get('label', 'N/A')}: from {route.get('from_price', 0)} (code: {route.get('code', 'N/A')})")
    
    print("\n" + "="*70)
    print("🧪 SECTION 4: DESTINATIONS (highlights, best_time, faqs)")
    print("="*70)
    
    # Test 4: Destinations
    success, dest_data = tester.test(
        "GET /api/public/destinations - returns destinations",
        "GET", "public/destinations",
        200
    )
    if success and dest_data:
        dest_count = len(dest_data) if isinstance(dest_data, list) else 0
        print(f"   ✓ Destinations count: {dest_count}")
        
        if dest_count > 0:
            # Check first 2 destinations for highlights, best_time, faqs
            for dest in dest_data[:2]:
                name = dest.get('name', 'N/A')
                highlights = dest.get('highlights', [])
                best_time = dest.get('best_time', '')
                faqs = dest.get('faqs', [])
                
                print(f"   ✓ {name}:")
                print(f"      - Highlights: {len(highlights)}")
                print(f"      - Best time: {best_time}")
                print(f"      - FAQs: {len(faqs)}")
    
    print("\n" + "="*70)
    print("🧪 SECTION 5: PACKAGES (price_from)")
    print("="*70)
    
    # Test 5: Packages
    success, pkg_data = tester.test(
        "GET /api/public/packages - returns packages",
        "GET", "public/packages",
        200
    )
    if success and pkg_data:
        pkg_count = len(pkg_data) if isinstance(pkg_data, list) else 0
        print(f"   ✓ Packages count: {pkg_count}")
        
        if pkg_count > 0:
            for pkg in pkg_data[:3]:
                print(f"      - {pkg.get('name', 'N/A')}: {pkg.get('price_from', 0)}")
    
    print("\n" + "="*70)
    print("🧪 SECTION 6: PROMOS")
    print("="*70)
    
    # Test 6: Promos
    success, promo_data = tester.test(
        "GET /api/public/promos - returns promos",
        "GET", "public/promos",
        200
    )
    if success and promo_data:
        promo_count = len(promo_data) if isinstance(promo_data, list) else 0
        print(f"   ✓ Promos count: {promo_count}")
        
        if promo_count > 0:
            for promo in promo_data[:3]:
                print(f"      - {promo.get('code', 'N/A')}: {promo.get('discount_type', 'N/A')} {promo.get('discount_value', 0)}")
    
    print("\n" + "="*70)
    print("🧪 SECTION 7: TRIP ESTIMATE CALCULATION")
    print("="*70)
    
    # Test 7: Trip estimate
    success, estimate_data = tester.test(
        "POST /api/public/trip-estimate - calculates estimate",
        "POST", "public/trip-estimate",
        200,
        data={
            "vehicle_type": "hiace_premio",
            "days": 3,
            "destination": "Bromo",
            "pax": 10
        }
    )
    if success and estimate_data:
        total = estimate_data.get('total', 0)
        days = estimate_data.get('days', 0)
        breakdown = estimate_data.get('breakdown', [])
        
        print(f"   ✓ Total: {total}")
        print(f"   ✓ Days: {days}")
        print(f"   ✓ Breakdown items: {len(breakdown)}")
        
        # Calculate DP
        if config_data:
            dp_percent = config_data.get('dp_percent', 30)
            expected_dp = int(total * dp_percent / 100)
            print(f"   ✓ Expected DP ({dp_percent}%): {expected_dp}")
    
    print("\n" + "="*70)
    print("🧪 SECTION 8: ARTICLES/BLOG")
    print("="*70)
    
    # Test 8: Articles
    success, article_data = tester.test(
        "GET /api/public/articles - returns articles",
        "GET", "public/articles",
        200
    )
    if success and article_data:
        article_count = len(article_data) if isinstance(article_data, list) else 0
        print(f"   ✓ Articles count: {article_count}")
        
        if article_count > 0:
            first_article = article_data[0]
            print(f"   ✓ First article: {first_article.get('title', 'N/A')}")
            print(f"      Slug: {first_article.get('slug', 'N/A')}")
    
    print("\n" + "="*70)
    print("🧪 SECTION 9: AUTH & RBAC")
    print("="*70)
    
    # Test 9: Login owner
    if tester.login("owner@demo.local", "demo12345"):
        # Test 10: Get vehicles (authenticated)
        success, vehicles = tester.test(
            "GET /api/vehicles - owner can access",
            "GET", "vehicles",
            200,
            auth=True
        )
        if success and vehicles:
            print(f"   ✓ Owner can access vehicles: {len(vehicles)} vehicles")
    
    # Test 11: Login marketing
    if tester.login("marketing@demo.local", "demo12345"):
        # Test 12: Marketing can access media
        success, _ = tester.test(
            "GET /api/media - marketing can access",
            "GET", "media",
            200,
            auth=True
        )
    
    # Test 13: Login driver
    if tester.login("driver@demo.local", "demo12345"):
        # Test 14: Driver CANNOT access media (should be 403)
        success, _ = tester.test(
            "GET /api/media - driver CANNOT access (403)",
            "GET", "media",
            403,
            auth=True
        )
    
    # Print summary
    tester.print_summary()
    
    return 0 if tester.tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
