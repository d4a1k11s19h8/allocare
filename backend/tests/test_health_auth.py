"""
test_health_auth.py — Health check, authentication, and registration tests.
"""
import pytest


# ═══════════════════════════════════════════════════════════════════
# 1. HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════

class TestHealthCheck:
    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_has_required_fields(self, client):
        data = client.get("/api/health").json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "data" in data
        assert "timestamp" in data

    def test_health_shows_seeded_data(self, client):
        data = client.get("/api/health").json()
        assert data["data"]["needs"] >= 12, "Expected at least 12 seeded needs"
        assert data["data"]["volunteers"] >= 54, "Expected at least 54 seeded volunteers"

    def test_health_gemini_key_status(self, client):
        data = client.get("/api/health").json()
        assert "gemini_api_key_configured" in data


# ═══════════════════════════════════════════════════════════════════
# 2. AUTHENTICATION — LOGIN
# ═══════════════════════════════════════════════════════════════════

class TestLogin:
    def test_login_valid_admin(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "admin@allocare.org",
            "password": "admin123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Login successful"
        assert data["user"]["email"] == "admin@allocare.org"

    def test_login_valid_volunteer(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "volunteer@allocare.org",
            "password": "vol123"
        })
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "volunteer"

    def test_login_wrong_password(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "admin@allocare.org",
            "password": "wrongpassword"
        })
        assert resp.status_code == 401

    def test_login_nonexistent_email(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "noone@nowhere.com",
            "password": "anything"
        })
        assert resp.status_code == 401

    def test_login_empty_email(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "",
            "password": "test"
        })
        assert resp.status_code == 401

    def test_login_no_password_hash_in_response(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "admin@allocare.org",
            "password": "admin123"
        })
        user = resp.json()["user"]
        assert "password_hash" not in user, "Password hash must NOT be returned"

    def test_login_missing_fields(self, client):
        resp = client.post("/api/auth/login", json={"email": "admin@allocare.org"})
        assert resp.status_code == 422  # Validation error


# ═══════════════════════════════════════════════════════════════════
# 3. AUTHENTICATION — REGISTRATION
# ═══════════════════════════════════════════════════════════════════

class TestRegistration:
    def test_register_new_org(self, client):
        import time
        email = f"testorg_{int(time.time())}@test.com"
        resp = client.post("/api/auth/register", json={
            "email": email,
            "password": "test123",
            "display_name": "Test NGO",
            "role": "organization"
        })
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "organization"

    def test_register_new_volunteer(self, client):
        import time
        email = f"testvol_{int(time.time())}@test.com"
        resp = client.post("/api/auth/register", json={
            "email": email,
            "password": "vol123",
            "display_name": "Test Volunteer",
            "role": "volunteer",
            "skills": ["cooking", "driving"],
            "zone": "Churu, Rajasthan"
        })
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "volunteer"

    def test_register_duplicate_email(self, client):
        # First registration
        client.post("/api/auth/register", json={
            "email": "dup@test.com",
            "password": "test123",
            "display_name": "Dup User",
            "role": "organization"
        })
        # Duplicate
        resp = client.post("/api/auth/register", json={
            "email": "dup@test.com",
            "password": "test123",
            "display_name": "Dup User 2",
            "role": "organization"
        })
        assert resp.status_code == 400

    def test_register_missing_required_fields(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "x@y.com"
        })
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════
# 4. DEMO SEED
# ═══════════════════════════════════════════════════════════════════

class TestDemoSeed:
    def test_seed_returns_success(self, client):
        resp = client.post("/api/demo/seed")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_seed_creates_data(self, client):
        client.post("/api/demo/seed")
        health = client.get("/api/health").json()
        assert health["data"]["needs"] >= 12
        assert health["data"]["volunteers"] >= 54
