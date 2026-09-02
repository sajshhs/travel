"""
Backend API tests for CMS Gap Closure G1-G10 (Rahaza Travel ERP).

Tests:
- G1: Unique slug/code validation (409 on duplicate)
- G2: Public promos filter by valid_until (expired promos hidden)
- G3: Image upload POST /api/uploads/cms (jpg/png/webp ≤6MB, RBAC)
- G4: Destinations new fields (intro/route_points/faqs)
- G5: Search query parameter ?q= (case-insensitive)
- G6: SEO metadata fields (meta_title/meta_description/og_image)
- G8: Duplicate content endpoint (slug auto-suffix, moderation reset)
- G9: Testimonials moderation (approved field filter in public)
- G10: Sort by position (ascending order)
- Regression: Auth, RBAC (driver 403 on /content/*)
"""
import io
import requests
import sys
from datetime import datetime, timedelta

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

class TestRunner:
    def __init__(self):
        self.token = None
        self.driver_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.cleanup_ids = {
            "destinations": [],
            "packages": [],
            "articles": [],
            "testimonials": [],
            "promos": [],
        }

    def log(self, msg):
        print(f"  {msg}")

    def test(self, name, condition, details=""):
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            print(f"✅ {name}")
            if details:
                self.log(details)
        else:
            self.tests_failed += 1
            self.failures.append(f"{name}: {details}")
            print(f"❌ {name}")
            if details:
                self.log(f"FAILED: {details}")

    def api_call(self, method, endpoint, expected_status=200, data=None, files=None, 
                 description="", token=None, raw_response=False):
        url = f"{BASE_URL}/{endpoint}"
        use_token = token if token is not None else self.token
        headers = {'Authorization': f'Bearer {use_token}'} if use_token else {}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
                else:
                    headers['Content-Type'] = 'application/json'
                    response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                headers['Content-Type'] = 'application/json'
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return None, None

            success = response.status_code == expected_status
            
            if raw_response:
                return success, response
            
            result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            
            if not success:
                self.log(f"Status: {response.status_code} (expected {expected_status})")
                self.log(f"Response: {result}")
            
            return success, result
        except Exception as e:
            self.log(f"Exception: {str(e)}")
            return False, {} if not raw_response else None

    def login(self, email, password):
        success, response = self.api_call('POST', 'auth/login', 200, 
                                         data={"email": email, "password": password},
                                         description="Login", token="")
        if success and 'token' in response:
            return response['token']
        return None

    def cleanup(self):
        """Delete test data created during tests"""
        print("\n🧹 Cleaning up test data...")
        for resource, ids in self.cleanup_ids.items():
            for item_id in ids:
                try:
                    self.api_call('DELETE', f'content/{resource}/{item_id}', expected_status=200)
                    print(f"  Deleted {resource}/{item_id}")
                except:
                    pass

    def summary(self):
        print(f"\n{'='*60}")
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} passed")
        if self.failures:
            print(f"\n❌ Failed tests:")
            for f in self.failures:
                print(f"  - {f}")
        print(f"{'='*60}\n")
        return 0 if self.tests_failed == 0 else 1


def main():
    runner = TestRunner()
    
    print("="*60)
    print("🧪 Testing CMS Gap Closure G1-G10 (Rahaza Travel ERP)")
    print("="*60 + "\n")

    # === LOGIN ===
    print("🔐 Login as owner...")
    runner.token = runner.login("owner@demo.local", "demo12345")
    if not runner.token:
        print("❌ Owner login failed, stopping tests")
        return 1
    print("✅ Logged in as owner\n")

    print("🔐 Login as driver (for RBAC tests)...")
    runner.driver_token = runner.login("driver@demo.local", "demo12345")
    if not runner.driver_token:
        print("⚠️  Driver login failed, RBAC tests will be skipped")
    else:
        print("✅ Logged in as driver\n")

    # ========================================================================
    # G1: UNIQUE SLUG/CODE VALIDATION (409)
    # ========================================================================
    print("="*60)
    print("🧪 G1: Unique slug/code validation (409 on duplicate)")
    print("="*60 + "\n")

    # G1.1: Create destination with unique slug
    print("1️⃣ Creating destination 'unique-dest-a'...")
    success, dest_a = runner.api_call('POST', 'content/destinations', 200, data={
        "slug": "unique-dest-a",
        "name": "Unique Destination A",
        "region": "Jawa Barat",
        "description": "Test destination A"
    })
    runner.test("G1.1: Create destination A", success and dest_a.get('id'),
                f"ID: {dest_a.get('id')}, slug: {dest_a.get('slug')}")
    if success:
        runner.cleanup_ids["destinations"].append(dest_a['id'])

    # G1.2: Try to create another destination with SAME slug → 409
    print("\n2️⃣ Creating destination with SAME slug 'unique-dest-a' → expect 409...")
    success, dup_dest = runner.api_call('POST', 'content/destinations', 409, data={
        "slug": "unique-dest-a",
        "name": "Duplicate Destination",
        "region": "Jawa Tengah",
        "description": "Should fail"
    })
    runner.test("G1.2: Duplicate slug rejected (409)", success,
                f"Response: {dup_dest.get('detail', '')}")
    runner.test("G1.2a: Error message contains 'sudah dipakai'", 
                'sudah dipakai' in str(dup_dest.get('detail', '')).lower(),
                f"Detail: {dup_dest.get('detail', '')}")

    # G1.3: Create destination B with different slug
    print("\n3️⃣ Creating destination 'unique-dest-b'...")
    success, dest_b = runner.api_call('POST', 'content/destinations', 200, data={
        "slug": "unique-dest-b",
        "name": "Unique Destination B",
        "region": "Bali",
        "description": "Test destination B"
    })
    runner.test("G1.3: Create destination B", success and dest_b.get('id'))
    if success:
        runner.cleanup_ids["destinations"].append(dest_b['id'])

    # G1.4: Update destination B slug to A's slug → 409
    if dest_b.get('id'):
        print("\n4️⃣ Updating destination B slug to 'unique-dest-a' → expect 409...")
        success, update_fail = runner.api_call('PUT', f'content/destinations/{dest_b["id"]}', 409, data={
            "slug": "unique-dest-a"
        })
        runner.test("G1.4: Update to duplicate slug rejected (409)", success,
                    f"Response: {update_fail.get('detail', '')}")

    # G1.5: Update destination B slug to SAME value (no-op, should succeed via exclude_id)
    if dest_b.get('id'):
        print("\n5️⃣ Updating destination B slug to its OWN slug (no-op) → expect 200...")
        success, update_ok = runner.api_call('PUT', f'content/destinations/{dest_b["id"]}', 200, data={
            "slug": "unique-dest-b",
            "name": "Updated Name B"
        })
        runner.test("G1.5: Update to same slug allowed (200)", success,
                    f"Slug: {update_ok.get('slug')}")

    # G1.6: Promo code uniqueness
    print("\n6️⃣ Creating promo with code 'PROMO2024'...")
    success, promo_a = runner.api_call('POST', 'content/promos', 200, data={
        "code": "PROMO2024",
        "title": "Promo A",
        "description": "Test promo",
        "discount_type": "percentage",
        "discount_value": 10,
        "active": True
    })
    runner.test("G1.6: Create promo A", success and promo_a.get('id'))
    if success:
        runner.cleanup_ids["promos"].append(promo_a['id'])

    print("\n7️⃣ Creating promo with SAME code 'PROMO2024' → expect 409...")
    success, promo_dup = runner.api_call('POST', 'content/promos', 409, data={
        "code": "PROMO2024",
        "title": "Promo Duplicate",
        "description": "Should fail",
        "discount_type": "fixed",
        "discount_value": 50000,
        "active": True
    })
    runner.test("G1.7: Duplicate promo code rejected (409)", success,
                f"Response: {promo_dup.get('detail', '')}")

    # ========================================================================
    # G2: PUBLIC PROMOS FILTER BY VALID_UNTIL
    # ========================================================================
    print("\n" + "="*60)
    print("🧪 G2: Public promos filter by valid_until (expired hidden)")
    print("="*60 + "\n")

    # G2.1: Create EXPIRED promo (valid_until in past)
    print("1️⃣ Creating EXPIRED promo (valid_until=2020-01-01)...")
    success, promo_expired = runner.api_call('POST', 'content/promos', 200, data={
        "code": "EXPIRED2020",
        "title": "Expired Promo",
        "description": "Should not appear in public",
        "discount_type": "percentage",
        "discount_value": 20,
        "valid_until": "2020-01-01",
        "active": True
    })
    runner.test("G2.1: Create expired promo", success and promo_expired.get('id'))
    if success:
        runner.cleanup_ids["promos"].append(promo_expired['id'])

    # G2.2: Create FUTURE promo (valid_until in future)
    print("\n2️⃣ Creating FUTURE promo (valid_until=2030-12-31)...")
    success, promo_future = runner.api_call('POST', 'content/promos', 200, data={
        "code": "FUTURE2030",
        "title": "Future Promo",
        "description": "Should appear in public",
        "discount_type": "fixed",
        "discount_value": 100000,
        "valid_until": "2030-12-31",
        "active": True
    })
    runner.test("G2.2: Create future promo", success and promo_future.get('id'))
    if success:
        runner.cleanup_ids["promos"].append(promo_future['id'])

    # G2.3: Create promo WITHOUT valid_until (永久有效)
    print("\n3️⃣ Creating promo WITHOUT valid_until (永久)...")
    success, promo_noexp = runner.api_call('POST', 'content/promos', 200, data={
        "code": "NOEXP",
        "title": "No Expiry Promo",
        "description": "Should appear in public",
        "discount_type": "percentage",
        "discount_value": 15,
        "active": True
    })
    runner.test("G2.3: Create no-expiry promo", success and promo_noexp.get('id'))
    if success:
        runner.cleanup_ids["promos"].append(promo_noexp['id'])

    # G2.4: GET /public/promos (NO AUTH) → should return FUTURE2030 & NOEXP, NOT EXPIRED2020
    print("\n4️⃣ GET /public/promos (no auth) → checking filter...")
    success, public_promos = runner.api_call('GET', 'public/promos', 200, token="")
    runner.test("G2.4: GET /public/promos success", success)
    
    if success:
        promo_codes = [p.get('code') for p in public_promos]
        has_future = "FUTURE2030" in promo_codes
        has_noexp = "NOEXP" in promo_codes
        has_expired = "EXPIRED2020" in promo_codes
        
        runner.test("G2.4a: FUTURE2030 visible in public", has_future,
                    f"Codes: {promo_codes}")
        runner.test("G2.4b: NOEXP visible in public", has_noexp,
                    f"Codes: {promo_codes}")
        runner.test("G2.4c: EXPIRED2020 NOT visible in public", not has_expired,
                    f"Codes: {promo_codes}")

    # G2.5: GET /content/promos (CMS admin) → should return ALL 3 promos
    print("\n5️⃣ GET /content/promos (admin) → checking all visible...")
    success, cms_promos = runner.api_call('GET', 'content/promos', 200)
    runner.test("G2.5: GET /content/promos success", success)
    
    if success:
        cms_codes = [p.get('code') for p in cms_promos]
        has_all = all(code in cms_codes for code in ["EXPIRED2020", "FUTURE2030", "NOEXP"])
        runner.test("G2.5a: All 3 promos visible in CMS", has_all,
                    f"Codes: {cms_codes}")

    # ========================================================================
    # G3: IMAGE UPLOAD
    # ========================================================================
    print("\n" + "="*60)
    print("🧪 G3: Image upload POST /api/uploads/cms")
    print("="*60 + "\n")

    # G3.1: Upload valid PNG (small)
    print("1️⃣ Uploading valid PNG (1x1 pixel)...")
    # Create a minimal valid PNG (1x1 pixel, transparent)
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    files = {'image': ('test.png', io.BytesIO(png_data), 'image/png')}
    success, upload_result = runner.api_call('POST', 'uploads/cms', 200, files=files)
    runner.test("G3.1: Upload valid PNG (200)", success,
                f"URL: {upload_result.get('url')}, size: {upload_result.get('size_bytes')} bytes")
    
    uploaded_url = None
    if success:
        runner.test("G3.1a: Response has url field", 'url' in upload_result,
                    f"URL: {upload_result.get('url')}")
        runner.test("G3.1b: Response has size_bytes", 'size_bytes' in upload_result,
                    f"Size: {upload_result.get('size_bytes')}")
        runner.test("G3.1c: Response has content_type", upload_result.get('content_type') == 'image/png',
                    f"Type: {upload_result.get('content_type')}")
        runner.test("G3.1d: URL format correct", 
                    upload_result.get('url', '').startswith('/api/uploads/cms/') and upload_result.get('url', '').endswith('.png'),
                    f"URL: {upload_result.get('url')}")
        uploaded_url = upload_result.get('url')

    # G3.2: GET uploaded image URL → 200, content-type image/png
    if uploaded_url:
        print("\n2️⃣ GET uploaded image URL...")
        full_url = f"https://trip-route-buttons.preview.emergentagent.com{uploaded_url}"
        try:
            img_response = requests.get(full_url, timeout=10)
            success = img_response.status_code == 200
            runner.test("G3.2: GET uploaded image (200)", success,
                        f"Status: {img_response.status_code}")
            runner.test("G3.2a: Content-Type is image/png", 
                        'image/png' in img_response.headers.get('content-type', ''),
                        f"Content-Type: {img_response.headers.get('content-type')}")
        except Exception as e:
            runner.test("G3.2: GET uploaded image", False, f"Exception: {e}")

    # G3.3: Upload text file (text/plain) → 415
    print("\n3️⃣ Uploading text file → expect 415...")
    txt_data = b'This is a text file'
    files = {'image': ('test.txt', io.BytesIO(txt_data), 'text/plain')}
    success, txt_result = runner.api_call('POST', 'uploads/cms', 415, files=files)
    runner.test("G3.3: Upload text file rejected (415)", success,
                f"Response: {txt_result.get('detail', '')}")
    runner.test("G3.3a: Error message mentions 'tidak didukung'",
                'tidak didukung' in str(txt_result.get('detail', '')).lower(),
                f"Detail: {txt_result.get('detail', '')}")

    # G3.4: Upload file >6MB → 413
    print("\n4️⃣ Uploading file >6MB → expect 413...")
    large_data = b'X' * (7 * 1024 * 1024)  # 7MB
    files = {'image': ('large.png', io.BytesIO(large_data), 'image/png')}
    success, large_result = runner.api_call('POST', 'uploads/cms', 413, files=files)
    runner.test("G3.4: Upload >6MB rejected (413)", success,
                f"Response: {large_result.get('detail', '')}")
    runner.test("G3.4a: Error message mentions '6MB'",
                '6mb' in str(large_result.get('detail', '')).lower(),
                f"Detail: {large_result.get('detail', '')}")

    # G3.5: Upload without 'image' field → 400 or 422
    print("\n5️⃣ Uploading without 'image' field → expect 400/422...")
    success, no_field = runner.api_call('POST', 'uploads/cms', expected_status=400, files={})
    if not success:
        # Try 422 if 400 didn't work
        success, no_field = runner.api_call('POST', 'uploads/cms', expected_status=422, files={})
    runner.test("G3.5: Upload without field rejected (400/422)", success,
                f"Response: {no_field.get('detail', '') if isinstance(no_field, dict) else no_field}")

    # G3.6: RBAC - driver token → 403
    if runner.driver_token:
        print("\n6️⃣ Upload with driver token → expect 403...")
        files = {'image': ('test.png', io.BytesIO(png_data), 'image/png')}
        success, driver_upload = runner.api_call('POST', 'uploads/cms', 403, files=files, token=runner.driver_token)
        runner.test("G3.6: Driver upload rejected (403)", success,
                    f"Response: {driver_upload.get('detail', '')}")

    # ========================================================================
    # G4: DESTINATIONS NEW FIELDS (intro/route_points/faqs)
    # ========================================================================
    print("\n" + "="*60)
    print("🧪 G4: Destinations new fields (intro/route_points/faqs)")
    print("="*60 + "\n")

    print("1️⃣ Creating destination with intro/route_points/faqs...")
    success, dest_g4 = runner.api_call('POST', 'content/destinations', 200, data={
        "slug": "dest-g4-test",
        "name": "Destination G4 Test",
        "region": "Jawa Timur",
        "description": "Test G4 fields",
        "intro": "This is the intro text for G4",
        "route_points": [
            {"name": "Point A", "lat": -6.9, "lng": 107.6},
            {"name": "Point B", "lat": -7.0, "lng": 107.7}
        ],
        "faqs": [
            {"q": "Question 1?", "a": "Answer 1"},
            {"q": "Question 2?", "a": "Answer 2"}
        ]
    })
    runner.test("G4.1: Create destination with new fields", success and dest_g4.get('id'))
    if success:
        runner.cleanup_ids["destinations"].append(dest_g4['id'])

    # G4.2: GET destination → verify fields are stored
    if dest_g4.get('id'):
        print("\n2️⃣ GET destination → verifying fields stored...")
        success, dest_verify = runner.api_call('GET', f'content/destinations', 200)
        if success:
            found = next((d for d in dest_verify if d.get('id') == dest_g4['id']), None)
            if found:
                runner.test("G4.2: intro field stored", found.get('intro') == "This is the intro text for G4",
                            f"intro: {found.get('intro')}")
                runner.test("G4.3: route_points field stored", 
                            isinstance(found.get('route_points'), list) and len(found.get('route_points', [])) == 2,
                            f"route_points: {found.get('route_points')}")
                runner.test("G4.4: faqs field stored",
                            isinstance(found.get('faqs'), list) and len(found.get('faqs', [])) == 2,
                            f"faqs: {found.get('faqs')}")
            else:
                runner.test("G4.2: Destination found in list", False, "Not found")

    # ========================================================================
    # G5: SEARCH QUERY PARAMETER
    # ========================================================================
    print("\n" + "="*60)
    print("🧪 G5: Search query parameter ?q= (case-insensitive)")
    print("="*60 + "\n")

    # G5.1: Create destinations for search test
    print("1️⃣ Creating destinations 'SearchAlpha' and 'SearchBeta'...")
    success, search_alpha = runner.api_call('POST', 'content/destinations', 200, data={
        "slug": "search-alpha",
        "name": "SearchAlpha",
        "region": "Region A",
        "description": "Alpha destination"
    })
    runner.test("G5.1: Create SearchAlpha", success and search_alpha.get('id'))
    if success:
        runner.cleanup_ids["destinations"].append(search_alpha['id'])

    success, search_beta = runner.api_call('POST', 'content/destinations', 200, data={
        "slug": "search-beta",
        "name": "SearchBeta",
        "region": "Region B",
        "description": "Beta destination"
    })
    runner.test("G5.2: Create SearchBeta", success and search_beta.get('id'))
    if success:
        runner.cleanup_ids["destinations"].append(search_beta['id'])

    # G5.3: Search with q=search → should return both
    print("\n2️⃣ Search with q=search → expect both results...")
    success, search_results = runner.api_call('GET', 'content/destinations?q=search', 200)
    runner.test("G5.3: Search q=search", success)
    if success:
        names = [d.get('name') for d in search_results]
        has_alpha = "SearchAlpha" in names
        has_beta = "SearchBeta" in names
        runner.test("G5.3a: SearchAlpha in results", has_alpha, f"Names: {names}")
        runner.test("G5.3b: SearchBeta in results", has_beta, f"Names: {names}")

    # G5.4: Search with q=alpha → should return only SearchAlpha
    print("\n3️⃣ Search with q=alpha → expect only SearchAlpha...")
    success, alpha_results = runner.api_call('GET', 'content/destinations?q=alpha', 200)
    runner.test("G5.4: Search q=alpha", success)
    if success:
        names = [d.get('name') for d in alpha_results]
        has_alpha = "SearchAlpha" in names
        has_beta = "SearchBeta" in names
        runner.test("G5.4a: SearchAlpha in results", has_alpha, f"Names: {names}")
        runner.test("G5.4b: SearchBeta NOT in results", not has_beta, f"Names: {names}")

    # G5.5: Search with q=Alpha (case-insensitive) → should return SearchAlpha
    print("\n4️⃣ Search with q=Alpha (uppercase) → expect SearchAlpha...")
    success, case_results = runner.api_call('GET', 'content/destinations?q=Alpha', 200)
    runner.test("G5.5: Search q=Alpha (case-insensitive)", success)
    if success:
        names = [d.get('name') for d in case_results]
        has_alpha = "SearchAlpha" in names
        runner.test("G5.5a: SearchAlpha found (case-insensitive)", has_alpha, f"Names: {names}")

    # G5.6: Search in articles (title/author/category)
    print("\n5️⃣ Creating articles for search test...")
    success, article_search = runner.api_call('POST', 'content/articles', 200, data={
        "slug": "article-search-test",
        "title": "SearchArticle Title",
        "excerpt": "Excerpt",
        "body": "Body",
        "author": "John Doe",
        "category": "Travel",
        "published": True
    })
    runner.test("G5.6: Create article for search", success and article_search.get('id'))
    if success:
        runner.cleanup_ids["articles"].append(article_search['id'])

    print("\n6️⃣ Search articles with q=searcharticle...")
    success, article_results = runner.api_call('GET', 'content/articles?q=searcharticle', 200)
    runner.test("G5.7: Search articles q=searcharticle", success)
    if success:
        titles = [a.get('title') for a in article_results]
        found = "SearchArticle Title" in titles
        runner.test("G5.7a: Article found by title search", found, f"Titles: {titles}")

    # ========================================================================
    # G6: SEO METADATA FIELDS
    # ========================================================================
    print("\n" + "="*60)
    print("🧪 G6: SEO metadata fields (meta_title/meta_description/og_image)")
    print("="*60 + "\n")

    # G6.1: Create destination with SEO fields
    print("1️⃣ Creating destination with SEO metadata...")
    success, dest_seo = runner.api_call('POST', 'content/destinations', 200, data={
        "slug": "dest-seo-test",
        "name": "SEO Destination",
        "region": "Bali",
        "description": "Test SEO fields",
        "meta_title": "SEO Title for Destination",
        "meta_description": "This is the meta description for SEO",
        "og_image": "/api/uploads/cms/seo-image.png"
    })
    runner.test("G6.1: Create destination with SEO fields", success and dest_seo.get('id'))
    if success:
        runner.cleanup_ids["destinations"].append(dest_seo['id'])

    # G6.2: GET /content/destinations/{id} → verify SEO fields stored
    if dest_seo.get('id'):
        print("\n2️⃣ GET destination → verifying SEO fields...")
        success, seo_verify = runner.api_call('GET', 'content/destinations', 200)
        if success:
            found = next((d for d in seo_verify if d.get('id') == dest_seo['id']), None)
            if found:
                runner.test("G6.2: meta_title stored", found.get('meta_title') == "SEO Title for Destination",
                            f"meta_title: {found.get('meta_title')}")
                runner.test("G6.3: meta_description stored", 
                            found.get('meta_description') == "This is the meta description for SEO",
                            f"meta_description: {found.get('meta_description')}")
                runner.test("G6.4: og_image stored", found.get('og_image') == "/api/uploads/cms/seo-image.png",
                            f"og_image: {found.get('og_image')}")

    # G6.5: GET /public/destinations/{slug} → verify SEO fields in public response
    if dest_seo.get('slug'):
        print("\n3️⃣ GET /public/destinations/{slug} → verifying SEO in public...")
        success, public_seo = runner.api_call('GET', f'public/destinations/{dest_seo["slug"]}', 200, token="")
        runner.test("G6.5: GET public destination", success)
        if success:
            runner.test("G6.5a: meta_title in public response", 
                        public_seo.get('meta_title') == "SEO Title for Destination",
                        f"meta_title: {public_seo.get('meta_title')}")
            runner.test("G6.5b: meta_description in public response",
                        public_seo.get('meta_description') == "This is the meta description for SEO",
                        f"meta_description: {public_seo.get('meta_description')}")
            runner.test("G6.5c: og_image in public response",
                        public_seo.get('og_image') == "/api/uploads/cms/seo-image.png",
                        f"og_image: {public_seo.get('og_image')}")

    # G6.6: Test SEO fields for articles
    print("\n4️⃣ Creating article with SEO metadata...")
    success, article_seo = runner.api_call('POST', 'content/articles', 200, data={
        "slug": "article-seo-test",
        "title": "SEO Article",
        "excerpt": "Excerpt",
        "body": "Body",
        "author": "Jane Doe",
        "published": True,
        "meta_title": "SEO Title for Article",
        "meta_description": "Article meta description",
        "og_image": "/api/uploads/cms/article-og.png"
    })
    runner.test("G6.6: Create article with SEO fields", success and article_seo.get('id'))
    if success:
        runner.cleanup_ids["articles"].append(article_seo['id'])

    # ========================================================================
    # G8: DUPLICATE CONTENT ENDPOINT
    # ========================================================================
    print("\n" + "="*60)
    print("🧪 G8: Duplicate content endpoint (slug auto-suffix)")
    print("="*60 + "\n")

    # G8.1: Create destination to duplicate
    print("1️⃣ Creating destination for duplication...")
    success, dest_orig = runner.api_call('POST', 'content/destinations', 200, data={
        "slug": "original-dest",
        "name": "Original Destination",
        "region": "Jawa Barat",
        "description": "Original description"
    })
    runner.test("G8.1: Create original destination", success and dest_orig.get('id'))
    if success:
        runner.cleanup_ids["destinations"].append(dest_orig['id'])

    # G8.2: Duplicate destination → slug should be 'original-dest-copy'
    if dest_orig.get('id'):
        print("\n2️⃣ Duplicating destination...")
        success, dest_dup1 = runner.api_call('POST', f'content/destinations/{dest_orig["id"]}/duplicate', 200)
        runner.test("G8.2: Duplicate destination (200)", success and dest_dup1.get('id'))
        if success:
            runner.cleanup_ids["destinations"].append(dest_dup1['id'])
            runner.test("G8.2a: New ID generated", dest_dup1.get('id') != dest_orig['id'],
                        f"New ID: {dest_dup1.get('id')}")
            runner.test("G8.2b: Slug has '-copy' suffix", dest_dup1.get('slug') == "original-dest-copy",
                        f"Slug: {dest_dup1.get('slug')}")
            runner.test("G8.2c: Name has '(Salinan)' suffix", "(Salinan)" in dest_dup1.get('name', ''),
                        f"Name: {dest_dup1.get('name')}")

    # G8.3: Duplicate again → slug should be 'original-dest-copy-2'
    if dest_orig.get('id'):
        print("\n3️⃣ Duplicating again...")
        success, dest_dup2 = runner.api_call('POST', f'content/destinations/{dest_orig["id"]}/duplicate', 200)
        runner.test("G8.3: Duplicate again (200)", success and dest_dup2.get('id'))
        if success:
            runner.cleanup_ids["destinations"].append(dest_dup2['id'])
            runner.test("G8.3a: Slug has '-copy-2' suffix", dest_dup2.get('slug') == "original-dest-copy-2",
                        f"Slug: {dest_dup2.get('slug')}")

    # G8.4: Duplicate testimonial → approved should be False
    print("\n4️⃣ Creating testimonial for duplication...")
    success, testi_orig = runner.api_call('POST', 'content/testimonials', 200, data={
        "name": "John Doe",
        "role": "Customer",
        "quote": "Great service!",
        "rating": 5,
        "approved": True
    })
    runner.test("G8.4: Create testimonial", success and testi_orig.get('id'))
    if success:
        runner.cleanup_ids["testimonials"].append(testi_orig['id'])

    if testi_orig.get('id'):
        print("\n5️⃣ Duplicating testimonial...")
        success, testi_dup = runner.api_call('POST', f'content/testimonials/{testi_orig["id"]}/duplicate', 200)
        runner.test("G8.5: Duplicate testimonial (200)", success and testi_dup.get('id'))
        if success:
            runner.cleanup_ids["testimonials"].append(testi_dup['id'])
            runner.test("G8.5a: approved reset to False", testi_dup.get('approved') == False,
                        f"approved: {testi_dup.get('approved')}")

    # G8.6: Duplicate article → published should be False
    print("\n6️⃣ Creating article for duplication...")
    success, article_orig = runner.api_call('POST', 'content/articles', 200, data={
        "slug": "article-to-duplicate",
        "title": "Article to Duplicate",
        "excerpt": "Excerpt",
        "body": "Body",
        "author": "Author",
        "published": True
    })
    runner.test("G8.6: Create article", success and article_orig.get('id'))
    if success:
        runner.cleanup_ids["articles"].append(article_orig['id'])

    if article_orig.get('id'):
        print("\n7️⃣ Duplicating article...")
        success, article_dup = runner.api_call('POST', f'content/articles/{article_orig["id"]}/duplicate', 200)
        runner.test("G8.7: Duplicate article (200)", success and article_dup.get('id'))
        if success:
            runner.cleanup_ids["articles"].append(article_dup['id'])
            runner.test("G8.7a: published reset to False", article_dup.get('published') == False,
                        f"published: {article_dup.get('published')}")

    # G8.8: Duplicate promo → active should be False
    print("\n8️⃣ Creating promo for duplication...")
    success, promo_orig = runner.api_call('POST', 'content/promos', 200, data={
        "code": "PROMO-DUP",
        "title": "Promo to Duplicate",
        "description": "Test",
        "discount_type": "percentage",
        "discount_value": 10,
        "active": True
    })
    runner.test("G8.8: Create promo", success and promo_orig.get('id'))
    if success:
        runner.cleanup_ids["promos"].append(promo_orig['id'])

    if promo_orig.get('id'):
        print("\n9️⃣ Duplicating promo...")
        success, promo_dup = runner.api_call('POST', f'content/promos/{promo_orig["id"]}/duplicate', 200)
        runner.test("G8.9: Duplicate promo (200)", success and promo_dup.get('id'))
        if success:
            runner.cleanup_ids["promos"].append(promo_dup['id'])
            runner.test("G8.9a: active reset to False", promo_dup.get('active') == False,
                        f"active: {promo_dup.get('active')}")

    # G8.10: RBAC - driver → 403
    if runner.driver_token and dest_orig.get('id'):
        print("\n🔟 Duplicate with driver token → expect 403...")
        success, driver_dup = runner.api_call('POST', f'content/destinations/{dest_orig["id"]}/duplicate', 403, 
                                              token=runner.driver_token)
        runner.test("G8.10: Driver duplicate rejected (403)", success)

    # G8.11: Duplicate non-existent ID → 404
    print("\n1️⃣1️⃣ Duplicate non-existent ID → expect 404...")
    success, not_found = runner.api_call('POST', 'content/destinations/dst_nonexistent/duplicate', 404)
    runner.test("G8.11: Duplicate non-existent ID (404)", success)

    # ========================================================================
    # G9: TESTIMONIALS MODERATION
    # ========================================================================
    print("\n" + "="*60)
    print("🧪 G9: Testimonials moderation (approved field)")
    print("="*60 + "\n")

    # G9.1: Create approved testimonial
    print("1️⃣ Creating APPROVED testimonial...")
    success, testi_approved = runner.api_call('POST', 'content/testimonials', 200, data={
        "name": "Approved Testi",
        "role": "Customer",
        "quote": "Excellent!",
        "rating": 5,
        "approved": True
    })
    runner.test("G9.1: Create approved testimonial", success and testi_approved.get('id'))
    if success:
        runner.cleanup_ids["testimonials"].append(testi_approved['id'])

    # G9.2: Create pending testimonial (approved=False)
    print("\n2️⃣ Creating PENDING testimonial (approved=False)...")
    success, testi_pending = runner.api_call('POST', 'content/testimonials', 200, data={
        "name": "Pending Testi",
        "role": "Customer",
        "quote": "Waiting approval",
        "rating": 4,
        "approved": False
    })
    runner.test("G9.2: Create pending testimonial", success and testi_pending.get('id'))
    if success:
        runner.cleanup_ids["testimonials"].append(testi_pending['id'])

    # G9.3: Create legacy testimonial (no approved field - backward compat)
    print("\n3️⃣ Creating LEGACY testimonial (no approved field)...")
    success, testi_legacy = runner.api_call('POST', 'content/testimonials', 200, data={
        "name": "Legacy Testi",
        "role": "Customer",
        "quote": "Old data",
        "rating": 5
    })
    runner.test("G9.3: Create legacy testimonial", success and testi_legacy.get('id'))
    if success:
        runner.cleanup_ids["testimonials"].append(testi_legacy['id'])

    # G9.4: GET /public/testimonials → should show approved & legacy, NOT pending
    print("\n4️⃣ GET /public/testimonials → checking filter...")
    success, public_testis = runner.api_call('GET', 'public/testimonials', 200, token="")
    runner.test("G9.4: GET /public/testimonials", success)
    if success:
        names = [t.get('name') for t in public_testis]
        has_approved = "Approved Testi" in names
        has_legacy = "Legacy Testi" in names
        has_pending = "Pending Testi" in names
        
        runner.test("G9.4a: Approved testimonial visible", has_approved, f"Names: {names}")
        runner.test("G9.4b: Legacy testimonial visible (backward compat)", has_legacy, f"Names: {names}")
        runner.test("G9.4c: Pending testimonial NOT visible", not has_pending, f"Names: {names}")

    # G9.5: GET /content/testimonials (admin) → should show all 3
    print("\n5️⃣ GET /content/testimonials (admin) → checking all visible...")
    success, cms_testis = runner.api_call('GET', 'content/testimonials', 200)
    runner.test("G9.5: GET /content/testimonials", success)
    if success:
        cms_names = [t.get('name') for t in cms_testis]
        has_all = all(name in cms_names for name in ["Approved Testi", "Pending Testi", "Legacy Testi"])
        runner.test("G9.5a: All 3 testimonials visible in CMS", has_all, f"Names: {cms_names}")

    # ========================================================================
    # G10: SORT BY POSITION
    # ========================================================================
    print("\n" + "="*60)
    print("🧪 G10: Sort by position (ascending order)")
    print("="*60 + "\n")

    # G10.1: Create destinations with different positions
    print("1️⃣ Creating destinations with positions 3, 1, 2...")
    success, dest_pos3 = runner.api_call('POST', 'content/destinations', 200, data={
        "slug": "dest-pos-3",
        "name": "Destination Position 3",
        "region": "Region",
        "description": "Pos 3",
        "position": 3
    })
    runner.test("G10.1: Create destination position=3", success and dest_pos3.get('id'))
    if success:
        runner.cleanup_ids["destinations"].append(dest_pos3['id'])

    success, dest_pos1 = runner.api_call('POST', 'content/destinations', 200, data={
        "slug": "dest-pos-1",
        "name": "Destination Position 1",
        "region": "Region",
        "description": "Pos 1",
        "position": 1
    })
    runner.test("G10.2: Create destination position=1", success and dest_pos1.get('id'))
    if success:
        runner.cleanup_ids["destinations"].append(dest_pos1['id'])

    success, dest_pos2 = runner.api_call('POST', 'content/destinations', 200, data={
        "slug": "dest-pos-2",
        "name": "Destination Position 2",
        "region": "Region",
        "description": "Pos 2",
        "position": 2
    })
    runner.test("G10.3: Create destination position=2", success and dest_pos2.get('id'))
    if success:
        runner.cleanup_ids["destinations"].append(dest_pos2['id'])

    # G10.4: GET /content/destinations → verify order (1, 2, 3)
    print("\n2️⃣ GET /content/destinations → verifying sort order...")
    success, sorted_dests = runner.api_call('GET', 'content/destinations', 200)
    runner.test("G10.4: GET destinations", success)
    if success:
        # Find our test destinations
        test_dests = [d for d in sorted_dests if d.get('slug', '').startswith('dest-pos-')]
        if len(test_dests) >= 3:
            positions = [d.get('position') for d in test_dests[:3]]
            runner.test("G10.4a: Destinations sorted by position (ascending)", 
                        positions == sorted(positions),
                        f"Positions: {positions}")
            # Check first is position=1
            first_pos = test_dests[0].get('position')
            runner.test("G10.4b: First destination has position=1", first_pos == 1,
                        f"First position: {first_pos}")

    # G10.5: GET /public/destinations → verify same order
    print("\n3️⃣ GET /public/destinations → verifying sort order...")
    success, public_sorted = runner.api_call('GET', 'public/destinations', 200, token="")
    runner.test("G10.5: GET public destinations", success)
    if success:
        test_public = [d for d in public_sorted if d.get('slug', '').startswith('dest-pos-')]
        if len(test_public) >= 3:
            positions = [d.get('position') for d in test_public[:3]]
            runner.test("G10.5a: Public destinations sorted by position", 
                        positions == sorted(positions),
                        f"Positions: {positions}")

    # G10.6: Update position → verify order changes
    if dest_pos1.get('id'):
        print("\n4️⃣ Updating position=1 to position=5...")
        success, updated = runner.api_call('PUT', f'content/destinations/{dest_pos1["id"]}', 200, data={
            "position": 5
        })
        runner.test("G10.6: Update position", success)

        print("\n5️⃣ GET destinations → verifying new order...")
        success, reordered = runner.api_call('GET', 'content/destinations', 200)
        if success:
            test_reordered = [d for d in reordered if d.get('slug', '').startswith('dest-pos-')]
            if len(test_reordered) >= 3:
                # Now order should be: pos=2, pos=3, pos=5
                positions = [d.get('position') for d in test_reordered[:3]]
                runner.test("G10.7: Order changed after update",
                            positions == sorted(positions) and positions[0] == 2,
                            f"New positions: {positions}")

    # ========================================================================
    # REGRESSION: AUTH & RBAC
    # ========================================================================
    print("\n" + "="*60)
    print("🧪 REGRESSION: Auth & RBAC")
    print("="*60 + "\n")

    # REG.1: POST /content/* without auth → 401
    print("1️⃣ POST /content/destinations without auth → expect 401...")
    success, no_auth = runner.api_call('POST', 'content/destinations', 401, 
                                       data={"slug": "test", "name": "Test"}, token="")
    runner.test("REG.1: POST without auth rejected (401)", success)

    # REG.2: Driver token → 403 on all /content/* endpoints
    if runner.driver_token:
        print("\n2️⃣ Driver access to /content/* → expect 403...")
        
        # GET
        success, driver_get = runner.api_call('GET', 'content/destinations', 403, token=runner.driver_token)
        runner.test("REG.2a: Driver GET /content/* (403)", success)
        
        # POST
        success, driver_post = runner.api_call('POST', 'content/destinations', 403,
                                               data={"slug": "test", "name": "Test"}, 
                                               token=runner.driver_token)
        runner.test("REG.2b: Driver POST /content/* (403)", success)
        
        # PUT (use existing destination)
        if dest_orig.get('id'):
            success, driver_put = runner.api_call('PUT', f'content/destinations/{dest_orig["id"]}', 403,
                                                  data={"name": "Updated"}, token=runner.driver_token)
            runner.test("REG.2c: Driver PUT /content/* (403)", success)
        
        # DELETE
        if dest_orig.get('id'):
            success, driver_del = runner.api_call('DELETE', f'content/destinations/{dest_orig["id"]}', 403,
                                                  token=runner.driver_token)
            runner.test("REG.2d: Driver DELETE /content/* (403)", success)

    # REG.3: Driver can access /public/* → 200
    if runner.driver_token:
        print("\n3️⃣ Driver access to /public/* → expect 200...")
        success, driver_public = runner.api_call('GET', 'public/destinations', 200, token=runner.driver_token)
        runner.test("REG.3: Driver GET /public/* (200)", success)

    # REG.4: Audit log check (optional)
    print("\n4️⃣ Checking audit log...")
    success, audit = runner.api_call('GET', 'audit?limit=10', 200)
    runner.test("REG.4: GET /audit (200)", success)
    if success:
        runner.test("REG.4a: Audit log has entries", len(audit) > 0,
                    f"Entries: {len(audit)}")

    # ========================================================================
    # CLEANUP
    # ========================================================================
    runner.cleanup()

    return runner.summary()


if __name__ == "__main__":
    sys.exit(main())
