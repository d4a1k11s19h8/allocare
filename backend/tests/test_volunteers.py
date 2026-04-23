"""
test_volunteers.py — Volunteer CRUD, pan-India coverage, and edge cases.
"""
import pytest


# ═══════════════════════════════════════════════════════════════════
# 1. LIST VOLUNTEERS
# ═══════════════════════════════════════════════════════════════════

class TestListVolunteers:
    def test_list_all_volunteers(self, client):
        resp = client.get("/api/volunteers?limit=100")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 54, f"Expected 54+ volunteers, got {data['total']}"

    def test_list_with_limit(self, client):
        resp = client.get("/api/volunteers?limit=5")
        assert resp.status_code == 200
        assert len(resp.json()["volunteers"]) <= 5

    def test_volunteers_have_coordinates(self, client):
        """Every seeded volunteer must have lat/lng."""
        vols = client.get("/api/volunteers?limit=100").json()["volunteers"]
        # Exclude dynamically registered test volunteers (no lat/lng)
        seeded = [v for v in vols if not v["display_name"].startswith(("Role Test", "New Vol", "Test "))]
        no_coords = [v["display_name"] for v in seeded if not v.get("lat") or not v.get("lng")]
        assert len(no_coords) == 0, f"Volunteers missing coordinates: {no_coords}"

    def test_volunteers_have_skills(self, client):
        """Every seeded volunteer must have at least one skill."""
        vols = client.get("/api/volunteers?limit=100").json()["volunteers"]
        # Exclude dynamically registered test volunteers
        seeded = [v for v in vols if not v["display_name"].startswith(("Role Test", "New Vol", "Test "))]
        no_skills = [v["display_name"] for v in seeded if not v.get("skills")]
        assert len(no_skills) == 0, f"Volunteers missing skills: {no_skills}"


# ═══════════════════════════════════════════════════════════════════
# 2. PAN-INDIA COVERAGE
# ═══════════════════════════════════════════════════════════════════

class TestPanIndiaCoverage:
    """Verify volunteers exist across all major Indian regions."""

    @pytest.fixture
    def all_volunteers(self, client):
        return client.get("/api/volunteers?limit=200").json()["volunteers"]

    def _volunteers_in_bbox(self, vols, lat_min, lat_max, lng_min, lng_max):
        """Count volunteers within a geographic bounding box."""
        return [v for v in vols
                if lat_min <= v.get("lat", 0) <= lat_max
                and lng_min <= v.get("lng", 0) <= lng_max]

    def test_coverage_mumbai(self, all_volunteers):
        """Mumbai metro area (18.8-19.3°N, 72.7-73.0°E)."""
        vols = self._volunteers_in_bbox(all_volunteers, 18.8, 19.3, 72.7, 73.0)
        assert len(vols) >= 8, f"Expected 8+ Mumbai volunteers, got {len(vols)}"

    def test_coverage_delhi_ncr(self, all_volunteers):
        """Delhi NCR (28.3-28.9°N, 76.8-77.5°E)."""
        vols = self._volunteers_in_bbox(all_volunteers, 28.3, 28.9, 76.8, 77.5)
        assert len(vols) >= 3, f"Expected 3+ Delhi volunteers, got {len(vols)}"

    def test_coverage_bangalore(self, all_volunteers):
        """Bangalore (12.8-13.1°N, 77.4-77.8°E)."""
        vols = self._volunteers_in_bbox(all_volunteers, 12.8, 13.1, 77.4, 77.8)
        assert len(vols) >= 2, f"Expected 2+ Bangalore volunteers, got {len(vols)}"

    def test_coverage_kolkata(self, all_volunteers):
        """Kolkata (22.4-22.7°N, 88.2-88.5°E)."""
        vols = self._volunteers_in_bbox(all_volunteers, 22.4, 22.7, 88.2, 88.5)
        assert len(vols) >= 2, f"Expected 2+ Kolkata volunteers, got {len(vols)}"

    def test_coverage_chennai(self, all_volunteers):
        """Chennai (12.9-13.2°N, 80.1-80.4°E)."""
        vols = self._volunteers_in_bbox(all_volunteers, 12.9, 13.2, 80.1, 80.4)
        assert len(vols) >= 1, f"Expected 1+ Chennai volunteer, got {len(vols)}"

    def test_coverage_hyderabad(self, all_volunteers):
        """Hyderabad (17.3-17.5°N, 78.3-78.6°E)."""
        vols = self._volunteers_in_bbox(all_volunteers, 17.3, 17.5, 78.3, 78.6)
        assert len(vols) >= 1, f"Expected 1+ Hyderabad volunteer"

    def test_coverage_northeast(self, all_volunteers):
        """Northeast India — Guwahati area (26.0-26.3°N, 91.5-91.9°E)."""
        vols = self._volunteers_in_bbox(all_volunteers, 26.0, 26.3, 91.5, 91.9)
        assert len(vols) >= 1, f"Expected 1+ NE volunteer"

    def test_coverage_south_india(self, all_volunteers):
        """Entire South India (below 16°N)."""
        vols = [v for v in all_volunteers if v.get("lat", 99) < 16.0]
        assert len(vols) >= 6, f"Expected 6+ South India volunteers, got {len(vols)}"

    def test_coverage_north_india(self, all_volunteers):
        """North India (above 26°N)."""
        vols = [v for v in all_volunteers if v.get("lat", 0) > 26.0]
        assert len(vols) >= 8, f"Expected 8+ North India volunteers, got {len(vols)}"


# ═══════════════════════════════════════════════════════════════════
# 3. GET SINGLE VOLUNTEER
# ═══════════════════════════════════════════════════════════════════

class TestGetVolunteer:
    def test_get_volunteer_by_id(self, client, first_volunteer_id):
        resp = client.get(f"/api/volunteers/{first_volunteer_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "display_name" in data
        assert "skills" in data

    def test_get_nonexistent_volunteer(self, client):
        resp = client.get("/api/volunteers/FAKE_VOL_999")
        assert resp.status_code == 404
