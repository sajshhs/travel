"""
Gap Tier A / Phase 7 Backend Testing
Tests: Auth/RBAC, Inbox (CRM), Notifications, Settings, Audit Logs, Public Web-Chat
"""
import requests
import sys
import time
from datetime import datetime

BASE_URL = "https://trip-route-buttons.preview.emergentagent.com/api"

class Phase7Tester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.tokens = {}
        self.errors = []
        self.users = {}

    def log(self, msg: str, level: str = "INFO"):
        prefix = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(level, "•")
        print(f"{prefix} {msg}")

    def test(self, name: str, condition: bool, error_msg: str = ""):
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            self.log(f"{name}: PASS", "PASS")
            return True
        else:
            self.tests_failed += 1
            self.log(f"{name}: FAIL - {error_msg}", "FAIL")
            self.errors.append(f"{name}: {error_msg}")
            return False

    def login(self, email: str, password: str):
        """Login and store token + user"""
        self.log(f"Logging in as {email}...")
        try:
            resp = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("token")
                user = data.get("user")
                if token and user:
                    self.tokens[email] = token
                    self.users[email] = user
                    self.log(f"Login successful for {email} (role: {user.get('role')})", "PASS")
                    return True
                else:
                    self.log(f"Login response missing token/user for {email}", "FAIL")
                    return False
            else:
                self.log(f"Login failed for {email}: {resp.status_code} - {resp.text}", "FAIL")
                return False
        except Exception as e:
            self.log(f"Login exception for {email}: {e}", "FAIL")
            return False

    def get(self, endpoint: str, email: str, params=None):
        """GET request with auth"""
        token = self.tokens.get(email)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)

    def post(self, endpoint: str, email: str, json=None):
        """POST request with auth"""
        token = self.tokens.get(email)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return requests.post(f"{BASE_URL}{endpoint}", headers=headers, json=json, timeout=10)

    def patch(self, endpoint: str, email: str, json=None):
        """PATCH request with auth"""
        token = self.tokens.get(email)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return requests.patch(f"{BASE_URL}{endpoint}", headers=headers, json=json, timeout=10)

    def test_auth_rbac(self):
        """Test AUTH/RBAC: login returns {token, user}, driver gets 403 on CRM/settings"""
        self.log("\n=== Testing AUTH/RBAC ===")
        
        # Login all three roles
        owner_ok = self.login("owner@demo.local", "demo12345")
        ops_ok = self.login("ops@demo.local", "demo12345")
        driver_ok = self.login("driver@demo.local", "demo12345")
        
        self.test("AUTH: owner login returns token+user", owner_ok, "Login failed")
        self.test("AUTH: ops_admin login returns token+user", ops_ok, "Login failed")
        self.test("AUTH: driver login returns token+user", driver_ok, "Login failed")
        
        if owner_ok:
            self.test("AUTH: owner user has role=owner", self.users["owner@demo.local"].get("role") == "owner", 
                     f"Expected owner, got {self.users['owner@demo.local'].get('role')}")
        if ops_ok:
            self.test("AUTH: ops_admin user has role=ops_admin", self.users["ops@demo.local"].get("role") == "ops_admin",
                     f"Expected ops_admin, got {self.users['ops@demo.local'].get('role')}")
        if driver_ok:
            self.test("AUTH: driver user has role=driver", self.users["driver@demo.local"].get("role") == "driver",
                     f"Expected driver, got {self.users['driver@demo.local'].get('role')}")
        
        # Test RBAC: driver should get 403 on CRM (inbox) and settings
        if driver_ok:
            try:
                r = self.get("/conversations", "driver@demo.local")
                self.test("RBAC: driver gets 403 on /conversations (CRM section)", r.status_code == 403,
                         f"Expected 403, got {r.status_code}")
            except Exception as e:
                self.test("RBAC: driver gets 403 on /conversations", False, str(e))
            
            try:
                r = self.get("/settings", "driver@demo.local")
                self.test("RBAC: driver gets 403 on /settings", r.status_code == 403,
                         f"Expected 403, got {r.status_code}")
            except Exception as e:
                self.test("RBAC: driver gets 403 on /settings", False, str(e))
        
        # Test owner/ops can access CRM
        if owner_ok:
            try:
                r = self.get("/conversations", "owner@demo.local")
                self.test("RBAC: owner can access /conversations", r.status_code == 200,
                         f"Expected 200, got {r.status_code}")
            except Exception as e:
                self.test("RBAC: owner can access /conversations", False, str(e))
        
        if ops_ok:
            try:
                r = self.get("/conversations", "ops@demo.local")
                self.test("RBAC: ops_admin can access /conversations", r.status_code == 200,
                         f"Expected 200, got {r.status_code}")
            except Exception as e:
                self.test("RBAC: ops_admin can access /conversations", False, str(e))

    def test_inbox(self):
        """Test INBOX (CRM): conversations CRUD, filters, messages, status, assign"""
        self.log("\n=== Testing INBOX (CRM) ===")
        
        email = "owner@demo.local"
        
        # GET /conversations
        try:
            r = self.get("/conversations", email)
            self.test("INBOX: GET /conversations returns 200", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                self.test("INBOX: GET /conversations returns array", isinstance(data, list),
                         f"Expected list, got {type(data)}")
        except Exception as e:
            self.test("INBOX: GET /conversations", False, str(e))
        
        # Test filters: status=open, assigned=mine, assigned=unassigned, channel=web, q=search
        try:
            r = self.get("/conversations", email, params={"status": "open"})
            self.test("INBOX: GET /conversations?status=open returns 200", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
        except Exception as e:
            self.test("INBOX: GET /conversations?status=open", False, str(e))
        
        try:
            r = self.get("/conversations", email, params={"assigned": "mine"})
            self.test("INBOX: GET /conversations?assigned=mine returns 200", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
        except Exception as e:
            self.test("INBOX: GET /conversations?assigned=mine", False, str(e))
        
        try:
            r = self.get("/conversations", email, params={"assigned": "unassigned"})
            self.test("INBOX: GET /conversations?assigned=unassigned returns 200", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
        except Exception as e:
            self.test("INBOX: GET /conversations?assigned=unassigned", False, str(e))
        
        try:
            r = self.get("/conversations", email, params={"channel": "web"})
            self.test("INBOX: GET /conversations?channel=web returns 200", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
        except Exception as e:
            self.test("INBOX: GET /conversations?channel=web", False, str(e))
        
        try:
            r = self.get("/conversations", email, params={"q": "test"})
            self.test("INBOX: GET /conversations?q=test returns 200", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
        except Exception as e:
            self.test("INBOX: GET /conversations?q=test", False, str(e))
        
        # POST /conversations - create a conversation
        conv_id = None
        try:
            payload = {
                "channel": "internal",
                "contact_name": "Test Contact Phase7",
                "contact_phone": "081234567890",
                "subject": "Test conversation for Phase 7",
                "message": "Initial test message"
            }
            r = self.post("/conversations", email, json=payload)
            self.test("INBOX: POST /conversations creates conversation", r.status_code == 200,
                     f"Expected 200, got {r.status_code} - {r.text}")
            if r.status_code == 200:
                data = r.json()
                conv_id = data.get("id")
                self.test("INBOX: POST /conversations returns conversation with id", bool(conv_id),
                         "No id in response")
                self.test("INBOX: POST /conversations returns messages array", "messages" in data,
                         "No messages array in response")
        except Exception as e:
            self.test("INBOX: POST /conversations", False, str(e))
        
        # GET /conversations/{id} - get conversation with messages
        if conv_id:
            try:
                r = self.get(f"/conversations/{conv_id}", email)
                self.test("INBOX: GET /conversations/{id} returns 200", r.status_code == 200,
                         f"Expected 200, got {r.status_code}")
                if r.status_code == 200:
                    data = r.json()
                    self.test("INBOX: GET /conversations/{id} returns messages array", "messages" in data,
                             "No messages array")
                    self.test("INBOX: GET /conversations/{id} messages is array", isinstance(data.get("messages"), list),
                             f"Expected list, got {type(data.get('messages'))}")
            except Exception as e:
                self.test("INBOX: GET /conversations/{id}", False, str(e))
            
            # PATCH /conversations/{id} - update status
            try:
                r = self.patch(f"/conversations/{conv_id}", email, json={"status": "snoozed"})
                self.test("INBOX: PATCH /conversations/{id} updates status", r.status_code == 200,
                         f"Expected 200, got {r.status_code}")
                if r.status_code == 200:
                    data = r.json()
                    self.test("INBOX: PATCH status=snoozed persists", data.get("status") == "snoozed",
                             f"Expected snoozed, got {data.get('status')}")
            except Exception as e:
                self.test("INBOX: PATCH /conversations/{id} status", False, str(e))
            
            # PATCH /conversations/{id} - assign to owner (validate agent exists)
            owner_id = self.users.get(email, {}).get("id")
            if owner_id:
                try:
                    r = self.patch(f"/conversations/{conv_id}", email, json={"assigned_to": owner_id})
                    self.test("INBOX: PATCH /conversations/{id} assigns to valid agent", r.status_code == 200,
                             f"Expected 200, got {r.status_code}")
                    if r.status_code == 200:
                        data = r.json()
                        self.test("INBOX: PATCH assigned_to persists", data.get("assigned_to") == owner_id,
                                 f"Expected {owner_id}, got {data.get('assigned_to')}")
                except Exception as e:
                    self.test("INBOX: PATCH /conversations/{id} assign", False, str(e))
            
            # PATCH /conversations/{id} - assign to invalid agent (should return 400)
            try:
                r = self.patch(f"/conversations/{conv_id}", email, json={"assigned_to": "invalid_user_id_xyz"})
                self.test("INBOX: PATCH /conversations/{id} with invalid agent returns 400", r.status_code == 400,
                         f"Expected 400, got {r.status_code}")
            except Exception as e:
                self.test("INBOX: PATCH /conversations/{id} invalid agent", False, str(e))
            
            # POST /conversations/{id}/messages - post agent reply (internal=false -> status delivered)
            try:
                r = self.post(f"/conversations/{conv_id}/messages", email, json={"body": "Agent reply test", "internal": False})
                self.test("INBOX: POST /conversations/{id}/messages posts agent reply", r.status_code == 200,
                         f"Expected 200, got {r.status_code}")
                if r.status_code == 200:
                    data = r.json()
                    self.test("INBOX: Agent reply has status=delivered", data.get("status") == "delivered",
                             f"Expected delivered, got {data.get('status')}")
            except Exception as e:
                self.test("INBOX: POST /conversations/{id}/messages reply", False, str(e))
            
            # POST /conversations/{id}/messages - post internal note (internal=true -> status sent)
            try:
                r = self.post(f"/conversations/{conv_id}/messages", email, json={"body": "Internal note test", "internal": True})
                self.test("INBOX: POST /conversations/{id}/messages posts internal note", r.status_code == 200,
                         f"Expected 200, got {r.status_code}")
                if r.status_code == 200:
                    data = r.json()
                    self.test("INBOX: Internal note has status=sent", data.get("status") == "sent",
                             f"Expected sent, got {data.get('status')}")
            except Exception as e:
                self.test("INBOX: POST /conversations/{id}/messages internal", False, str(e))
            
            # POST /conversations/{id}/read - mark conversation read
            try:
                r = self.post(f"/conversations/{conv_id}/read", email)
                self.test("INBOX: POST /conversations/{id}/read marks read", r.status_code == 200,
                         f"Expected 200, got {r.status_code}")
                if r.status_code == 200:
                    data = r.json()
                    self.test("INBOX: POST /conversations/{id}/read returns ok", data.get("ok") == True,
                             f"Expected ok=True, got {data}")
            except Exception as e:
                self.test("INBOX: POST /conversations/{id}/read", False, str(e))

    def test_notifications(self):
        """Test NOTIFICATIONS: list, unread_count, scan, read_all, read, dismiss, role visibility"""
        self.log("\n=== Testing NOTIFICATIONS ===")
        
        # Test with owner
        email = "owner@demo.local"
        
        # GET /notifications
        try:
            r = self.get("/notifications", email)
            self.test("NOTIF: GET /notifications returns 200", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                self.test("NOTIF: GET /notifications returns array", isinstance(data, list),
                         f"Expected list, got {type(data)}")
        except Exception as e:
            self.test("NOTIF: GET /notifications", False, str(e))
        
        # GET /notifications?status=pending
        try:
            r = self.get("/notifications", email, params={"status": "pending"})
            self.test("NOTIF: GET /notifications?status=pending returns 200", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
        except Exception as e:
            self.test("NOTIF: GET /notifications?status=pending", False, str(e))
        
        # GET /notifications/unread_count
        try:
            r = self.get("/notifications/unread_count", email)
            self.test("NOTIF: GET /notifications/unread_count returns 200", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                self.test("NOTIF: GET /notifications/unread_count returns {count}", "count" in data,
                         f"No count in response: {data}")
                self.test("NOTIF: unread_count is integer", isinstance(data.get("count"), int),
                         f"Expected int, got {type(data.get('count'))}")
        except Exception as e:
            self.test("NOTIF: GET /notifications/unread_count", False, str(e))
        
        # POST /notifications/scan (owner/ops only)
        try:
            r = self.post("/notifications/scan", email)
            self.test("NOTIF: POST /notifications/scan (owner) returns 200", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                self.test("NOTIF: POST /notifications/scan returns {created}", "created" in data,
                         f"No created in response: {data}")
        except Exception as e:
            self.test("NOTIF: POST /notifications/scan", False, str(e))
        
        # Test driver cannot scan (should get 403)
        if "driver@demo.local" in self.tokens:
            try:
                r = self.post("/notifications/scan", "driver@demo.local")
                self.test("NOTIF: POST /notifications/scan (driver) returns 403", r.status_code == 403,
                         f"Expected 403, got {r.status_code}")
            except Exception as e:
                self.test("NOTIF: POST /notifications/scan (driver)", False, str(e))
        
        # POST /notifications/read_all
        try:
            r = self.post("/notifications/read_all", email)
            self.test("NOTIF: POST /notifications/read_all returns 200", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
        except Exception as e:
            self.test("NOTIF: POST /notifications/read_all", False, str(e))
        
        # Get a notification to test read/dismiss
        notif_id = None
        try:
            r = self.get("/notifications", email, params={"limit": 1})
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and len(data) > 0:
                    notif_id = data[0].get("id")
        except:
            pass
        
        if notif_id:
            # POST /notifications/{id}/read
            try:
                r = self.post(f"/notifications/{notif_id}/read", email)
                self.test("NOTIF: POST /notifications/{id}/read returns 200", r.status_code == 200,
                         f"Expected 200, got {r.status_code}")
            except Exception as e:
                self.test("NOTIF: POST /notifications/{id}/read", False, str(e))
            
            # POST /notifications/{id}/dismiss
            try:
                r = self.post(f"/notifications/{notif_id}/dismiss", email)
                self.test("NOTIF: POST /notifications/{id}/dismiss returns 200", r.status_code == 200,
                         f"Expected 200, got {r.status_code}")
            except Exception as e:
                self.test("NOTIF: POST /notifications/{id}/dismiss", False, str(e))
        
        # Test role visibility: driver sees only notifications targeted to driver/all, not 'manager'
        if "driver@demo.local" in self.tokens:
            try:
                r = self.get("/notifications", "driver@demo.local")
                self.test("NOTIF: driver can GET /notifications", r.status_code == 200,
                         f"Expected 200, got {r.status_code}")
                if r.status_code == 200:
                    data = r.json()
                    # Check that driver doesn't see manager-only notifications
                    manager_notifs = [n for n in data if n.get("target_role") == "manager"]
                    self.test("NOTIF: driver doesn't see manager-only notifications", len(manager_notifs) == 0,
                             f"Driver saw {len(manager_notifs)} manager notifications")
            except Exception as e:
                self.test("NOTIF: driver visibility", False, str(e))

    def test_settings(self):
        """Test SETTINGS: GET/PATCH settings, audit log creation"""
        self.log("\n=== Testing SETTINGS ===")
        
        email = "owner@demo.local"
        
        # GET /settings (owner only)
        try:
            r = self.get("/settings", email)
            self.test("SETTINGS: GET /settings (owner) returns 200", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                expected_keys = ["company_info", "pricing_defaults", "operational", "pricing_rules", "map_provider", "theme_config"]
                for key in expected_keys:
                    self.test(f"SETTINGS: GET /settings returns key '{key}'", key in data,
                             f"Missing key: {key}")
        except Exception as e:
            self.test("SETTINGS: GET /settings", False, str(e))
        
        # Test ops_admin cannot access settings (should get 403)
        if "ops@demo.local" in self.tokens:
            try:
                r = self.get("/settings", "ops@demo.local")
                self.test("SETTINGS: GET /settings (ops_admin) returns 403", r.status_code == 403,
                         f"Expected 403, got {r.status_code}")
            except Exception as e:
                self.test("SETTINGS: GET /settings (ops_admin)", False, str(e))
        
        # PATCH /settings - update company_info
        try:
            test_value = f"Test Company Phase7 {int(time.time())}"
            r = self.patch("/settings", email, json={"company_info": {"name": test_value, "city": "Jakarta"}})
            self.test("SETTINGS: PATCH /settings updates company_info", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
            if r.status_code == 200:
                # Verify the change persisted
                r2 = self.get("/settings", email)
                if r2.status_code == 200:
                    data = r2.json()
                    self.test("SETTINGS: PATCH company_info persists", data.get("company_info", {}).get("name") == test_value,
                             f"Expected {test_value}, got {data.get('company_info', {}).get('name')}")
        except Exception as e:
            self.test("SETTINGS: PATCH /settings company_info", False, str(e))
        
        # PATCH /settings - update pricing_defaults
        try:
            r = self.patch("/settings", email, json={"pricing_defaults": {"dp_percent": 35, "min_rental_hours": 10}})
            self.test("SETTINGS: PATCH /settings updates pricing_defaults", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
            if r.status_code == 200:
                # Verify the change persisted
                r2 = self.get("/settings", email)
                if r2.status_code == 200:
                    data = r2.json()
                    self.test("SETTINGS: PATCH pricing_defaults persists", data.get("pricing_defaults", {}).get("dp_percent") == 35,
                             f"Expected 35, got {data.get('pricing_defaults', {}).get('dp_percent')}")
        except Exception as e:
            self.test("SETTINGS: PATCH /settings pricing_defaults", False, str(e))

    def test_audit_logs(self):
        """Test AUDIT LOGS: GET /audit-logs returns list (owner/ops)"""
        self.log("\n=== Testing AUDIT LOGS ===")
        
        email = "owner@demo.local"
        
        # GET /audit-logs
        try:
            r = self.get("/audit-logs", email)
            self.test("AUDIT: GET /audit-logs (owner) returns 200", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                self.test("AUDIT: GET /audit-logs returns array", isinstance(data, list),
                         f"Expected list, got {type(data)}")
                # Check that settings changes created audit entries
                settings_audits = [a for a in data if a.get("entity_type") == "settings"]
                self.test("AUDIT: Settings changes created audit entries", len(settings_audits) > 0,
                         f"Expected audit entries for settings, found {len(settings_audits)}")
        except Exception as e:
            self.test("AUDIT: GET /audit-logs", False, str(e))
        
        # Test ops_admin can access audit logs
        if "ops@demo.local" in self.tokens:
            try:
                r = self.get("/audit-logs", "ops@demo.local")
                # Note: permissions_config.py shows audit is owner-only, so ops should get 403
                self.test("AUDIT: GET /audit-logs (ops_admin) returns 403", r.status_code == 403,
                         f"Expected 403, got {r.status_code}")
            except Exception as e:
                self.test("AUDIT: GET /audit-logs (ops_admin)", False, str(e))
        
        # Test driver cannot access audit logs
        if "driver@demo.local" in self.tokens:
            try:
                r = self.get("/audit-logs", "driver@demo.local")
                self.test("AUDIT: GET /audit-logs (driver) returns 403", r.status_code == 403,
                         f"Expected 403, got {r.status_code}")
            except Exception as e:
                self.test("AUDIT: GET /audit-logs (driver)", False, str(e))

    def test_public_chat(self):
        """Test PUBLIC WEB-CHAT: POST /public/chat creates conversation, GET /public/chat/{token} returns thread"""
        self.log("\n=== Testing PUBLIC WEB-CHAT ===")
        
        # POST /public/chat - create new conversation (no auth)
        chat_token = None
        try:
            payload = {
                "name": "Test Visitor Phase7",
                "phone": "081234567890",
                "message": "Hello from public web chat test",
                "hp": ""  # honeypot field should be empty
            }
            r = requests.post(f"{BASE_URL}/public/chat", json=payload, timeout=10)
            self.test("PUBLIC CHAT: POST /public/chat creates conversation", r.status_code == 200,
                     f"Expected 200, got {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                chat_token = data.get("token")
                self.test("PUBLIC CHAT: POST /public/chat returns token", bool(chat_token),
                         "No token in response")
                self.test("PUBLIC CHAT: POST /public/chat returns status", data.get("status") == "received",
                         f"Expected status=received, got {data.get('status')}")
        except Exception as e:
            self.test("PUBLIC CHAT: POST /public/chat", False, str(e))
        
        # POST /public/chat - continue conversation with token
        if chat_token:
            try:
                payload = {
                    "name": "Test Visitor Phase7",
                    "phone": "081234567890",
                    "message": "Follow-up message in same thread",
                    "token": chat_token,
                    "hp": ""
                }
                r = requests.post(f"{BASE_URL}/public/chat", json=payload, timeout=10)
                self.test("PUBLIC CHAT: POST /public/chat continues conversation", r.status_code == 200,
                         f"Expected 200, got {r.status_code}")
            except Exception as e:
                self.test("PUBLIC CHAT: POST /public/chat continue", False, str(e))
            
            # GET /public/chat/{token} - get public thread
            try:
                r = requests.get(f"{BASE_URL}/public/chat/{chat_token}", timeout=10)
                self.test("PUBLIC CHAT: GET /public/chat/{token} returns thread", r.status_code == 200,
                         f"Expected 200, got {r.status_code}")
                if r.status_code == 200:
                    data = r.json()
                    self.test("PUBLIC CHAT: GET /public/chat/{token} returns messages array", "messages" in data,
                             "No messages in response")
                    self.test("PUBLIC CHAT: messages is array", isinstance(data.get("messages"), list),
                             f"Expected list, got {type(data.get('messages'))}")
                    # Check that internal notes are hidden
                    messages = data.get("messages", [])
                    internal_msgs = [m for m in messages if m.get("internal") == True]
                    self.test("PUBLIC CHAT: internal notes are hidden from public", len(internal_msgs) == 0,
                             f"Found {len(internal_msgs)} internal messages in public thread")
            except Exception as e:
                self.test("PUBLIC CHAT: GET /public/chat/{token}", False, str(e))
            
            # Verify conversation appears in agent Inbox
            if "owner@demo.local" in self.tokens:
                try:
                    time.sleep(1)  # Give it a moment to propagate
                    r = self.get("/conversations", "owner@demo.local", params={"channel": "web"})
                    if r.status_code == 200:
                        data = r.json()
                        web_convs = [c for c in data if c.get("channel") == "web" and "Test Visitor Phase7" in c.get("contact_name", "")]
                        self.test("PUBLIC CHAT: conversation appears in agent Inbox", len(web_convs) > 0,
                                 f"Expected web conversation in Inbox, found {len(web_convs)}")
                except Exception as e:
                    self.test("PUBLIC CHAT: verify in Inbox", False, str(e))

    def run_all(self):
        """Run all Phase 7 tests"""
        self.log("\n" + "="*60)
        self.log("Gap Tier A / Phase 7 Backend Testing")
        self.log("="*60)
        
        self.test_auth_rbac()
        self.test_inbox()
        self.test_notifications()
        self.test_settings()
        self.test_audit_logs()
        self.test_public_chat()
        
        # Summary
        self.log("\n" + "="*60)
        self.log(f"SUMMARY: {self.tests_passed}/{self.tests_run} tests passed", 
                "PASS" if self.tests_failed == 0 else "FAIL")
        self.log("="*60)
        
        if self.errors:
            self.log("\nFailed tests:")
            for err in self.errors:
                self.log(f"  - {err}", "FAIL")
        
        return 0 if self.tests_failed == 0 else 1

def main():
    tester = Phase7Tester()
    return tester.run_all()

if __name__ == "__main__":
    sys.exit(main())
