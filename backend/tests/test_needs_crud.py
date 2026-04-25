"""
test_needs_crud.py: Need reports CRUD, filtering, and edge cases.
"""
import pytest


# ═══════════════════════════════════════════════════════════════════
# 1. LIST NEEDS
# ═══════════════════════════════════════════════════════════════════

class TestListNeeds:
    def test_list_all_needs(self, client):
        resp = client.get("/api/needs")
        assert resp.status_code == 200
        data = resp.json()
        assert "needs" in data
        assert "total" in data
        assert data["total"] >= 12

    def test_list_needs_with_limit(self, client):
        resp = client.get("/api/needs?limit=3")
        assert resp.status_code == 200
        assert len(resp.json()["needs"]) <= 3

    def test_filter_by_status_open(self, client):
        resp = client.get("/api/needs?status=open")
        assert resp.status_code == 200
        needs = resp.json()["needs"]
        for n in needs:
            assert n.get("status") == "open"

    def test_filter_by_issue_type_food(self, client):
        resp = client.get("/api/needs?issue_type=food")
        assert resp.status_code == 200
        needs = resp.json()["needs"]
        for n in needs:
            assert n.get("issue_type") == "food"

    def test_filter_by_urgency_critical(self, client):
        resp = client.get("/api/needs?urgency_label=critical")
        assert resp.status_code == 200
        needs = resp.json()["needs"]
        for n in needs:
            assert n.get("urgency_label") == "critical"

    def test_filter_all_types_returns_everything(self, client):
        all_resp = client.get("/api/needs")
        typed_resp = client.get("/api/needs?issue_type=all")
        assert typed_resp.json()["total"] == all_resp.json()["total"]

    def test_needs_sorted_by_urgency_desc(self, client):
        needs = client.get("/api/needs?limit=50").json()["needs"]
        scores = [n.get("urgency_score", 0) for n in needs]
        assert scores == sorted(scores, reverse=True), "Needs should be sorted by urgency descending"


# ═══════════════════════════════════════════════════════════════════
# 2. GET SINGLE NEED
# ═══════════════════════════════════════════════════════════════════

class TestGetNeed:
    def test_get_need_by_id(self, client, first_need_id):
        resp = client.get(f"/api/needs/{first_need_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == first_need_id

    def test_get_nonexistent_need(self, client):
        resp = client.get("/api/needs/FAKE_ID_999999")
        assert resp.status_code == 404

    def test_get_need_has_required_fields(self, client, first_need_id):
        data = client.get(f"/api/needs/{first_need_id}").json()
        required = ["id", "status", "urgency_score", "urgency_label"]
        for field in required:
            assert field in data, f"Missing required field: {field}"
        # raw_text or summary should exist
        assert "raw_text" in data or "summary" in data, "Need must have raw_text or summary"


# ═══════════════════════════════════════════════════════════════════
# 3. CREATE NEED
# ═══════════════════════════════════════════════════════════════════

class TestCreateNeed:
    def test_create_basic_need(self, client):
        resp = client.post("/api/needs", json={
            "raw_text": "Severe water shortage in Churu, Rajasthan. 500 families affected.",
            "source": "manual",
            "zone": "Churu, Rajasthan",
            "issue_type": "water",
            "severity_score": 8,
            "affected_count": 500
        })
        assert resp.status_code == 200
        assert "id" in resp.json()

    def test_create_need_minimal(self, client):
        """Only raw_text is truly required."""
        resp = client.post("/api/needs", json={
            "raw_text": "Help needed"
        })
        assert resp.status_code == 200

    def test_create_need_small_location_churu(self, client):
        """Edge case: small town like Churu, Rajasthan."""
        resp = client.post("/api/needs", json={
            "raw_text": "Drought in Churu district, Rajasthan. No water for 3 villages.",
            "zone": "Churu, Rajasthan",
            "issue_type": "water",
            "severity_score": 9,
            "affected_count": 1200
        })
        assert resp.status_code == 200

    def test_create_need_small_location_barmer(self, client):
        """Edge case: remote location: Barmer, Rajasthan."""
        resp = client.post("/api/needs", json={
            "raw_text": "Extreme heatwave, 45+ degrees. Elderly need shelter.",
            "zone": "Barmer, Rajasthan",
            "issue_type": "health",
            "severity_score": 9
        })
        assert resp.status_code == 200

    def test_create_need_northeast_location(self, client):
        """Edge case: Northeast India: Tawang, Arunachal Pradesh."""
        resp = client.post("/api/needs", json={
            "raw_text": "Landslide blocked road to Tawang. 200 people stranded.",
            "zone": "Tawang, Arunachal Pradesh",
            "issue_type": "safety",
            "severity_score": 10
        })
        assert resp.status_code == 200

    def test_create_need_unicode_hindi(self, client):
        """Edge case: Hindi/Devanagari text."""
        resp = client.post("/api/needs", json={
            "raw_text": "चुरू में भीषण सूखा। 500 परिवार प्रभावित।",
            "zone": "Churu, Rajasthan",
            "issue_type": "water"
        })
        assert resp.status_code == 200

    def test_create_need_very_long_text(self, client):
        """Edge case: very long description."""
        long_text = "Water crisis. " * 500  # ~7000 chars
        resp = client.post("/api/needs", json={
            "raw_text": long_text,
            "zone": "Mumbai"
        })
        assert resp.status_code == 200

    def test_create_need_empty_raw_text(self, client):
        """Edge case: empty raw_text should still work (field is present)."""
        resp = client.post("/api/needs", json={
            "raw_text": "",
            "zone": "Delhi"
        })
        # FastAPI allows empty string for str field
        assert resp.status_code == 200

    def test_created_need_appears_in_list(self, client):
        """Verify created need shows up in listing."""
        create_resp = client.post("/api/needs", json={
            "raw_text": "Unique test need XYZ123 for verification",
            "zone": "Jaisalmer, Rajasthan"
        })
        new_id = create_resp.json()["id"]
        get_resp = client.get(f"/api/needs/{new_id}")
        assert get_resp.status_code == 200
        assert "XYZ123" in get_resp.json()["raw_text"]
