#!/usr/bin/env python3
"""backend_test_f8b_ga4_dispatch.py — Test GA4 dispatch worker behavior.

This script:
1. Creates a test lead to enqueue conversion events
2. Triggers the dispatch worker
3. Verifies GA4 is marked as 'skipped' with proper reason
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
    print("  GA4 DISPATCH WORKER TEST")
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
    test_name = f"GA4 Dispatch Test {uuid.uuid4().hex[:6]}"
    
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
        return 1
    
    lead_data = r.json()
    lead_id = lead_data.get("id")
    print(f"✅ Lead created: {lead_id}")
    
    # Check initial status
    print(f"\n🔍 Checking initial conversion events status...")
    events = await db.conversion_events.find(
        {"ref_id": lead_id},
        {"_id": 0, "provider": 1, "status": 1}
    ).to_list(10)
    
    for event in events:
        print(f"   {event['provider']}: {event['status']}")
    
    # Trigger dispatch worker
    print(f"\n⚙️  Triggering dispatch worker...")
    r = requests.post(f"{API}/tracking/dispatch", headers=headers, json={}, timeout=30)
    
    if r.status_code != 200:
        print(f"❌ Dispatch failed: HTTP {r.status_code}")
        print(f"   Response: {r.text}")
        return 1
    
    dispatch_result = r.json()
    print(f"✅ Dispatch completed: {dispatch_result}")
    
    # Check status after dispatch
    print(f"\n🔍 Checking conversion events after dispatch...")
    events = await db.conversion_events.find(
        {"ref_id": lead_id},
        {"_id": 0, "provider": 1, "status": 1, "last_error": 1, "http_status": 1}
    ).to_list(10)
    
    print("\n" + "="*70)
    print("  DISPATCH RESULTS")
    print("="*70)
    
    ga4_found = False
    ga4_status = None
    ga4_error = None
    
    for event in events:
        provider = event.get("provider")
        status = event.get("status")
        error = event.get("last_error", "")
        http_status = event.get("http_status")
        
        print(f"\nProvider: {provider}")
        print(f"  Status: {status}")
        if error:
            print(f"  Error: {error}")
        if http_status:
            print(f"  HTTP Status: {http_status}")
        
        if provider == "ga4":
            ga4_found = True
            ga4_status = status
            ga4_error = error
    
    print("\n" + "="*70)
    print("  VERIFICATION")
    print("="*70)
    
    # Verify GA4 behavior
    if not ga4_found:
        print("❌ GA4 provider not found")
        return 1
    
    print(f"✅ GA4 provider found")
    
    # GA4 should be skipped (not 5xx, not silent)
    if ga4_status == "skipped":
        print(f"✅ GA4 status is 'skipped' (correct)")
    elif ga4_status == "pending":
        print(f"⚠️  GA4 status is still 'pending' (worker may not have processed it yet)")
    else:
        print(f"❌ GA4 status is '{ga4_status}' (expected 'skipped')")
    
    # Check for proper error message
    if ga4_error:
        print(f"✅ GA4 has error reason: {ga4_error}")
        
        # Check if reason mentions credentials
        if "Measurement ID" in ga4_error or "API secret" in ga4_error or "GA4" in ga4_error:
            print(f"✅ Error mentions GA4 credentials (Measurement ID or API secret)")
        else:
            print(f"⚠️  Error doesn't mention GA4 credentials: {ga4_error}")
    else:
        if ga4_status == "skipped":
            print(f"⚠️  GA4 is skipped but has no error reason")
        else:
            print(f"⚠️  GA4 has no error reason (still pending)")
    
    # Cleanup
    print(f"\n🧹 Cleaning up test data...")
    await db.leads.delete_many({"id": lead_id})
    await db.conversion_events.delete_many({"ref_id": lead_id})
    print(f"✅ Test lead and conversion events deleted")
    
    print("\n" + "="*70)
    print("  ✅ GA4 DISPATCH TEST COMPLETED")
    print("="*70 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
