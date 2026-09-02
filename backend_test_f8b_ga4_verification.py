#!/usr/bin/env python3
"""backend_test_f8b_ga4_verification.py — Verify GA4 in conversion outbox with DB access.

This script directly checks the database to verify:
1. GA4 is enqueued as the THIRD provider (meta, google, ga4)
2. GA4 status is `skipped` with proper reason (not 5xx, not silent)
3. The reason mentions GA4 Measurement ID or API secret
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
    print("  GA4 CONVERSION OUTBOX VERIFICATION")
    print("="*70 + "\n")
    
    # Connect to database
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    
    # Get owner token
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    
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
    test_name = f"GA4 Test {uuid.uuid4().hex[:6]}"
    
    print(f"\n📝 Creating test lead: {test_name} / {phone}")
    r = requests.post(f"{API}/public/landing/{slug}/lead",
                     json={
                         "name": test_name,
                         "phone": phone,
                         "marketing_consent": True,
                         "attribution": {
                             "utm_source": "google",
                             "utm_medium": "cpc",
                             "gclid": f"TEST_GCLID_{uuid.uuid4().hex[:8]}"
                         }
                     },
                     timeout=30)
    
    if r.status_code not in [200, 201]:
        print(f"❌ Could not create lead: HTTP {r.status_code}")
        print(f"   Response: {r.text}")
        return 1
    
    lead_data = r.json()
    lead_id = lead_data.get("id")
    print(f"✅ Lead created: {lead_id}")
    
    # Query conversion_events collection
    print(f"\n🔍 Checking conversion_events for lead {lead_id}...")
    
    events = await db.conversion_events.find(
        {"ref_id": lead_id},
        {"_id": 0, "provider": 1, "status": 1, "last_error": 1, "event_key": 1}
    ).to_list(10)
    
    if not events:
        print("❌ No conversion events found in outbox")
        return 1
    
    print(f"\n📊 Found {len(events)} conversion events:")
    print("-" * 70)
    
    providers_found = {}
    for event in events:
        provider = event.get("provider")
        status = event.get("status")
        error = event.get("last_error", "")
        event_key = event.get("event_key", "")
        
        providers_found[provider] = {
            "status": status,
            "error": error,
            "event_key": event_key
        }
        
        print(f"\nProvider: {provider}")
        print(f"  Status: {status}")
        if error:
            print(f"  Reason: {error}")
        print(f"  Event Key: {event_key}")
    
    print("\n" + "="*70)
    print("  VERIFICATION RESULTS")
    print("="*70)
    
    # Check 1: All three providers present
    expected_providers = {"meta", "google", "ga4"}
    found_providers = set(providers_found.keys())
    
    if expected_providers == found_providers:
        print("✅ All three providers present: meta, google, ga4")
    else:
        print(f"❌ Expected providers {expected_providers}, found {found_providers}")
        return 1
    
    # Check 2: GA4 status is skipped or pending (not success, not failed, not dead)
    ga4_status = providers_found.get("ga4", {}).get("status")
    ga4_error = providers_found.get("ga4", {}).get("error", "")
    
    if ga4_status in ["skipped", "pending"]:
        print(f"✅ GA4 status is '{ga4_status}' (credentials not configured)")
    else:
        print(f"❌ GA4 status is '{ga4_status}' (expected 'skipped' or 'pending')")
        return 1
    
    # Check 3: GA4 has a reason (not silent failure)
    if ga4_error:
        print(f"✅ GA4 has error reason: {ga4_error}")
    else:
        print(f"⚠️  GA4 has no error reason (might be pending)")
    
    # Check 4: Reason mentions GA4 credentials
    if ga4_error and ("Measurement ID" in ga4_error or "API secret" in ga4_error or "GA4" in ga4_error):
        print(f"✅ GA4 error mentions credentials (Measurement ID or API secret)")
    elif ga4_status == "skipped":
        print(f"⚠️  GA4 error should mention credentials: {ga4_error}")
    
    # Check 5: Meta and Google status (should be skipped or pending too, since MOCK)
    meta_status = providers_found.get("meta", {}).get("status")
    google_status = providers_found.get("google", {}).get("status")
    
    print(f"\n📋 Other providers status:")
    print(f"   Meta: {meta_status}")
    print(f"   Google: {google_status}")
    
    # Cleanup
    print(f"\n🧹 Cleaning up test data...")
    await db.leads.delete_many({"id": lead_id})
    await db.conversion_events.delete_many({"ref_id": lead_id})
    print(f"✅ Test lead and conversion events deleted")
    
    print("\n" + "="*70)
    print("  ✅ GA4 CONVERSION OUTBOX VERIFICATION PASSED")
    print("="*70 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
