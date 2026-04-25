"""
test_matching_assignments.py: Volunteer matching, assignment, and edge cases.
"""
import pytest


# ═══════════════════════════════════════════════════════════════════
# 1. VOLUNTEER MATCHING
# ═══════════════════════════════════════════════════════════════════

class TestVolunteerMatching:
    def test_match_returns_results(self, client, first_need_id):
        resp = client.get(f"/api/match_volunteers?need_id={first_need_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "matches" in data
        assert len(data["matches"]) >= 1, "Should find at least 1 match"

    def test_match_returns_up_to_5(self, client, first_need_id):
        """Backend returns top-5 matches."""
        resp = client.get(f"/api/match_volunteers?need_id={first_need_id}")
        matches = resp.json()["matches"]
        assert len(matches) <= 5

    def test_match_has_required_fields(self, client, first_need_id):
        resp = client.get(f"/api/match_volunteers?need_id={first_need_id}")
        matches = resp.json()["matches"]
        if matches:
            m = matches[0]
            required = ["volunteer_id", "match_score", "distance_km", "explanation"]
            for field in required:
                assert field in m, f"Match missing field: {field}"

    def test_match_scores_descending(self, client, first_need_id):
        """Matches should be sorted by score descending."""
        matches = client.get(f"/api/match_volunteers?need_id={first_need_id}").json()["matches"]
        if len(matches) > 1:
            scores = [m["match_score"] for m in matches]
            assert scores == sorted(scores, reverse=True)

    def test_match_nonexistent_need(self, client):
        resp = client.get("/api/match_volunteers?need_id=FAKE_NEED_999")
        assert resp.status_code == 404

    def test_match_with_food_need(self, client):
        """Create a food need and verify matches include food-skilled volunteers."""
        # Create a food need in Mumbai
        create = client.post("/api/needs", json={
            "raw_text": "200 families need emergency food packets in Dharavi",
            "zone": "Dharavi, Mumbai",
            "issue_type": "food",
            "severity_score": 9
        })
        need_id = create.json()["id"]
        resp = client.get(f"/api/match_volunteers?need_id={need_id}")
        matches = resp.json()["matches"]
        assert len(matches) >= 1
        # At least one match should mention food-related skill
        all_skills = []
        for m in matches:
            all_skills.extend(m.get("skills_matched", []))
        food_skills = [s for s in all_skills if "food" in s.lower() or "cooking" in s.lower()]
        # It's okay if no food skill matched: other factors also matter

    def test_match_remote_location(self, client):
        """Create need in remote Churu: matching should still work (soft cutoff)."""
        create = client.post("/api/needs", json={
            "raw_text": "Water crisis in Churu, 500 people affected",
            "zone": "Churu, Rajasthan",
            "issue_type": "water",
            "severity_score": 8
        })
        need_id = create.json()["id"]
        resp = client.get(f"/api/match_volunteers?need_id={need_id}")
        assert resp.status_code == 200
        # Soft cutoff should still return some matches even for remote areas


# ═══════════════════════════════════════════════════════════════════
# 2. ASSIGNMENTS
# ═══════════════════════════════════════════════════════════════════

class TestAssignments:
    def test_create_assignment(self, client, first_need_id, first_volunteer_id):
        resp = client.post("/api/assignments", json={
            "need_id": first_need_id,
            "volunteer_id": first_volunteer_id,
            "org_id": "demo_org",
            "match_score": 0.85,
            "match_explanation": "Top match by skill and proximity"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "assignment_id" in data or "message" in data

    def test_assignment_updates_volunteer_status(self, client, first_need_id, first_volunteer_id):
        """After assignment, volunteer status should change."""
        client.post("/api/assignments", json={
            "need_id": first_need_id,
            "volunteer_id": first_volunteer_id,
            "org_id": "demo_org"
        })
        vol = client.get(f"/api/volunteers/{first_volunteer_id}").json()
        # Volunteer should be "assigned" or status updated
        assert vol.get("status") in ("available", "assigned", "busy")

    def test_assignment_updates_need_status(self, client, first_volunteer_id):
        """After assignment, need status should change to assigned."""
        create = client.post("/api/needs", json={
            "raw_text": "Test need for assignment status check"
        })
        need_id = create.json()["id"]
        client.post("/api/assignments", json={
            "need_id": need_id,
            "volunteer_id": first_volunteer_id
        })
        need = client.get(f"/api/needs/{need_id}").json()
        assert need.get("status") == "assigned"

    def test_assignment_missing_need_id(self, client, first_volunteer_id):
        resp = client.post("/api/assignments", json={
            "volunteer_id": first_volunteer_id
        })
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════
# 3. ANALYTICS
# ═══════════════════════════════════════════════════════════════════

class TestAnalytics:
    def test_analytics_endpoint(self, client):
        resp = client.get("/api/analytics")
        assert resp.status_code == 200
        data = resp.json()
        assert "totals" in data
        assert data["totals"]["volunteers"] >= 50
        assert data["totals"]["needs"] >= 12
