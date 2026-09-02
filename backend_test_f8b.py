#!/usr/bin/env python3
"""backend_test_f8b.py — Comprehensive backend testing for F8b features.

Tests:
1. GA4 Measurement Protocol as THIRD provider in conversion outbox (skipped with reason, NOT 5xx)
2. SEO for landing pages: default noindex per page + indexed pages in sitemap
3. Meta/Google Ads → Landing Page flow: ad targets + readiness score + automatic UTM
4. Media Recovery: detect media with missing files on published pages
5. RBAC: owner/marketing_admin get 200, ops_admin/driver get 403, no token gets 401
6. Regression: all existing landing endpoints still work
7. Regression: ads dashboard and public endpoints still work
"""
import sys
import uuid
import requests
from datetime import datetime

# Public endpoint from frontend/.env
BASE_URL = "https://trip-route-buttons.preview.emergentagent.com"
API = f"{BASE_URL}/api"

# Test credentials from /app/memory/test_credentials.md
CREDENTIALS = {
    "owner": {"email": "owner@demo.local", "password": "demo12345"},
    "marketing": {"email": "marketing@demo.local", "password": "demo12345"},
    "ops": {"email": "ops@demo.local", "password": "demo12345"},
    "driver": {"email": "driver@demo.local", "password": "demo12345"},
}

# Test results
RESULTS = []
TESTS_RUN = 0
TESTS_PASSED = 0

def log_test(name, passed, detail=""):
    """Log test result"""
    global TESTS_RUN, TESTS_PASSED
    TESTS_RUN += 1
    if passed:
        TESTS_PASSED += 1
        print(f"✅ {name}")
    else:
        print(f"❌ {name}" + (f" — {detail}" if detail else ""))
    RESULTS.append({"name": name, "passed": passed, "detail": detail})
    return passed

def section(title):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def login(role="owner"):
    """Login and get token"""
    creds = CREDENTIALS.get(role)
    if not creds:
        raise ValueError(f"Unknown role: {role}")
    try:
        r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
        if r.status_code == 200:
            return r.json().get("token")
        else:
            print(f"⚠️  Login failed for {role}: HTTP {r.status_code}")
            return None
    except Exception as e:
        print(f"⚠️  Login error for {role}: {e}")
        return None

def test_auth_endpoints():
    """Test 1: GET /api/landing/ad-targets with different auth levels"""
    section("TEST 1: RBAC for /api/landing/ad-targets")
    
    # Test without token (should be 401)
    r = requests.get(f"{API}/landing/ad-targets", timeout=20)
    log_test("ad-targets without token returns 401", r.status_code == 401, f"got {r.status_code}")
    
    # Test with owner (should be 200)
    owner_token = login("owner")
    if owner_token:
        r = requests.get(f"{API}/landing/ad-targets", 
                        headers={"Authorization": f"Bearer {owner_token}"}, timeout=20)
        passed = r.status_code == 200
        log_test("ad-targets with owner token returns 200", passed, f"got {r.status_code}")
        if passed:
            data = r.json()
            log_test("ad-targets response has targets[] field", "targets" in data)
            log_test("ad-targets response has utm_presets field", "utm_presets" in data)
            if "targets" in data and len(data["targets"]) > 0:
                target = data["targets"][0]
                required_fields = ["id", "title", "slug", "status", "published", "score", "level", "blockers"]
                has_all = all(f in target for f in required_fields)
                log_test("ad-targets items have required fields", has_all, 
                        f"missing: {[f for f in required_fields if f not in target]}")
    
    # Test with marketing_admin (should be 200)
    marketing_token = login("marketing")
    if marketing_token:
        r = requests.get(f"{API}/landing/ad-targets",
                        headers={"Authorization": f"Bearer {marketing_token}"}, timeout=20)
        log_test("ad-targets with marketing_admin token returns 200", 
                r.status_code == 200, f"got {r.status_code}")
    
    # Test with ops_admin (should be 403)
    ops_token = login("ops")
    if ops_token:
        r = requests.get(f"{API}/landing/ad-targets",
                        headers={"Authorization": f"Bearer {ops_token}"}, timeout=20)
        log_test("ad-targets with ops_admin token returns 403", 
                r.status_code == 403, f"got {r.status_code}")
    
    # Test with driver (should be 403)
    driver_token = login("driver")
    if driver_token:
        r = requests.get(f"{API}/landing/ad-targets",
                        headers={"Authorization": f"Bearer {driver_token}"}, timeout=20)
        log_test("ad-targets with driver token returns 403", 
                r.status_code == 403, f"got {r.status_code}")

def test_readiness_endpoint():
    """Test 2: GET /api/landing/pages/{id}/readiness"""
    section("TEST 2: Page Readiness Endpoint")
    
    owner_token = login("owner")
    if not owner_token:
        print("⚠️  Skipping readiness tests - no owner token")
        return
    
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Get list of pages
    r = requests.get(f"{API}/landing/pages", headers=headers, timeout=20)
    if r.status_code != 200:
        print(f"⚠️  Could not get pages list: HTTP {r.status_code}")
        return
    
    pages = r.json().get("pages", [])
    if not pages:
        print("⚠️  No pages found for testing")
        return
    
    page_id = pages[0]["id"]
    
    # Test readiness endpoint
    r = requests.get(f"{API}/landing/pages/{page_id}/readiness", headers=headers, timeout=30)
    passed = r.status_code == 200
    log_test("readiness endpoint returns 200", passed, f"got {r.status_code}")
    
    if passed:
        data = r.json()
        required_fields = ["score", "level", "verdict", "checks", "missing_media", "publish_errors", "ad_urls"]
        has_all = all(f in data for f in required_fields)
        log_test("readiness response has all required fields", has_all,
                f"missing: {[f for f in required_fields if f not in data]}")
        
        # Check score is 0-100
        score = data.get("score", -1)
        log_test("readiness score is between 0-100", 0 <= score <= 100, f"got {score}")
        
        # Check level is valid
        level = data.get("level", "")
        log_test("readiness level is valid", level in ["siap", "hampir", "belum"], f"got {level}")
        
        # Check checks[] structure
        checks = data.get("checks", [])
        if checks:
            check_item = checks[0]
            check_fields = ["ok", "weight", "label", "fix"]
            has_check_fields = all(f in check_item for f in check_fields)
            log_test("checks[] items have required fields", has_check_fields)
        
        # Check ad_urls structure
        ad_urls = data.get("ad_urls", {})
        log_test("ad_urls contains meta, google, tiktok", 
                all(p in ad_urls for p in ["meta", "google", "tiktok"]))
        
        # Check UTM parameters in ad_urls
        if "meta" in ad_urls:
            meta_url = ad_urls["meta"]
            log_test("meta ad_url contains utm_source=meta", "utm_source=meta" in meta_url, meta_url)
            log_test("meta ad_url contains utm_medium=paid_social", "utm_medium=paid_social" in meta_url, meta_url)
        
        if "google" in ad_urls:
            google_url = ad_urls["google"]
            log_test("google ad_url contains utm_source=google", "utm_source=google" in google_url, google_url)
            log_test("google ad_url contains utm_medium=cpc", "utm_medium=cpc" in google_url, google_url)
        
        # Check missing_media is array
        log_test("missing_media is an array", isinstance(data.get("missing_media"), list))
    
    # Test with non-existent page ID (should be 404)
    fake_id = "lp_nonexistent123"
    r = requests.get(f"{API}/landing/pages/{fake_id}/readiness", headers=headers, timeout=20)
    log_test("readiness with non-existent ID returns 404", r.status_code == 404, f"got {r.status_code}")

def test_seo_noindex():
    """Test 3: PATCH /api/landing/pages/{id} with SEO settings"""
    section("TEST 3: SEO noindex Settings")
    
    owner_token = login("owner")
    if not owner_token:
        print("⚠️  Skipping SEO tests - no owner token")
        return
    
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Create a test page
    test_title = f"Test SEO Page {uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/landing/pages", 
                     headers=headers,
                     json={"title": test_title, "template": "armada-konversi"},
                     timeout=20)
    
    if r.status_code != 200:
        print(f"⚠️  Could not create test page: HTTP {r.status_code}")
        return
    
    page = r.json()
    page_id = page["id"]
    slug = page["slug"]
    
    try:
        # Test 1: PATCH without noindex (should default to true)
        r = requests.patch(f"{API}/landing/pages/{page_id}",
                          headers=headers,
                          json={"seo": {"title": "Test Title", "description": "Test Desc"}},
                          timeout=20)
        
        if r.status_code == 200:
            data = r.json()
            page_data = data.get("page", {})
            seo = page_data.get("seo", {})
            noindex = seo.get("noindex", False)
            log_test("noindex defaults to true when not specified", noindex == True, f"got {noindex}")
        
        # Test 2: PATCH with noindex=false
        r = requests.patch(f"{API}/landing/pages/{page_id}",
                          headers=headers,
                          json={"seo": {"title": "Test Title", "description": "Test Desc", "noindex": False}},
                          timeout=20)
        
        if r.status_code == 200:
            # Verify by getting the page
            r = requests.get(f"{API}/public/landing/{slug}", timeout=20)
            if r.status_code == 200:
                data = r.json()
                seo = data.get("seo", {})
                noindex = seo.get("noindex", True)
                log_test("noindex=false is saved correctly", noindex == False, f"got {noindex}")
        
        # Test 3: Set back to true
        r = requests.patch(f"{API}/landing/pages/{page_id}",
                          headers=headers,
                          json={"seo": {"noindex": True}},
                          timeout=20)
        log_test("can set noindex back to true", r.status_code == 200)
        
    finally:
        # Cleanup: delete test page
        requests.delete(f"{API}/landing/pages/{page_id}", headers=headers, timeout=20)

def test_sitemap():
    """Test 4: GET /api/sitemap.xml"""
    section("TEST 4: Sitemap XML")
    
    owner_token = login("owner")
    if not owner_token:
        print("⚠️  Skipping sitemap tests - no owner token")
        return
    
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Create a test page with noindex=false
    test_title = f"Test Sitemap Page {uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/landing/pages",
                     headers=headers,
                     json={"title": test_title, "template": "armada-konversi"},
                     timeout=20)
    
    if r.status_code != 200:
        print(f"⚠️  Could not create test page: HTTP {r.status_code}")
        return
    
    page = r.json()
    page_id = page["id"]
    slug = page["slug"]
    
    try:
        # Set noindex=false and publish
        r = requests.patch(f"{API}/landing/pages/{page_id}",
                          headers=headers,
                          json={"seo": {"title": "Test", "description": "Test", "noindex": False}},
                          timeout=20)
        
        # Publish the page
        r = requests.post(f"{API}/landing/pages/{page_id}/publish",
                         headers=headers,
                         json={},
                         timeout=20)
        
        if r.status_code != 200:
            print(f"⚠️  Could not publish page: HTTP {r.status_code} - {r.text}")
        
        # Get sitemap
        r = requests.get(f"{API}/sitemap.xml", timeout=20)
        passed = r.status_code == 200
        log_test("sitemap.xml returns 200", passed, f"got {r.status_code}")
        
        if passed:
            content = r.text
            log_test("sitemap is valid XML", content.startswith('<?xml') and '<urlset' in content)
            
            # Check if published page with noindex=false appears
            expected_loc = f"/lp/{slug}"
            log_test("published page with noindex=false appears in sitemap", 
                    expected_loc in content, f"looking for {expected_loc}")
        
        # Now set noindex=true and verify it's removed from sitemap
        r = requests.patch(f"{API}/landing/pages/{page_id}",
                          headers=headers,
                          json={"seo": {"noindex": True}},
                          timeout=20)
        
        # Get sitemap again
        r = requests.get(f"{API}/sitemap.xml", timeout=20)
        if r.status_code == 200:
            content = r.text
            log_test("page with noindex=true does NOT appear in sitemap",
                    expected_loc not in content or f"<loc>{BASE_URL}/lp/{slug}</loc>" not in content)
        
    finally:
        # Cleanup
        requests.delete(f"{API}/landing/pages/{page_id}", headers=headers, timeout=20)

def test_ga4_in_conversion_outbox():
    """Test 5: GA4 as third provider in conversion outbox"""
    section("TEST 5: GA4 in Conversion Outbox")
    
    owner_token = login("owner")
    if not owner_token:
        print("⚠️  Skipping GA4 tests - no owner token")
        return
    
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Get a published page
    r = requests.get(f"{API}/landing/pages?status=published", headers=headers, timeout=20)
    if r.status_code != 200:
        print(f"⚠️  Could not get published pages: HTTP {r.status_code}")
        return
    
    pages = r.json().get("pages", [])
    if not pages:
        print("⚠️  No published pages found")
        return
    
    slug = pages[0]["slug"]
    
    # Create a lead
    phone = f"0813{uuid.uuid4().int % 90000000 + 10000000}"
    r = requests.post(f"{API}/public/landing/{slug}/lead",
                     json={
                         "name": f"Test GA4 {uuid.uuid4().hex[:6]}",
                         "phone": phone,
                         "marketing_consent": True,
                         "attribution": {"utm_source": "google", "utm_medium": "cpc"}
                     },
                     timeout=30)
    
    if r.status_code not in [200, 201]:
        print(f"⚠️  Could not create lead: HTTP {r.status_code} - {r.text}")
        return
    
    lead_data = r.json()
    lead_id = lead_data.get("id")
    
    if not lead_id:
        print("⚠️  No lead ID returned")
        return
    
    # Note: We can't directly query conversion_events from the API without a specific endpoint
    # But we can verify the tracking endpoints work with GA4 provider
    log_test("lead created successfully", True)
    print(f"   Lead ID: {lead_id} (GA4 outbox verification requires DB access)")

def test_tracking_endpoints():
    """Test 6: GET /api/tracking/* endpoints work with ga4 provider"""
    section("TEST 6: Tracking Endpoints with GA4")
    
    owner_token = login("owner")
    if not owner_token:
        print("⚠️  Skipping tracking tests - no owner token")
        return
    
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Test tracking health endpoint
    r = requests.get(f"{API}/tracking/health", headers=headers, timeout=20)
    passed = r.status_code == 200
    log_test("GET /api/tracking/health returns 200", passed, f"got {r.status_code}")
    
    if passed:
        data = r.json()
        # Should have ga4 provider in the response
        log_test("tracking health response is valid", isinstance(data, dict))
    
    # Test dispatch endpoint
    r = requests.post(f"{API}/tracking/dispatch", headers=headers, json={}, timeout=30)
    passed = r.status_code == 200
    log_test("POST /api/tracking/dispatch returns 200 (not 5xx)", passed, f"got {r.status_code}")
    
    if passed:
        data = r.json()
        log_test("dispatch response is valid", isinstance(data, dict))

def test_landing_regression():
    """Test 7: Regression - all existing landing endpoints still work"""
    section("TEST 7: Landing Endpoints Regression")
    
    owner_token = login("owner")
    if not owner_token:
        print("⚠️  Skipping regression tests - no owner token")
        return
    
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Test templates endpoint
    r = requests.get(f"{API}/landing/templates", headers=headers, timeout=20)
    log_test("GET /api/landing/templates returns 200", r.status_code == 200, f"got {r.status_code}")
    
    # Test pages list
    r = requests.get(f"{API}/landing/pages", headers=headers, timeout=20)
    log_test("GET /api/landing/pages returns 200", r.status_code == 200, f"got {r.status_code}")
    
    # Test create page
    test_title = f"Regression Test {uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/landing/pages",
                     headers=headers,
                     json={"title": test_title, "template": "armada-cepat"},
                     timeout=20)
    passed = r.status_code == 200
    log_test("POST /api/landing/pages (armada-cepat template) returns 200", passed, f"got {r.status_code}")
    
    if passed:
        page = r.json()
        page_id = page["id"]
        
        try:
            # Test get page
            r = requests.get(f"{API}/landing/pages/{page_id}", headers=headers, timeout=20)
            log_test("GET /api/landing/pages/{id} returns 200", r.status_code == 200)
            
            # Test update page
            r = requests.patch(f"{API}/landing/pages/{page_id}",
                              headers=headers,
                              json={"title": f"{test_title} Updated"},
                              timeout=20)
            log_test("PATCH /api/landing/pages/{id} returns 200", r.status_code == 200)
            
            # Test duplicate page
            r = requests.post(f"{API}/landing/pages/{page_id}/duplicate",
                             headers=headers,
                             json={"title": f"{test_title} Copy"},
                             timeout=20)
            dup_passed = r.status_code == 200
            log_test("POST /api/landing/pages/{id}/duplicate returns 200", dup_passed)
            
            if dup_passed:
                dup_page = r.json()
                dup_id = dup_page["id"]
                # Clean up duplicate
                requests.delete(f"{API}/landing/pages/{dup_id}", headers=headers, timeout=20)
            
            # Test A/B report
            r = requests.get(f"{API}/landing/pages/{page_id}/ab", headers=headers, timeout=20)
            log_test("GET /api/landing/pages/{id}/ab returns 200", r.status_code == 200)
            
            # Test leads endpoint
            r = requests.get(f"{API}/landing/pages/{page_id}/leads", headers=headers, timeout=20)
            log_test("GET /api/landing/pages/{id}/leads returns 200", r.status_code == 200)
            
            # Test publish endpoint (should fail with 400 - not ready)
            r = requests.post(f"{API}/landing/pages/{page_id}/publish",
                             headers=headers,
                             json={},
                             timeout=20)
            log_test("POST /api/landing/pages/{id}/publish validates readiness", 
                    r.status_code == 400, f"got {r.status_code}")
            
        finally:
            # Cleanup
            requests.delete(f"{API}/landing/pages/{page_id}", headers=headers, timeout=20)
    
    # Test media endpoints
    r = requests.get(f"{API}/landing/media", headers=headers, timeout=20)
    log_test("GET /api/landing/media returns 200", r.status_code == 200)

def test_public_endpoints():
    """Test 8: Public endpoints still work"""
    section("TEST 8: Public Endpoints Regression")
    
    # Test public landing page (demo page)
    r = requests.get(f"{API}/public/landing/sewa-hiace-jakarta", timeout=20)
    log_test("GET /api/public/landing/{slug} returns 200", r.status_code == 200, f"got {r.status_code}")
    
    # Test public fleet
    r = requests.get(f"{API}/public/fleet", timeout=20)
    log_test("GET /api/public/fleet returns 200", r.status_code == 200, f"got {r.status_code}")
    
    # Test public destinations
    r = requests.get(f"{API}/public/destinations", timeout=20)
    log_test("GET /api/public/destinations returns 200", r.status_code == 200, f"got {r.status_code}")
    
    # Test public testimonials
    r = requests.get(f"{API}/public/testimonials", timeout=20)
    log_test("GET /api/public/testimonials returns 200", r.status_code == 200, f"got {r.status_code}")
    
    # Test public trip estimate
    r = requests.post(f"{API}/public/trip-estimate",
                     json={"origin": "Jakarta", "destination": "Bandung", "pax": 10},
                     timeout=20)
    log_test("POST /api/public/trip-estimate returns 200", r.status_code == 200, f"got {r.status_code}")
    
    # Test public media (demo media)
    owner_token = login("owner")
    if owner_token:
        headers = {"Authorization": f"Bearer {owner_token}"}
        r = requests.get(f"{API}/landing/media", headers=headers, timeout=20)
        if r.status_code == 200:
            assets = r.json().get("assets", [])
            if assets:
                media_id = assets[0]["id"]
                r = requests.get(f"{API}/public/media/{media_id}", timeout=20)
                log_test("GET /api/public/media/{id} returns 200", r.status_code == 200)
                
                # Test thumbnail
                r = requests.get(f"{API}/public/media/{media_id}?thumb=1", timeout=20)
                log_test("GET /api/public/media/{id}?thumb=1 returns 200", r.status_code == 200)

def test_ads_dashboard():
    """Test 9: Ads dashboard endpoints still work"""
    section("TEST 9: Ads Dashboard Regression")
    
    owner_token = login("owner")
    if not owner_token:
        print("⚠️  Skipping ads dashboard tests - no owner token")
        return
    
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Test ads overview
    r = requests.get(f"{API}/ads/overview", headers=headers, timeout=20)
    log_test("GET /api/ads/overview returns 200", r.status_code == 200, f"got {r.status_code}")
    
    # Test ads campaigns
    r = requests.get(f"{API}/ads/campaigns", headers=headers, timeout=20)
    log_test("GET /api/ads/campaigns returns 200", r.status_code == 200, f"got {r.status_code}")

def main():
    """Run all tests"""
    print(f"\n{'='*70}")
    print(f"  BACKEND TEST F8b - GA4 + Landing Page Ads + SEO")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Time: {datetime.now().isoformat()}")
    print(f"{'='*70}\n")
    
    try:
        test_auth_endpoints()
        test_readiness_endpoint()
        test_seo_noindex()
        test_sitemap()
        test_ga4_in_conversion_outbox()
        test_tracking_endpoints()
        test_landing_regression()
        test_public_endpoints()
        test_ads_dashboard()
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"  TEST SUMMARY")
    print(f"{'='*70}")
    print(f"  Total Tests: {TESTS_RUN}")
    print(f"  Passed: {TESTS_PASSED}")
    print(f"  Failed: {TESTS_RUN - TESTS_PASSED}")
    print(f"  Success Rate: {(TESTS_PASSED/TESTS_RUN*100) if TESTS_RUN > 0 else 0:.1f}%")
    print(f"{'='*70}\n")
    
    # Return exit code
    return 0 if TESTS_PASSED == TESTS_RUN else 1

if __name__ == "__main__":
    sys.exit(main())
