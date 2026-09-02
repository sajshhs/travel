#!/usr/bin/env python3
"""
Backend Test Suite for Phase E1 - Event Bus + Automation Engine + WhatsApp Adapter
===================================================================================
Tests automation rules, event processing, WhatsApp mock integration, and RBAC.
"""
import requests
import sys
import json
import time
from datetime import datetime

class E1TestSuite:
    def __init__(self, base_url="https://trip-route-buttons.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        
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
    
    def headers(self, email):
        """Get auth headers for user"""
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
        
        return owner_ok and ops_ok
    
    def test_automation_rules_crud(self):
        """Test automation rules CRUD endpoints"""
        self.log("\n=== Testing Automation Rules CRUD ===", "info")
        
        # GET /api/automation/rules (should have 8 seeded rules)
        try:
            url = f"{self.base_url}/api/automation/rules"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/automation/rules returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                rules = response.json()
                self.test(
                    "8 default rules seeded",
                    len(rules) >= 8,
                    f"Expected 8+, got {len(rules)}"
                )
                
                # Check all rules are enabled
                enabled_count = sum(1 for r in rules if r.get("enabled"))
                self.test(
                    "All default rules are enabled",
                    enabled_count >= 8,
                    f"Expected 8+ enabled, got {enabled_count}"
                )
                
                # Store first rule ID for later tests
                if rules:
                    self.rule_id = rules[0].get("id")
        except Exception as e:
            self.test("GET /api/automation/rules", False, str(e))
        
        # POST /api/automation/rules (create new rule)
        try:
            url = f"{self.base_url}/api/automation/rules"
            new_rule = {
                "name": "Test Rule E1",
                "description": "Test automation rule",
                "event_type": "lead.created",
                "enabled": True,
                "conditions": [{"field": "source", "op": "eq", "value": "whatsapp"}],
                "actions": [{"type": "create_notification", "params": {"title": "Test notification"}}]
            }
            response = requests.post(url, json=new_rule, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/automation/rules returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                created = response.json()
                self.test(
                    "Created rule has aur_ prefix",
                    created.get("id", "").startswith("aur_"),
                    f"Got ID: {created.get('id')}"
                )
                self.created_rule_id = created.get("id")
        except Exception as e:
            self.test("POST /api/automation/rules", False, str(e))
        
        # GET /api/automation/rules/{id}
        if hasattr(self, 'rule_id'):
            try:
                url = f"{self.base_url}/api/automation/rules/{self.rule_id}"
                response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "GET /api/automation/rules/{id} returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
            except Exception as e:
                self.test("GET /api/automation/rules/{id}", False, str(e))
        
        # PATCH /api/automation/rules/{id} (toggle enabled)
        if hasattr(self, 'created_rule_id'):
            try:
                url = f"{self.base_url}/api/automation/rules/{self.created_rule_id}"
                response = requests.patch(url, json={"enabled": False}, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "PATCH /api/automation/rules/{id} returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
                
                if response.status_code == 200:
                    updated = response.json()
                    self.test(
                        "Rule enabled toggled to False",
                        updated.get("enabled") == False,
                        f"Expected False, got {updated.get('enabled')}"
                    )
            except Exception as e:
                self.test("PATCH /api/automation/rules/{id}", False, str(e))
        
        # DELETE /api/automation/rules/{id}
        if hasattr(self, 'created_rule_id'):
            try:
                url = f"{self.base_url}/api/automation/rules/{self.created_rule_id}"
                response = requests.delete(url, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "DELETE /api/automation/rules/{id} returns 200",
                    response.status_code == 200,
                    f"Got {response.status_code}"
                )
            except Exception as e:
                self.test("DELETE /api/automation/rules/{id}", False, str(e))
    
    def test_automation_metadata(self):
        """Test automation metadata endpoints"""
        self.log("\n=== Testing Automation Metadata ===", "info")
        
        # GET /api/automation/event-types
        try:
            url = f"{self.base_url}/api/automation/event-types"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/automation/event-types returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test(
                    "Event types list contains events",
                    len(data.get("events", [])) > 0,
                    f"Got {len(data.get('events', []))} events"
                )
                self.test(
                    "Action types list contains actions",
                    len(data.get("actions", [])) > 0,
                    f"Got {len(data.get('actions', []))} actions"
                )
        except Exception as e:
            self.test("GET /api/automation/event-types", False, str(e))
        
        # GET /api/automation/stats
        try:
            url = f"{self.base_url}/api/automation/stats"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/automation/stats returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                stats = response.json()
                self.test(
                    "Stats contains rules_active",
                    "rules_active" in stats,
                    "rules_active missing"
                )
                self.test(
                    "Stats contains runs_total",
                    "runs_total" in stats,
                    "runs_total missing"
                )
        except Exception as e:
            self.test("GET /api/automation/stats", False, str(e))
    
    def test_event_bus_end_to_end(self):
        """Test Event Bus + Engine end-to-end: lead.created → automation run"""
        self.log("\n=== Testing Event Bus End-to-End ===", "info")
        
        # Create a new lead (should emit lead.created event)
        try:
            url = f"{self.base_url}/api/leads"
            lead_data = {
                "customer_name": f"Test Lead E1 {int(time.time())}",
                "phone": f"+6281234{int(time.time()) % 100000}",
                "email": "test@example.com",
                "source": "whatsapp",
                "destination": "Bali",
                "message": "Test lead for E1 automation"
            }
            response = requests.post(url, json=lead_data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/leads returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                lead = response.json()
                self.lead_id = lead.get("id")
                
                # Wait a moment for event processing
                time.sleep(2)
                
                # Check automation runs
                runs_url = f"{self.base_url}/api/automation/runs"
                runs_response = requests.get(runs_url, headers=self.headers("owner@demo.local"), timeout=10)
                
                if runs_response.status_code == 200:
                    runs = runs_response.json()
                    
                    # Find runs for lead.created event
                    lead_created_runs = [r for r in runs if r.get("event_type") == "lead.created"]
                    self.test(
                        "lead.created event triggered automation runs",
                        len(lead_created_runs) > 0,
                        f"Expected runs, got {len(lead_created_runs)}"
                    )
                    
                    # Check for 'Auto-ack lead baru' rule execution
                    auto_ack_run = next((r for r in lead_created_runs if "Auto-ack" in r.get("rule_name", "")), None)
                    if auto_ack_run:
                        self.test(
                            "'Auto-ack lead baru' rule executed",
                            auto_ack_run.get("status") in ["success", "skipped"],
                            f"Got status: {auto_ack_run.get('status')}"
                        )
                        
                        # Check actions executed
                        actions = auto_ack_run.get("actions", [])
                        self.test(
                            "Auto-ack rule has actions",
                            len(actions) > 0,
                            f"Expected actions, got {len(actions)}"
                        )
                        
                        # Check for send_wa action
                        wa_action = next((a for a in actions if a.get("type") == "send_wa"), None)
                        if wa_action:
                            self.test(
                                "send_wa action executed",
                                wa_action.get("status") in ["success", "sent", "skipped"],
                                f"Got status: {wa_action.get('status')}"
                            )
                
                # Check events collection
                events_url = f"{self.base_url}/api/automation/events"
                events_response = requests.get(events_url, headers=self.headers("owner@demo.local"), timeout=10)
                
                if events_response.status_code == 200:
                    events = events_response.json()
                    lead_created_events = [e for e in events if e.get("type") == "lead.created"]
                    self.test(
                        "lead.created event recorded in events collection",
                        len(lead_created_events) > 0,
                        f"Expected events, got {len(lead_created_events)}"
                    )
        except Exception as e:
            self.test("Event Bus end-to-end test", False, str(e))
    
    def test_other_event_triggers(self):
        """Test other event triggers (quotation.sent, booking.confirmed, payment.recorded)"""
        self.log("\n=== Testing Other Event Triggers ===", "info")
        
        # Note: These tests depend on having quotations, bookings, and payments
        # We'll test the endpoints exist and return proper responses
        
        # Check if we can query runs by event type
        try:
            url = f"{self.base_url}/api/automation/runs?event_type=quotation.sent"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/automation/runs?event_type=quotation.sent returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
        except Exception as e:
            self.test("Query runs by event_type", False, str(e))
        
        # Check events can be filtered
        try:
            url = f"{self.base_url}/api/automation/events?event_type=booking.confirmed"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/automation/events?event_type=booking.confirmed returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
        except Exception as e:
            self.test("Query events by type", False, str(e))
    
    def test_idempotency(self):
        """Test idempotency: same event should not create duplicate runs"""
        self.log("\n=== Testing Idempotency ===", "info")
        
        # Get current run count
        try:
            url = f"{self.base_url}/api/automation/runs"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                initial_runs = response.json()
                initial_count = len(initial_runs)
                
                # Create a lead (triggers event)
                lead_url = f"{self.base_url}/api/leads"
                lead_data = {
                    "customer_name": f"Idempotency Test {int(time.time())}",
                    "phone": f"+6281999{int(time.time()) % 100000}",
                    "source": "website",
                    "destination": "Jakarta"
                }
                lead_response = requests.post(lead_url, json=lead_data, headers=self.headers("owner@demo.local"), timeout=10)
                
                if lead_response.status_code == 200:
                    time.sleep(2)
                    
                    # Get runs again
                    runs_response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
                    if runs_response.status_code == 200:
                        new_runs = runs_response.json()
                        new_count = len(new_runs)
                        
                        # Should have new runs, but not duplicates
                        self.test(
                            "New runs created after lead creation",
                            new_count > initial_count,
                            f"Initial: {initial_count}, New: {new_count}"
                        )
                        
                        # Check no duplicate dedupe_keys
                        dedupe_keys = [r.get("dedupe_key") for r in new_runs if r.get("dedupe_key")]
                        unique_keys = set(dedupe_keys)
                        self.test(
                            "No duplicate dedupe_keys in runs",
                            len(dedupe_keys) == len(unique_keys),
                            f"Total: {len(dedupe_keys)}, Unique: {len(unique_keys)}"
                        )
        except Exception as e:
            self.test("Idempotency test", False, str(e))
    
    def test_wa_config_templates(self):
        """Test WhatsApp config & templates (owner-only)"""
        self.log("\n=== Testing WhatsApp Config & Templates ===", "info")
        
        # GET /api/wa/config (owner)
        try:
            url = f"{self.base_url}/api/wa/config"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/wa/config as owner returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                config = response.json()
                self.test(
                    "WA config has provider field",
                    "provider" in config,
                    "provider missing"
                )
                self.test(
                    "WA config masks access_token",
                    "access_token_set" in config.get("meta", {}),
                    "access_token_set missing"
                )
        except Exception as e:
            self.test("GET /api/wa/config", False, str(e))
        
        # PATCH /api/wa/config (owner)
        try:
            url = f"{self.base_url}/api/wa/config"
            update_data = {
                "price_per_message": 400,
                "auto_reply_enabled": True
            }
            response = requests.patch(url, json=update_data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "PATCH /api/wa/config as owner returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
        except Exception as e:
            self.test("PATCH /api/wa/config", False, str(e))
        
        # GET /api/wa/templates
        try:
            url = f"{self.base_url}/api/wa/templates"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/wa/templates returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                templates = response.json()
                self.test(
                    "WA templates list is not empty",
                    len(templates) > 0,
                    f"Got {len(templates)} templates"
                )
        except Exception as e:
            self.test("GET /api/wa/templates", False, str(e))
        
        # PUT /api/wa/templates/{key} (upsert)
        try:
            url = f"{self.base_url}/api/wa/templates/test_template"
            template_data = {
                "name": "Test Template",
                "language": "id",
                "category": "utility",
                "body": "Test template body {customer_name}"
            }
            response = requests.put(url, json=template_data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "PUT /api/wa/templates/{key} returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
        except Exception as e:
            self.test("PUT /api/wa/templates/{key}", False, str(e))
        
        # DELETE /api/wa/templates/{key}
        try:
            url = f"{self.base_url}/api/wa/templates/test_template"
            response = requests.delete(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "DELETE /api/wa/templates/{key} returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
        except Exception as e:
            self.test("DELETE /api/wa/templates/{key}", False, str(e))
    
    def test_wa_simulate_inbound(self):
        """Test WA simulate-inbound endpoint"""
        self.log("\n=== Testing WA Simulate Inbound ===", "info")
        
        try:
            url = f"{self.base_url}/api/wa/simulate-inbound"
            simulate_data = {
                "from_phone": f"+6281888{int(time.time()) % 100000}",
                "text": "Halo, saya mau sewa mobil ke Bali",
                "name": "Test Customer E1"
            }
            response = requests.post(url, json=simulate_data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/wa/simulate-inbound returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                result = response.json()
                self.test(
                    "Simulate inbound returns status received",
                    result.get("status") == "received",
                    f"Got status: {result.get('status')}"
                )
                self.test(
                    "Simulate inbound creates conversation",
                    "conversation_id" in result,
                    "conversation_id missing"
                )
                
                # Wait for event processing
                time.sleep(2)
                
                # Check if wa.inbound event was created
                events_url = f"{self.base_url}/api/automation/events?event_type=wa.inbound"
                events_response = requests.get(events_url, headers=self.headers("owner@demo.local"), timeout=10)
                
                if events_response.status_code == 200:
                    events = events_response.json()
                    self.test(
                        "wa.inbound event created",
                        len(events) > 0,
                        f"Expected events, got {len(events)}"
                    )
                
                # Check if automation run was created for 'Routing WA masuk'
                runs_url = f"{self.base_url}/api/automation/runs?event_type=wa.inbound"
                runs_response = requests.get(runs_url, headers=self.headers("owner@demo.local"), timeout=10)
                
                if runs_response.status_code == 200:
                    runs = runs_response.json()
                    routing_run = next((r for r in runs if "Routing" in r.get("rule_name", "")), None)
                    self.test(
                        "'Routing WA masuk' rule executed",
                        routing_run is not None,
                        "Routing rule not found in runs"
                    )
        except Exception as e:
            self.test("POST /api/wa/simulate-inbound", False, str(e))
    
    def test_wa_webhook(self):
        """Test WA webhook endpoints"""
        self.log("\n=== Testing WA Webhook ===", "info")
        
        # GET /api/wa/webhook without token (should return 403)
        try:
            url = f"{self.base_url}/api/wa/webhook"
            response = requests.get(url, timeout=10)
            
            self.test(
                "GET /api/wa/webhook without token returns 403",
                response.status_code == 403,
                f"Got {response.status_code}"
            )
        except Exception as e:
            self.test("GET /api/wa/webhook without token", False, str(e))
        
        # GET /api/wa/webhook with correct verification (should return challenge)
        try:
            url = f"{self.base_url}/api/wa/webhook"
            params = {
                "hub.mode": "subscribe",
                "hub.verify_token": "rahaza-wa-verify",
                "hub.challenge": "test_challenge_123"
            }
            response = requests.get(url, params=params, timeout=10)
            
            self.test(
                "GET /api/wa/webhook with correct token returns challenge",
                response.status_code == 200 and response.text == "test_challenge_123",
                f"Got {response.status_code}, body: {response.text[:50]}"
            )
        except Exception as e:
            self.test("GET /api/wa/webhook verification", False, str(e))
        
        # POST /api/wa/webhook (inbound message)
        try:
            url = f"{self.base_url}/api/wa/webhook"
            webhook_data = {
                "from": f"+6281777{int(time.time()) % 100000}",
                "text": "Test webhook message",
                "name": "Webhook Test"
            }
            response = requests.post(url, json=webhook_data, timeout=10)
            
            self.test(
                "POST /api/wa/webhook returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                result = response.json()
                self.test(
                    "Webhook returns status ok",
                    result.get("status") == "ok",
                    f"Got status: {result.get('status')}"
                )
        except Exception as e:
            self.test("POST /api/wa/webhook", False, str(e))
    
    def test_inbox_wa_messaging(self):
        """Test Inbox WA messaging with opt-in/out"""
        self.log("\n=== Testing Inbox WA Messaging ===", "info")
        
        # First, create a conversation via simulate-inbound
        try:
            simulate_url = f"{self.base_url}/api/wa/simulate-inbound"
            simulate_data = {
                "from_phone": f"+6281666{int(time.time()) % 100000}",
                "text": "Test inbox messaging",
                "name": "Inbox Test Customer"
            }
            simulate_response = requests.post(simulate_url, json=simulate_data, headers=self.headers("owner@demo.local"), timeout=10)
            
            if simulate_response.status_code == 200:
                result = simulate_response.json()
                conversation_id = result.get("conversation_id")
                
                if conversation_id:
                    # Send a message to the conversation
                    msg_url = f"{self.base_url}/api/conversations/{conversation_id}/messages"
                    msg_data = {
                        "body": "Test reply from agent",
                        "internal": False
                    }
                    msg_response = requests.post(msg_url, json=msg_data, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    self.test(
                        "POST /api/conversations/{id}/messages returns 200",
                        msg_response.status_code == 200,
                        f"Got {msg_response.status_code}"
                    )
                    
                    if msg_response.status_code == 200:
                        message = msg_response.json()
                        self.test(
                            "Message has WA fields (status, cost)",
                            "status" in message and "cost" in message,
                            "WA fields missing"
                        )
                    
                    # Test opt-out
                    optout_url = f"{self.base_url}/api/conversations/{conversation_id}/wa-optout"
                    optout_response = requests.post(optout_url, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    self.test(
                        "POST /api/conversations/{id}/wa-optout returns 200",
                        optout_response.status_code == 200,
                        f"Got {optout_response.status_code}"
                    )
                    
                    # Try to send message after opt-out (should be rejected)
                    msg_after_optout = requests.post(msg_url, json=msg_data, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    self.test(
                        "Message after opt-out is rejected (400)",
                        msg_after_optout.status_code == 400,
                        f"Expected 400, got {msg_after_optout.status_code}"
                    )
                    
                    # Test opt-in
                    optin_url = f"{self.base_url}/api/conversations/{conversation_id}/wa-optin"
                    optin_response = requests.post(optin_url, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    self.test(
                        "POST /api/conversations/{id}/wa-optin returns 200",
                        optin_response.status_code == 200,
                        f"Got {optin_response.status_code}"
                    )
                    
                    # Try to send message after opt-in (should succeed)
                    msg_after_optin = requests.post(msg_url, json=msg_data, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    self.test(
                        "Message after opt-in succeeds (200)",
                        msg_after_optin.status_code == 200,
                        f"Got {msg_after_optin.status_code}"
                    )
        except Exception as e:
            self.test("Inbox WA messaging test", False, str(e))
    
    def test_rbac(self):
        """Test RBAC: driver should be denied access to automation endpoints"""
        self.log("\n=== Testing RBAC ===", "info")
        
        # Driver should get 403 on automation endpoints
        driver_tests = [
            ("GET", f"{self.base_url}/api/automation/rules"),
            ("POST", f"{self.base_url}/api/automation/rules"),
            ("GET", f"{self.base_url}/api/automation/runs"),
            ("GET", f"{self.base_url}/api/automation/events"),
            ("GET", f"{self.base_url}/api/wa/config"),
            ("PATCH", f"{self.base_url}/api/wa/config"),
        ]
        
        for method, url in driver_tests:
            try:
                if method == "GET":
                    response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
                elif method == "POST":
                    response = requests.post(url, json={"test": "data"}, headers=self.headers("driver@demo.local"), timeout=10)
                elif method == "PATCH":
                    response = requests.patch(url, json={"test": "data"}, headers=self.headers("driver@demo.local"), timeout=10)
                
                self.test(
                    f"Driver {method} {url.split('/api/')[-1]} returns 403",
                    response.status_code == 403,
                    f"Expected 403, got {response.status_code}"
                )
            except Exception as e:
                self.test(f"Driver {method} RBAC test", False, str(e))
        
        # Ops admin should have access to automation endpoints
        try:
            url = f"{self.base_url}/api/automation/rules"
            response = requests.get(url, headers=self.headers("ops@demo.local"), timeout=10)
            
            self.test(
                "Ops admin GET /api/automation/rules returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
        except Exception as e:
            self.test("Ops admin automation access", False, str(e))
        
        # Ops admin should NOT have access to wa/config (owner-only)
        try:
            url = f"{self.base_url}/api/wa/config"
            response = requests.get(url, headers=self.headers("ops@demo.local"), timeout=10)
            
            self.test(
                "Ops admin GET /api/wa/config returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("Ops admin wa/config access", False, str(e))
    
    def test_reset_defaults(self):
        """Test POST /api/automation/rules/reset-defaults (owner-only)"""
        self.log("\n=== Testing Reset Defaults ===", "info")
        
        try:
            url = f"{self.base_url}/api/automation/rules/reset-defaults"
            response = requests.post(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "POST /api/automation/rules/reset-defaults returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                result = response.json()
                self.test(
                    "Reset defaults installs 8 rules",
                    result.get("installed") == 8,
                    f"Expected 8, got {result.get('installed')}"
                )
        except Exception as e:
            self.test("POST /api/automation/rules/reset-defaults", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*70, "info")
        self.log("Phase E1 - Event Bus + Automation Engine + WhatsApp Adapter", "info")
        self.log("Backend Test Suite", "info")
        self.log("="*70, "info")
        
        # Run tests in order
        if not self.test_auth():
            self.log("\n⚠️  Authentication failed. Cannot proceed with other tests.", "warn")
            return False
        
        # Core automation tests
        self.test_automation_rules_crud()
        self.test_automation_metadata()
        self.test_event_bus_end_to_end()
        self.test_other_event_triggers()
        self.test_idempotency()
        
        # WhatsApp tests
        self.test_wa_config_templates()
        self.test_wa_simulate_inbound()
        self.test_wa_webhook()
        self.test_inbox_wa_messaging()
        
        # RBAC tests
        self.test_rbac()
        
        # Reset defaults
        self.test_reset_defaults()
        
        # Print summary
        self.log("\n" + "="*70, "info")
        self.log("TEST SUMMARY", "info")
        self.log("="*70, "info")
        self.log(f"Total Tests: {self.tests_run}", "info")
        self.log(f"Passed: {self.tests_passed}", "pass")
        self.log(f"Failed: {self.tests_failed}", "fail" if self.tests_failed > 0 else "info")
        
        if self.tests_failed > 0:
            self.log("\nFailed Tests:", "fail")
            for failure in self.failures:
                self.log(f"  - {failure}", "fail")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"\nSuccess Rate: {success_rate:.1f}%", "pass" if success_rate >= 95 else "warn")
        
        return self.tests_failed == 0


def main():
    tester = E1TestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
