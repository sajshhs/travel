#!/usr/bin/env python3
"""
Backend Test Suite for FASE 1 - Public Site Features
=====================================================
Tests:
- GET /api/public/theme → {preset, mode}
- GET /api/public/stats → {stats:[...]} with 4 items
- POST /api/public/trip-estimate → {total, breakdown[], days, note}
"""
import requests
import sys
import json

class Fase1TestSuite:
    def __init__(self, base_url="https://trip-route-buttons.preview.emergentagent.com"):
        self.base_url = base_url
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
    
    def test_public_theme(self):
        """Test GET /api/public/theme"""
        self.log("\n=== Testing GET /api/public/theme ===", "info")
        
        try:
            url = f"{self.base_url}/api/public/theme"
            response = requests.get(url, timeout=10)
            
            self.test(
                "GET /api/public/theme returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"Response: {json.dumps(data, indent=2)}", "info")
                
                # Check preset field
                self.test(
                    "Response has 'preset' field",
                    "preset" in data,
                    "preset field missing"
                )
                
                # Check preset value is one of the valid options
                valid_presets = ["azure", "midnight", "sunrise", "harbor"]
                self.test(
                    "preset is one of azure/midnight/sunrise/harbor",
                    data.get("preset") in valid_presets,
                    f"Got preset: {data.get('preset')}"
                )
                
                # Check mode field
                self.test(
                    "Response has 'mode' field",
                    "mode" in data,
                    "mode field missing"
                )
                
                # Check mode value is light or dark
                valid_modes = ["light", "dark"]
                self.test(
                    "mode is either light or dark",
                    data.get("mode") in valid_modes,
                    f"Got mode: {data.get('mode')}"
                )
                
        except Exception as e:
            self.test("GET /api/public/theme", False, str(e))
    
    def test_public_stats(self):
        """Test GET /api/public/stats"""
        self.log("\n=== Testing GET /api/public/stats ===", "info")
        
        try:
            url = f"{self.base_url}/api/public/stats"
            response = requests.get(url, timeout=10)
            
            self.test(
                "GET /api/public/stats returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"Response: {json.dumps(data, indent=2)}", "info")
                
                # Check stats field
                self.test(
                    "Response has 'stats' field",
                    "stats" in data,
                    "stats field missing"
                )
                
                stats = data.get("stats", [])
                
                # Check stats is an array
                self.test(
                    "stats is an array",
                    isinstance(stats, list),
                    f"stats is {type(stats)}"
                )
                
                # Check stats has 4 items
                self.test(
                    "stats has 4 items",
                    len(stats) == 4,
                    f"Expected 4 items, got {len(stats)}"
                )
                
                # Check each stat has required fields
                expected_keys = ["fleet", "destinations", "rating", "service"]
                found_keys = [s.get("key") for s in stats]
                
                for key in expected_keys:
                    self.test(
                        f"stats contains '{key}' item",
                        key in found_keys,
                        f"Missing {key} in stats"
                    )
                
                # Check fleet value is >= 1
                fleet_stat = next((s for s in stats if s.get("key") == "fleet"), None)
                if fleet_stat:
                    self.test(
                        "fleet value >= 1",
                        isinstance(fleet_stat.get("value"), (int, float)) and fleet_stat.get("value") >= 1,
                        f"Got fleet value: {fleet_stat.get('value')}"
                    )
                
                # Check destinations value is >= 1
                dest_stat = next((s for s in stats if s.get("key") == "destinations"), None)
                if dest_stat:
                    self.test(
                        "destinations value >= 1",
                        isinstance(dest_stat.get("value"), (int, float)) and dest_stat.get("value") >= 1,
                        f"Got destinations value: {dest_stat.get('value')}"
                    )
                
                # Check rating value is numeric
                rating_stat = next((s for s in stats if s.get("key") == "rating"), None)
                if rating_stat:
                    self.test(
                        "rating value is numeric",
                        isinstance(rating_stat.get("value"), (int, float)),
                        f"Got rating value: {rating_stat.get('value')} (type: {type(rating_stat.get('value'))})"
                    )
                
        except Exception as e:
            self.test("GET /api/public/stats", False, str(e))
    
    def test_trip_estimate(self):
        """Test POST /api/public/trip-estimate"""
        self.log("\n=== Testing POST /api/public/trip-estimate ===", "info")
        
        # Test with the exact payload from requirements
        payload = {
            "vehicle_type": "hiace_premio",
            "days": 2,
            "distance_km": 300,
            "destination": "Bromo",
            "pax": 4
        }
        
        try:
            url = f"{self.base_url}/api/public/trip-estimate"
            response = requests.post(url, json=payload, timeout=10)
            
            self.test(
                "POST /api/public/trip-estimate returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"Response: {json.dumps(data, indent=2)}", "info")
                
                # Check required fields
                required_fields = ["total", "breakdown", "days", "note"]
                for field in required_fields:
                    self.test(
                        f"Response has '{field}' field",
                        field in data,
                        f"{field} field missing"
                    )
                
                # Check total is numeric
                self.test(
                    "total is numeric",
                    isinstance(data.get("total"), (int, float)),
                    f"total is {type(data.get('total'))}"
                )
                
                # Check total is positive
                self.test(
                    "total is positive",
                    data.get("total", 0) > 0,
                    f"Got total: {data.get('total')}"
                )
                
                # Check breakdown is array
                self.test(
                    "breakdown is array",
                    isinstance(data.get("breakdown"), list),
                    f"breakdown is {type(data.get('breakdown'))}"
                )
                
                # Check breakdown has items
                breakdown = data.get("breakdown", [])
                self.test(
                    "breakdown has items",
                    len(breakdown) > 0,
                    f"breakdown is empty"
                )
                
                # Check days matches request
                self.test(
                    "days matches request",
                    data.get("days") == payload["days"],
                    f"Expected {payload['days']}, got {data.get('days')}"
                )
                
                # Check note is string
                self.test(
                    "note is string",
                    isinstance(data.get("note"), str),
                    f"note is {type(data.get('note'))}"
                )
                
        except Exception as e:
            self.test("POST /api/public/trip-estimate", False, str(e))
        
        # Test with different vehicle types
        self.log("\n=== Testing different vehicle types ===", "info")
        vehicle_types = ["hiace", "elf", "bus", "avanza"]
        
        for vtype in vehicle_types:
            try:
                payload = {
                    "vehicle_type": vtype,
                    "days": 2,
                    "distance_km": 300,
                    "destination": "Bali",
                    "pax": 4
                }
                url = f"{self.base_url}/api/public/trip-estimate"
                response = requests.post(url, json=payload, timeout=10)
                
                self.test(
                    f"trip-estimate works with vehicle_type={vtype}",
                    response.status_code == 200 and response.json().get("total", 0) > 0,
                    f"Got status {response.status_code}"
                )
            except Exception as e:
                self.test(f"trip-estimate with {vtype}", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*60, "info")
        self.log("FASE 1 Backend Test Suite - Public Site Features", "info")
        self.log("="*60, "info")
        
        # Run tests
        self.test_public_theme()
        self.test_public_stats()
        self.test_trip_estimate()
        
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
    tester = Fase1TestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
