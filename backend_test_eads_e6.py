#!/usr/bin/env python3
"""
Backend Test Suite for E-ADS (Attribution & Marketing) + E6 Prep (WhatsApp Meta Cloud)
========================================================================================
Tests public lead capture with attribution, Lead Ads webhooks, analytics channels, and WhatsApp test-send.
"""
import requests
import sys
import json
from datetime import datetime

class EAdsE6TestSuite:
    def __init__(self, base_url="https://trip-route-buttons.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.created_lead_ids = []
        
    def log(self, msg, status="info"):
        symbols = {"pass": "✅", "fail": "❌", "info": "🔍", "warn": "⚠️"}
        print(f"{symbols.get(status, '•')} {msg}")
    
    def test(self, name, condition, details=""):
        """Record test result"""
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            self.log(f"PASS: {name}", "pass")
            return True
        else:
            self.tests_failed += 1
            self.failures.append(f"{name}: {details}")
            self.log(f"FAIL: {name} - {details}", "fail")
            return False
    
    def login(self, email, password):
        """Login and store token"""
        try:
            url = f"{self.base_url}/api/auth/login"
            response = requests.post(url, json={"email": email, "password": password}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                token = data.get("token")
                if token:
                    self.tokens[email] = token
                    self.log(f"Login successful: {email}", "pass")
                    return True
            self.log(f"Login failed for {email}: {response.status_code}", "fail")
            return False
        except Exception as e:
            self.log(f"Login error for {email}: {str(e)}", "fail")
            return False
    
    def headers(self, email=None):
        """Get auth headers for user"""
        if email is None:
            return {"Content-Type": "application/json"}
        token = self.tokens.get(email)
        if not token:
            return {"Content-Type": "application/json"}
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    
    def test_auth(self):
        """Test authentication for all users"""
        self.log("\n=== Testing Authentication ===", "info")
        
        owner_ok = self.login("owner@demo.local", "demo12345")
        ops_ok = self.login("ops@demo.local", "demo12345")
        driver_ok = self.login("driver@demo.local", "demo12345")
        
        self.test("Owner login", owner_ok)
        self.test("Ops Admin login", ops_ok)
        self.test("Driver login", driver_ok)
        
        return owner_ok and driver_ok
    
    def test_public_quotation_attribution(self):
        """Test POST /api/public/quotation with attribution (first_touch, last_touch, marketing_consent)"""
        self.log("\n=== Testing Public Quotation with Attribution ===", "info")
        
        # Test with full attribution (first_touch + last_touch with gclid)
        try:
            url = f"{self.base_url}/api/public/quotation"
            payload = {
                "name": "Test User Attribution",
                "phone": "628111000111",
                "email": "test@example.com",
                "destination": "Bali",
                "trip_date": "2025-09-15",
                "pax": 10,
                "message": "Test quotation with attribution",
                "attribution": {
                    "first_touch": {
                        "utm_source": "google",
                        "utm_medium": "cpc",
                        "utm_campaign": "summer-promo",
                        "gclid": "abc123"
                    },
                    "last_touch": {
                        "utm_source": "google",
                        "utm_medium": "cpc",
                        "utm_campaign": "summer-promo",
                        "gclid": "abc123"
                    }
                },
                "marketing_consent": True
            }
            
            response = requests.post(url, json=payload, headers=self.headers(), timeout=10)
            
            self.test(
                "POST /api/public/quotation returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test(
                    "Quotation response has status 'received'",
                    data.get("status") == "received",
                    f"Got status: {data.get('status')}"
                )
                
                lead_id = data.get("id")
                if lead_id:
                    self.created_lead_ids.append(lead_id)
                    
                    # Verify lead was created with correct channel via GET /api/leads
                    leads_url = f"{self.base_url}/api/leads"
                    leads_response = requests.get(leads_url, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    if leads_response.status_code == 200:
                        leads = leads_response.json()
                        created_lead = next((l for l in leads if l.get("phone") == "628111000111"), None)
                        
                        if created_lead:
                            self.test(
                                "Lead created with channel='google_ads' (gclid detected)",
                                created_lead.get("channel") == "google_ads",
                                f"Got channel: {created_lead.get('channel')}"
                            )
                            
                            self.test(
                                "Lead has marketing_consent=True",
                                created_lead.get("marketing_consent") == True,
                                f"Got marketing_consent: {created_lead.get('marketing_consent')}"
                            )
                        else:
                            self.test("Lead found in database", False, "Lead not found by phone")
        except Exception as e:
            self.test("POST /api/public/quotation with attribution", False, str(e))
    
    def test_lead_ads_meta_simple(self):
        """Test POST /api/public/lead-ads/meta with simple payload"""
        self.log("\n=== Testing Lead Ads Meta (Simple Payload) ===", "info")
        
        try:
            url = f"{self.base_url}/api/public/lead-ads/meta"
            payload = {
                "full_name": "Ads Lead Simple",
                "phone": "628111000222",
                "campaign": "promo-bali"
            }
            
            response = requests.post(url, json=payload, headers=self.headers(), timeout=10)
            
            self.test(
                "POST /api/public/lead-ads/meta returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                self.test(
                    "Lead Ads response has status 'received'",
                    data.get("status") == "received",
                    f"Got status: {data.get('status')}"
                )
                
                self.test(
                    "Lead Ads response has channel 'meta_ads'",
                    data.get("channel") == "meta_ads",
                    f"Got channel: {data.get('channel')}"
                )
                
                lead_id = data.get("id")
                if lead_id:
                    self.created_lead_ids.append(lead_id)
                    
                    # Verify lead details
                    leads_url = f"{self.base_url}/api/leads"
                    leads_response = requests.get(leads_url, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    if leads_response.status_code == 200:
                        leads = leads_response.json()
                        created_lead = next((l for l in leads if l.get("phone") == "628111000222"), None)
                        
                        if created_lead:
                            self.test(
                                "Lead has source='ads'",
                                created_lead.get("source") == "ads",
                                f"Got source: {created_lead.get('source')}"
                            )
                            
                            self.test(
                                "Lead has marketing_consent=True (Lead Ads implicit consent)",
                                created_lead.get("marketing_consent") == True,
                                f"Got marketing_consent: {created_lead.get('marketing_consent')}"
                            )
        except Exception as e:
            self.test("POST /api/public/lead-ads/meta simple", False, str(e))
    
    def test_lead_ads_meta_envelope(self):
        """Test POST /api/public/lead-ads/meta with Meta envelope (field_data)"""
        self.log("\n=== Testing Lead Ads Meta (Envelope field_data) ===", "info")
        
        try:
            url = f"{self.base_url}/api/public/lead-ads/meta"
            payload = {
                "field_data": [
                    {"name": "full_name", "values": ["Sinta Envelope"]},
                    {"name": "phone_number", "values": ["628222333444"]}
                ]
            }
            
            response = requests.post(url, json=payload, headers=self.headers(), timeout=10)
            
            self.test(
                "POST /api/public/lead-ads/meta (envelope) returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                lead_id = data.get("id")
                
                if lead_id:
                    self.created_lead_ids.append(lead_id)
                    
                    # Verify lead was parsed correctly
                    leads_url = f"{self.base_url}/api/leads"
                    leads_response = requests.get(leads_url, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    if leads_response.status_code == 200:
                        leads = leads_response.json()
                        created_lead = next((l for l in leads if l.get("phone") == "628222333444"), None)
                        
                        if created_lead:
                            self.test(
                                "Lead name parsed from field_data envelope",
                                created_lead.get("customer_name") == "Sinta Envelope",
                                f"Got name: {created_lead.get('customer_name')}"
                            )
        except Exception as e:
            self.test("POST /api/public/lead-ads/meta envelope", False, str(e))
    
    def test_lead_ads_providers(self):
        """Test POST /api/public/lead-ads/{provider} for different providers"""
        self.log("\n=== Testing Lead Ads Different Providers ===", "info")
        
        providers = [
            ("google", "google_ads"),
            ("tiktok", "tiktok_ads")
        ]
        
        for provider, expected_channel in providers:
            try:
                url = f"{self.base_url}/api/public/lead-ads/{provider}"
                payload = {
                    "full_name": f"Lead from {provider}",
                    "phone": f"6281110003{provider[:2]}",
                    "campaign": f"test-{provider}"
                }
                
                response = requests.post(url, json=payload, headers=self.headers(), timeout=10)
                
                self.test(
                    f"POST /api/public/lead-ads/{provider} returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    self.test(
                        f"Lead Ads {provider} has channel '{expected_channel}'",
                        data.get("channel") == expected_channel,
                        f"Expected {expected_channel}, got {data.get('channel')}"
                    )
                    
                    if data.get("id"):
                        self.created_lead_ids.append(data.get("id"))
            except Exception as e:
                self.test(f"POST /api/public/lead-ads/{provider}", False, str(e))
    
    def test_lead_ads_invalid_provider(self):
        """Test POST /api/public/lead-ads/xyz (invalid provider) returns 400"""
        self.log("\n=== Testing Lead Ads Invalid Provider ===", "info")
        
        try:
            url = f"{self.base_url}/api/public/lead-ads/xyz"
            payload = {
                "full_name": "Test Invalid",
                "phone": "628111000999"
            }
            
            response = requests.post(url, json=payload, headers=self.headers(), timeout=10)
            
            self.test(
                "POST /api/public/lead-ads/xyz returns 400",
                response.status_code == 400,
                f"Expected 400, got {response.status_code}"
            )
            
            if response.status_code == 400:
                data = response.json()
                self.test(
                    "Error message mentions 'Provider tidak didukung'",
                    "Provider tidak didukung" in data.get("detail", ""),
                    f"Got detail: {data.get('detail')}"
                )
        except Exception as e:
            self.test("POST /api/public/lead-ads/xyz invalid", False, str(e))
    
    def test_analytics_channels(self):
        """Test GET /api/analytics/channels?days=90 (owner)"""
        self.log("\n=== Testing Analytics Channels ===", "info")
        
        try:
            url = f"{self.base_url}/api/analytics/channels?days=90"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/analytics/channels returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                self.test(
                    "Analytics response has 'channels' array",
                    "channels" in data and isinstance(data["channels"], list),
                    f"channels field missing or not array"
                )
                
                self.test(
                    "Analytics response has 'totals' object",
                    "totals" in data and isinstance(data["totals"], dict),
                    f"totals field missing or not object"
                )
                
                # Check channel structure
                if data.get("channels"):
                    channel = data["channels"][0]
                    required_fields = ["channel", "label", "leads", "won", "spend", "cpl", "cac", "roas"]
                    
                    for field in required_fields:
                        self.test(
                            f"Channel object has '{field}' field",
                            field in channel,
                            f"{field} missing from channel object"
                        )
                    
                    # Check if google_ads and meta_ads appear with proper labels
                    channels_dict = {c["channel"]: c for c in data["channels"]}
                    
                    if "google_ads" in channels_dict:
                        self.test(
                            "google_ads has label 'Google Ads'",
                            channels_dict["google_ads"].get("label") == "Google Ads",
                            f"Got label: {channels_dict['google_ads'].get('label')}"
                        )
                    
                    if "meta_ads" in channels_dict:
                        self.test(
                            "meta_ads has label 'Meta Ads'",
                            channels_dict["meta_ads"].get("label") == "Meta Ads",
                            f"Got label: {channels_dict['meta_ads'].get('label')}"
                        )
        except Exception as e:
            self.test("GET /api/analytics/channels", False, str(e))
    
    def test_wa_test_send_owner(self):
        """Test POST /api/wa/test-send (owner) returns 200 with mock provider"""
        self.log("\n=== Testing WhatsApp Test Send (Owner) ===", "info")
        
        try:
            url = f"{self.base_url}/api/wa/test-send"
            payload = {
                "to_phone": "628123456789",
                "text": "Test message from E-ADS test suite"
            }
            
            response = requests.post(url, json=payload, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/wa/test-send (owner) returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                self.test(
                    "WhatsApp test-send has status 'sent'",
                    data.get("status") == "sent",
                    f"Got status: {data.get('status')}"
                )
                
                self.test(
                    "WhatsApp test-send has ok=True",
                    data.get("ok") == True,
                    f"Got ok: {data.get('ok')}"
                )
                
                self.test(
                    "WhatsApp test-send has provider='mock' (default)",
                    data.get("provider") == "mock",
                    f"Got provider: {data.get('provider')}"
                )
        except Exception as e:
            self.test("POST /api/wa/test-send owner", False, str(e))
    
    def test_rbac_wa_test_send_driver(self):
        """Test POST /api/wa/test-send as driver returns 403"""
        self.log("\n=== Testing RBAC: WhatsApp Test Send (Driver) ===", "info")
        
        try:
            url = f"{self.base_url}/api/wa/test-send"
            payload = {
                "to_phone": "628123456789"
            }
            
            response = requests.post(url, json=payload, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "POST /api/wa/test-send (driver) returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("POST /api/wa/test-send driver RBAC", False, str(e))
    
    def test_rbac_analytics_channels_driver(self):
        """Test GET /api/analytics/channels as driver returns 403"""
        self.log("\n=== Testing RBAC: Analytics Channels (Driver) ===", "info")
        
        try:
            url = f"{self.base_url}/api/analytics/channels?days=90"
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "GET /api/analytics/channels (driver) returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("GET /api/analytics/channels driver RBAC", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*60, "info")
        self.log("E-ADS + E6 Prep Backend Test Suite", "info")
        self.log("="*60, "info")
        
        # Run tests in order
        if not self.test_auth():
            self.log("\n⚠️  Authentication failed. Cannot proceed with other tests.", "warn")
            return False
        
        # E-ADS tests
        self.test_public_quotation_attribution()
        self.test_lead_ads_meta_simple()
        self.test_lead_ads_meta_envelope()
        self.test_lead_ads_providers()
        self.test_lead_ads_invalid_provider()
        self.test_analytics_channels()
        
        # E6 tests
        self.test_wa_test_send_owner()
        
        # RBAC tests
        self.test_rbac_wa_test_send_driver()
        self.test_rbac_analytics_channels_driver()
        
        # Print summary
        self.log("\n" + "="*60, "info")
        self.log("TEST SUMMARY", "info")
        self.log("="*60, "info")
        self.log(f"Total Tests: {self.tests_run}", "info")
        self.log(f"Passed: {self.tests_passed}", "pass")
        self.log(f"Failed: {self.tests_failed}", "fail" if self.tests_failed > 0 else "info")
        
        if self.tests_failed > 0:
            self.log("\nFailed Tests:", "fail")
            for failure in self.failures:
                self.log(f"  - {failure}", "fail")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"\nSuccess Rate: {success_rate:.1f}%", "pass" if success_rate == 100 else "warn")
        
        return self.tests_failed == 0


def main():
    tester = EAdsE6TestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
