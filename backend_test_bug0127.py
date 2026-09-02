"""
Backend API Test - BUG-0127 Data Cleanliness Verification
Tests that NO test pollution data exists in the system
"""
import requests
import sys
from datetime import datetime

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

class DataCleanlinessTest:
    def __init__(self):
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.critical_issues = []

    def login(self, email="owner@demo.local", password="demo12345"):
        """Login and get auth token"""
        print(f"\n🔐 Logging in as {email}...")
        try:
            response = requests.post(f"{BASE_URL}/auth/login", 
                                   json={"email": email, "password": password})
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token") or data.get("token")
                print(f"✅ Login successful")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return False

    def headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }

    def test_customers_clean(self):
        """Test that customers collection has EXACTLY 4 demo customers"""
        print("\n" + "="*70)
        print("🧪 TEST 1: Customers - MUST have EXACTLY 4 demo customers")
        print("="*70)
        self.tests_run += 1
        
        try:
            response = requests.get(f"{BASE_URL}/customers", headers=self.headers())
            if response.status_code != 200:
                self.tests_failed += 1
                self.failures.append(f"GET /customers failed: {response.status_code}")
                print(f"❌ FAIL - Status: {response.status_code}")
                return False
            
            customers = response.json()
            print(f"   Found {len(customers)} customers")
            
            # Expected demo customers
            expected_names = ['PT Maju Jaya', 'Keluarga Andi', 'CV Sentosa Wisata', 'Keluarga Hendra']
            
            # Test pollution markers
            pollution_markers = [
                'AAAA', 'aaaa', 'Smoke Customer', 'Penjaga INV', 'Guard Lead',
                'Uji Balapan', 'Budi Pemesan', 'Tamu Bandara'
            ]
            
            issues = []
            
            # Check count
            if len(customers) != 4:
                issues.append(f"Expected EXACTLY 4 customers, found {len(customers)}")
            
            # Check for pollution
            for customer in customers:
                name = customer.get('name', '')
                
                # Check for pollution markers
                for marker in pollution_markers:
                    if marker in name:
                        issues.append(f"POLLUTION FOUND: Customer '{name}' contains '{marker}'")
                        self.critical_issues.append(f"Customer pollution: {name}")
                
                # Check for oversized names (>200 chars)
                if len(name) > 200:
                    issues.append(f"OVERSIZED NAME: Customer '{name[:50]}...' has {len(name)} characters (max 200)")
                    self.critical_issues.append(f"Oversized customer name: {len(name)} chars")
                
                print(f"   - {name}")
            
            # Check if we have the expected demo customers
            found_names = [c.get('name', '') for c in customers]
            for expected in expected_names:
                if expected not in found_names:
                    issues.append(f"Missing expected demo customer: {expected}")
            
            if issues:
                self.tests_failed += 1
                self.failures.append("Customers collection has pollution")
                print(f"❌ FAIL - Issues found:")
                for issue in issues:
                    print(f"   ⚠️  {issue}")
                return False
            else:
                self.tests_passed += 1
                print(f"✅ PASS - Customers collection is clean with 4 demo customers")
                return True
                
        except Exception as e:
            self.tests_failed += 1
            self.failures.append(f"Customers test error: {str(e)}")
            print(f"❌ FAIL - Error: {str(e)}")
            return False

    def test_audit_logs_clean(self):
        """Test that audit logs have no giant summaries"""
        print("\n" + "="*70)
        print("🧪 TEST 2: Audit Logs - No summaries > 1000 chars, no test markers")
        print("="*70)
        self.tests_run += 1
        
        try:
            response = requests.get(f"{BASE_URL}/audit-logs", headers=self.headers())
            if response.status_code != 200:
                self.tests_failed += 1
                self.failures.append(f"GET /audit_logs failed: {response.status_code}")
                print(f"❌ FAIL - Status: {response.status_code}")
                return False
            
            logs = response.json()
            print(f"   Found {len(logs)} audit log entries")
            
            pollution_markers = ['Smoke', 'Penjaga INV', 'guard-media', 'Guard Lead']
            
            issues = []
            
            for log in logs:
                summary = log.get('summary', '')
                
                # Check for oversized summaries
                if len(summary) > 1000:
                    issues.append(f"OVERSIZED SUMMARY: {len(summary)} characters (max 1000)")
                    self.critical_issues.append(f"Oversized audit summary: {len(summary)} chars")
                
                # Check for pollution markers
                for marker in pollution_markers:
                    if marker in summary:
                        issues.append(f"POLLUTION: Summary contains '{marker}'")
                        self.critical_issues.append(f"Audit log pollution: {marker}")
            
            if issues:
                self.tests_failed += 1
                self.failures.append("Audit logs have pollution")
                print(f"❌ FAIL - Issues found:")
                for issue in issues[:10]:  # Show first 10 issues
                    print(f"   ⚠️  {issue}")
                if len(issues) > 10:
                    print(f"   ... and {len(issues) - 10} more issues")
                return False
            else:
                self.tests_passed += 1
                print(f"✅ PASS - Audit logs are clean")
                return True
                
        except Exception as e:
            self.tests_failed += 1
            self.failures.append(f"Audit logs test error: {str(e)}")
            print(f"❌ FAIL - Error: {str(e)}")
            return False

    def test_inbox_clean(self):
        """Test that inbox has no test conversations"""
        print("\n" + "="*70)
        print("🧪 TEST 3: Inbox - No test conversation names")
        print("="*70)
        self.tests_run += 1
        
        try:
            response = requests.get(f"{BASE_URL}/conversations", headers=self.headers())
            if response.status_code != 200:
                self.tests_failed += 1
                self.failures.append(f"GET /conversations failed: {response.status_code}")
                print(f"❌ FAIL - Status: {response.status_code}")
                return False
            
            conversations = response.json()
            print(f"   Found {len(conversations)} conversations")
            
            pollution_markers = [
                'Penjaga INV-PRICE-01', 'Penjaga INV-BOOK-02', 'Smoke Customer',
                'Guard Lead', 'Penjaga INV'
            ]
            
            issues = []
            
            for conv in conversations:
                contact_name = conv.get('contact_name', '')
                
                # Check for pollution markers
                for marker in pollution_markers:
                    if marker in contact_name:
                        issues.append(f"POLLUTION: Conversation with '{contact_name}' contains '{marker}'")
                        self.critical_issues.append(f"Inbox pollution: {contact_name}")
            
            if issues:
                self.tests_failed += 1
                self.failures.append("Inbox has pollution")
                print(f"❌ FAIL - Issues found:")
                for issue in issues:
                    print(f"   ⚠️  {issue}")
                return False
            else:
                self.tests_passed += 1
                print(f"✅ PASS - Inbox is clean")
                return True
                
        except Exception as e:
            self.tests_failed += 1
            self.failures.append(f"Inbox test error: {str(e)}")
            print(f"❌ FAIL - Error: {str(e)}")
            return False

    def test_bookings_clean(self):
        """Test that bookings only has demo bookings BK-0001 to BK-0010"""
        print("\n" + "="*70)
        print("🧪 TEST 4: Bookings - Only demo bookings BK-0001 to BK-0010")
        print("="*70)
        self.tests_run += 1
        
        try:
            response = requests.get(f"{BASE_URL}/bookings", headers=self.headers())
            if response.status_code != 200:
                self.tests_failed += 1
                self.failures.append(f"GET /bookings failed: {response.status_code}")
                print(f"❌ FAIL - Status: {response.status_code}")
                return False
            
            bookings = response.json()
            print(f"   Found {len(bookings)} bookings")
            
            issues = []
            test_booking_codes = []
            
            for booking in bookings:
                code = booking.get('code', '')
                customer_name = booking.get('customer_name', '')
                
                # Check if it's a demo booking (BK-0001 to BK-0010)
                if code and code.startswith('BK-'):
                    try:
                        num = int(code.split('-')[1])
                        if num > 10:
                            test_booking_codes.append(code)
                            issues.append(f"NON-DEMO BOOKING: {code} (expected only BK-0001 to BK-0010)")
                    except (ValueError, IndexError):
                        pass
                
                # Check for test customer names
                test_markers = ['Smoke', 'Penjaga', 'Guard', 'Uji']
                for marker in test_markers:
                    if marker in customer_name:
                        issues.append(f"TEST CUSTOMER: Booking {code} has customer '{customer_name}'")
                        self.critical_issues.append(f"Booking pollution: {code} - {customer_name}")
            
            if issues:
                self.tests_failed += 1
                self.failures.append("Bookings have pollution")
                print(f"❌ FAIL - Issues found:")
                for issue in issues[:10]:
                    print(f"   ⚠️  {issue}")
                if len(issues) > 10:
                    print(f"   ... and {len(issues) - 10} more issues")
                return False
            else:
                self.tests_passed += 1
                print(f"✅ PASS - Bookings are clean (only demo data)")
                return True
                
        except Exception as e:
            self.tests_failed += 1
            self.failures.append(f"Bookings test error: {str(e)}")
            print(f"❌ FAIL - Error: {str(e)}")
            return False

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("📊 BUG-0127 DATA CLEANLINESS TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100) if self.tests_run > 0 else 0:.1f}%")
        
        if self.critical_issues:
            print(f"\n🚨 CRITICAL ISSUES FOUND: {len(self.critical_issues)}")
            for issue in self.critical_issues:
                print(f"   ⚠️  {issue}")
        
        if self.failures:
            print("\n❌ FAILED TESTS:")
            for i, failure in enumerate(self.failures, 1):
                print(f"   {i}. {failure}")
        
        print("\n" + "="*70)
        
        if self.tests_failed == 0:
            print("✅ BUG-0127 VERIFICATION: PASSED - No test pollution found")
        else:
            print("❌ BUG-0127 VERIFICATION: FAILED - Test pollution detected")
        print("="*70)


def main():
    tester = DataCleanlinessTest()
    
    print("\n" + "="*70)
    print("🧪 BUG-0127 DATA CLEANLINESS VERIFICATION")
    print("Testing that NO test pollution data exists in the system")
    print("="*70)
    
    # Login as owner
    if not tester.login("owner@demo.local", "demo12345"):
        print("❌ Cannot proceed without login")
        return 1
    
    # Run all cleanliness tests
    tester.test_customers_clean()
    tester.test_audit_logs_clean()
    tester.test_inbox_clean()
    tester.test_bookings_clean()
    
    # Print summary
    tester.print_summary()
    
    return 0 if tester.tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
