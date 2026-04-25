"""
test_routing_nearby.py: OSRM routing, nearby volunteers, and edge cases.
"""
import pytest
import math


# ═══════════════════════════════════════════════════════════════════
# 1. ROUTE API
# ═══════════════════════════════════════════════════════════════════

class TestRouteAPI:
    def test_route_mumbai_short(self, client):
        """Short intra-city route: Dharavi to Kurla (~4km)."""
        resp = client.get("/api/route?from_lat=19.045&from_lng=72.857&to_lat=19.073&to_lng=72.879")
        assert resp.status_code == 200
        data = resp.json()
        assert data["distance_km"] > 0
        assert data["duration_min"] > 0
        assert data["source"] in ("osrm", "haversine")

    def test_route_delhi_to_agra(self, client):
        """Long inter-city route: Delhi to Agra (~230km)."""
        resp = client.get("/api/route?from_lat=28.628&from_lng=77.217&to_lat=27.175&to_lng=78.042")
        assert resp.status_code == 200
        data = resp.json()
        assert data["distance_km"] > 150, "Delhi-Agra should be > 150km road"
        assert data["duration_min"] > 60, "Should take > 1 hour"

    def test_route_churu_to_jaipur(self, client):
        """Small town route: Churu, Rajasthan to Jaipur (~270km)."""
        resp = client.get("/api/route?from_lat=28.305&from_lng=74.964&to_lat=26.912&to_lng=75.787")
        assert resp.status_code == 200
        data = resp.json()
        assert data["distance_km"] > 100

    def test_route_same_point(self, client):
        """Edge case: origin == destination (0km)."""
        resp = client.get("/api/route?from_lat=19.045&from_lng=72.857&to_lat=19.045&to_lng=72.857")
        assert resp.status_code == 200
        data = resp.json()
        assert data["distance_km"] <= 0.5, "Same point should be ~0km"

    def test_route_returns_polyline(self, client):
        """Route must include a polyline array for map display."""
        resp = client.get("/api/route?from_lat=19.045&from_lng=72.857&to_lat=19.073&to_lng=72.879")
        data = resp.json()
        assert "polyline" in data
        assert isinstance(data["polyline"], list)
        if data["source"] == "osrm":
            assert len(data["polyline"]) > 2, "OSRM polyline should have multiple points"

    def test_route_has_quality_score(self, client):
        """Route must include a quality score."""
        resp = client.get("/api/route?from_lat=19.045&from_lng=72.857&to_lat=19.073&to_lng=72.879")
        data = resp.json()
        assert "route_quality" in data
        assert 0 <= data["route_quality"] <= 1.0

    def test_route_invalid_coords(self, client):
        """Edge case: invalid/extreme coordinates."""
        resp = client.get("/api/route?from_lat=0&from_lng=0&to_lat=0&to_lng=0")
        assert resp.status_code == 200  # Should not crash, should fallback

    def test_route_cross_country(self, client):
        """Edge case: Mumbai to Guwahati (very long)."""
        resp = client.get("/api/route?from_lat=19.076&from_lng=72.877&to_lat=26.144&to_lng=91.736")
        assert resp.status_code == 200
        data = resp.json()
        assert data["distance_km"] > 1500


# ═══════════════════════════════════════════════════════════════════
# 2. NEARBY VOLUNTEERS API
# ═══════════════════════════════════════════════════════════════════

class TestNearbyVolunteers:
    def test_nearby_mumbai_default_radius(self, client):
        """Find volunteers near Mumbai with default 50km radius."""
        resp = client.get("/api/nearby_volunteers?lat=19.044&lng=72.855")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 10, "Should find 10+ volunteers near Mumbai"

    def test_nearby_mumbai_small_radius(self, client):
        """Small radius: 5km around Dharavi."""
        resp = client.get("/api/nearby_volunteers?lat=19.044&lng=72.855&radius_km=5")
        assert resp.status_code == 200
        data = resp.json()
        # Even small radius should find some volunteers in dense area
        assert data["total"] >= 1

    def test_nearby_delhi(self, client):
        """Find volunteers near Delhi."""
        resp = client.get("/api/nearby_volunteers?lat=28.628&lng=77.217&radius_km=30")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3, "Should find 3+ volunteers near Delhi"

    def test_nearby_bangalore(self, client):
        resp = client.get("/api/nearby_volunteers?lat=12.971&lng=77.594&radius_km=30")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2

    def test_nearby_kolkata(self, client):
        resp = client.get("/api/nearby_volunteers?lat=22.572&lng=88.363&radius_km=30")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2

    def test_nearby_guwahati(self, client):
        """Northeast India coverage test."""
        resp = client.get("/api/nearby_volunteers?lat=26.144&lng=91.736&radius_km=50")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_nearby_churu_rajasthan(self, client):
        """Small town: Churu, Rajasthan. Likely no volunteers within 50km."""
        resp = client.get("/api/nearby_volunteers?lat=28.305&lng=74.964&radius_km=50")
        assert resp.status_code == 200
        # It's okay if there are 0: tests that the API works for remote areas

    def test_nearby_churu_large_radius(self, client):
        """Churu with 300km radius should find at least Jaipur/Delhi volunteers."""
        resp = client.get("/api/nearby_volunteers?lat=28.305&lng=74.964&radius_km=300")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1, "300km radius from Churu should reach Delhi or Jaipur volunteers"

    def test_nearby_ocean_no_volunteers(self, client):
        """Edge case: point in the ocean (Arabian Sea)."""
        resp = client.get("/api/nearby_volunteers?lat=15.0&lng=68.0&radius_km=50")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_nearby_sorted_by_distance(self, client):
        """Results must be sorted by ascending distance."""
        resp = client.get("/api/nearby_volunteers?lat=19.044&lng=72.855&radius_km=50")
        vols = resp.json()["volunteers"]
        if len(vols) > 1:
            distances = [v["distance_km"] for v in vols]
            assert distances == sorted(distances), "Results must be sorted by distance"

    def test_nearby_response_fields(self, client):
        """Each volunteer in results has required fields."""
        resp = client.get("/api/nearby_volunteers?lat=19.044&lng=72.855&radius_km=50")
        vols = resp.json()["volunteers"]
        if vols:
            v = vols[0]
            required = ["id", "display_name", "lat", "lng", "skills", "distance_km", "road_distance_km"]
            for field in required:
                assert field in v, f"Missing field: {field}"

    def test_nearby_road_distance_greater_than_straight(self, client):
        """Road distance should always be ≥ straight-line distance."""
        resp = client.get("/api/nearby_volunteers?lat=19.044&lng=72.855&radius_km=50")
        for v in resp.json()["volunteers"]:
            assert v["road_distance_km"] >= v["distance_km"], \
                f"Road distance ({v['road_distance_km']}) < straight-line ({v['distance_km']})"

    def test_nearby_zero_radius(self, client):
        """Edge case: 0km radius should return 0 or 1 volunteers."""
        resp = client.get("/api/nearby_volunteers?lat=19.044&lng=72.855&radius_km=0")
        assert resp.status_code == 200
        assert resp.json()["total"] <= 1


# ═══════════════════════════════════════════════════════════════════
# 3. HAVERSINE UNIT TESTS (direct module import)
# ═══════════════════════════════════════════════════════════════════

class TestHaversine:
    def setup_method(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from routing_client import _haversine
        self.haversine = _haversine

    def test_same_point_zero(self):
        assert self.haversine(19.0, 72.8, 19.0, 72.8) == 0.0

    def test_mumbai_to_pune(self):
        """Mumbai to Pune ≈ 150km straight line."""
        d = self.haversine(19.076, 72.877, 18.520, 73.857)
        assert 100 < d < 170, f"Mumbai-Pune straight line should be ~150km, got {d}"

    def test_delhi_to_mumbai(self):
        """Delhi to Mumbai ≈ 1150km straight line."""
        d = self.haversine(28.628, 77.217, 19.076, 72.877)
        assert 1050 < d < 1250, f"Delhi-Mumbai should be ~1150km, got {d}"

    def test_churu_to_jaipur(self):
        """Churu to Jaipur ≈ 195km straight line."""
        d = self.haversine(28.305, 74.964, 26.912, 75.787)
        assert 150 < d < 250, f"Churu-Jaipur should be ~195km, got {d}"

    def test_symmetry(self):
        """Distance A→B == distance B→A."""
        d1 = self.haversine(19.076, 72.877, 28.628, 77.217)
        d2 = self.haversine(28.628, 77.217, 19.076, 72.877)
        assert abs(d1 - d2) < 0.01
