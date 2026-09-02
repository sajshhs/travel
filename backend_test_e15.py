#!/usr/bin/env python3
"""
Backend Test Suite for E15: GPS Dual-Source (Device Fisik via Traccar)
========================================================================
Tests webhook, device assignment, failover, alarms, RBAC
"""
import requests
import sys
import json
from datetime import datetime
from time import sleep

class E15TestSuite:
    def __init__(self, base_url="https://trip-route-buttons.preview.emergentagent.com"):
        self.base_url = base_url
        self.secret = "c5ec694b7067a93fcf056bebc1ec8a547e6aefec07da7b85"
        self.tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.vehicle_id = None
        self.test_imei = f"TEST{datetime.now().strftime('%H%M%S')}"
        
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
    
    def traccar_payload(self, imei, lat, lng, speed_knot, alarm=None, power=12.8, ignition=True):
        """Generate Traccar webhook payload"""
        attrs = {
            "ignition": ignition,
            "motion": speed_knot > 1,
            "power": power,
            "battery": 4.1,
            "batteryLevel": 95,
            "sat": 12,
            "blocked": False
        }
        if alarm:
            attrs["alarm"] = alarm
        return {
            "position": {
                "id": 1,
                "deviceId": 1,
                "protocol": "teltonika",
                "fixTime": "2026-07-01T18:00:00.000+00:00",
                "valid": True,
                "latitude": lat,
                "longitude": lng,
                "speed": speed_knot,
                "course": 90.0,
                "attributes": attrs,
            },
            "device": {
                "id": 1,
                "uniqueId": imei,
                "name": "TEST-Teltonika"
            },
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
    
    def test_get_vehicle(self):
        """Get a vehicle for testing"""
        self.log("\n=== Getting Test Vehicle ===", "info")
        
        try:
            url = f"{self.base_url}/api/vehicles"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                vehicles = response.json()
                if vehicles and isinstance(vehicles, list):
                    self.vehicle_id = vehicles[0]["id"]
                    self.log(f"Using vehicle: {vehicles[0].get('name')} ({self.vehicle_id})", "info")
                    return True
            
            self.log("No vehicles found", "fail")
            return False
        except Exception as e:
            self.log(f"Error getting vehicles: {str(e)}", "fail")
            return False
    
    def test_webhook_auth(self):
        """Test webhook authentication (correct/wrong secret)"""
        self.log("\n=== Testing Webhook Authentication ===", "info")
        
        payload = self.traccar_payload(self.test_imei, -6.2, 106.8, 5.0)
        
        # Test with correct secret (X-Gps-Token header)
        try:
            url = f"{self.base_url}/api/gps/webhook"
            headers = {"Content-Type": "application/json", "X-Gps-Token": self.secret}
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            # Should be 200 even if IMEI unmapped (graceful handling)
            self.test(
                "Webhook with correct X-Gps-Token header",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
        except Exception as e:
            self.test("Webhook with correct secret", False, str(e))
        
        # Test with wrong secret
        try:
            url = f"{self.base_url}/api/gps/webhook"
            headers = {"Content-Type": "application/json", "X-Gps-Token": "WRONG_SECRET"}
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            self.test(
                "Webhook with wrong secret returns 401",
                response.status_code == 401,
                f"Expected 401, got {response.status_code}"
            )
        except Exception as e:
            self.test("Webhook with wrong secret", False, str(e))
        
        # Test without secret
        try:
            url = f"{self.base_url}/api/gps/webhook"
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            self.test(
                "Webhook without secret returns 401",
                response.status_code == 401,
                f"Expected 401, got {response.status_code}"
            )
        except Exception as e:
            self.test("Webhook without secret", False, str(e))
    
    def test_device_assignment(self):
        """Test device assignment (IMEI mapping to vehicle)"""
        self.log("\n=== Testing Device Assignment ===", "info")
        
        if not self.vehicle_id:
            self.log("No vehicle ID, skipping device assignment tests", "warn")
            return False
        
        # Test assign device as owner
        try:
            url = f"{self.base_url}/api/gps/devices/{self.vehicle_id}/assign"
            data = {"imei": self.test_imei, "enabled": True, "note": "Test device"}
            response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "Owner can assign device",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                result = response.json()
                self.test(
                    "Assign returns ok=True",
                    result.get("ok") == True,
                    f"Got {result}"
                )
                self.test(
                    "Assign returns vehicle_id",
                    result.get("vehicle_id") == self.vehicle_id,
                    f"Expected {self.vehicle_id}, got {result.get('vehicle_id')}"
                )
        except Exception as e:
            self.test("Owner assign device", False, str(e))
        
        # Test assign device as ops_admin
        try:
            # Use a different IMEI for ops test
            ops_imei = f"OPS{datetime.now().strftime('%H%M%S')}"
            url = f"{self.base_url}/api/gps/devices/{self.vehicle_id}/assign"
            data = {"imei": ops_imei, "enabled": True, "note": "Ops test"}
            response = requests.post(url, json=data, headers=self.headers("ops@demo.local"), timeout=10)
            
            self.test(
                "Ops_admin can assign device",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
        except Exception as e:
            self.test("Ops_admin assign device", False, str(e))
        
        # Test assign device as driver (should fail with 403)
        try:
            driver_imei = f"DRV{datetime.now().strftime('%H%M%S')}"
            url = f"{self.base_url}/api/gps/devices/{self.vehicle_id}/assign"
            data = {"imei": driver_imei, "enabled": True}
            response = requests.post(url, json=data, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "Driver CANNOT assign device (403)",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("Driver assign device RBAC", False, str(e))
        
        return True
    
    def test_webhook_ingest(self):
        """Test webhook ingestion with mapped IMEI"""
        self.log("\n=== Testing Webhook Ingest (Mapped IMEI) ===", "info")
        
        if not self.vehicle_id:
            self.log("No vehicle ID, skipping webhook ingest tests", "warn")
            return False
        
        # Send webhook with mapped IMEI (27 knots ≈ 50 km/h)
        try:
            url = f"{self.base_url}/api/gps/webhook"
            payload = self.traccar_payload(self.test_imei, -6.2000, 106.8000, 27.0)
            headers = {"Content-Type": "application/json", "X-Gps-Token": self.secret}
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            self.test(
                "Webhook with mapped IMEI returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                result = response.json()
                self.test(
                    "Webhook returns status=ok",
                    result.get("status") == "ok",
                    f"Got status={result.get('status')}"
                )
                self.test(
                    "Webhook returns correct vehicle_id",
                    result.get("vehicle_id") == self.vehicle_id,
                    f"Expected {self.vehicle_id}, got {result.get('vehicle_id')}"
                )
                # 27 knots * 1.852 ≈ 50 km/h
                speed_kmh = result.get("speed_kmh", 0)
                self.test(
                    "Speed converted from knots to km/h (27kn≈50km/h)",
                    abs(speed_kmh - 50.0) < 0.5,
                    f"Expected ~50, got {speed_kmh}"
                )
        except Exception as e:
            self.test("Webhook ingest with mapped IMEI", False, str(e))
        
        return True
    
    def test_webhook_unmapped(self):
        """Test webhook with unmapped IMEI (should be ignored gracefully)"""
        self.log("\n=== Testing Webhook with Unmapped IMEI ===", "info")
        
        unknown_imei = f"UNKNOWN{datetime.now().strftime('%H%M%S')}"
        
        try:
            url = f"{self.base_url}/api/gps/webhook"
            payload = self.traccar_payload(unknown_imei, -6.2, 106.8, 5.0)
            headers = {"Content-Type": "application/json", "X-Gps-Token": self.secret}
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            self.test(
                "Webhook with unmapped IMEI returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                result = response.json()
                self.test(
                    "Unmapped IMEI returns status=ignored",
                    result.get("status") == "ignored",
                    f"Got status={result.get('status')}"
                )
                self.test(
                    "Unmapped IMEI returns reason=imei_unmapped",
                    result.get("reason") == "imei_unmapped",
                    f"Got reason={result.get('reason')}"
                )
        except Exception as e:
            self.test("Webhook with unmapped IMEI", False, str(e))
    
    def test_gps_live(self):
        """Test /api/gps/live endpoint (shows device source)"""
        self.log("\n=== Testing GPS Live Endpoint ===", "info")
        
        try:
            url = f"{self.base_url}/api/gps/live"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/gps/live returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                live = response.json()
                self.test(
                    "GPS live returns array",
                    isinstance(live, list),
                    f"Expected list, got {type(live)}"
                )
                
                # Find our test vehicle
                if self.vehicle_id:
                    row = next((x for x in live if x.get("vehicle_id") == self.vehicle_id), None)
                    if row:
                        self.test(
                            "Test vehicle appears in live data",
                            True,
                            ""
                        )
                        self.test(
                            "Live data has source field",
                            "source" in row,
                            f"source field missing"
                        )
                        self.test(
                            "Live data source is 'device'",
                            row.get("source") == "device",
                            f"Expected 'device', got {row.get('source')}"
                        )
                        self.test(
                            "Live data has power_v",
                            row.get("power_v") is not None,
                            f"power_v missing"
                        )
                        self.test(
                            "Live data has ignition",
                            row.get("ignition") is not None,
                            f"ignition missing"
                        )
                    else:
                        self.log("Test vehicle not found in live data (may need time to propagate)", "warn")
        except Exception as e:
            self.test("GET /api/gps/live", False, str(e))
    
    def test_failover(self):
        """Test failover: device priority over phone"""
        self.log("\n=== Testing Failover (Device Priority) ===", "info")
        
        if not self.vehicle_id:
            self.log("No vehicle ID, skipping failover tests", "warn")
            return False
        
        # First, send device position (fresh)
        try:
            url = f"{self.base_url}/api/gps/webhook"
            payload = self.traccar_payload(self.test_imei, -6.2100, 106.8100, 30.0)
            headers = {"Content-Type": "application/json", "X-Gps-Token": self.secret}
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            self.test(
                "Send device position for failover test",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
        except Exception as e:
            self.test("Send device position", False, str(e))
        
        # Then send phone position
        try:
            url = f"{self.base_url}/api/locations"
            data = {
                "vehicle_id": self.vehicle_id,
                "lat": -6.3,
                "lng": 106.9,
                "speed": 10
            }
            response = requests.post(url, json=data, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "Send phone position for failover test",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
        except Exception as e:
            self.test("Send phone position", False, str(e))
        
        # Check /api/gps/live - should prioritize device
        try:
            url = f"{self.base_url}/api/gps/live"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                live = response.json()
                row = next((x for x in live if x.get("vehicle_id") == self.vehicle_id), None)
                
                if row:
                    self.test(
                        "Failover: source is 'device' (device prioritized)",
                        row.get("source") == "device",
                        f"Expected 'device', got {row.get('source')}"
                    )
                    self.test(
                        "Failover: has_phone is True",
                        row.get("has_phone") == True,
                        f"Expected True, got {row.get('has_phone')}"
                    )
                    self.test(
                        "Failover: has_device is True",
                        row.get("has_device") == True,
                        f"Expected True, got {row.get('has_device')}"
                    )
                else:
                    self.log("Test vehicle not found in live data for failover test", "warn")
        except Exception as e:
            self.test("Failover check in /api/gps/live", False, str(e))
    
    def test_alarm(self):
        """Test alarm notification (powerCut)"""
        self.log("\n=== Testing Alarm Notification ===", "info")
        
        if not self.vehicle_id:
            self.log("No vehicle ID, skipping alarm tests", "warn")
            return False
        
        # Send webhook with powerCut alarm
        try:
            url = f"{self.base_url}/api/gps/webhook"
            payload = self.traccar_payload(self.test_imei, -6.2100, 106.8100, 0.0, alarm="powerCut")
            headers = {"Content-Type": "application/json", "X-Gps-Token": self.secret}
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            self.test(
                "Webhook with powerCut alarm returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                result = response.json()
                alarm_info = result.get("alarm", {})
                self.test(
                    "Alarm info returned in webhook response",
                    alarm_info.get("alarm") == "powerCut",
                    f"Got {alarm_info}"
                )
        except Exception as e:
            self.test("Webhook with alarm", False, str(e))
        
        # Check notifications
        try:
            url = f"{self.base_url}/api/notifications"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            if response.status_code == 200:
                notifs = response.json()
                has_alarm = isinstance(notifs, list) and any(
                    n.get("type") == "gps_alarm" for n in notifs
                )
                self.test(
                    "GPS alarm notification created",
                    has_alarm,
                    f"No gps_alarm notification found"
                )
        except Exception as e:
            self.test("Check alarm notifications", False, str(e))
    
    def test_devices_endpoint(self):
        """Test /api/gps/devices endpoint"""
        self.log("\n=== Testing GPS Devices Endpoint ===", "info")
        
        try:
            url = f"{self.base_url}/api/gps/devices"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/gps/devices returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                devices = response.json()
                self.test(
                    "Devices endpoint returns array",
                    isinstance(devices, list),
                    f"Expected list, got {type(devices)}"
                )
                
                # Find our test vehicle
                if self.vehicle_id:
                    row = next((d for d in devices if d.get("vehicle_id") == self.vehicle_id), None)
                    if row:
                        self.test(
                            "Test vehicle has IMEI in devices list",
                            row.get("imei") == self.test_imei,
                            f"Expected {self.test_imei}, got {row.get('imei')}"
                        )
                        self.test(
                            "Device has online status",
                            "online" in row,
                            f"online field missing"
                        )
        except Exception as e:
            self.test("GET /api/gps/devices", False, str(e))
    
    def test_summary_endpoint(self):
        """Test /api/gps/summary endpoint"""
        self.log("\n=== Testing GPS Summary Endpoint ===", "info")
        
        try:
            url = f"{self.base_url}/api/gps/summary"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/gps/summary returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                summary = response.json()
                self.test(
                    "Summary has with_device count",
                    "with_device" in summary,
                    f"with_device missing"
                )
                self.test(
                    "Summary has online count",
                    "online" in summary,
                    f"online missing"
                )
                self.test(
                    "Summary with_device >= 1",
                    summary.get("with_device", 0) >= 1,
                    f"Expected >= 1, got {summary.get('with_device')}"
                )
        except Exception as e:
            self.test("GET /api/gps/summary", False, str(e))
    
    def test_device_removal(self):
        """Test device removal (unassign)"""
        self.log("\n=== Testing Device Removal ===", "info")
        
        if not self.vehicle_id:
            self.log("No vehicle ID, skipping device removal tests", "warn")
            return False
        
        # Test driver cannot remove device (403)
        try:
            url = f"{self.base_url}/api/gps/devices/{self.vehicle_id}"
            response = requests.delete(url, headers=self.headers("driver@demo.local"), timeout=10)
            
            self.test(
                "Driver CANNOT remove device (403)",
                response.status_code == 403,
                f"Expected 403, got {response.status_code}"
            )
        except Exception as e:
            self.test("Driver remove device RBAC", False, str(e))
        
        # Test owner can remove device
        try:
            url = f"{self.base_url}/api/gps/devices/{self.vehicle_id}"
            response = requests.delete(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "Owner can remove device",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                result = response.json()
                self.test(
                    "Remove returns ok=True",
                    result.get("ok") == True,
                    f"Got {result}"
                )
        except Exception as e:
            self.test("Owner remove device", False, str(e))
    
    def test_regression_locations_live(self):
        """Test regression: /api/locations/live still works"""
        self.log("\n=== Testing Regression: /api/locations/live ===", "info")
        
        try:
            url = f"{self.base_url}/api/locations/live"
            response = requests.get(url, headers=self.headers("owner@demo.local"), timeout=10)
            
            self.test(
                "GET /api/locations/live returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test(
                    "/api/locations/live returns array",
                    isinstance(data, list),
                    f"Expected list, got {type(data)}"
                )
                
                # Check if source field is present
                if data:
                    self.test(
                        "/api/locations/live includes 'source' field",
                        "source" in data[0],
                        f"source field missing"
                    )
        except Exception as e:
            self.test("Regression /api/locations/live", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*60, "info")
        self.log("E15 GPS Dual-Source Backend Test Suite", "info")
        self.log("="*60, "info")
        
        # Run tests in order
        if not self.test_auth():
            self.log("\n⚠️  Authentication failed. Cannot proceed with other tests.", "warn")
            return False
        
        if not self.test_get_vehicle():
            self.log("\n⚠️  No vehicles found. Cannot proceed with device tests.", "warn")
            return False
        
        # Core E15 tests
        self.test_webhook_auth()
        self.test_device_assignment()
        self.test_webhook_ingest()
        self.test_webhook_unmapped()
        self.test_gps_live()
        self.test_failover()
        self.test_alarm()
        self.test_devices_endpoint()
        self.test_summary_endpoint()
        self.test_device_removal()
        self.test_regression_locations_live()
        
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
    tester = E15TestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
