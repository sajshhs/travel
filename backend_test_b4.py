#!/usr/bin/env python3
"""
Backend Test Suite for Phase 9 / B4 Identity & Dedupe
======================================================
Tests phone normalization, dedupe on customer creation, auto-link Lead→Customer,
lead/quotation convert dedupe, Contact 360 view, and RBAC.
"""
import requests
import sys
import json
from datetime import datetime, timedelta

class B4TestSuite:
    def __init__(self, base_url="https://trip-route-buttons.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.created_ids = {}
        
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
        
        return owner_ok and ops_ok and driver_ok
    
    def test_phone_normalization(self):
        """Test phone normalization to +62 format"""
        self.log("\n=== Testing Phone Normalization ===", "info")
        
        test_cases = [
            ("081298765432", "+6281298765432", "08xx format"),
            ("0813222333", "+62813222333", "08xx short format"),
            ("+62 813 222 333", "+62813222333", "+62 with spaces"),
            ("628123456789", "+628123456789", "62xx format"),
            ("8123456789", "+628123456789", "8xx format (no leading 0)"),
        ]
        
        for input_phone, expected_normalized, description in test_cases:
            try:
                # Create customer with this phone
                url = f"{self.base_url}/api/customers"
                data = {
                    "name": f"Test Customer {input_phone}",
                    "phone": input_phone,
                    "email": f"test_{input_phone.replace('+', '').replace(' ', '')}@test.com",
                    "type": "individual"
                }
                response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
                
                if response.status_code == 200:
                    customer = response.json()
                    normalized = customer.get("phone_normalized")
                    
                    self.test(
                        f"Phone normalization: {description}",
                        normalized == expected_normalized,
                        f"Input: {input_phone}, Expected: {expected_normalized}, Got: {normalized}"
                    )
                    
                    # Store for cleanup
                    if customer.get("id"):
                        self.created_ids.setdefault("customers", []).append(customer["id"])
                else:
                    self.test(
                        f"Phone normalization: {description}",
                        False,
                        f"Failed to create customer: {response.status_code}"
                    )
            except Exception as e:
                self.test(f"Phone normalization: {description}", False, str(e))
    
    def test_dedupe_customer_creation(self):
        """Test dedupe on customer creation (409 conflict)"""
        self.log("\n=== Testing Dedupe on Customer Creation ===", "info")
        
        # Seed has "Keluarga Andi" with phone "0813222333" → normalized "+62813222333"
        
        # Test 1: Try to create with same normalized phone (different format)
        try:
            url = f"{self.base_url}/api/customers"
            data = {
                "name": "Duplicate Customer",
                "phone": "+62813222333",  # Same as Keluarga Andi's normalized phone
                "email": "duplicate@test.com",
                "type": "individual"
            }
            response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "Dedupe: Creating customer with existing phone returns 409",
                response.status_code == 409,
                f"Expected 409, got {response.status_code}"
            )
            
            if response.status_code == 409:
                detail = response.json().get("detail", "")
                self.test(
                    "Dedupe: 409 response mentions existing customer name",
                    "Keluarga Andi" in detail,
                    f"Expected 'Keluarga Andi' in detail, got: {detail}"
                )
        except Exception as e:
            self.test("Dedupe: 409 on duplicate phone", False, str(e))
        
        # Test 2: Try with variant format (0813-222-333)
        try:
            url = f"{self.base_url}/api/customers"
            data = {
                "name": "Another Duplicate",
                "phone": "0813-222-333",  # Same phone with dashes
                "email": "another@test.com",
                "type": "individual"
            }
            response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "Dedupe: Creating customer with phone variant (dashes) returns 409",
                response.status_code == 409,
                f"Expected 409, got {response.status_code}"
            )
        except Exception as e:
            self.test("Dedupe: 409 on phone variant", False, str(e))
        
        # Test 3: Create with unique phone should succeed
        try:
            url = f"{self.base_url}/api/customers"
            unique_phone = "081999888777"
            data = {
                "name": "Unique Customer",
                "phone": unique_phone,
                "email": "unique@test.com",
                "type": "individual"
            }
            response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "Dedupe: Creating customer with unique phone returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
            
            if response.status_code == 200:
                customer = response.json()
                self.test(
                    "Dedupe: Unique customer has phone_normalized set",
                    customer.get("phone_normalized") == "+6281999888777",
                    f"Expected +6281999888777, got {customer.get('phone_normalized')}"
                )
                
                if customer.get("id"):
                    self.created_ids.setdefault("customers", []).append(customer["id"])
        except Exception as e:
            self.test("Dedupe: Create unique customer", False, str(e))
        
        # Test 4: Dedupe by email when phone empty
        try:
            # First create customer with email only
            url = f"{self.base_url}/api/customers"
            data = {
                "name": "Email Only Customer",
                "phone": "",
                "email": "emailonly@test.com",
                "type": "individual"
            }
            response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                # Try to create another with same email
                data2 = {
                    "name": "Duplicate Email Customer",
                    "phone": "",
                    "email": "emailonly@test.com",
                    "type": "individual"
                }
                response2 = requests.post(url, json=data2, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "Dedupe: Creating customer with existing email returns 409",
                    response2.status_code == 409,
                    f"Expected 409, got {response2.status_code}"
                )
                
                if response.json().get("id"):
                    self.created_ids.setdefault("customers", []).append(response.json()["id"])
        except Exception as e:
            self.test("Dedupe: Email dedupe", False, str(e))
    
    def test_auto_link_lead_to_customer(self):
        """Test auto-link Lead→Customer"""
        self.log("\n=== Testing Auto-link Lead→Customer ===", "info")
        
        # Test 1: Create lead with phone matching existing customer (Keluarga Andi: 0813222333)
        try:
            url = f"{self.base_url}/api/leads"
            data = {
                "customer_name": "Test Lead Matching",
                "phone": "0813222333",  # Matches Keluarga Andi
                "email": "testlead@test.com",
                "source": "manual",
                "destination": "Bali",
                "pax": 5
            }
            response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "Auto-link: Creating lead with matching phone returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
            
            if response.status_code == 200:
                lead = response.json()
                
                self.test(
                    "Auto-link: Lead has phone_normalized set",
                    lead.get("phone_normalized") == "+62813222333",
                    f"Expected +62813222333, got {lead.get('phone_normalized')}"
                )
                
                self.test(
                    "Auto-link: Lead has linked_customer_id set",
                    lead.get("linked_customer_id") is not None,
                    f"linked_customer_id is None"
                )
                
                if lead.get("id"):
                    self.created_ids.setdefault("leads", []).append(lead["id"])
        except Exception as e:
            self.test("Auto-link: Lead with matching phone", False, str(e))
        
        # Test 2: Create lead with non-matching phone
        try:
            url = f"{self.base_url}/api/leads"
            data = {
                "customer_name": "Test Lead Non-Matching",
                "phone": "081777666555",  # Unique phone
                "email": "nonmatch@test.com",
                "source": "manual",
                "destination": "Yogyakarta",
                "pax": 3
            }
            response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                lead = response.json()
                
                self.test(
                    "Auto-link: Lead with non-matching phone has linked_customer_id null",
                    lead.get("linked_customer_id") is None,
                    f"Expected None, got {lead.get('linked_customer_id')}"
                )
                
                self.test(
                    "Auto-link: Lead with non-matching phone has phone_normalized set",
                    lead.get("phone_normalized") == "+6281777666555",
                    f"Expected +6281777666555, got {lead.get('phone_normalized')}"
                )
                
                if lead.get("id"):
                    self.created_ids.setdefault("leads", []).append(lead["id"])
        except Exception as e:
            self.test("Auto-link: Lead with non-matching phone", False, str(e))
    
    def test_lead_convert_dedupe(self):
        """Test lead convert dedupe"""
        self.log("\n=== Testing Lead Convert Dedupe ===", "info")
        
        # Test 1: Convert lead with phone matching existing customer
        try:
            # First create a lead with matching phone
            url = f"{self.base_url}/api/leads"
            data = {
                "customer_name": "Lead to Convert Matching",
                "phone": "0813222333",  # Matches Keluarga Andi
                "email": "convert@test.com",
                "source": "manual",
                "destination": "Bromo",
                "pax": 4
            }
            response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                lead = response.json()
                lead_id = lead.get("id")
                
                # Convert the lead
                convert_url = f"{self.base_url}/api/leads/{lead_id}/convert"
                convert_response = requests.post(convert_url, json={}, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "Lead convert: Converting lead with matching phone returns 200",
                    convert_response.status_code == 200,
                    f"Expected 200, got {convert_response.status_code}"
                )
                
                if convert_response.status_code == 200:
                    result = convert_response.json()
                    
                    self.test(
                        "Lead convert: Returns existing customer (created: false)",
                        result.get("created") == False,
                        f"Expected created=False, got {result.get('created')}"
                    )
                    
                    self.test(
                        "Lead convert: Customer object returned",
                        result.get("customer") is not None,
                        f"Customer object missing"
                    )
                    
                    # Verify lead updated
                    lead_check_url = f"{self.base_url}/api/leads/{lead_id}"
                    lead_check = requests.get(lead_check_url, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    if lead_check.status_code == 200:
                        updated_lead = lead_check.json()
                        
                        self.test(
                            "Lead convert: Lead stage set to 'won'",
                            updated_lead.get("stage") == "won",
                            f"Expected 'won', got {updated_lead.get('stage')}"
                        )
                        
                        self.test(
                            "Lead convert: Lead has converted_customer_id set",
                            updated_lead.get("converted_customer_id") is not None,
                            f"converted_customer_id is None"
                        )
                        
                        self.test(
                            "Lead convert: Lead has linked_customer_id set",
                            updated_lead.get("linked_customer_id") is not None,
                            f"linked_customer_id is None"
                        )
                
                if lead_id:
                    self.created_ids.setdefault("leads", []).append(lead_id)
        except Exception as e:
            self.test("Lead convert: Matching phone dedupe", False, str(e))
        
        # Test 2: Convert lead with unique phone (creates new customer)
        try:
            # Create lead with unique phone
            url = f"{self.base_url}/api/leads"
            data = {
                "customer_name": "Lead to Convert Unique",
                "phone": "081555444333",  # Unique phone
                "email": "convertunique@test.com",
                "source": "manual",
                "destination": "Dieng",
                "pax": 6
            }
            response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                lead = response.json()
                lead_id = lead.get("id")
                
                # Convert the lead
                convert_url = f"{self.base_url}/api/leads/{lead_id}/convert"
                convert_response = requests.post(convert_url, json={}, headers=self.headers("owner@demo.local"), timeout=10)
                
                if convert_response.status_code == 200:
                    result = convert_response.json()
                    
                    self.test(
                        "Lead convert: Converting lead with unique phone creates new customer (created: true)",
                        result.get("created") == True,
                        f"Expected created=True, got {result.get('created')}"
                    )
                    
                    customer = result.get("customer")
                    if customer:
                        self.test(
                            "Lead convert: New customer has phone_normalized set",
                            customer.get("phone_normalized") == "+6281555444333",
                            f"Expected +6281555444333, got {customer.get('phone_normalized')}"
                        )
                        
                        if customer.get("id"):
                            self.created_ids.setdefault("customers", []).append(customer["id"])
                
                if lead_id:
                    self.created_ids.setdefault("leads", []).append(lead_id)
        except Exception as e:
            self.test("Lead convert: Unique phone creates customer", False, str(e))
    
    def test_quotation_convert_dedupe(self):
        """Test quotation convert dedupe"""
        self.log("\n=== Testing Quotation Convert Dedupe ===", "info")
        
        # This test requires creating a quotation, sending it, accepting it, then converting
        # We'll use the B2 flow: create → send → accept → convert
        
        try:
            # Step 1: Create quotation with phone matching existing customer
            url = f"{self.base_url}/api/quotations"
            data = {
                "customer_name": "Quotation Test Customer",
                "phone": "0813222333",  # Matches Keluarga Andi
                "email": "quotest@test.com",
                "destination": "Bali",
                "trip_date": (datetime.now() + timedelta(days=10)).isoformat(),
                "pax": 8,
                "vehicle_type": "hiace_premio",
                "days": 3,
                "distance_km": 500,
                "notes": "Test quotation"
            }
            response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                quotation = response.json()
                quo_id = quotation.get("id")
                
                self.test(
                    "Quotation convert: Quotation created with phone_normalized",
                    quotation.get("phone_normalized") == "+62813222333",
                    f"Expected +62813222333, got {quotation.get('phone_normalized')}"
                )
                
                # Step 2: Send quotation
                send_url = f"{self.base_url}/api/quotations/{quo_id}/send"
                send_response = requests.post(send_url, json={}, headers=self.headers("owner@demo.local"), timeout=10)
                
                if send_response.status_code == 200:
                    # Step 3: Accept quotation
                    accept_url = f"{self.base_url}/api/quotations/{quo_id}/accept"
                    accept_response = requests.post(accept_url, json={}, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    if accept_response.status_code == 200:
                        # Step 4: Get a vehicle and convert
                        vehicles_url = f"{self.base_url}/api/vehicles"
                        vehicles_response = requests.get(vehicles_url, headers=self.headers("owner@demo.local"), timeout=10)
                        
                        if vehicles_response.status_code == 200:
                            vehicles = vehicles_response.json()
                            if len(vehicles) > 0:
                                vehicle_id = vehicles[0].get("id")
                                
                                # Convert quotation
                                convert_url = f"{self.base_url}/api/quotations/{quo_id}/convert"
                                convert_data = {
                                    "vehicle_id": vehicle_id,
                                    "start_datetime": (datetime.now() + timedelta(days=10)).isoformat(),
                                    "end_datetime": (datetime.now() + timedelta(days=13)).isoformat()
                                }
                                convert_response = requests.post(convert_url, json=convert_data, headers=self.headers("owner@demo.local"), timeout=10)
                                
                                self.test(
                                    "Quotation convert: Converting quotation with matching phone returns 200",
                                    convert_response.status_code == 200,
                                    f"Expected 200, got {convert_response.status_code}"
                                )
                                
                                if convert_response.status_code == 200:
                                    result = convert_response.json()
                                    
                                    self.test(
                                        "Quotation convert: Customer object returned",
                                        result.get("customer") is not None,
                                        f"Customer object missing"
                                    )
                                    
                                    self.test(
                                        "Quotation convert: Booking object returned",
                                        result.get("booking") is not None,
                                        f"Booking object missing"
                                    )
                                    
                                    # Verify no duplicate customer created (should reuse existing)
                                    customer = result.get("customer")
                                    if customer:
                                        self.test(
                                            "Quotation convert: Reused existing customer (phone_normalized matches)",
                                            customer.get("phone_normalized") == "+62813222333",
                                            f"Expected +62813222333, got {customer.get('phone_normalized')}"
                                        )
                                    
                                    # Store booking for cleanup
                                    booking = result.get("booking")
                                    if booking and booking.get("id"):
                                        self.created_ids.setdefault("bookings", []).append(booking["id"])
                
                if quo_id:
                    self.created_ids.setdefault("quotations", []).append(quo_id)
        except Exception as e:
            self.test("Quotation convert: Dedupe test", False, str(e))
    
    def test_contact_360_view(self):
        """Test Contact 360 view"""
        self.log("\n=== Testing Contact 360 View ===", "info")
        
        # Seed has "CV Sentosa Wisata" customer linked to a 'won' lead
        # We need to find this customer first
        try:
            # Get all customers
            url = f"{self.base_url}/api/customers"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                customers = response.json()
                sentosa = None
                for c in customers:
                    if "Sentosa" in c.get("name", ""):
                        sentosa = c
                        break
                
                if sentosa:
                    customer_id = sentosa.get("id")
                    
                    # Get customer detail (Contact 360)
                    detail_url = f"{self.base_url}/api/customers/{customer_id}"
                    detail_response = requests.get(detail_url, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    self.test(
                        "Contact 360: GET /api/customers/{id} returns 200",
                        detail_response.status_code == 200,
                        f"Expected 200, got {detail_response.status_code}"
                    )
                    
                    if detail_response.status_code == 200:
                        customer = detail_response.json()
                        
                        # Check required fields
                        required_fields = ["bookings", "leads", "quotations", "conversations", "timeline", "stats", "phone_normalized"]
                        for field in required_fields:
                            self.test(
                                f"Contact 360: Customer has '{field}' field",
                                field in customer,
                                f"Field '{field}' missing"
                            )
                        
                        # Check stats structure
                        stats = customer.get("stats", {})
                        required_stats = ["bookings_count", "total_spent", "active_bookings", "leads_count", "quotations_count", "conversations_count"]
                        for stat in required_stats:
                            self.test(
                                f"Contact 360: Stats has '{stat}' field",
                                stat in stats,
                                f"Stat '{stat}' missing"
                            )
                        
                        # Verify CV Sentosa Wisata has at least 1 lead (from seed)
                        leads_count = stats.get("leads_count", 0)
                        self.test(
                            "Contact 360: CV Sentosa Wisata has leads_count >= 1",
                            leads_count >= 1,
                            f"Expected leads_count >= 1, got {leads_count}"
                        )
                        
                        # Check timeline has lead entry
                        timeline = customer.get("timeline", [])
                        has_lead_entry = any(item.get("type") == "lead" for item in timeline)
                        self.test(
                            "Contact 360: Timeline has 'lead' entry",
                            has_lead_entry,
                            f"No lead entry found in timeline"
                        )
                        
                        # Check timeline is sorted descending by date
                        if len(timeline) > 1:
                            dates = [item.get("date") for item in timeline if item.get("date")]
                            is_sorted = all(dates[i] >= dates[i+1] for i in range(len(dates)-1))
                            self.test(
                                "Contact 360: Timeline sorted descending by date",
                                is_sorted,
                                f"Timeline not sorted correctly"
                            )
                else:
                    self.log("CV Sentosa Wisata customer not found in seed data", "warn")
        except Exception as e:
            self.test("Contact 360: View test", False, str(e))
    
    def test_contact_360_aggregation(self):
        """Test Contact 360 aggregation by phone"""
        self.log("\n=== Testing Contact 360 Aggregation by Phone ===", "info")
        
        try:
            # Step 1: Create a customer with unique phone
            unique_phone = "081333222111"
            url = f"{self.base_url}/api/customers"
            data = {
                "name": "Aggregation Test Customer",
                "phone": unique_phone,
                "email": "aggtest@test.com",
                "type": "individual"
            }
            response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                customer = response.json()
                customer_id = customer.get("id")
                
                # Step 2: Create a lead with same phone (should auto-link)
                lead_url = f"{self.base_url}/api/leads"
                lead_data = {
                    "customer_name": "Lead for Aggregation",
                    "phone": unique_phone,
                    "email": "leadagg@test.com",
                    "source": "manual",
                    "destination": "Bandung",
                    "pax": 4
                }
                lead_response = requests.post(lead_url, json=lead_data, headers=self.headers("owner@demo.local"), timeout=10)
                
                if lead_response.status_code == 200:
                    lead = lead_response.json()
                    lead_id = lead.get("id")
                    
                    # Step 3: Create a quotation with same phone
                    quo_url = f"{self.base_url}/api/quotations"
                    quo_data = {
                        "customer_name": "Quotation for Aggregation",
                        "phone": unique_phone,
                        "email": "quoagg@test.com",
                        "destination": "Yogyakarta",
                        "trip_date": (datetime.now() + timedelta(days=15)).isoformat(),
                        "pax": 6,
                        "vehicle_type": "hiace_premio",
                        "days": 2,
                        "distance_km": 300
                    }
                    quo_response = requests.post(quo_url, json=quo_data, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    if quo_response.status_code == 200:
                        quotation = quo_response.json()
                        quo_id = quotation.get("id")
                        
                        # Step 4: Get customer detail (Contact 360)
                        detail_url = f"{self.base_url}/api/customers/{customer_id}"
                        detail_response = requests.get(detail_url, headers=self.headers("owner@demo.local"), timeout=10)
                        
                        if detail_response.status_code == 200:
                            customer_detail = detail_response.json()
                            
                            # Verify leads array includes the created lead
                            leads = customer_detail.get("leads", [])
                            lead_ids = [l.get("id") for l in leads]
                            self.test(
                                "Contact 360 Aggregation: Leads array includes lead with matching phone",
                                lead_id in lead_ids,
                                f"Lead {lead_id} not found in leads array"
                            )
                            
                            # Verify quotations array includes the created quotation
                            quotations = customer_detail.get("quotations", [])
                            quo_ids = [q.get("id") for q in quotations]
                            self.test(
                                "Contact 360 Aggregation: Quotations array includes quotation with matching phone",
                                quo_id in quo_ids,
                                f"Quotation {quo_id} not found in quotations array"
                            )
                            
                            # Verify stats reflect the aggregated data
                            stats = customer_detail.get("stats", {})
                            self.test(
                                "Contact 360 Aggregation: Stats leads_count >= 1",
                                stats.get("leads_count", 0) >= 1,
                                f"Expected leads_count >= 1, got {stats.get('leads_count')}"
                            )
                            
                            self.test(
                                "Contact 360 Aggregation: Stats quotations_count >= 1",
                                stats.get("quotations_count", 0) >= 1,
                                f"Expected quotations_count >= 1, got {stats.get('quotations_count')}"
                            )
                        
                        if quo_id:
                            self.created_ids.setdefault("quotations", []).append(quo_id)
                    
                    if lead_id:
                        self.created_ids.setdefault("leads", []).append(lead_id)
                
                if customer_id:
                    self.created_ids.setdefault("customers", []).append(customer_id)
        except Exception as e:
            self.test("Contact 360 Aggregation: Test", False, str(e))
    
    def test_rbac(self):
        """Test RBAC for customers and crm sections"""
        self.log("\n=== Testing RBAC ===", "info")
        
        # Test 1: Unauthenticated requests return 401
        try:
            url = f"{self.base_url}/api/customers"
            response = requests.get(url, timeout=10)  # No auth header
            
            self.test(
                "RBAC: GET /api/customers without auth returns 401",
                response.status_code == 401,
                f"Expected 401, got {response.status_code}"
            )
        except Exception as e:
            self.test("RBAC: Unauthenticated customers", False, str(e))
        
        try:
            url = f"{self.base_url}/api/leads"
            response = requests.get(url, timeout=10)  # No auth header
            
            self.test(
                "RBAC: GET /api/leads without auth returns 401",
                response.status_code == 401,
                f"Expected 401, got {response.status_code}"
            )
        except Exception as e:
            self.test("RBAC: Unauthenticated leads", False, str(e))
        
        # Test 2: Driver gets 403 for customers section
        try:
            url = f"{self.base_url}/api/customers"
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "RBAC: Driver GET /api/customers returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("RBAC: Driver customers forbidden", False, str(e))
        
        try:
            url = f"{self.base_url}/api/customers"
            data = {"name": "Test", "phone": "081234567890", "type": "individual"}
            response = requests.post(url, json=data, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "RBAC: Driver POST /api/customers returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("RBAC: Driver customers POST forbidden", False, str(e))
        
        # Test 3: Driver gets 403 for crm section (leads)
        try:
            url = f"{self.base_url}/api/leads"
            response = requests.get(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "RBAC: Driver GET /api/leads returns 403",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("RBAC: Driver leads forbidden", False, str(e))
        
        # Test 4: Owner gets 200 for customers
        try:
            url = f"{self.base_url}/api/customers"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "RBAC: Owner GET /api/customers returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
        except Exception as e:
            self.test("RBAC: Owner customers allowed", False, str(e))
        
        # Test 5: Ops Admin gets 200 for customers
        try:
            url = f"{self.base_url}/api/customers"
            response = requests.get(url, headers=self.headers("ops@demo.local"), timeout=10)
            
            self.test(
                "RBAC: Ops Admin GET /api/customers returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
        except Exception as e:
            self.test("RBAC: Ops Admin customers allowed", False, str(e))
        
        # Test 6: Owner gets 200 for leads
        try:
            url = f"{self.base_url}/api/leads"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "RBAC: Owner GET /api/leads returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
        except Exception as e:
            self.test("RBAC: Owner leads allowed", False, str(e))
        
        # Test 7: Ops Admin gets 200 for leads
        try:
            url = f"{self.base_url}/api/leads"
            response = requests.get(url, headers=self.headers("ops@demo.local"), timeout=10)
            
            self.test(
                "RBAC: Ops Admin GET /api/leads returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
        except Exception as e:
            self.test("RBAC: Ops Admin leads allowed", False, str(e))
    
    def test_regression(self):
        """Test regression: customer update, delete with bookings, B1/B2/B3 endpoints"""
        self.log("\n=== Testing Regression ===", "info")
        
        # Test 1: Customer update recomputes phone_normalized
        try:
            # Create customer
            url = f"{self.base_url}/api/customers"
            data = {
                "name": "Regression Test Customer",
                "phone": "081222333444",
                "email": "regression@test.com",
                "type": "individual"
            }
            response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                customer = response.json()
                customer_id = customer.get("id")
                
                # Update phone
                update_url = f"{self.base_url}/api/customers/{customer_id}"
                update_data = {"phone": "081555666777"}
                update_response = requests.patch(update_url, json=update_data, headers=self.headers("owner@demo.local"), timeout=10)
                
                self.test(
                    "Regression: PATCH /api/customers/{id} returns 200",
                    update_response.status_code == 200,
                    f"Expected 200, got {update_response.status_code}"
                )
                
                if update_response.status_code == 200:
                    updated = update_response.json()
                    
                    self.test(
                        "Regression: Customer update recomputes phone_normalized",
                        updated.get("phone_normalized") == "+6281555666777",
                        f"Expected +6281555666777, got {updated.get('phone_normalized')}"
                    )
                
                if customer_id:
                    self.created_ids.setdefault("customers", []).append(customer_id)
        except Exception as e:
            self.test("Regression: Customer update", False, str(e))
        
        # Test 2: Delete customer with bookings blocked
        try:
            # Get a customer with bookings (from seed: "PT Maju Jaya" or "Keluarga Andi")
            url = f"{self.base_url}/api/customers"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                customers = response.json()
                customer_with_booking = None
                for c in customers:
                    if "Maju Jaya" in c.get("name", "") or "Keluarga Andi" in c.get("name", ""):
                        customer_with_booking = c
                        break
                
                if customer_with_booking:
                    customer_id = customer_with_booking.get("id")
                    
                    # Try to delete
                    delete_url = f"{self.base_url}/api/customers/{customer_id}"
                    delete_response = requests.delete(delete_url, headers=self.headers("owner@demo.local"), timeout=10)
                    
                    self.test(
                        "Regression: Delete customer with bookings returns 400",
                        delete_response.status_code == 400,
                        f"Expected 400, got {delete_response.status_code}"
                    )
                    
                    if delete_response.status_code == 400:
                        detail = delete_response.json().get("detail", "")
                        self.test(
                            "Regression: 400 response mentions bookings",
                            "booking" in detail.lower(),
                            f"Expected 'booking' in detail, got: {detail}"
                        )
        except Exception as e:
            self.test("Regression: Delete customer with bookings", False, str(e))
        
        # Test 3: B1 pricing endpoint still works
        try:
            url = f"{self.base_url}/api/pricing/rules"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "Regression: B1 GET /api/pricing/rules returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
        except Exception as e:
            self.test("Regression: B1 pricing endpoint", False, str(e))
        
        # Test 4: B2 quotations endpoint still works
        try:
            url = f"{self.base_url}/api/quotations"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "Regression: B2 GET /api/quotations returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
        except Exception as e:
            self.test("Regression: B2 quotations endpoint", False, str(e))
        
        # Test 5: B3 content endpoint still works
        try:
            url = f"{self.base_url}/api/content/destinations"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "Regression: B3 GET /api/content/destinations returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
        except Exception as e:
            self.test("Regression: B3 content endpoint", False, str(e))
        
        # Test 6: Bookings endpoint still works
        try:
            url = f"{self.base_url}/api/bookings"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "Regression: GET /api/bookings returns 200",
                response.status_code == 200,
                f"Expected 200, got {response.status_code}"
            )
        except Exception as e:
            self.test("Regression: Bookings endpoint", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*70, "info")
        self.log("Phase 9 / B4 Identity & Dedupe Backend Test Suite", "info")
        self.log("="*70, "info")
        
        # Run tests in order
        if not self.test_auth():
            self.log("\n⚠️  Authentication failed. Cannot proceed with other tests.", "warn")
            return False
        
        self.test_phone_normalization()
        self.test_dedupe_customer_creation()
        self.test_auto_link_lead_to_customer()
        self.test_lead_convert_dedupe()
        self.test_quotation_convert_dedupe()
        self.test_contact_360_view()
        self.test_contact_360_aggregation()
        self.test_rbac()
        self.test_regression()
        
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
    tester = B4TestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
