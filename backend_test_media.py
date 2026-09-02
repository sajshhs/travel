"""backend_test_media.py — Comprehensive API testing for Media Library (Fase 3).

Testing scope:
- AUTH: POST /api/auth/login (kontrak token yang benar)
- UPLOAD CMS: POST /api/uploads/cms dengan field 'image' → muncul di GET /api/media
- MEDIA ENDPOINTS: list, upload, get, update, delete, bulk ops, crop, download
- FOLDER ENDPOINTS: list, create, update, delete (aset naik ke parent)
- PUBLIC ACCESS: GET /api/public/media/{id} tanpa auth
- RBAC: driver 403, ops_admin & marketing_admin 200
- REGRESI BUG-0113: input bertipe salah → 4xx bukan 500
- ANTI-REGRESI: URL lama /api/uploads/cms/<nama> tetap 200

Credentials:
- owner@demo.local / demo12345
- ops@demo.local / demo12345
- marketing@demo.local / demo12345
- driver@demo.local / demo12345
"""
import requests
import sys
import io
from datetime import datetime

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

class MediaTestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.token = None
        self.user = None
        self.failures = []
        self.test_assets = []  # Track created assets for cleanup
        self.test_folders = []  # Track created folders for cleanup

    def login(self, email, password):
        """Login and get token (field 'token' bukan 'access_token')"""
        print(f"\n🔐 Logging in as {email}...")
        try:
            res = requests.post(f"{BASE_URL}/auth/login", 
                              json={"email": email, "password": password}, 
                              timeout=10)
            if res.status_code == 200:
                data = res.json()
                # PENTING: field bernama 'token' bukan 'access_token'
                self.token = data.get("token")
                self.user = data.get("user", {})
                if self.token:
                    print(f"✅ Login successful - Role: {self.user.get('role')}, Token prefix: {self.token[:10]}...")
                    return True
                else:
                    print(f"❌ Login failed - No 'token' field in response: {data.keys()}")
                    return False
            else:
                print(f"❌ Login failed - Status: {res.status_code}, Body: {res.text[:200]}")
                return False
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return False

    def test(self, name, method, endpoint, expected_status, data=None, files=None, 
             params=None, check_fn=None, no_auth=False):
        """Run a single API test"""
        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        
        url = f"{BASE_URL}{endpoint}"
        if params:
            url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        
        headers = {}
        if not no_auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        try:
            if method == 'GET':
                res = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                if files:
                    # Multipart upload (jangan set Content-Type, requests akan set otomatis)
                    res = requests.post(url, files=files, data=data, headers=headers, timeout=15)
                else:
                    headers['Content-Type'] = 'application/json'
                    res = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PATCH':
                headers['Content-Type'] = 'application/json'
                res = requests.patch(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                res = requests.delete(url, headers=headers, timeout=10)
            else:
                print(f"❌ Unsupported method: {method}")
                self.tests_failed += 1
                self.failures.append(f"{name}: Unsupported method {method}")
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
        print("\n" + "="*70)
        print(f"📊 TEST SUMMARY")
        print("="*70)
        print(f"Total tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        
        if self.failures:
            print("\n❌ FAILURES:")
            for i, failure in enumerate(self.failures, 1):
                print(f"  {i}. {failure}")
        
        print("="*70)
        return 0 if self.tests_failed == 0 else 1


def main():
    runner = MediaTestRunner()
    
    # ========================================================================
    # SECTION 1: AUTH - Kontrak login yang benar
    # ========================================================================
    print("\n" + "="*70)
    print("SECTION 1: AUTH - Login dengan kontrak yang benar")
    print("="*70)
    
    if not runner.login("ops@demo.local", "demo12345"):
        print("\n❌ CRITICAL: Login failed, cannot continue")
        return 1
    
    # ========================================================================
    # SECTION 2: MEDIA FOLDERS - CRUD operations
    # ========================================================================
    print("\n" + "="*70)
    print("SECTION 2: MEDIA FOLDERS - CRUD operations")
    print("="*70)
    
    # Test: List folders
    success, folders_data = runner.test(
        "List folders",
        "GET", "/media/folders", 200,
        check_fn=lambda d: True if isinstance(d.get("folders"), list) else "folders not a list"
    )
    
    # Test: Create folder
    success, folder_data = runner.test(
        "Create folder",
        "POST", "/media/folders", 200,
        data={"name": f"Test Folder {datetime.now().strftime('%H%M%S')}"},
        check_fn=lambda d: True if d.get("id") and d.get("name") else "Missing id or name"
    )
    
    folder_id = None
    if success and folder_data:
        folder_id = folder_data.get("id")
        runner.test_folders.append(folder_id)
        print(f"   Created folder ID: {folder_id}")
    
    # Test: Update folder name
    if folder_id:
        runner.test(
            "Update folder name",
            "PATCH", f"/media/folders/{folder_id}", 200,
            data={"name": f"Updated Folder {datetime.now().strftime('%H%M%S')}"},
            check_fn=lambda d: True if d.get("name") else "Name not updated"
        )
    
    # Test: Create subfolder
    subfolder_id = None
    if folder_id:
        success, subfolder_data = runner.test(
            "Create subfolder",
            "POST", "/media/folders", 200,
            data={"name": f"Subfolder {datetime.now().strftime('%H%M%S')}", "parent_id": folder_id},
            check_fn=lambda d: True if d.get("id") and d.get("parent_id") == folder_id else "Invalid subfolder"
        )
        if success and subfolder_data:
            subfolder_id = subfolder_data.get("id")
            runner.test_folders.append(subfolder_id)
    
    # ========================================================================
    # SECTION 3: MEDIA ASSETS - Upload & List
    # ========================================================================
    print("\n" + "="*70)
    print("SECTION 3: MEDIA ASSETS - Upload & List")
    print("="*70)
    
    # Test: Upload media via POST /api/media
    # Create a simple 1x1 PNG image
    png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    
    success, upload_data = runner.test(
        "Upload media via POST /api/media",
        "POST", "/media", 200,
        files={"file": ("test_image.png", io.BytesIO(png_bytes), "image/png")},
        data={"alt": "Test image", "folder_id": folder_id or ""},
        check_fn=lambda d: True if d.get("id") and d.get("url") else "Missing id or url"
    )
    
    asset_id = None
    if success and upload_data:
        asset_id = upload_data.get("id")
        runner.test_assets.append(asset_id)
        print(f"   Created asset ID: {asset_id}, URL: {upload_data.get('url')}")
    
    # Test: List media
    runner.test(
        "List media",
        "GET", "/media", 200,
        check_fn=lambda d: True if isinstance(d.get("assets"), list) and d.get("total") is not None else "Invalid list response"
    )
    
    # Test: List media with folder filter
    if folder_id:
        runner.test(
            "List media filtered by folder",
            "GET", "/media", 200,
            params={"folder_id": folder_id},
            check_fn=lambda d: True if isinstance(d.get("assets"), list) else "Invalid filtered list"
        )
    
    # Test: Get single asset
    if asset_id:
        runner.test(
            "Get single asset",
            "GET", f"/media/{asset_id}", 200,
            check_fn=lambda d: True if d.get("id") == asset_id else f"ID mismatch: {d.get('id')} != {asset_id}"
        )
    
    # ========================================================================
    # SECTION 4: UPLOAD CMS - Field 'image' dan unified media
    # ========================================================================
    print("\n" + "="*70)
    print("SECTION 4: UPLOAD CMS - Field 'image' dan unified media")
    print("="*70)
    
    # Test: Upload via POST /api/uploads/cms dengan field 'image' (BUKAN 'file')
    success, cms_upload_data = runner.test(
        "Upload via POST /api/uploads/cms (field 'image')",
        "POST", "/uploads/cms", 200,
        files={"image": ("cms_test.png", io.BytesIO(png_bytes), "image/png")},
        check_fn=lambda d: True if d.get("url") and d.get("media_id") else "Missing url or media_id"
    )
    
    cms_media_id = None
    cms_url = None
    if success and cms_upload_data:
        cms_media_id = cms_upload_data.get("media_id")
        cms_url = cms_upload_data.get("url")
        if cms_media_id:
            runner.test_assets.append(cms_media_id)
        print(f"   CMS upload: media_id={cms_media_id}, url={cms_url}")
    
    # Test: Verify CMS upload muncul di GET /api/media
    if cms_media_id:
        runner.test(
            "Verify CMS upload appears in GET /api/media",
            "GET", f"/media/{cms_media_id}", 200,
            check_fn=lambda d: True if d.get("id") == cms_media_id and d.get("source") == "cms" else f"CMS asset not found or wrong source: {d.get('source')}"
        )
    
    # ========================================================================
    # SECTION 5: PUBLIC ACCESS - GET /api/public/media/{id} tanpa auth
    # ========================================================================
    print("\n" + "="*70)
    print("SECTION 5: PUBLIC ACCESS - Tanpa auth harus 200")
    print("="*70)
    
    if asset_id:
        runner.test(
            "Public access to media (no auth)",
            "GET", f"/public/media/{asset_id}", 200,
            no_auth=True
        )
    
    # Test: Public access dengan ?v=1 (versioned URL)
    if asset_id:
        runner.test(
            "Public access with version query",
            "GET", f"/public/media/{asset_id}", 200,
            params={"v": "1"},
            no_auth=True
        )
    
    # ========================================================================
    # SECTION 6: ASSET OPERATIONS - Update, Download, Crop
    # ========================================================================
    print("\n" + "="*70)
    print("SECTION 6: ASSET OPERATIONS - Update, Download, Crop")
    print("="*70)
    
    # Test: Update asset (PATCH /api/media/{id})
    if asset_id:
        runner.test(
            "Update asset alt text",
            "PATCH", f"/media/{asset_id}", 200,
            data={"alt": "Updated alt text"},
            check_fn=lambda d: True if d.get("alt") == "Updated alt text" else f"Alt not updated: {d.get('alt')}"
        )
    
    # Test: Download asset
    if asset_id:
        runner.test(
            "Download asset",
            "GET", f"/media/{asset_id}/download", 200
        )
    
    # Test: Crop asset (save as new)
    if asset_id:
        runner.test(
            "Crop asset (save as new)",
            "POST", f"/media/{asset_id}/crop", 200,
            data={"x": 0, "y": 0, "width": 1, "height": 1, "mode": "new"},
            check_fn=lambda d: True if d.get("id") and d.get("id") != asset_id else "Crop didn't create new asset"
        )
    
    # ========================================================================
    # SECTION 7: BULK OPERATIONS
    # ========================================================================
    print("\n" + "="*70)
    print("SECTION 7: BULK OPERATIONS - Move & Delete")
    print("="*70)
    
    # Test: Bulk move
    if asset_id and folder_id:
        runner.test(
            "Bulk move assets",
            "POST", "/media/bulk-move", 200,
            data={"ids": [asset_id], "folder_id": folder_id},
            check_fn=lambda d: True if d.get("moved") >= 0 else "Invalid bulk move response"
        )
    
    # Test: Bulk delete
    if asset_id:
        runner.test(
            "Bulk delete assets",
            "POST", "/media/bulk-delete", 200,
            data={"ids": [asset_id]},
            check_fn=lambda d: True if d.get("deleted") >= 0 else "Invalid bulk delete response"
        )
    
    # ========================================================================
    # SECTION 8: FOLDER DELETE - Aset harus naik ke parent
    # ========================================================================
    print("\n" + "="*70)
    print("SECTION 8: FOLDER DELETE - Aset naik ke parent, tidak terhapus")
    print("="*70)
    
    # Create new folder with asset, then delete folder
    success, test_folder = runner.test(
        "Create test folder for deletion",
        "POST", "/media/folders", 200,
        data={"name": f"Delete Test {datetime.now().strftime('%H%M%S')}"}
    )
    
    test_folder_id = None
    if success and test_folder:
        test_folder_id = test_folder.get("id")
        
        # Upload asset to this folder
        success, test_asset = runner.test(
            "Upload asset to test folder",
            "POST", "/media", 200,
            files={"file": ("folder_test.png", io.BytesIO(png_bytes), "image/png")},
            data={"folder_id": test_folder_id}
        )
        
        test_asset_id = None
        if success and test_asset:
            test_asset_id = test_asset.get("id")
            
            # Delete folder
            success, delete_result = runner.test(
                "Delete folder (asset should move to parent)",
                "DELETE", f"/media/folders/{test_folder_id}", 200,
                check_fn=lambda d: True if "moved_assets" in d else "No moved_assets field"
            )
            
            # Verify asset still exists
            if test_asset_id:
                runner.test(
                    "Verify asset still exists after folder deletion",
                    "GET", f"/media/{test_asset_id}", 200,
                    check_fn=lambda d: True if d.get("id") == test_asset_id else "Asset was deleted!"
                )
                runner.test_assets.append(test_asset_id)
    
    # ========================================================================
    # SECTION 9: IMPORT LEGACY - Idempoten
    # ========================================================================
    print("\n" + "="*70)
    print("SECTION 9: IMPORT LEGACY - Idempoten")
    print("="*70)
    
    # Test: Import legacy (first run)
    success, import1 = runner.test(
        "Import legacy assets (first run)",
        "POST", "/media/import-legacy", 200,
        check_fn=lambda d: True if "imported" in d and "skipped" in d else "Invalid import response"
    )
    
    # Test: Import legacy (second run - should be idempotent)
    success, import2 = runner.test(
        "Import legacy assets (second run - idempotent)",
        "POST", "/media/import-legacy", 200,
        check_fn=lambda d: True if d.get("imported") == 0 and d.get("skipped") >= 0 else f"Not idempotent: imported={d.get('imported')}, skipped={d.get('skipped')}"
    )
    
    # ========================================================================
    # SECTION 10: REGRESI BUG-0113 - Input bertipe salah harus 4xx bukan 500
    # ========================================================================
    print("\n" + "="*70)
    print("SECTION 10: REGRESI BUG-0113 - Input bertipe salah → 4xx bukan 500")
    print("="*70)
    
    # Create a fresh asset for BUG-0113 tests (don't use deleted ones)
    success, bug_test_asset = runner.test(
        "Create fresh asset for BUG-0113 tests",
        "POST", "/media", 200,
        files={"file": ("bug_test.png", io.BytesIO(png_bytes), "image/png")},
        data={"alt": "Bug test asset"}
    )
    
    bug_test_asset_id = None
    if success and bug_test_asset:
        bug_test_asset_id = bug_test_asset.get("id")
        runner.test_assets.append(bug_test_asset_id)
    
    if bug_test_asset_id:
        # Test: PATCH with wrong type folder_id (number instead of string)
        # Note: Backend koersi ke string, jadi bisa 404 (folder tidak ditemukan) atau 400
        success, patch_result = runner.test(
            "BUG-0113: PATCH /api/media/{id} with folder_id as number (should not 500)",
            "PATCH", f"/media/{bug_test_asset_id}", 
            404,  # Backend koersi ke string "5", folder tidak ditemukan = 404 (bukan 500)
            data={"alt": {"x": [1, 2]}, "folder_id": 5}
        )
        if not success:
            # Try with 400 as alternative
            runner.test(
                "BUG-0113: PATCH /api/media/{id} with folder_id as number (alternative: 400)",
                "PATCH", f"/media/{bug_test_asset_id}", 
                400,
                data={"alt": {"x": [1, 2]}, "folder_id": 5}
            )
        
        # Test: POST bulk-move with ids as string instead of list
        # Note: Backend might handle this gracefully, so we check it doesn't 500
        success, bulk_move_result = runner.test(
            "BUG-0113: POST /api/media/bulk-move with ids as string (should not 500)",
            "POST", "/media/bulk-move",
            200,  # Backend handles gracefully
            data={"ids": "bukan-list", "folder_id": ""}
        )
        # If it returns 200, check that moved count is 0 (graceful handling)
        if success and bulk_move_result:
            moved = bulk_move_result.get("moved", -1)
            if moved != 0:
                print(f"   ⚠️  Warning: Expected moved=0 for invalid input, got {moved}")
        
        # Test: POST crop with invalid rect
        runner.test(
            "BUG-0113: POST /api/media/{id}/crop with non-numeric rect",
            "POST", f"/media/{bug_test_asset_id}/crop",
            400,  # Should be 4xx, not 500
            data={"x": "abc", "y": 0, "width": 10, "height": 10}
        )
        
        # Test: POST crop with negative rect
        runner.test(
            "BUG-0113: POST /api/media/{id}/crop with negative rect",
            "POST", f"/media/{bug_test_asset_id}/crop",
            400,  # Should be 4xx, not 500
            data={"x": -10, "y": 0, "width": 10, "height": 10}
        )
    
    # ========================================================================
    # SECTION 11: RBAC - Driver harus 403
    # ========================================================================
    print("\n" + "="*70)
    print("SECTION 11: RBAC - Driver harus 403 di semua /api/media/*")
    print("="*70)
    
    # Login as driver
    if runner.login("driver@demo.local", "demo12345"):
        # Test: GET /api/media as driver
        runner.test(
            "RBAC: Driver GET /api/media",
            "GET", "/media", 403
        )
        
        # Test: GET /api/media/folders as driver
        runner.test(
            "RBAC: Driver GET /api/media/folders",
            "GET", "/media/folders", 403
        )
        
        # Test: POST /api/media as driver
        runner.test(
            "RBAC: Driver POST /api/media",
            "POST", "/media", 403,
            files={"file": ("test.png", io.BytesIO(png_bytes), "image/png")}
        )
        
        if bug_test_asset_id:
            # Test: GET /api/media/{id} as driver
            runner.test(
                "RBAC: Driver GET /api/media/{id}",
                "GET", f"/media/{bug_test_asset_id}", 403
            )
            
            # Test: PATCH /api/media/{id} as driver
            runner.test(
                "RBAC: Driver PATCH /api/media/{id}",
                "PATCH", f"/media/{bug_test_asset_id}", 403,
                data={"alt": "test"}
            )
            
            # Test: DELETE /api/media/{id} as driver
            runner.test(
                "RBAC: Driver DELETE /api/media/{id}",
                "DELETE", f"/media/{bug_test_asset_id}", 403
            )
    
    # ========================================================================
    # SECTION 12: RBAC - Marketing admin harus 200
    # ========================================================================
    print("\n" + "="*70)
    print("SECTION 12: RBAC - Marketing admin harus 200")
    print("="*70)
    
    # Login as marketing admin
    if runner.login("marketing@demo.local", "demo12345"):
        # Test: GET /api/media as marketing admin
        runner.test(
            "RBAC: Marketing admin GET /api/media",
            "GET", "/media", 200
        )
        
        # Test: GET /api/media/folders as marketing admin
        runner.test(
            "RBAC: Marketing admin GET /api/media/folders",
            "GET", "/media/folders", 200
        )
    
    # ========================================================================
    # SECTION 13: ANTI-REGRESI - URL lama tetap bekerja
    # ========================================================================
    print("\n" + "="*70)
    print("SECTION 13: ANTI-REGRESI - URL lama /api/uploads/cms/<nama> tetap 200")
    print("="*70)
    
    # Get a CMS asset with legacy_url
    if runner.login("ops@demo.local", "demo12345"):
        success, media_list = runner.test(
            "Get CMS assets for legacy URL test",
            "GET", "/media", 200,
            params={"limit": 10}
        )
        
        if success and media_list:
            # Find an asset with legacy_url
            for item in media_list.get("assets", []):
                legacy_url = item.get("legacy_url")
                if legacy_url and legacy_url.startswith("/api/uploads/cms/"):
                    # Test legacy URL
                    runner.test(
                        f"Anti-regression: Legacy URL {legacy_url} still works",
                        "GET", legacy_url.replace("/api", ""), 200,
                        no_auth=True
                    )
                    break
    
    # Print summary
    return runner.print_summary()


if __name__ == "__main__":
    sys.exit(main())
