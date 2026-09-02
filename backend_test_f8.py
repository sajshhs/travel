"""backend_test_f8.py — Comprehensive API testing for FASE F8 Landing Page Builder.

Testing scope:
- POST /api/landing/pages (8 templates, especially 'armada-cepat' BUG-0109)
- PATCH /api/landing/pages/{id} (blocks, SEO, A/B)
- POST /api/landing/pages/{id}/publish (INV-LP-01 validation)
- POST /api/landing/pages/{id}/duplicate
- Media Library: POST/GET/PATCH/DELETE /api/landing/media
- Public: GET /api/public/landing/{slug}, POST lead, POST track
- RBAC: marketing_admin OK, ops_admin & driver 403

Credentials:
- owner@demo.local / demo12345 (full access)
- marketing@demo.local / demo12345 (marketing_admin - owner of Landing Page feature)
- ops@demo.local / demo12345 (ops_admin - MUST get 403)
- driver@demo.local / demo12345 (driver - MUST get 403)
"""
import requests
import sys
import io
import uuid
from datetime import datetime

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

class TestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.token = None
        self.user = None
        self.failures = []
        self.created_pages = []
        self.created_media = []

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
                    print(f"✅ Login successful - Role: {self.user.get('role')}")
                    return True
                else:
                    print(f"❌ Login failed - No token in response")
                    return False
            else:
                print(f"❌ Login failed - Status: {res.status_code}")
                return False
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return False

    def test(self, name, method, endpoint, expected_status, data=None, params=None, check_fn=None, headers=None, files=None):
        """Run a single API test"""
        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        
        url = f"{BASE_URL}{endpoint}"
        if params:
            url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        
        req_headers = {}
        if self.token and headers is None:
            req_headers['Authorization'] = f'Bearer {self.token}'
        elif headers:
            req_headers.update(headers)
        
        if not files:
            req_headers['Content-Type'] = 'application/json'
        
        try:
            if method == 'GET':
                res = requests.get(url, headers=req_headers, timeout=15)
            elif method == 'POST':
                if files:
                    res = requests.post(url, headers=req_headers, files=files, data=data, timeout=30)
                else:
                    res = requests.post(url, json=data, headers=req_headers, timeout=15)
            elif method == 'PATCH':
                res = requests.patch(url, json=data, headers=req_headers, timeout=15)
            elif method == 'DELETE':
                res = requests.delete(url, headers=req_headers, timeout=15)
            else:
                print(f"❌ Unsupported method: {method}")
                self.tests_failed += 1
                return False, None

            success = res.status_code == expected_status
            response_data = None
            try:
                response_data = res.json()
            except Exception:
                pass

            if success:
                if check_fn:
                    check_result = check_fn(response_data)
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
                error_msg = response_data.get('detail') if response_data and isinstance(response_data, dict) else str(response_data)[:200]
                self.failures.append(f"{name}: Expected {expected_status}, got {res.status_code} - {error_msg}")
                print(f"❌ FAIL - Expected {expected_status}, got {res.status_code}")
                if response_data:
                    print(f"   Response: {error_msg}")
                return False, response_data

        except Exception as e:
            self.tests_failed += 1
            self.failures.append(f"{name}: Exception - {str(e)}")
            print(f"❌ FAIL - Exception: {str(e)}")
            return False, None

    def cleanup(self):
        """Clean up created resources"""
        print("\n🧹 Cleaning up test resources...")
        for page_id in self.created_pages:
            try:
                requests.delete(f"{BASE_URL}/landing/pages/{page_id}", 
                              headers={'Authorization': f'Bearer {self.token}'}, timeout=10)
            except Exception:
                pass
        for media_id in self.created_media:
            try:
                requests.delete(f"{BASE_URL}/landing/media/{media_id}",
                              headers={'Authorization': f'Bearer {self.token}'}, timeout=10)
            except Exception:
                pass

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("📊 TEST SUMMARY - FASE F8 Landing Page Builder")
        print("="*70)
        print(f"Total tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100) if self.tests_run > 0 else 0:.1f}%")
        
        if self.failures:
            print("\n❌ FAILED TESTS:")
            for i, failure in enumerate(self.failures, 1):
                print(f"  {i}. {failure}")
        
        print("="*70)
        return 0 if self.tests_failed == 0 else 1


def png_bytes(w=900, h=600):
    """Generate a simple PNG for testing"""
    try:
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (w, h), (11, 123, 211)).save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        # Fallback: minimal PNG header
        return b'\x89PNG\r\n\x1a\n' + b'\x00' * 100


def main():
    runner = TestRunner()
    
    # Login as marketing_admin (owner of Landing Page feature)
    if not runner.login("marketing@demo.local", "demo12345"):
        print("❌ Cannot proceed without login")
        return 1

    print("\n" + "="*70)
    print("🧪 BACKEND TEST SUITE - FASE F8 Landing Page Builder")
    print("="*70)
    
    # ========================================================================
    # F8-1: GET /api/landing/templates
    # ========================================================================
    success, templates_data = runner.test(
        "F8-1: GET /api/landing/templates",
        "GET", "/landing/templates", 200,
        check_fn=lambda d: (
            True if d and "templates" in d and len(d["templates"]) >= 8
            else f"Expected at least 8 templates, got {len(d.get('templates', []))}"
        )
    )
    
    if success and templates_data:
        templates = templates_data.get("templates", [])
        print(f"   📋 Templates: {len(templates)}")
        for t in templates[:3]:
            print(f"      - {t.get('key')}: {t.get('name')} ({t.get('segment')})")
    
    # ========================================================================
    # F8-2: POST /api/landing/pages - Create from MULTIPLE templates
    # ========================================================================
    test_templates = ["armada-cepat", "armada-konversi", "destinasi-promo"]
    created_pages = {}
    
    for template_key in test_templates:
        slug = f"test-{template_key}-{uuid.uuid4().hex[:6]}"
        success, page_data = runner.test(
            f"F8-2: POST /api/landing/pages template={template_key} (BUG-0109 check)",
            "POST", "/landing/pages", 200,
            data={
                "template": template_key,
                "title": f"Test {template_key}",
                "slug": slug
            },
            check_fn=lambda d: (
                True if d and d.get("id") and d.get("slug") == slug and d.get("status") == "draft"
                else f"Invalid response: {d}"
            )
        )
        
        if success and page_data:
            page_id = page_data.get("id")
            runner.created_pages.append(page_id)
            created_pages[template_key] = {"id": page_id, "slug": slug, "data": page_data}
            print(f"   📋 Created page: {page_id} - slug: {slug}")
    
    # ========================================================================
    # F8-3: GET /api/landing/pages (list)
    # ========================================================================
    runner.test(
        "F8-3: GET /api/landing/pages (list)",
        "GET", "/landing/pages", 200,
        check_fn=lambda d: (
            True if d and "pages" in d and "total" in d
            else "Missing pages or total in response"
        )
    )
    
    # ========================================================================
    # F8-4: GET /api/landing/pages/{id} (detail)
    # ========================================================================
    if created_pages:
        first_page = list(created_pages.values())[0]
        runner.test(
            "F8-4: GET /api/landing/pages/{id} (detail)",
            "GET", f"/landing/pages/{first_page['id']}", 200,
            check_fn=lambda d: (
                True if d and d.get("id") == first_page['id'] and "blocks" in d and "theme" in d and "seo" in d
                else "Missing required fields in page detail"
            )
        )
    
    # ========================================================================
    # F8-5: PATCH /api/landing/pages/{id} - Update blocks & SEO
    # ========================================================================
    if created_pages:
        first_page = list(created_pages.values())[0]
        success, updated_data = runner.test(
            "F8-5: PATCH /api/landing/pages/{id} - Update SEO",
            "PATCH", f"/landing/pages/{first_page['id']}", 200,
            data={
                "seo": {
                    "title": "Sewa Hiace Murah Jakarta",
                    "description": "Sewa Hiace dengan driver berpengalaman"
                }
            },
            check_fn=lambda d: (
                True if d and d.get("page", {}).get("seo", {}).get("title") == "Sewa Hiace Murah Jakarta"
                else f"SEO not updated correctly: {d.get('page', {}).get('seo')}"
            )
        )
    
    # ========================================================================
    # F8-6: POST /api/landing/pages/{id}/publish - REJECT without SEO/conversion blocks
    # ========================================================================
    if created_pages:
        # Create a new page and try to publish without proper setup
        slug_invalid = f"test-invalid-{uuid.uuid4().hex[:6]}"
        success, invalid_page = runner.test(
            "F8-6a: Create page for publish rejection test",
            "POST", "/landing/pages", 200,
            data={"template": "armada-konversi", "title": "Invalid Page", "slug": slug_invalid}
        )
        
        if success and invalid_page:
            runner.created_pages.append(invalid_page.get("id"))
            
            # Remove all conversion blocks and empty SEO
            runner.test(
                "F8-6b: PATCH to remove conversion blocks",
                "PATCH", f"/landing/pages/{invalid_page['id']}", 200,
                data={
                    "blocks": [],
                    "seo": {"title": "", "description": ""}
                }
            )
            
            # Try to publish - should reject with clear reason
            runner.test(
                "F8-6c: POST publish without SEO/conversion blocks (should reject 400)",
                "POST", f"/landing/pages/{invalid_page['id']}/publish", 400,
                check_fn=lambda d: (
                    True if d and "detail" in d and ("konversi" in d["detail"].lower() or "seo" in d["detail"].lower())
                    else f"Error message should mention conversion blocks or SEO: {d.get('detail')}"
                )
            )
    
    # ========================================================================
    # F8-7: POST /api/landing/pages/{id}/publish - SUCCESS
    # ========================================================================
    if created_pages:
        first_page = list(created_pages.values())[0]
        
        # Ensure SEO is filled
        runner.test(
            "F8-7a: PATCH to fill SEO for publish",
            "PATCH", f"/landing/pages/{first_page['id']}", 200,
            data={
                "seo": {
                    "title": "Sewa Hiace Jakarta Murah",
                    "description": "Sewa Hiace dengan driver profesional"
                }
            }
        )
        
        # Publish
        success, publish_data = runner.test(
            "F8-7b: POST publish with valid page (should succeed)",
            "POST", f"/landing/pages/{first_page['id']}/publish", 200,
            check_fn=lambda d: (
                True if d and d.get("status") == "published" and d.get("url")
                else f"Publish failed: {d}"
            )
        )
        
        if success and publish_data:
            print(f"   📋 Published URL: {publish_data.get('url')}")
            first_page['published'] = True
            first_page['public_url'] = publish_data.get('url')
    
    # ========================================================================
    # F8-8: Media Library - Upload image
    # ========================================================================
    img_data = png_bytes()
    success, media_data = runner.test(
        "F8-8: POST /api/landing/media (upload image)",
        "POST", "/landing/media", 200,
        files={"file": ("test-hero.png", img_data, "image/png")},
        data={"alt": "Test Hero Image"},
        check_fn=lambda d: (
            True if d and d.get("id") and d.get("kind") == "image" and d.get("url", "").startswith("/api/public/media/")
            else f"Invalid media response: {d}"
        )
    )
    
    media_id = None
    if success and media_data:
        media_id = media_data.get("id")
        runner.created_media.append(media_id)
        print(f"   📋 Uploaded media: {media_id} - URL: {media_data.get('url')}")
        print(f"   📋 Dimensions: {media_data.get('width')}x{media_data.get('height')}")
    
    # ========================================================================
    # F8-9: GET /api/landing/media (list)
    # ========================================================================
    runner.test(
        "F8-9: GET /api/landing/media (list)",
        "GET", "/landing/media", 200,
        check_fn=lambda d: (
            True if d and "assets" in d and "counts" in d and "storage" in d
            else "Missing required fields in media list"
        )
    )
    
    # ========================================================================
    # F8-10: PATCH /api/landing/media/{id} (update alt text)
    # ========================================================================
    if media_id:
        runner.test(
            "F8-10: PATCH /api/landing/media/{id} (update alt)",
            "PATCH", f"/landing/media/{media_id}", 200,
            data={"alt": "Updated Hero Image for Hiace"},
            check_fn=lambda d: (
                True if d and d.get("alt") == "Updated Hero Image for Hiace"
                else f"Alt text not updated: {d.get('alt')}"
            )
        )
    
    # ========================================================================
    # F8-11: GET /api/public/media/{id} (public access without auth)
    # ========================================================================
    if media_id:
        runner.test(
            "F8-11: GET /api/public/media/{id} (public, no auth)",
            "GET", f"/public/media/{media_id}", 200,
            headers={}  # No auth
        )
    
    # ========================================================================
    # F8-12: GET /api/public/landing/{slug} (public page)
    # ========================================================================
    if created_pages:
        first_page = list(created_pages.values())[0]
        if first_page.get('published'):
            runner.test(
                "F8-12: GET /api/public/landing/{slug} (public, no auth)",
                "GET", f"/public/landing/{first_page['slug']}", 200,
                headers={},  # No auth
                check_fn=lambda d: (
                    True if d and "blocks" in d and "theme" in d and "seo" in d and "page_id" in d
                    else "Missing required fields in public page"
                )
            )
    
    # ========================================================================
    # F8-13: POST /api/public/landing/{slug}/lead - SUCCESS
    # ========================================================================
    if created_pages:
        first_page = list(created_pages.values())[0]
        if first_page.get('published'):
            phone = f"0812{uuid.uuid4().int % 90000000 + 10000000}"
            success, lead_data = runner.test(
                "F8-13a: POST /api/public/landing/{slug}/lead (success)",
                "POST", f"/public/landing/{first_page['slug']}/lead", 200,
                headers={},  # No auth
                data={
                    "name": "Test User",
                    "phone": phone,
                    "email": "test@example.com",
                    "destination": "Bromo",
                    "pax": 15,
                    "marketing_consent": True,
                    "attribution": {
                        "utm_source": "google",
                        "utm_campaign": "test-campaign",
                        "gclid": "TEST-GCLID-123"
                    },
                    "click_ids": {"fbclid": "FB-TEST"},
                    "variant_id": "A"
                },
                check_fn=lambda d: (
                    True if d and d.get("id") and d.get("status") == "received"
                    else f"Lead submission failed: {d}"
                )
            )
            
            if success and lead_data:
                print(f"   📋 Lead created: {lead_data.get('id')}")
                
                # Test idempotent - submit again with same phone
                runner.test(
                    "F8-13b: POST lead again (idempotent - should return same ID)",
                    "POST", f"/public/landing/{first_page['slug']}/lead", 200,
                    headers={},
                    data={
                        "name": "Test User",
                        "phone": phone,
                        "email": "test@example.com",
                        "destination": "Bromo",
                        "pax": 15,
                        "marketing_consent": True,
                        "variant_id": "A"
                    },
                    check_fn=lambda d: (
                        True if d and d.get("id") == lead_data.get("id") and d.get("duplicate") is True
                        else f"Idempotent check failed: expected same ID {lead_data.get('id')}, got {d.get('id')}"
                    )
                )
    
    # ========================================================================
    # F8-14: POST /api/public/landing/{slug}/lead - REJECT without consent
    # ========================================================================
    if created_pages:
        first_page = list(created_pages.values())[0]
        if first_page.get('published'):
            runner.test(
                "F8-14: POST lead without consent (should reject 400)",
                "POST", f"/public/landing/{first_page['slug']}/lead", 400,
                headers={},
                data={
                    "name": "Test User No Consent",
                    "phone": "081299998888",
                    "marketing_consent": False
                },
                check_fn=lambda d: (
                    True if d and "detail" in d and "persetujuan" in d["detail"].lower()
                    else f"Error should mention consent: {d.get('detail')}"
                )
            )
    
    # ========================================================================
    # F8-15: POST /api/public/landing/{slug}/lead - REJECT invalid phone
    # ========================================================================
    if created_pages:
        first_page = list(created_pages.values())[0]
        if first_page.get('published'):
            runner.test(
                "F8-15: POST lead with invalid phone (should reject 400)",
                "POST", f"/public/landing/{first_page['slug']}/lead", 400,
                headers={},
                data={
                    "name": "Test User",
                    "phone": "123",
                    "marketing_consent": True
                },
                check_fn=lambda d: (
                    True if d and "detail" in d and "nomor" in d["detail"].lower()
                    else f"Error should mention phone: {d.get('detail')}"
                )
            )
    
    # ========================================================================
    # F8-16: POST /api/public/landing/{slug}/track
    # ========================================================================
    if created_pages:
        first_page = list(created_pages.values())[0]
        if first_page.get('published'):
            runner.test(
                "F8-16a: POST track view event",
                "POST", f"/public/landing/{first_page['slug']}/track", 200,
                headers={},
                data={"type": "view", "variant_id": "A"}
            )
            
            runner.test(
                "F8-16b: POST track cta_click event",
                "POST", f"/public/landing/{first_page['slug']}/track", 200,
                headers={},
                data={"type": "cta_click", "variant_id": "A"}
            )
            
            runner.test(
                "F8-16c: POST track invalid event type (should reject 400)",
                "POST", f"/public/landing/{first_page['slug']}/track", 400,
                headers={},
                data={"type": "invalid_event", "variant_id": "A"}
            )
    
    # ========================================================================
    # F8-17: POST /api/landing/pages/{id}/duplicate
    # ========================================================================
    if created_pages:
        first_page = list(created_pages.values())[0]
        success, dup_data = runner.test(
            "F8-17: POST /api/landing/pages/{id}/duplicate",
            "POST", f"/landing/pages/{first_page['id']}/duplicate", 200,
            check_fn=lambda d: (
                True if d and d.get("id") != first_page['id'] and d.get("slug") != first_page['slug'] and d.get("status") == "draft"
                else f"Duplicate failed: {d}"
            )
        )
        
        if success and dup_data:
            runner.created_pages.append(dup_data.get("id"))
            print(f"   📋 Duplicated page: {dup_data.get('id')} - slug: {dup_data.get('slug')}")
    
    # ========================================================================
    # F8-18: GET /api/landing/pages/{id}/ab (A/B report)
    # ========================================================================
    if created_pages:
        first_page = list(created_pages.values())[0]
        runner.test(
            "F8-18: GET /api/landing/pages/{id}/ab (A/B report)",
            "GET", f"/landing/pages/{first_page['id']}/ab", 200,
            check_fn=lambda d: (
                True if d and "variants" in d and "enough_data" in d
                else "Missing required fields in A/B report"
            )
        )
    
    # ========================================================================
    # F8-19: GET /api/landing/pages/{id}/leads
    # ========================================================================
    if created_pages:
        first_page = list(created_pages.values())[0]
        runner.test(
            "F8-19: GET /api/landing/pages/{id}/leads",
            "GET", f"/landing/pages/{first_page['id']}/leads", 200,
            check_fn=lambda d: (
                True if d and "leads" in d and "total" in d
                else "Missing required fields in leads list"
            )
        )
    
    # ========================================================================
    # F8-20: RBAC - ops_admin should get 403
    # ========================================================================
    if runner.login("ops@demo.local", "demo12345"):
        runner.test(
            "F8-20a: GET /api/landing/pages as ops_admin (should reject 403)",
            "GET", "/landing/pages", 403
        )
        
        runner.test(
            "F8-20b: GET /api/landing/media as ops_admin (should reject 403)",
            "GET", "/landing/media", 403
        )
    
    # ========================================================================
    # F8-21: RBAC - driver should get 403
    # ========================================================================
    if runner.login("driver@demo.local", "demo12345"):
        runner.test(
            "F8-21a: GET /api/landing/pages as driver (should reject 403)",
            "GET", "/landing/pages", 403
        )
        
        runner.test(
            "F8-21b: GET /api/landing/media as driver (should reject 403)",
            "GET", "/landing/media", 403
        )
    
    # ========================================================================
    # F8-22: RBAC - owner should have access
    # ========================================================================
    if runner.login("owner@demo.local", "demo12345"):
        runner.test(
            "F8-22: GET /api/landing/pages as owner (should succeed)",
            "GET", "/landing/pages", 200
        )
    
    # Cleanup
    runner.cleanup()
    
    # Print summary
    return runner.print_summary()


if __name__ == "__main__":
    sys.exit(main())
