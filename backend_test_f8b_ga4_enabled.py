#!/usr/bin/env python3
"""backend_test_f8b_ga4_enabled.py — Test GA4 error message when integration is enabled.

This script:
1. Enables Google Ads integration (which includes GA4)
2. Creates a test lead
3. Triggers dispatch
4. Verifies GA4 error message mentions specific credentials
"""
import asyncio
import os
import sys
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(ROOT / "backend" / ".env")

from motor.motor_asyncio import AsyncIOMotorClient
from core_utils import now_iso

# Public endpoint
BASE_URL = "https://trip-route-buttons.preview.emergentagent.com"
API = f"{BASE_URL}/api"

def login(email="owner@demo.local"):
    """Login and get token"""
    r = requests.post(f"{API}/auth/login", 
                     json={"email": email, "password": "demo12345"}, 
                     timeout=20)
    return r.json()["token"]

async def main():
    print("\n" + "="*70)
    print("  GA4 ERROR MESSAGE TEST (Integration Enabled)")
    print("="*70 + "\n")
    
    # Connect to database
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    
    # Get owner token
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Save current integration config
    print("📋 Saving current integration config...")
    current_config = await db.settings.find_one({"key": "google_ads_config"}, {"_id": 0})
    
    try:
        # Enable Google Ads integration (without credentials)
        print("⚙️  Enabling Google Ads integration (without credentials)...")
        await db.settings.update_one(
            {"key": "google_ads_config"},
            {"$set": {
                "key": "google_ads_config",
                "value": {"enabled": True},
                "updated_at": now_iso()
            }},
            upsert=True
        )
        
        # Get a published page
        r = requests.get(f"{API}/landing/pages?status=published", headers=headers, timeout=20)
        if r.status_code != 200:
            print(f"❌ Could not get published pages: HTTP {r.status_code}")
            return 1
        
        pages = r.json().get("pages", [])
        if not pages:
            print("❌ No published pages found")
            return 1
        
        slug = pages[0]["slug"]
        print(f"✅ Using published page: /lp/{slug}")
        
        # Create a test lead
        phone = f"0813{uuid.uuid4().int % 90000000 + 10000000}"
        test_name = f"GA4 Enabled Test {uuid.uuid4().hex[:6]}"
        
        print(f"\n📝 Creating test lead: {test_name} / {phone}")
        r = requests.post(f"{API}/public/landing/{slug}/lead",
                         json={
                             "name": test_name,
                             "phone": phone,
                             "marketing_consent": True,
                             "attribution": {
                                 "utm_source": "google",
                                 "utm_medium": "cpc"
                             }
                         },
                         timeout=30)
        
        if r.status_code not in [200, 201]:
            print(f"❌ Could not create lead: HTTP {r.status_code}")
            return 1
        
        lead_data = r.json()
        lead_id = lead_data.get("id")
        print(f"✅ Lead created: {lead_id}")
        
        # Trigger dispatch worker
        print(f"\n⚙️  Triggering dispatch worker...")
        r = requests.post(f"{API}/tracking/dispatch", headers=headers, json={}, timeout=30)
        
        if r.status_code != 200:
            print(f"❌ Dispatch failed: HTTP {r.status_code}")
            return 1
        
        dispatch_result = r.json()
        print(f"✅ Dispatch completed: {dispatch_result}")
        
        # Check GA4 status and error message
        print(f"\n🔍 Checking GA4 conversion event...")
        ga4_event = await db.conversion_events.find_one(
            {"ref_id": lead_id, "provider": "ga4"},
            {"_id": 0, "status": 1, "last_error": 1}
        )
        
        if not ga4_event:
            print("❌ GA4 event not found")
            return 1
        
        status = ga4_event.get("status")
        error = ga4_event.get("last_error", "")
        
        print("\n" + "="*70)
        print("  GA4 EVENT DETAILS")
        print("="*70)
        print(f"Status: {status}")
        print(f"Error: {error}")
        
        print("\n" + "="*70)
        print("  VERIFICATION")
        print("="*70)
        
        # Verify status is skipped
        if status == "skipped":
            print("✅ GA4 status is 'skipped'")
        else:
            print(f"❌ GA4 status is '{status}' (expected 'skipped')")
        
        # Verify error message mentions GA4 credentials
        if error:
            print(f"✅ GA4 has error message")
            
            if "Measurement ID" in error or "GA4" in error:
                print(f"✅ Error mentions GA4 Measurement ID")
            elif "API secret" in error:
                print(f"✅ Error mentions API secret")
            else:
                print(f"⚠️  Error doesn't specifically mention GA4 credentials: {error}")
        else:
            print(f"❌ GA4 has no error message")
        
        # Cleanup test data
        print(f"\n🧹 Cleaning up test data...")
        await db.leads.delete_many({"id": lead_id})
        await db.conversion_events.delete_many({"ref_id": lead_id})
        print(f"✅ Test lead and conversion events deleted")
        
    finally:
        # Restore original config
        print(f"\n🔄 Restoring original integration config...")
        if current_config:
            await db.settings.replace_one(
                {"key": "google_ads_config"},
                current_config
            )
        else:
            await db.settings.delete_one({"key": "google_ads_config"})
        print(f"✅ Config restored")
    
    print("\n" + "="*70)
    print("  ✅ GA4 ERROR MESSAGE TEST COMPLETED")
    print("="*70 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
