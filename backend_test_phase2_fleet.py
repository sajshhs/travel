#!/usr/bin/env python3
"""
Backend Test Suite for Phase 2 Fleet Features
==============================================
Tests fleet API endpoints with new fields: gallery, tour_scenes, specs, highlights, year, color, price_from
"""
import requests
import sys
import json

class FleetTestSuite:
    def __init__(self, base_url="https://trip-route-buttons.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.fleet_items = []
        
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
    
    def test_fleet_list(self):
        """Test GET /api/public/fleet returns list with new fields"""
        self.log("\n=== Testing GET /api/public/fleet ===", "info")
        
        try:
            url = f"{self.base_url}/api/public/fleet"
            response = requests.get(url, timeout=10)
            
            self.test(
                "GET /api/public/fleet returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.fleet_items = data
                
                self.test(
                    "Fleet list is an array",
                    isinstance(data, list),
                    f"Expected list, got {type(data)}"
                )
                
                if isinstance(data, list) and len(data) > 0:
                    self.log(f"Found {len(data)} fleet items", "info")
                    
                    # Test first item has required fields
                    first = data[0]
                    required_fields = ['id', 'code', 'name', 'type', 'capacity', 'features', 'photos']
                    new_fields = ['gallery', 'tour_scenes', 'specs', 'highlights', 'year', 'color', 'price_from']
                    
                    for field in required_fields:
                        self.test(
                            f"Fleet item has '{field}' field",
                            field in first,
                            f"Missing field: {field}"
                        )
                    
                    for field in new_fields:
                        self.test(
                            f"Fleet item has new '{field}' field",
                            field in first,
                            f"Missing new field: {field}"
                        )
                    
                    # Test field types
                    if 'gallery' in first:
                        self.test(
                            "gallery is a list",
                            isinstance(first.get('gallery'), list),
                            f"Expected list, got {type(first.get('gallery'))}"
                        )
                    
                    if 'tour_scenes' in first:
                        self.test(
                            "tour_scenes is a list",
                            isinstance(first.get('tour_scenes'), list),
                            f"Expected list, got {type(first.get('tour_scenes'))}"
                        )
                    
                    if 'specs' in first:
                        self.test(
                            "specs is a list",
                            isinstance(first.get('specs'), list),
                            f"Expected list, got {type(first.get('specs'))}"
                        )
                    
                    if 'highlights' in first:
                        self.test(
                            "highlights is a list",
                            isinstance(first.get('highlights'), list),
                            f"Expected list, got {type(first.get('highlights'))}"
                        )
                    
                    if 'capacity' in first:
                        self.test(
                            "capacity is a number",
                            isinstance(first.get('capacity'), (int, float)),
                            f"Expected number, got {type(first.get('capacity'))}"
                        )
                    
                    if 'year' in first and first.get('year') is not None:
                        self.test(
                            "year is a number",
                            isinstance(first.get('year'), (int, float)),
                            f"Expected number, got {type(first.get('year'))}"
                        )
                    
                    if 'price_from' in first and first.get('price_from') is not None:
                        self.test(
                            "price_from is a number",
                            isinstance(first.get('price_from'), (int, float)),
                            f"Expected number, got {type(first.get('price_from'))}"
                        )
                    
                    # Log sample data for inspection
                    self.log(f"Sample fleet item: {first.get('name')} ({first.get('code')})", "info")
                    self.log(f"  - Capacity: {first.get('capacity')}", "info")
                    self.log(f"  - Year: {first.get('year')}", "info")
                    self.log(f"  - Color: {first.get('color')}", "info")
                    self.log(f"  - Price from: {first.get('price_from')}", "info")
                    self.log(f"  - Gallery items: {len(first.get('gallery', []))}", "info")
                    self.log(f"  - Tour scenes: {len(first.get('tour_scenes', []))}", "info")
                    self.log(f"  - Specs: {len(first.get('specs', []))}", "info")
                    self.log(f"  - Highlights: {len(first.get('highlights', []))}", "info")
                else:
                    self.log("No fleet items found (empty list)", "warn")
                    
        except Exception as e:
            self.test("GET /api/public/fleet", False, str(e))
    
    def test_fleet_detail(self):
        """Test GET /api/public/fleet/{id} returns detail with all new fields"""
        self.log("\n=== Testing GET /api/public/fleet/{id} ===", "info")
        
        if not self.fleet_items:
            self.log("Skipping detail test - no fleet items available", "warn")
            return
        
        # Test first fleet item detail
        first_id = self.fleet_items[0].get('id')
        
        try:
            url = f"{self.base_url}/api/public/fleet/{first_id}"
            response = requests.get(url, timeout=10)
            
            self.test(
                f"GET /api/public/fleet/{first_id} returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                detail = response.json()
                
                # Test all required fields present
                required_fields = ['id', 'code', 'name', 'type', 'capacity', 'features', 'photos', 
                                   'gallery', 'tour_scenes', 'specs', 'highlights', 'year', 'color', 'price_from']
                
                for field in required_fields:
                    self.test(
                        f"Fleet detail has '{field}' field",
                        field in detail,
                        f"Missing field: {field}"
                    )
                
                # Test gallery structure if present
                gallery = detail.get('gallery', [])
                if gallery and len(gallery) > 0:
                    first_gallery = gallery[0]
                    if isinstance(first_gallery, dict):
                        self.test(
                            "Gallery item has 'url' field",
                            'url' in first_gallery,
                            f"Gallery item missing url: {first_gallery}"
                        )
                        self.log(f"Gallery has {len(gallery)} items", "info")
                
                # Test tour_scenes structure if present
                tour_scenes = detail.get('tour_scenes', [])
                if tour_scenes and len(tour_scenes) > 0:
                    first_scene = tour_scenes[0]
                    if isinstance(first_scene, dict):
                        scene_fields = ['id', 'label', 'panorama']
                        for field in scene_fields:
                            self.test(
                                f"Tour scene has '{field}' field",
                                field in first_scene,
                                f"Tour scene missing {field}: {first_scene}"
                            )
                        self.log(f"Tour has {len(tour_scenes)} scenes", "info")
                
                # Test specs structure if present
                specs = detail.get('specs', [])
                if specs and len(specs) > 0:
                    first_spec = specs[0]
                    if isinstance(first_spec, dict):
                        spec_fields = ['key', 'label', 'value']
                        for field in spec_fields:
                            self.test(
                                f"Spec item has '{field}' field",
                                field in first_spec,
                                f"Spec item missing {field}: {first_spec}"
                            )
                        self.log(f"Specs has {len(specs)} items", "info")
                
                # Test highlights
                highlights = detail.get('highlights', [])
                if highlights and len(highlights) > 0:
                    self.test(
                        "Highlights are strings",
                        all(isinstance(h, str) for h in highlights),
                        f"Some highlights are not strings"
                    )
                    self.log(f"Highlights has {len(highlights)} items", "info")
                
                self.log(f"Detail for: {detail.get('name')}", "info")
                
        except Exception as e:
            self.test(f"GET /api/public/fleet/{first_id}", False, str(e))
        
        # Test non-existent ID returns 404
        try:
            url = f"{self.base_url}/api/public/fleet/veh_nonexistent"
            response = requests.get(url, timeout=10)
            
            self.test(
                "GET /api/public/fleet/{invalid_id} returns 404",
                response.status_code == 404,
                f"Expected 404, got {response.status_code}"
            )
        except Exception as e:
            self.test("GET /api/public/fleet/{invalid_id}", False, str(e))
    
    def test_trip_estimate(self):
        """Test POST /api/public/trip-estimate still works"""
        self.log("\n=== Testing POST /api/public/trip-estimate ===", "info")
        
        try:
            url = f"{self.base_url}/api/public/trip-estimate"
            payload = {
                "vehicle_type": "hiace_premio",
                "days": 2,
                "distance_km": 300,
                "destination": "Bali",
                "pax": 4
            }
            response = requests.post(url, json=payload, timeout=10)
            
            self.test(
                "POST /api/public/trip-estimate returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                required_fields = ['breakdown', 'total', 'days', 'vehicle_type']
                for field in required_fields:
                    self.test(
                        f"Trip estimate has '{field}' field",
                        field in data,
                        f"Missing field: {field}"
                    )
                
                if 'total' in data:
                    self.test(
                        "Trip estimate total is a number",
                        isinstance(data.get('total'), (int, float)),
                        f"Expected number, got {type(data.get('total'))}"
                    )
                    self.log(f"Estimate total: Rp {data.get('total'):,.0f}", "info")
                
        except Exception as e:
            self.test("POST /api/public/trip-estimate", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*60, "info")
        self.log("Phase 2 Fleet Features Backend Test Suite", "info")
        self.log("="*60, "info")
        
        # Run tests in order
        self.test_fleet_list()
        self.test_fleet_detail()
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
    tester = FleetTestSuite()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
