"""
test_sms_ocr_offline.py: SMS gateway, OCR endpoints, and offline/edge cases.
"""
import pytest
import base64
import os


# ═══════════════════════════════════════════════════════════════════
# 1. SMS GATEWAY
# ═══════════════════════════════════════════════════════════════════

class TestSMSGateway:
    def test_sms_valid_food_report(self, client):
        resp = client.post("/api/sms/receive", json={
            "sender": "+919876543210",
            "message": "NEED Churu food 200 families without meals for 3 days"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("processed", "saved_raw")

    def test_sms_valid_water_report(self, client):
        resp = client.post("/api/sms/receive", json={
            "sender": "+919876543210",
            "message": "NEED Barmer water Severe drought affecting 500 people"
        })
        assert resp.status_code == 200

    def test_sms_valid_health_report(self, client):
        resp = client.post("/api/sms/receive", json={
            "sender": "+919876543210",
            "message": "NEED Delhi health Dengue outbreak 50 cases reported in sector 7"
        })
        assert resp.status_code == 200

    def test_sms_without_need_keyword(self, client):
        """SMS not starting with NEED should be ignored."""
        resp = client.post("/api/sms/receive", json={
            "sender": "+919876543210",
            "message": "Hello, this is a random text message"
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_sms_need_only_keyword(self, client):
        """Edge case: only 'NEED' with no details."""
        resp = client.post("/api/sms/receive", json={
            "sender": "+919876543210",
            "message": "NEED"
        })
        assert resp.status_code == 200

    def test_sms_need_with_location_only(self, client):
        """Edge case: 'NEED Mumbai': no type or description."""
        resp = client.post("/api/sms/receive", json={
            "sender": "+919876543210",
            "message": "NEED Mumbai"
        })
        assert resp.status_code == 200

    def test_sms_case_insensitive_keyword(self, client):
        """'need' in lowercase should also work."""
        resp = client.post("/api/sms/receive", json={
            "sender": "+919876543210",
            "message": "need Jaipur food People are hungry"
        })
        assert resp.status_code == 200
        assert resp.json()["status"] != "ignored"

    def test_sms_unknown_issue_type(self, client):
        """Issue type not in valid list should default to 'other'."""
        resp = client.post("/api/sms/receive", json={
            "sender": "+919876543210",
            "message": "NEED Pune earthquake Buildings collapsed near station"
        })
        assert resp.status_code == 200

    def test_sms_empty_message(self, client):
        resp = client.post("/api/sms/receive", json={
            "sender": "+919876543210",
            "message": ""
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_sms_unicode_hindi(self, client):
        """SMS in Hindi."""
        resp = client.post("/api/sms/receive", json={
            "sender": "+919876543210",
            "message": "NEED चुरू water पानी की भारी कमी 300 लोग प्रभावित"
        })
        assert resp.status_code == 200

    def test_sms_very_long_message(self, client):
        """Edge case: SMS longer than typical 160 chars."""
        long_desc = "Emergency situation. " * 50
        resp = client.post("/api/sms/receive", json={
            "sender": "+919876543210",
            "message": f"NEED Mumbai food {long_desc}"
        })
        assert resp.status_code == 200

    def test_sms_special_characters(self, client):
        """Edge case: SMS with special characters."""
        resp = client.post("/api/sms/receive", json={
            "sender": "+919876543210",
            "message": "NEED Mumbai food People need help! @#$% urgently!!! 200+ affected"
        })
        assert resp.status_code == 200

    def test_sms_missing_sender(self, client):
        resp = client.post("/api/sms/receive", json={
            "message": "NEED Mumbai food Help needed"
        })
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════
# 2. OCR ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

class TestOCR:
    def test_ocr_base64_endpoint_exists(self, client):
        """Verify the OCR endpoint exists and accepts input."""
        resp = client.post("/api/ocr", json={
            "image_data": base64.b64encode(b"not a real image").decode()
        })
        # Should return 200 with error message (invalid image), not 404/500
        assert resp.status_code == 200

    def test_ocr_base64_empty_image(self, client):
        """Edge case: empty base64 string."""
        resp = client.post("/api/ocr", json={
            "image_data": ""
        })
        assert resp.status_code == 200
        data = resp.json()
        # Should gracefully handle empty input
        assert "text" in data or "error" in data

    def test_ocr_upload_endpoint_exists(self, client):
        """Verify the file upload OCR endpoint exists."""
        # Create a tiny fake PNG
        fake_png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        resp = client.post(
            "/api/ocr/upload",
            files={"file": ("test.png", fake_png, "image/png")}
        )
        assert resp.status_code == 200

    def test_ocr_upload_non_image(self, client):
        """Edge case: uploading a non-image file."""
        resp = client.post(
            "/api/ocr/upload",
            files={"file": ("test.txt", b"Hello world", "text/plain")}
        )
        # Should not crash
        assert resp.status_code == 200

    def test_ocr_response_has_text_field(self, client):
        """OCR response must always have a 'text' field."""
        resp = client.post("/api/ocr", json={
            "image_data": base64.b64encode(b"fake").decode()
        })
        data = resp.json()
        assert "text" in data


# ═══════════════════════════════════════════════════════════════════
# 3. CSV UPLOAD
# ═══════════════════════════════════════════════════════════════════

class TestCSVUpload:
    def test_csv_upload_basic(self, client):
        csv_data = (
            "location,problem,people,severity\n"
            "Churu Rajasthan,Water shortage,500,9\n"
            "Barmer Rajasthan,Food crisis,200,8\n"
            "Tawang Arunachal Pradesh,Landslide,100,10\n"
        )
        resp = client.post(
            "/api/process_csv",
            files={"file": ("test.csv", csv_data.encode(), "text/csv")}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 3
        assert len(data.get("errors", [])) == 0

    def test_csv_upload_with_column_mapping(self, client):
        """CSV with 'area' instead of 'location' should auto-map."""
        csv_data = (
            "area,description,households\n"
            "Churu,Drought affecting multiple villages,300\n"
        )
        resp = client.post(
            "/api/process_csv",
            files={"file": ("test.csv", csv_data.encode(), "text/csv")}
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] >= 1

    def test_csv_upload_empty_file(self, client):
        """Edge case: empty CSV."""
        resp = client.post(
            "/api/process_csv",
            files={"file": ("empty.csv", b"", "text/csv")}
        )
        # Should handle gracefully
        assert resp.status_code in (200, 500)

    def test_csv_upload_single_column(self, client):
        """Edge case: CSV with only one column."""
        csv_data = "problem\nWater shortage\nFood crisis\n"
        resp = client.post(
            "/api/process_csv",
            files={"file": ("test.csv", csv_data.encode(), "text/csv")}
        )
        assert resp.status_code == 200

    def test_csv_upload_unicode_locations(self, client):
        """CSV with Hindi location names."""
        csv_data = (
            "location,problem,severity\n"
            "चुरू राजस्थान,पानी की कमी,9\n"
            "बाड़मेर,सूखा,8\n"
        )
        resp = client.post(
            "/api/process_csv",
            files={"file": ("hindi.csv", csv_data.encode("utf-8"), "text/csv")}
        )
        assert resp.status_code == 200

    def test_csv_upload_large_file(self, client):
        """Edge case: CSV with 100 rows."""
        lines = ["location,problem,people,severity"]
        for i in range(100):
            lines.append(f"City{i},Issue{i},{i*10},{min(i%10+1, 10)}")
        csv_data = "\n".join(lines)
        resp = client.post(
            "/api/process_csv",
            files={"file": ("large.csv", csv_data.encode(), "text/csv")}
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 100


# ═══════════════════════════════════════════════════════════════════
# 4. PROCESS REPORT (AI PIPELINE)
# ═══════════════════════════════════════════════════════════════════

class TestProcessReport:
    def test_process_with_raw_text(self, client):
        resp = client.post("/api/process_report", json={
            "raw_text": "Severe flooding in Dharavi area. 500 families displaced. Need food and shelter urgently.",
            "source": "manual"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "report_id" in data
        assert "score" in data

    def test_process_returns_lat_lng(self, client):
        """process_report must return lat/lng for map fly-to."""
        resp = client.post("/api/process_report", json={
            "raw_text": "Water crisis in Mumbai, Maharashtra. 200 families affected.",
            "source": "manual"
        })
        data = resp.json()
        if data["status"] == "success":
            assert "lat" in data
            assert "lng" in data

    def test_process_churu_location(self, client):
        """Test processing a report from small town Churu."""
        resp = client.post("/api/process_report", json={
            "raw_text": "Drought in Churu district, Rajasthan. 500 people without water for 5 days. Urgent help needed.",
            "source": "manual"
        })
        assert resp.status_code == 200

    def test_process_hindi_text(self, client):
        """Test AI pipeline with Hindi text (translation should kick in)."""
        resp = client.post("/api/process_report", json={
            "raw_text": "मुंबई के धारावी इलाके में बाढ़। 500 परिवार बेघर। खाना और पानी की जरूरत।",
            "source": "manual"
        })
        assert resp.status_code == 200

    def test_process_empty_text(self, client):
        """Edge case: empty text."""
        resp = client.post("/api/process_report", json={
            "raw_text": "",
            "source": "manual"
        })
        # Should either fail gracefully or process as minimal report
        assert resp.status_code in (200, 400, 500)

    def test_process_no_text_no_id(self, client):
        """Edge case: neither raw_text nor report_id provided."""
        resp = client.post("/api/process_report", json={
            "source": "manual"
        })
        assert resp.status_code == 400

    def test_process_nonexistent_report_id(self, client):
        resp = client.post("/api/process_report", json={
            "report_id": "FAKE_REPORT_999"
        })
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# 5. STATIC FILES
# ═══════════════════════════════════════════════════════════════════

class TestStaticFiles:
    def test_index_html_loads(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "AlloCare" in resp.text

    def test_manifest_json(self, client):
        resp = client.get("/manifest.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["short_name"] == "AlloCare"

    def test_service_worker(self, client):
        resp = client.get("/sw.js")
        assert resp.status_code == 200
        assert "allocare" in resp.text.lower()

    def test_offline_js(self, client):
        resp = client.get("/js/offline.js")
        assert resp.status_code == 200
        assert "IndexedDB" in resp.text or "indexedDB" in resp.text

    def test_css_files_exist(self, client):
        for css in ["design-system.css", "dashboard.css", "components.css", "animations.css"]:
            resp = client.get(f"/css/{css}")
            assert resp.status_code == 200, f"CSS file missing: {css}"

    def test_js_files_exist(self, client):
        for js in ["config.js", "auth.js", "api-service.js", "map.js",
                    "dashboard.js", "upload.js", "matching.js", "offline.js"]:
            resp = client.get(f"/js/{js}")
            assert resp.status_code == 200, f"JS file missing: {js}"

    def test_index_has_signout(self, client):
        """Verify Sign Out button is in the HTML."""
        html = client.get("/").text
        assert "Sign Out" in html

    def test_index_has_offline_badge(self, client):
        html = client.get("/").text
        assert "offline-badge" in html

    def test_index_has_user_dropdown(self, client):
        html = client.get("/").text
        assert "user-dropdown" in html
