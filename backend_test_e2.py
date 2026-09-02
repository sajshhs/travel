#!/usr/bin/env python3
"""
Backend Test Suite for Phase E2 - CRM Growth Engine
====================================================
Tests Scoreboard, RFM, Segments, Sequences, and Campaigns (PRIMARY)
"""
import requests
import sys
import json
from datetime import datetime, timedelta

class E2TestSuite:
    def __init__(self, base_url="https://trip-route-buttons.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.segment_id = None
        self.sequence_id = None
        self.campaign_id = None
        
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
    
    def login(self):
        """Login as owner"""
        try:
            url = f"{self.base_url}/api/auth/login"
            response = requests.post(url, json={"email": "owner@demo.local", "password": "demo12345"}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                if self.token:
                    self.log("Login successful: owner@demo.local", "pass")
                    return True
            self.log(f"Login failed: {response.status_code}", "fail")
            return False
        except Exception as e:
            self.log(f"Login error: {str(e)}", "fail")
            return False
    
    def headers(self):
        """Get auth headers"""
        if not self.token:
            return {"Content-Type": "application/json"}
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
    
    def test_scoreboard(self):
        """Test GET /api/crm/scoreboard"""
        self.log("\n=== Testing Scoreboard ===", "info")
        
        try:
            url = f"{self.base_url}/api/crm/scoreboard"
            response = requests.get(url, headers=self.headers(), timeout=10)
            
            self.test(
                "GET /api/crm/scoreboard returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test(
                    "Scoreboard has 'leads' key",
                    "leads" in data,
                    "Missing 'leads' key"
                )
                self.test(
                    "Scoreboard has 'bands' key",
                    "bands" in data,
                    "Missing 'bands' key"
                )
                self.test(
                    "Scoreboard has 'total' key",
                    "total" in data,
                    "Missing 'total' key"
                )
                
                # Check bands structure
                if "bands" in data:
                    bands = data["bands"]
                    self.test(
                        "Bands has hot/warm/cold",
                        "hot" in bands and "warm" in bands and "cold" in bands,
                        f"Bands: {bands}"
                    )
        except Exception as e:
            self.test("GET /api/crm/scoreboard", False, str(e))
    
    def test_aging(self):
        """Test GET /api/crm/aging"""
        self.log("\n=== Testing SLA Aging ===", "info")
        
        try:
            url = f"{self.base_url}/api/crm/aging"
            response = requests.get(url, headers=self.headers(), timeout=10)
            
            self.test(
                "GET /api/crm/aging returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test(
                    "Aging has 'buckets' key",
                    "buckets" in data,
                    "Missing 'buckets' key"
                )
                self.test(
                    "Aging has 'counts' key",
                    "counts" in data,
                    "Missing 'counts' key"
                )
                
                # Check buckets structure
                if "buckets" in data:
                    buckets = data["buckets"]
                    expected_buckets = ["breached", "at_risk", "on_track", "responded"]
                    for bucket in expected_buckets:
                        self.test(
                            f"Buckets has '{bucket}'",
                            bucket in buckets,
                            f"Missing bucket: {bucket}"
                        )
        except Exception as e:
            self.test("GET /api/crm/aging", False, str(e))
    
    def test_rfm(self):
        """Test GET /api/crm/rfm"""
        self.log("\n=== Testing RFM/LTV ===", "info")
        
        try:
            url = f"{self.base_url}/api/crm/rfm"
            response = requests.get(url, headers=self.headers(), timeout=10)
            
            self.test(
                "GET /api/crm/rfm returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test(
                    "RFM has 'customers' key",
                    "customers" in data,
                    "Missing 'customers' key"
                )
                self.test(
                    "RFM has 'segments' key",
                    "segments" in data,
                    "Missing 'segments' key"
                )
                self.test(
                    "RFM has 'lifecycles' key",
                    "lifecycles" in data,
                    "Missing 'lifecycles' key"
                )
                self.test(
                    "RFM has 'total' key",
                    "total" in data,
                    "Missing 'total' key"
                )
        except Exception as e:
            self.test("GET /api/crm/rfm", False, str(e))
    
    def test_recompute(self):
        """Test POST /api/crm/recompute"""
        self.log("\n=== Testing Recompute ===", "info")
        
        try:
            url = f"{self.base_url}/api/crm/recompute"
            response = requests.post(url, headers=self.headers(), timeout=15)
            
            self.test(
                "POST /api/crm/recompute returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test(
                    "Recompute has 'leads_scored' key",
                    "leads_scored" in data,
                    "Missing 'leads_scored' key"
                )
                self.test(
                    "Recompute has 'customers_rfm' key",
                    "customers_rfm" in data,
                    "Missing 'customers_rfm' key"
                )
        except Exception as e:
            self.test("POST /api/crm/recompute", False, str(e))
    
    def test_segments(self):
        """Test Segments CRUD"""
        self.log("\n=== Testing Segments ===", "info")
        
        # List segments
        try:
            url = f"{self.base_url}/api/crm/segments"
            response = requests.get(url, headers=self.headers(), timeout=10)
            
            self.test(
                "GET /api/crm/segments returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                segments = response.json()
                self.test(
                    "Segments is a list",
                    isinstance(segments, list),
                    f"Expected list, got {type(segments)}"
                )
                
                # Check if pre-seeded segments exist
                if len(segments) > 0:
                    self.log(f"Found {len(segments)} pre-seeded segments", "info")
                    # Store first segment for preview test
                    self.segment_id = segments[0].get("id")
        except Exception as e:
            self.test("GET /api/crm/segments", False, str(e))
        
        # Create segment
        try:
            url = f"{self.base_url}/api/crm/segments"
            segment_data = {
                "name": "Test Segment E2",
                "audience": "customer",
                "criteria": {"lifecycle": "active"},
                "description": "Test segment for E2"
            }
            response = requests.post(url, json=segment_data, headers=self.headers(), timeout=10)
            
            self.test(
                "POST /api/crm/segments returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                created = response.json()
                self.test(
                    "Segment has ID with seg_ prefix",
                    created.get("id", "").startswith("seg_"),
                    f"Got ID: {created.get('id')}"
                )
                self.test(
                    "Segment name matches",
                    created.get("name") == "Test Segment E2",
                    f"Expected 'Test Segment E2', got {created.get('name')}"
                )
                self.test(
                    "Segment audience is customer",
                    created.get("audience") == "customer",
                    f"Expected 'customer', got {created.get('audience')}"
                )
                
                # Store for later tests
                if not self.segment_id:
                    self.segment_id = created.get("id")
        except Exception as e:
            self.test("POST /api/crm/segments", False, str(e))
        
        # Preview segment
        if self.segment_id:
            try:
                url = f"{self.base_url}/api/crm/segments/{self.segment_id}/preview"
                response = requests.get(url, headers=self.headers(), timeout=10)
                
                self.test(
                    "GET /api/crm/segments/{id}/preview returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
                
                if response.status_code == 200:
                    preview = response.json()
                    self.test(
                        "Preview has 'count' key",
                        "count" in preview,
                        "Missing 'count' key"
                    )
                    self.test(
                        "Preview has 'sample' key",
                        "sample" in preview,
                        "Missing 'sample' key"
                    )
                    self.test(
                        "Preview has 'reachable' key",
                        "reachable" in preview,
                        "Missing 'reachable' key"
                    )
            except Exception as e:
                self.test("GET /api/crm/segments/{id}/preview", False, str(e))
    
    def test_sequences(self):
        """Test Sequences CRUD"""
        self.log("\n=== Testing Sequences ===", "info")
        
        # List sequences
        try:
            url = f"{self.base_url}/api/crm/sequences"
            response = requests.get(url, headers=self.headers(), timeout=10)
            
            self.test(
                "GET /api/crm/sequences returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                sequences = response.json()
                self.test(
                    "Sequences is a list",
                    isinstance(sequences, list),
                    f"Expected list, got {type(sequences)}"
                )
        except Exception as e:
            self.test("GET /api/crm/sequences", False, str(e))
        
        # Create sequence
        try:
            url = f"{self.base_url}/api/crm/sequences"
            sequence_data = {
                "name": "Test Sequence E2",
                "description": "Test sequence for E2",
                "audience": "lead",
                "enabled": True,
                "steps": [
                    {"day": 0, "action": "whatsapp", "message": "Welcome!"},
                    {"day": 3, "action": "whatsapp", "message": "Follow-up"}
                ]
            }
            response = requests.post(url, json=sequence_data, headers=self.headers(), timeout=10)
            
            self.test(
                "POST /api/crm/sequences returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                created = response.json()
                self.test(
                    "Sequence has ID with seq_ prefix",
                    created.get("id", "").startswith("seq_"),
                    f"Got ID: {created.get('id')}"
                )
                self.test(
                    "Sequence name matches",
                    created.get("name") == "Test Sequence E2",
                    f"Expected 'Test Sequence E2', got {created.get('name')}"
                )
                self.test(
                    "Sequence has steps",
                    len(created.get("steps", [])) == 2,
                    f"Expected 2 steps, got {len(created.get('steps', []))}"
                )
                
                # Store for later tests
                self.sequence_id = created.get("id")
        except Exception as e:
            self.test("POST /api/crm/sequences", False, str(e))
    
    def test_campaigns(self):
        """Test Campaigns CRUD and Send (PRIMARY FEATURE)"""
        self.log("\n=== Testing Campaigns (PRIMARY) ===", "info")
        
        # List campaigns
        try:
            url = f"{self.base_url}/api/crm/campaigns"
            response = requests.get(url, headers=self.headers(), timeout=10)
            
            self.test(
                "GET /api/crm/campaigns returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                campaigns = response.json()
                self.test(
                    "Campaigns is a list",
                    isinstance(campaigns, list),
                    f"Expected list, got {type(campaigns)}"
                )
        except Exception as e:
            self.test("GET /api/crm/campaigns", False, str(e))
        
        # Create campaign (requires segment)
        if not self.segment_id:
            self.log("No segment available, skipping campaign creation", "warn")
            return
        
        try:
            url = f"{self.base_url}/api/crm/campaigns"
            campaign_data = {
                "name": "Test Campaign E2",
                "audience": "customer",
                "segment_id": self.segment_id,
                "message": "Halo {name}, promo spesial untuk Anda!",
                "template_key": None,
                "scheduled_at": None
            }
            response = requests.post(url, json=campaign_data, headers=self.headers(), timeout=10)
            
            self.test(
                "POST /api/crm/campaigns returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                created = response.json()
                self.test(
                    "Campaign has ID with cmp_ prefix",
                    created.get("id", "").startswith("cmp_"),
                    f"Got ID: {created.get('id')}"
                )
                self.test(
                    "Campaign name matches",
                    created.get("name") == "Test Campaign E2",
                    f"Expected 'Test Campaign E2', got {created.get('name')}"
                )
                self.test(
                    "Campaign status is draft",
                    created.get("status") == "draft",
                    f"Expected 'draft', got {created.get('status')}"
                )
                self.test(
                    "Campaign has segment_id",
                    created.get("segment_id") == self.segment_id,
                    f"Expected {self.segment_id}, got {created.get('segment_id')}"
                )
                
                # Store for later tests
                self.campaign_id = created.get("id")
        except Exception as e:
            self.test("POST /api/crm/campaigns", False, str(e))
        
        # Send campaign
        if self.campaign_id:
            try:
                url = f"{self.base_url}/api/crm/campaigns/{self.campaign_id}/send"
                response = requests.post(url, headers=self.headers(), timeout=15)
                
                self.test(
                    "POST /api/crm/campaigns/{id}/send returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
                
                if response.status_code == 200:
                    stats = response.json()
                    self.test(
                        "Send stats has 'total' key",
                        "total" in stats,
                        "Missing 'total' key"
                    )
                    self.test(
                        "Send stats has 'sent' key",
                        "sent" in stats,
                        "Missing 'sent' key"
                    )
                    self.test(
                        "Send stats has 'failed' key",
                        "failed" in stats,
                        "Missing 'failed' key"
                    )
                    self.test(
                        "Send stats has 'cost' key",
                        "cost" in stats,
                        "Missing 'cost' key"
                    )
                    
                    self.log(f"Campaign sent: {stats.get('sent')}/{stats.get('total')} · Cost: {stats.get('cost')}", "info")
            except Exception as e:
                self.test("POST /api/crm/campaigns/{id}/send", False, str(e))
            
            # Get campaign with recipients
            try:
                url = f"{self.base_url}/api/crm/campaigns/{self.campaign_id}"
                response = requests.get(url, headers=self.headers(), timeout=10)
                
                self.test(
                    "GET /api/crm/campaigns/{id} returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
                
                if response.status_code == 200:
                    campaign = response.json()
                    self.test(
                        "Campaign has 'recipients' key",
                        "recipients" in campaign,
                        "Missing 'recipients' key"
                    )
                    self.test(
                        "Campaign has 'stats' key",
                        "stats" in campaign,
                        "Missing 'stats' key"
                    )
                    self.test(
                        "Campaign status is sent",
                        campaign.get("status") == "sent",
                        f"Expected 'sent', got {campaign.get('status')}"
                    )
                    
                    recipients = campaign.get("recipients", [])
                    if len(recipients) > 0:
                        self.log(f"Found {len(recipients)} recipients", "info")
                        # Check recipient structure
                        first = recipients[0]
                        self.test(
                            "Recipient has 'id' key",
                            "id" in first,
                            "Missing 'id' key"
                        )
                        self.test(
                            "Recipient has 'status' key",
                            "status" in first,
                            "Missing 'status' key"
                        )
            except Exception as e:
                self.test("GET /api/crm/campaigns/{id}", False, str(e))
    
    def test_wa_templates(self):
        """Test GET /api/wa/templates"""
        self.log("\n=== Testing WhatsApp Templates ===", "info")
        
        try:
            url = f"{self.base_url}/api/wa/templates"
            response = requests.get(url, headers=self.headers(), timeout=10)
            
            self.test(
                "GET /api/wa/templates returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                templates = response.json()
                self.test(
                    "Templates is a list",
                    isinstance(templates, list),
                    f"Expected list, got {type(templates)}"
                )
        except Exception as e:
            self.test("GET /api/wa/templates", False, str(e))
    
    def test_validation(self):
        """Test validation errors"""
        self.log("\n=== Testing Validation ===", "info")
        
        # Campaign without segment_id should fail
        try:
            url = f"{self.base_url}/api/crm/campaigns"
            campaign_data = {
                "name": "Invalid Campaign",
                "audience": "customer",
                "message": "Test"
            }
            response = requests.post(url, json=campaign_data, headers=self.headers(), timeout=10)
            
            self.test(
                "POST campaign without segment_id returns 400",
                response.status_code == 400,
                f"Expected 400, got {response.status_code}"
            )
        except Exception as e:
            self.test("Campaign validation (no segment)", False, str(e))
        
        # Campaign without message/template should fail
        if self.segment_id:
            try:
                url = f"{self.base_url}/api/crm/campaigns"
                campaign_data = {
                    "name": "Invalid Campaign 2",
                    "audience": "customer",
                    "segment_id": self.segment_id
                }
                response = requests.post(url, json=campaign_data, headers=self.headers(), timeout=10)
                
                self.test(
                    "POST campaign without message/template returns 400",
                    response.status_code == 400,
                    f"Expected 400, got {response.status_code}"
                )
            except Exception as e:
                self.test("Campaign validation (no message)", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*60, "info")
        self.log("Phase E2 - CRM Growth Engine Backend Test Suite", "info")
        self.log("="*60, "info")
        
        # Login
        if not self.login():
            self.log("\n⚠️  Authentication failed. Cannot proceed.", "warn")
            return False
        
        # Run tests in order
        self.test_scoreboard()
        self.test_aging()
        self.test_rfm()
        self.test_recompute()
        self.test_segments()
        self.test_sequences()
        self.test_wa_templates()
        self.test_campaigns()  # PRIMARY
        self.test_validation()
        
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
    tester = E2TestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
