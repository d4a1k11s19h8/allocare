"""
test_roles.py: Role-based access control, volunteer assignments, and admin powers.
"""
import pytest
import time


# ═══════════════════════════════════════════════════════════════════
# 1. ROLE DEFINITIONS & LOGIN
# ═══════════════════════════════════════════════════════════════════

class TestRoleLogin:
    def test_admin_login_returns_org_role(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "admin@allocare.org",
            "password": "admin123"
        })
        assert resp.status_code == 200
        user = resp.json()["user"]
        assert user["role"] == "organization"

    def test_volunteer_login_returns_vol_role(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "volunteer@allocare.org",
            "password": "vol123"
        })
        assert resp.status_code == 200
        user = resp.json()["user"]
        assert user["role"] == "volunteer"

    def test_login_response_has_id(self, client):
        """Both roles must return a user ID for frontend routing."""
        for creds in [
            {"email": "admin@allocare.org", "password": "admin123"},
            {"email": "volunteer@allocare.org", "password": "vol123"},
        ]:
            resp = client.post("/api/auth/login", json=creds)
            user = resp.json()["user"]
            assert "id" in user or "_id" in user, f"User {creds['email']} missing 'id' or '_id'"

    def test_register_as_volunteer(self, client):
        email = f"testvol_role_{int(time.time())}@test.com"
        resp = client.post("/api/auth/register", json={
            "email": email,
            "password": "test123",
            "display_name": "Role Test Vol",
            "role": "volunteer",
            "skills": ["cooking", "driving"],
            "zone": "Mumbai"
        })
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "volunteer"

    def test_register_as_organization(self, client):
        email = f"testorg_role_{int(time.time())}@test.com"
        resp = client.post("/api/auth/register", json={
            "email": email,
            "password": "test123",
            "display_name": "Role Test NGO",
            "role": "organization"
        })
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "organization"


# ═══════════════════════════════════════════════════════════════════
# 2. ADMIN/ORG POWERS
# ═══════════════════════════════════════════════════════════════════

class TestAdminPowers:
    """Verify admin/org can do everything."""

    def test_admin_can_create_need(self, client):
        resp = client.post("/api/needs", json={
            "raw_text": "Admin created: Flood in Dharavi",
            "zone": "Dharavi, Mumbai",
            "issue_type": "water",
            "severity_score": 9
        })
        assert resp.status_code == 200

    def test_admin_can_view_all_needs(self, client):
        resp = client.get("/api/needs?limit=100")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_admin_can_view_all_volunteers(self, client):
        resp = client.get("/api/volunteers?limit=100")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 50

    def test_admin_can_match_volunteers(self, client, first_need_id):
        resp = client.get(f"/api/match_volunteers?need_id={first_need_id}")
        assert resp.status_code == 200
        assert "matches" in resp.json()

    def test_admin_can_assign_volunteer(self, client, first_need_id, first_volunteer_id):
        resp = client.post("/api/assignments", json={
            "need_id": first_need_id,
            "volunteer_id": first_volunteer_id,
            "org_id": "demo_org"
        })
        assert resp.status_code == 200

    def test_admin_can_view_analytics(self, client):
        resp = client.get("/api/analytics")
        assert resp.status_code == 200
        assert "totals" in resp.json()

    def test_admin_can_upload_csv(self, client):
        csv_data = "location,problem,severity\nMumbai,Test issue,5\n"
        resp = client.post(
            "/api/process_csv",
            files={"file": ("test.csv", csv_data.encode(), "text/csv")}
        )
        assert resp.status_code == 200

    def test_admin_can_process_report(self, client):
        resp = client.post("/api/process_report", json={
            "raw_text": "Severe drought in Churu, 500 affected",
            "source": "manual"
        })
        assert resp.status_code == 200

    def test_admin_can_sms_receive(self, client):
        resp = client.post("/api/sms/receive", json={
            "sender": "+919999999999",
            "message": "NEED Mumbai food 100 families hungry"
        })
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# 3. VOLUNTEER ASSIGNMENTS ENDPOINT
# ═══════════════════════════════════════════════════════════════════

class TestVolunteerAssignments:
    """Test the new GET /api/volunteers/{vol_id}/assignments endpoint."""

    def test_get_assignments_for_volunteer(self, client, first_volunteer_id):
        resp = client.get(f"/api/volunteers/{first_volunteer_id}/assignments")
        assert resp.status_code == 200
        data = resp.json()
        assert "assignments" in data
        assert "total" in data
        assert isinstance(data["assignments"], list)

    def test_assignments_for_seeded_volunteer(self, client, first_volunteer_id):
        """A seeded volunteer should have an accessible assignments endpoint."""
        resp = client.get(f"/api/volunteers/{first_volunteer_id}/assignments")
        assert resp.status_code == 200
        assert "assignments" in resp.json()
        assert "total" in resp.json()

    def test_assignment_appears_after_creation(self, client):
        """Assign a volunteer -> their assignments endpoint should show it."""
        # Create a need
        need_resp = client.post("/api/needs", json={
            "raw_text": "Test need for assignment flow",
            "zone": "Mumbai"
        })
        need_id = need_resp.json()["id"]

        # Get first volunteer
        vols = client.get("/api/volunteers?limit=1").json()["volunteers"]
        vol_id = vols[0]["id"]

        # Assign
        client.post("/api/assignments", json={
            "need_id": need_id,
            "volunteer_id": vol_id
        })

        # Check assignments
        resp = client.get(f"/api/volunteers/{vol_id}/assignments")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

        # Verify enriched need data
        assignment = data["assignments"][-1]  # Latest
        assert assignment["need"] is not None
        assert assignment["need"]["zone"] == "Mumbai"

    def test_assignment_has_enriched_need_fields(self, client, first_volunteer_id):
        """Assignment response includes full need context."""
        # Create & assign
        need_resp = client.post("/api/needs", json={
            "raw_text": "Flood near gateway of India",
            "zone": "Colaba, Mumbai",
            "issue_type": "water",
            "severity_score": 9
        })
        need_id = need_resp.json()["id"]
        client.post("/api/assignments", json={
            "need_id": need_id,
            "volunteer_id": first_volunteer_id
        })

        resp = client.get(f"/api/volunteers/{first_volunteer_id}/assignments")
        assignments = resp.json()["assignments"]
        latest = [a for a in assignments if a["need"] and a["need"]["id"] == need_id]
        assert len(latest) >= 1

        need_data = latest[0]["need"]
        required_fields = ["id", "summary", "zone", "issue_type", "urgency_score",
                           "urgency_label", "affected_count", "required_skills", "status"]
        for field in required_fields:
            assert field in need_data, f"Missing need field: {field}"

    def test_nonexistent_volunteer_assignments(self, client):
        resp = client.get("/api/volunteers/FAKE_VOL_XXXX/assignments")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# 4. VOLUNTEER TASK COMPLETION FLOW
# ═══════════════════════════════════════════════════════════════════

class TestVolunteerTaskFlow:
    """End-to-end: Admin assigns -> Volunteer completes -> Points awarded."""

    def test_full_task_lifecycle(self, client):
        """Full lifecycle: create need → assign volunteer → complete task → check impact."""
        # 1. Create need
        need = client.post("/api/needs", json={
            "raw_text": "Lifecycle test: water crisis in Churu",
            "zone": "Churu, Rajasthan",
            "issue_type": "water",
            "severity_score": 8,
            "affected_count": 200
        }).json()
        need_id = need["id"]

        # 2. Get a volunteer
        vols = client.get("/api/volunteers?limit=1").json()["volunteers"]
        vol_id = vols[0]["id"]
        initial_points = vols[0].get("impact_points", 0)

        # 3. Admin assigns
        assign_resp = client.post("/api/assignments", json={
            "need_id": need_id,
            "volunteer_id": vol_id,
            "match_score": 0.92,
            "match_explanation": "Top match for water crisis skills"
        })
        assert assign_resp.status_code == 200
        assignment_id = assign_resp.json()["assignment_id"]

        # 4. Volunteer sees the task
        tasks = client.get(f"/api/volunteers/{vol_id}/assignments").json()
        matching = [t for t in tasks["assignments"] if t["assignment_id"] == assignment_id]
        assert len(matching) == 1
        assert matching[0]["status"] == "pending"
        assert matching[0]["need"]["zone"] == "Churu, Rajasthan"

        # 5. Volunteer completes
        complete_resp = client.post("/api/complete_task", json={
            "assignment_id": assignment_id
        })
        assert complete_resp.status_code == 200
        scorecard = complete_resp.json()["scorecard"]
        assert scorecard["points_earned"] > 0

        # 6. Verify volunteer status reset
        vol_after = client.get(f"/api/volunteers/{vol_id}").json()
        assert vol_after["status"] == "available"

        # 7. Verify need resolved
        need_after = client.get(f"/api/needs/{need_id}").json()
        assert need_after["status"] == "resolved"


# ═══════════════════════════════════════════════════════════════════
# 5. FRONTEND ROLE UI (HTML checks)
# ═══════════════════════════════════════════════════════════════════

class TestFrontendRoleUI:
    """Verify the HTML has role-based UI elements."""

    def test_html_has_my_tasks_view(self, client):
        html = client.get("/").text
        assert 'id="view-my-tasks"' in html

    def test_html_has_volunteer_nav_item(self, client):
        html = client.get("/").text
        assert 'nav-volunteer-only' in html
        assert 'data-view="my-tasks"' in html

    def test_html_has_admin_nav_items(self, client):
        html = client.get("/").text
        assert 'nav-admin-only' in html

    def test_html_has_volunteer_profile_section(self, client):
        html = client.get("/").text
        assert 'vol-profile-name' in html
        assert 'vol-impact-points' in html

    def test_html_has_volunteer_demo_login_hint(self, client):
        html = client.get("/").text
        assert 'volunteer@allocare.org' in html
        assert 'vol123' in html

    def test_html_has_admin_demo_login_hint(self, client):
        html = client.get("/").text
        assert 'admin@allocare.org' in html
        assert 'admin123' in html

    def test_auth_js_has_role_enforcement(self, client):
        js = client.get("/js/auth.js").text
        assert 'nav-volunteer-only' in js
        assert 'nav-admin-only' in js
        assert 'volunteer-restrictions' in js

    def test_dashboard_js_has_my_tasks(self, client):
        js = client.get("/js/dashboard.js").text
        assert 'renderMyTasks' in js
        assert 'createTaskCard' in js
        assert 'completeMyTask' in js
