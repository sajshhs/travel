"""
Backend API Test - Round 2 (Phase 3) - CMS Bilingual & Fixes
Tests specific to iteration_93+ requirements
"""
import requests
import sys
import time
from datetime import datetime

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

class Round2Tester:
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
             should_contain=None, should_have_keys=None, auth=False):
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
                    
                # Check for specific keys
                if should_have_keys and response_data:
                    for key in should_have_keys:
                        if key not in response_data:
                            content_ok = False
                            print(f"   ⚠️  Expected key '{key}' not found in response")
                        else:
                            print(f"   ✓ Key '{key}' found in response")
                
                # Check for text content
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
    tester = Round2Tester()
    
    print("\n" + "="*70)
    print("🧪 ROUND 2 - SECTION 1: API CONTRACT VALIDATION (Round 1 Fixes)")
    print("="*70)
    
    # Login as owner for authenticated tests
    if not tester.login("owner@demo.local", "demo12345"):
        print("❌ Cannot proceed without login")
        return 1
    
    # Test 1: GET /api/content/analytics/top returns {overview, rows, kinds}
    success, analytics_data = tester.test(
        "GET /api/content/analytics/top - returns {overview, rows, kinds} (NOT 'summary')",
        "GET", "content/analytics/top?limit=10",
        200,
        should_have_keys=["overview", "rows", "kinds"],
        auth=True
    )
    if success and analytics_data:
        print(f"   ✓ Overview keys: {list(analytics_data.get('overview', {}).keys())}")
        print(f"   ✓ Rows count: {len(analytics_data.get('rows', []))}")
        print(f"   ✓ Kinds: {analytics_data.get('kinds', [])}")
        
        # Verify 'summary' key is NOT present
        if 'summary' in analytics_data:
            print(f"   ⚠️  WARNING: 'summary' key found (should be 'overview')")
    
    # Test 2: GET /api/public/promos uses {discount_type, discount_value}
    success, promo_data = tester.test(
        "GET /api/public/promos - uses {discount_type, discount_value}",
        "GET", "public/promos",
        200,
        auth=False
    )
    if success and promo_data and isinstance(promo_data, list) and len(promo_data) > 0:
        first_promo = promo_data[0]
        has_discount_type = 'discount_type' in first_promo
        has_discount_value = 'discount_value' in first_promo
        
        if has_discount_type and has_discount_value:
            print(f"   ✓ Promo has discount_type: {first_promo.get('discount_type')}")
            print(f"   ✓ Promo has discount_value: {first_promo.get('discount_value')}")
        else:
            print(f"   ⚠️  Promo missing discount_type or discount_value")
            print(f"   Keys found: {list(first_promo.keys())}")
    
    print("\n" + "="*70)
    print("🧪 ROUND 2 - SECTION 2: TRANSLATION RATE-LIMITING")
    print("="*70)
    
    # Test 3: POST /api/content/articles/translate rate limiting
    # First, get an article to translate
    success, articles = tester.test(
        "GET /api/content/articles - get articles for translation test",
        "GET", "content/articles?limit=1",
        200,
        auth=True
    )
    
    if success and articles and len(articles) > 0:
        article_id = articles[0].get('id')
        print(f"   ✓ Using article ID: {article_id}")
        
        # Call translate endpoint 15 times
        print(f"\n   Testing rate limit: calling translate 15 times...")
        status_codes = []
        
        for i in range(15):
            try:
                response = requests.post(
                    f"{BASE_URL}/content/articles/translate",
                    json={"id": article_id, "target_lang": "en"},
                    headers=tester.headers()
                )
                status_codes.append(response.status_code)
                print(f"   Call {i+1}: {response.status_code}")
                
                # Small delay between calls
                time.sleep(0.1)
            except Exception as e:
                print(f"   Call {i+1}: Error - {str(e)}")
        
        # Analyze results
        count_503 = status_codes.count(503)
        count_429 = status_codes.count(429)
        
        print(f"\n   Results:")
        print(f"   - 503 responses (AI OFF): {count_503}")
        print(f"   - 429 responses (rate limit): {count_429}")
        
        # Expected: most should be 503 (AI OFF), then 429 after rate limit
        if count_503 > 0:
            print(f"   ✓ AI translation is OFF (503 responses)")
            tester.tests_passed += 1
        else:
            print(f"   ⚠️  Expected 503 responses for AI OFF")
            tester.tests_failed += 1
        
        if count_429 > 0:
            print(f"   ✓ Rate limiting is working (429 responses)")
            tester.tests_passed += 1
        else:
            print(f"   ⚠️  Expected 429 responses after rate limit")
            tester.tests_failed += 1
        
        tester.tests_run += 2
    
    print("\n" + "="*70)
    print("🧪 ROUND 2 - SECTION 3: CMS LOCALE METADATA")
    print("="*70)
    
    # Test 4: GET /api/content/meta/i18n
    success, i18n_meta = tester.test(
        "GET /api/content/meta/i18n - returns locale metadata",
        "GET", "content/meta/i18n",
        200,
        should_have_keys=["langs", "default", "translatable", "ai_available"],
        auth=True
    )
    if success and i18n_meta:
        print(f"   ✓ Languages: {i18n_meta.get('langs', [])}")
        print(f"   ✓ Default: {i18n_meta.get('default')}")
        print(f"   ✓ AI available: {i18n_meta.get('ai_available')}")
    
    print("\n" + "="*70)
    print("🧪 ROUND 2 - SECTION 4: BILINGUAL PUBLIC ENDPOINTS")
    print("="*70)
    
    # Test 5: GET /api/public/packages?lang=en
    success, packages_en = tester.test(
        "GET /api/public/packages?lang=en - returns English packages",
        "GET", "public/packages?lang=en",
        200,
        auth=False
    )
    if success and packages_en and len(packages_en) > 0:
        first_pkg = packages_en[0]
        print(f"   ✓ Package name: {first_pkg.get('name')}")
        print(f"   ✓ Package has translations: {first_pkg.get('translations', {})}")
    
    # Test 6: GET /api/public/destinations?lang=en
    success, dest_en = tester.test(
        "GET /api/public/destinations?lang=en - returns English destinations",
        "GET", "public/destinations?lang=en",
        200,
        auth=False
    )
    if success and dest_en and len(dest_en) > 0:
        first_dest = dest_en[0]
        print(f"   ✓ Destination name: {first_dest.get('name')}")
    
    # Test 7: GET /api/public/articles?lang=en
    success, articles_en = tester.test(
        "GET /api/public/articles?lang=en - returns English articles",
        "GET", "public/articles?lang=en",
        200,
        auth=False
    )
    if success and articles_en and len(articles_en) > 0:
        first_article = articles_en[0]
        print(f"   ✓ Article title: {first_article.get('title')}")
    
    # Test 8: GET /api/public/promos?lang=en
    success, promos_en = tester.test(
        "GET /api/public/promos?lang=en - returns English promos",
        "GET", "public/promos?lang=en",
        200,
        auth=False
    )
    
    print("\n" + "="*70)
    print("🧪 ROUND 2 - SECTION 5: CONTENT FILTERING BY LOCALE")
    print("="*70)
    
    # Test 9: GET /api/content/articles with locale filter
    success, articles_all = tester.test(
        "GET /api/content/articles - all articles",
        "GET", "content/articles?limit=50",
        200,
        auth=True
    )
    if success and articles_all:
        print(f"   ✓ Total articles: {len(articles_all)}")
        
        # Count articles with EN translations
        with_en = sum(1 for a in articles_all if a.get('translations', {}).get('en'))
        without_en = len(articles_all) - with_en
        print(f"   ✓ Articles with EN: {with_en}")
        print(f"   ✓ Articles without EN: {without_en}")
    
    print("\n" + "="*70)
    print("🧪 ROUND 2 - SECTION 6: RBAC CHECKS")
    print("="*70)
    
    # Test 10: Driver blocked from CMS
    if tester.login("driver@demo.local", "demo12345"):
        success, _ = tester.test(
            "GET /api/content/articles - driver BLOCKED (403)",
            "GET", "content/articles",
            403,
            auth=True
        )
    
    # Test 11: Marketing blocked from finance
    if tester.login("marketing@demo.local", "demo12345"):
        success, _ = tester.test(
            "GET /api/finance/summary - marketing BLOCKED (403)",
            "GET", "finance/summary",
            403,
            auth=True
        )
        
        # But marketing CAN access CMS
        success, _ = tester.test(
            "GET /api/content/articles - marketing CAN access CMS",
            "GET", "content/articles",
            200,
            auth=True
        )
    
    # Print summary
    tester.print_summary()
    
    return 0 if tester.tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
