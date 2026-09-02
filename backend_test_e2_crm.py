#!/usr/bin/env python3
"""
Backend Test Suite for E2 CRM Growth Engine (Iteration 33)
===========================================================
Tests Segments, Campaigns, Sequences, Scoreboard, RFM APIs
"""
import requests
import sys
import json
from datetime import datetime

class E2CRMTestSuite:
    def __init__(self, base_url="https://trip-route-buttons.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.segment_ids = []
        self.campaign_ids = []
        
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
    
    def test_segments_list(self):
        """Test GET /api/crm/segments - should return 3 seeded segments"""
        self.log("\n=== Testing Segments List ===", "info")
        
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
                    "Segments list has 3 seeded segments",
                    len(segments) == 3,
                    f"Expected 3, got {len(segments)}"
                )
                
                # Check for expected segments
                segment_names = [s.get("name") for s in segments]
                expected_names = ["Semua Pelanggan", "Lead Hot", "Pelanggan Bernilai Tinggi"]
                
                for expected_name in expected_names:
                    found = expected_name in segment_names
                    self.test(
                        f"Segment '{expected_name}' exists",
                        found,
                        f"Not found in {segment_names}"
                    )
                
                # Store segment IDs for later tests
                for seg in segments:
                    self.segment_ids.append(seg.get("id"))
                    
                    # Verify segment structure
                    self.test(
                        f"Segment '{seg.get('name')}' has required fields",
                        all(k in seg for k in ["id", "name", "audience", "criteria"]),
                        f"Missing fields in {seg.keys()}"
                    )
                
                return segments
        except Exception as e:
            self.test("GET /api/crm/segments", False, str(e))
            return []
    
    def test_segment_preview(self, segments):
        """Test GET /api/crm/segments/{id}/preview"""
        self.log("\n=== Testing Segment Preview ===", "info")
        
        for seg in segments:
            seg_id = seg.get("id")
            seg_name = seg.get("name")
            
            try:
                url = f"{self.base_url}/api/crm/segments/{seg_id}/preview"
                response = requests.get(url, headers=self.headers(), timeout=10)
                
                self.test(
                    f"GET /api/crm/segments/{seg_id}/preview returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
                
                if response.status_code == 200:
                    preview = response.json()
                    
                    self.test(
                        f"Preview for '{seg_name}' has count field",
                        "count" in preview,
                        f"Missing count in {preview.keys()}"
                    )
                    
                    self.test(
                        f"Preview for '{seg_name}' has reachable field",
                        "reachable" in preview,
                        f"Missing reachable in {preview.keys()}"
                    )
                    
                    # Check specific segment expectations
                    if seg_name == "Semua Pelanggan":
                        # Should have customers
                        self.test(
                            "'Semua Pelanggan' has members",
                            preview.get("count", 0) > 0,
                            f"Expected > 0, got {preview.get('count')}"
                        )
                    elif seg_name == "Lead Hot":
                        # Should have 3 hot leads
                        self.test(
                            "'Lead Hot' has 3 members",
                            preview.get("count", 0) == 3,
                            f"Expected 3, got {preview.get('count')}"
                        )
                    
                    self.log(f"  '{seg_name}': {preview.get('count')} members, {preview.get('reachable')} reachable", "info")
            except Exception as e:
                self.test(f"Preview segment '{seg_name}'", False, str(e))
    
    def test_campaigns_list(self):
        """Test GET /api/crm/campaigns - should return 1 seeded SENT campaign"""
        self.log("\n=== Testing Campaigns List ===", "info")
        
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
                    "Campaigns list has at least 1 campaign",
                    len(campaigns) >= 1,
                    f"Expected >= 1, got {len(campaigns)}"
                )
                
                # Find the seeded campaign
                promo_campaign = None
                for c in campaigns:
                    if c.get("name") == "Promo Akhir Pekan":
                        promo_campaign = c
                        break
                
                self.test(
                    "Seeded campaign 'Promo Akhir Pekan' exists",
                    promo_campaign is not None,
                    "Campaign not found"
                )
                
                if promo_campaign:
                    self.test(
                        "'Promo Akhir Pekan' status is 'sent'",
                        promo_campaign.get("status") == "sent",
                        f"Expected 'sent', got {promo_campaign.get('status')}"
                    )
                    
                    stats = promo_campaign.get("stats", {})
                    self.test(
                        "'Promo Akhir Pekan' has stats.total = 3",
                        stats.get("total") == 3,
                        f"Expected 3, got {stats.get('total')}"
                    )
                    
                    self.test(
                        "'Promo Akhir Pekan' has stats.sent = 3",
                        stats.get("sent") == 3,
                        f"Expected 3, got {stats.get('sent')}"
                    )
                    
                    self.test(
                        "'Promo Akhir Pekan' has stats.cost = 1050",
                        stats.get("cost") == 1050,
                        f"Expected 1050, got {stats.get('cost')}"
                    )
                    
                    # Store campaign ID for detail test
                    self.campaign_ids.append(promo_campaign.get("id"))
                
                return campaigns
        except Exception as e:
            self.test("GET /api/crm/campaigns", False, str(e))
            return []
    
    def test_campaign_detail(self):
        """Test GET /api/crm/campaigns/{id} - should return campaign with 3 recipients"""
        self.log("\n=== Testing Campaign Detail ===", "info")
        
        if not self.campaign_ids:
            self.log("No campaign IDs to test", "warn")
            return
        
        campaign_id = self.campaign_ids[0]
        
        try:
            url = f"{self.base_url}/api/crm/campaigns/{campaign_id}"
            response = requests.get(url, headers=self.headers(), timeout=10)
            
            self.test(
                f"GET /api/crm/campaigns/{campaign_id} returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                campaign = response.json()
                
                self.test(
                    "Campaign detail has recipients field",
                    "recipients" in campaign,
                    f"Missing recipients in {campaign.keys()}"
                )
                
                recipients = campaign.get("recipients", [])
                self.test(
                    "Campaign has 3 recipients",
                    len(recipients) == 3,
                    f"Expected 3, got {len(recipients)}"
                )
                
                # Check recipient structure
                for i, rec in enumerate(recipients):
                    self.test(
                        f"Recipient {i+1} has required fields",
                        all(k in rec for k in ["id", "name", "phone", "status"]),
                        f"Missing fields in {rec.keys()}"
                    )
                    
                    self.test(
                        f"Recipient {i+1} status is 'sent'",
                        rec.get("status") == "sent",
                        f"Expected 'sent', got {rec.get('status')}"
                    )
        except Exception as e:
            self.test(f"GET campaign detail", False, str(e))
    
    def test_create_campaign(self):
        """Test POST /api/crm/campaigns - create a new campaign"""
        self.log("\n=== Testing Create Campaign ===", "info")
        
        if not self.segment_ids:
            self.log("No segment IDs to test", "warn")
            return None
        
        # Use first segment (Semua Pelanggan)
        segment_id = self.segment_ids[0]
        
        campaign_data = {
            "name": "Test Campaign E2",
            "audience": "customer",
            "segment_id": segment_id,
            "message": "Halo {name}, ini pesan test dari automation.",
            "scheduled_at": None
        }
        
        try:
            url = f"{self.base_url}/api/crm/campaigns"
            response = requests.post(url, json=campaign_data, headers=self.headers(), timeout=10)
            
            self.test(
                "POST /api/crm/campaigns returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                campaign = response.json()
                
                self.test(
                    "Created campaign has ID",
                    "id" in campaign and campaign.get("id"),
                    "Missing ID"
                )
                
                self.test(
                    "Created campaign name matches",
                    campaign.get("name") == "Test Campaign E2",
                    f"Expected 'Test Campaign E2', got {campaign.get('name')}"
                )
                
                self.test(
                    "Created campaign status is 'draft'",
                    campaign.get("status") == "draft",
                    f"Expected 'draft', got {campaign.get('status')}"
                )
                
                return campaign
        except Exception as e:
            self.test("POST /api/crm/campaigns", False, str(e))
            return None
    
    def test_send_campaign(self, campaign):
        """Test POST /api/crm/campaigns/{id}/send"""
        self.log("\n=== Testing Send Campaign ===", "info")
        
        if not campaign:
            self.log("No campaign to send", "warn")
            return
        
        campaign_id = campaign.get("id")
        
        try:
            url = f"{self.base_url}/api/crm/campaigns/{campaign_id}/send"
            response = requests.post(url, headers=self.headers(), timeout=15)
            
            self.test(
                f"POST /api/crm/campaigns/{campaign_id}/send returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                stats = response.json()
                
                self.test(
                    "Send response has 'total' field",
                    "total" in stats,
                    f"Missing total in {stats.keys()}"
                )
                
                self.test(
                    "Send response has 'sent' field",
                    "sent" in stats,
                    f"Missing sent in {stats.keys()}"
                )
                
                self.test(
                    "Send response has 'cost' field",
                    "cost" in stats,
                    f"Missing cost in {stats.keys()}"
                )
                
                self.log(f"  Campaign sent: {stats.get('sent')}/{stats.get('total')} recipients, cost: {stats.get('cost')}", "info")
        except Exception as e:
            self.test(f"POST send campaign", False, str(e))
    
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
                    "Scoreboard has 'leads' field",
                    "leads" in data,
                    f"Missing leads in {data.keys()}"
                )
                
                self.test(
                    "Scoreboard has 'bands' field",
                    "bands" in data,
                    f"Missing bands in {data.keys()}"
                )
                
                bands = data.get("bands", {})
                self.test(
                    "Scoreboard bands has 'hot' count",
                    "hot" in bands,
                    f"Missing hot in {bands.keys()}"
                )
                
                # Should have 3 hot leads from seed
                self.test(
                    "Scoreboard has 3 hot leads",
                    bands.get("hot", 0) == 3,
                    f"Expected 3, got {bands.get('hot')}"
                )
                
                self.log(f"  Bands: hot={bands.get('hot')}, warm={bands.get('warm')}, cold={bands.get('cold')}", "info")
        except Exception as e:
            self.test("GET /api/crm/scoreboard", False, str(e))
    
    def test_rfm(self):
        """Test GET /api/crm/rfm"""
        self.log("\n=== Testing RFM ===", "info")
        
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
                    "RFM has 'customers' field",
                    "customers" in data,
                    f"Missing customers in {data.keys()}"
                )
                
                self.test(
                    "RFM has 'segments' field",
                    "segments" in data,
                    f"Missing segments in {data.keys()}"
                )
                
                customers = data.get("customers", [])
                self.test(
                    "RFM has customers",
                    len(customers) > 0,
                    f"Expected > 0, got {len(customers)}"
                )
                
                # Check customer structure
                if customers:
                    cust = customers[0]
                    self.test(
                        "RFM customer has required fields",
                        all(k in cust for k in ["id", "name", "rfm_segment", "lifecycle", "monetary"]),
                        f"Missing fields in {cust.keys()}"
                    )
                
                self.log(f"  Total customers: {len(customers)}", "info")
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
                    "Recompute response has 'leads_scored' field",
                    "leads_scored" in data,
                    f"Missing leads_scored in {data.keys()}"
                )
                
                self.log(f"  Leads scored: {data.get('leads_scored')}", "info")
        except Exception as e:
            self.test("POST /api/crm/recompute", False, str(e))
    
    def test_sequences_list(self):
        """Test GET /api/crm/sequences"""
        self.log("\n=== Testing Sequences List ===", "info")
        
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
                    "Sequences list has at least 1 sequence",
                    len(sequences) >= 1,
                    f"Expected >= 1, got {len(sequences)}"
                )
                
                # Check for seeded sequence
                nurturing_seq = None
                for seq in sequences:
                    if seq.get("name") == "Nurturing Lead Baru":
                        nurturing_seq = seq
                        break
                
                self.test(
                    "Seeded sequence 'Nurturing Lead Baru' exists",
                    nurturing_seq is not None,
                    "Sequence not found"
                )
                
                if nurturing_seq:
                    self.test(
                        "'Nurturing Lead Baru' has steps",
                        len(nurturing_seq.get("steps", [])) > 0,
                        f"Expected > 0 steps, got {len(nurturing_seq.get('steps', []))}"
                    )
        except Exception as e:
            self.test("GET /api/crm/sequences", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*60, "info")
        self.log("E2 CRM Growth Engine Backend Test Suite (Iteration 33)", "info")
        self.log("="*60, "info")
        
        # Login
        if not self.login():
            self.log("\n⚠️  Authentication failed. Cannot proceed.", "warn")
            return False
        
        # Run tests in order
        segments = self.test_segments_list()
        self.test_segment_preview(segments)
        
        campaigns = self.test_campaigns_list()
        self.test_campaign_detail()
        
        new_campaign = self.test_create_campaign()
        self.test_send_campaign(new_campaign)
        
        self.test_scoreboard()
        self.test_rfm()
        self.test_recompute()
        self.test_sequences_list()
        
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
    tester = E2CRMTestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
