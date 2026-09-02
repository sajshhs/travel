#!/usr/bin/env python3
"""
Backend Test Suite for FASE 3 - Destinasi Immersif + Scroll-Story + Peta Rute
===============================================================================
Tests public destinations endpoints with new Phase 3 fields:
- intro, highlights, itinerary, route_points, faqs, best_time, lat, lng, gallery, hotel_recommendations
"""
import requests
import sys
import json

class Fase3DestinationsTest:
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
    
    def test_destinations_list(self):
        """Test GET /api/public/destinations returns list with Phase 3 fields"""
        self.log("\n=== Testing GET /api/public/destinations (List) ===", "info")
        
        try:
            url = f"{self.base_url}/api/public/destinations"
            response = requests.get(url, timeout=10)
            
            self.test(
                "GET /api/public/destinations returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code != 200:
                return False
            
            data = response.json()
            
            self.test(
                "Destinations list is an array",
                isinstance(data, list),
                f"Expected list, got {type(data)}"
            )
            
            self.test(
                "Destinations list has at least 4 items",
                len(data) >= 4,
                f"Expected 4+, got {len(data)}"
            )
            
            if len(data) > 0:
                dest = data[0]
                
                # Check basic fields
                basic_fields = ["id", "slug", "name", "region", "description"]
                for field in basic_fields:
                    self.test(
                        f"Destination has '{field}' field",
                        field in dest,
                        f"Missing field: {field}"
                    )
                
                # Check Phase 3 new fields exist (may be empty)
                phase3_fields = ["intro", "highlights", "itinerary", "route_points", 
                                "faqs", "best_time", "lat", "lng", "gallery", "hotel_recommendations"]
                for field in phase3_fields:
                    has_field = field in dest
                    self.test(
                        f"Destination has Phase 3 field '{field}'",
                        has_field,
                        f"Missing Phase 3 field: {field}"
                    )
            
            return True
            
        except Exception as e:
            self.test("GET /api/public/destinations", False, str(e))
            return False
    
    def test_destination_detail(self, slug):
        """Test GET /api/public/destinations/{slug} with Phase 3 fields populated"""
        self.log(f"\n=== Testing GET /api/public/destinations/{slug} (Detail) ===", "info")
        
        try:
            url = f"{self.base_url}/api/public/destinations/{slug}"
            response = requests.get(url, timeout=10)
            
            self.test(
                f"GET /api/public/destinations/{slug} returns 200",
                response.status_code == 200,
                f"Got {response.status_code}"
            )
            
            if response.status_code != 200:
                return False
            
            d = response.json()
            
            # Check basic fields
            self.test(
                f"{slug}: has 'name' field",
                "name" in d and d["name"],
                f"Missing or empty name"
            )
            
            self.test(
                f"{slug}: has 'slug' field matching",
                d.get("slug") == slug,
                f"Expected slug '{slug}', got '{d.get('slug')}'"
            )
            
            # Check Phase 3 fields populated
            self.test(
                f"{slug}: has 'intro' or 'description'",
                bool(d.get("intro") or d.get("description")),
                f"Both intro and description are empty"
            )
            
            # Check highlights (array with at least 1 item)
            highlights = d.get("highlights", [])
            self.test(
                f"{slug}: has highlights array",
                isinstance(highlights, list),
                f"highlights is not a list: {type(highlights)}"
            )
            
            self.test(
                f"{slug}: has at least 1 highlight",
                len(highlights) >= 1,
                f"Expected 1+, got {len(highlights)}"
            )
            
            if len(highlights) > 0:
                h = highlights[0]
                self.test(
                    f"{slug}: highlight has 'title' and 'desc'",
                    "title" in h and "desc" in h,
                    f"Highlight missing title or desc: {h}"
                )
            
            # Check itinerary (array with at least 1 item)
            itinerary = d.get("itinerary", [])
            self.test(
                f"{slug}: has itinerary array",
                isinstance(itinerary, list),
                f"itinerary is not a list: {type(itinerary)}"
            )
            
            self.test(
                f"{slug}: has at least 1 itinerary item",
                len(itinerary) >= 1,
                f"Expected 1+, got {len(itinerary)}"
            )
            
            if len(itinerary) > 0:
                it = itinerary[0]
                self.test(
                    f"{slug}: itinerary has 'day', 'title', 'desc'",
                    "day" in it and "title" in it and "desc" in it,
                    f"Itinerary missing required fields: {it}"
                )
            
            # Check route_points (array with at least 2 items for map)
            route_points = d.get("route_points", [])
            self.test(
                f"{slug}: has route_points array",
                isinstance(route_points, list),
                f"route_points is not a list: {type(route_points)}"
            )
            
            self.test(
                f"{slug}: has at least 2 route_points (for map)",
                len(route_points) >= 2,
                f"Expected 2+, got {len(route_points)}"
            )
            
            if len(route_points) > 0:
                rp = route_points[0]
                self.test(
                    f"{slug}: route_point has 'name', 'lat', 'lng'",
                    "name" in rp and "lat" in rp and "lng" in rp,
                    f"Route point missing required fields: {rp}"
                )
                
                self.test(
                    f"{slug}: route_point lat/lng are numbers",
                    isinstance(rp.get("lat"), (int, float)) and isinstance(rp.get("lng"), (int, float)),
                    f"lat/lng not numbers: lat={rp.get('lat')}, lng={rp.get('lng')}"
                )
            
            # Check FAQs (array with at least 1 item)
            faqs = d.get("faqs", [])
            self.test(
                f"{slug}: has faqs array",
                isinstance(faqs, list),
                f"faqs is not a list: {type(faqs)}"
            )
            
            self.test(
                f"{slug}: has at least 1 FAQ",
                len(faqs) >= 1,
                f"Expected 1+, got {len(faqs)}"
            )
            
            if len(faqs) > 0:
                faq = faqs[0]
                self.test(
                    f"{slug}: FAQ has 'q' and 'a'",
                    "q" in faq and "a" in faq,
                    f"FAQ missing q or a: {faq}"
                )
            
            # Check optional fields
            self.test(
                f"{slug}: has 'best_time' field",
                "best_time" in d,
                f"Missing best_time field"
            )
            
            self.test(
                f"{slug}: has 'lat' and 'lng' coordinates",
                "lat" in d and "lng" in d,
                f"Missing lat or lng"
            )
            
            # Check hotel_recommendations (optional, but should be array)
            hotels = d.get("hotel_recommendations", [])
            self.test(
                f"{slug}: hotel_recommendations is array",
                isinstance(hotels, list),
                f"hotel_recommendations is not a list: {type(hotels)}"
            )
            
            if len(hotels) > 0:
                hotel = hotels[0]
                self.test(
                    f"{slug}: hotel has 'name', 'rating', 'price_range'",
                    "name" in hotel and "rating" in hotel and "price_range" in hotel,
                    f"Hotel missing required fields: {hotel}"
                )
            
            # Check gallery (optional, but should be array)
            gallery = d.get("gallery", [])
            self.test(
                f"{slug}: gallery is array",
                isinstance(gallery, list),
                f"gallery is not a list: {type(gallery)}"
            )
            
            return True
            
        except Exception as e:
            self.test(f"GET /api/public/destinations/{slug}", False, str(e))
            return False
    
    def test_all_destinations_detail(self):
        """Test all seeded destinations have Phase 3 fields"""
        self.log("\n=== Testing All Seeded Destinations ===", "info")
        
        # Expected seeded destinations (from seed data)
        expected_slugs = ["bali", "bromo", "yogyakarta", "dieng"]
        
        for slug in expected_slugs:
            self.test_destination_detail(slug)
    
    def test_trip_estimate(self):
        """Test POST /api/public/trip-estimate (regression)"""
        self.log("\n=== Testing POST /api/public/trip-estimate (Regression) ===", "info")
        
        try:
            url = f"{self.base_url}/api/public/trip-estimate"
            payload = {
                "vehicle_type": "hiace_premio",
                "days": 2,
                "distance_km": 300,
                "destination": "Bromo",
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
                
                self.test(
                    "Trip estimate has 'total' field",
                    "total" in data,
                    f"Missing total field"
                )
                
                self.test(
                    "Trip estimate has 'breakdown' array",
                    "breakdown" in data and isinstance(data["breakdown"], list),
                    f"Missing or invalid breakdown"
                )
                
                self.test(
                    "Trip estimate total is positive number",
                    isinstance(data.get("total"), (int, float)) and data.get("total") > 0,
                    f"Total is not positive: {data.get('total')}"
                )
        
        except Exception as e:
            self.test("POST /api/public/trip-estimate", False, str(e))
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*70, "info")
        self.log("FASE 3 - Destinasi Immersif Backend Test Suite", "info")
        self.log("="*70, "info")
        
        # Run tests
        self.test_destinations_list()
        self.test_all_destinations_detail()
        self.test_trip_estimate()
        
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
        self.log(f"\nSuccess Rate: {success_rate:.1f}%", "pass" if success_rate == 100 else "warn")
        
        return self.tests_failed == 0


def main():
    tester = Fase3DestinationsTest()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
