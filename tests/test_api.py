import pytest


class TestAuth:
    def test_register(self, client):
        resp = client.post("/api/v1/auth/register?email=new@user.com&password=pass123")
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["email"] == "new@user.com"

    def test_register_duplicate(self, client, auth_token):
        resp = client.post("/api/v1/auth/register?email=test@test.com&password=test123")
        assert resp.status_code == 400

    def test_login(self, client, auth_token):
        resp = client.post("/api/v1/auth/login?email=test@test.com&password=test123")
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["email"] == "test@test.com"

    def test_login_wrong_password(self, client):
        resp = client.post("/api/v1/auth/login?email=test@test.com&password=wrong")
        assert resp.status_code == 401

    def test_me(self, client, auth_headers):
        resp = client.get("/api/v1/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@test.com"
        assert "id" in data

    def test_me_unauthorized(self, client):
        resp = client.get("/api/v1/me")
        assert resp.status_code == 401


class TestRuns:
    def test_log_run(self, client, auth_headers):
        resp = client.post("/api/v1/runs?date=2026-06-10&distance_km=10&duration_min=50&rating=4", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] > 0
        assert data["run_count"] == 1

    def test_log_run_with_all_fields(self, client, auth_headers):
        resp = client.post(
            "/api/v1/runs?date=2026-06-10&distance_km=5&duration_min=25&rating=3"
            "&avg_hr=145&max_hr=175&elevation_gain=50&notes=test"
            "&tough_reasons=%5B%22heat%22%5D&run_type=easy"
            "&perceived_effort=5&pre_run_energy=4&sleep_hours=7.5&muscle_soreness=2",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_count"] == 1

    def test_get_empty_history(self, client, auth_headers):
        resp = client.get("/api/v1/runs", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["runs"] == []

    def test_get_history(self, client, auth_headers):
        client.post("/api/v1/runs?date=2026-06-10&distance_km=10&duration_min=50&rating=4", headers=auth_headers)
        resp = client.get("/api/v1/runs", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["runs"][0]["distance_km"] == 10.0

    def test_rate_run(self, client, auth_headers):
        r = client.post("/api/v1/runs?date=2026-06-10&distance_km=10&duration_min=50&rating=3", headers=auth_headers).json()
        resp = client.patch(f"/api/v1/runs/{r['id']}/rate?rating=5", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["rating"] == 5

    def test_rate_run_not_found(self, client, auth_headers):
        resp = client.patch("/api/v1/runs/999/rate?rating=5", headers=auth_headers)
        assert resp.status_code == 404


class TestForecast:
    def test_forecast(self, client, auth_headers):
        resp = client.get("/api/v1/forecast?lat=34.425&lon=8.784&time_pref=evening", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "days" in data
        assert len(data["days"]) == 7
        assert "location" in data
        assert data["location"]["lat"] == 34.425

    def test_forecast_with_plan(self, client, auth_headers):
        resp = client.get("/api/v1/forecast?lat=34.425&lon=8.784&time_pref=morning&planned_distance=10&planned_duration=50", headers=auth_headers)
        assert resp.status_code == 200


class TestGoals:
    def test_set_goals(self, client, auth_headers):
        resp = client.put("/api/v1/goals?weekly_distance_km=30&weekly_runs=4", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["weekly_distance_km"] == 30
        assert data["weekly_runs"] == 4

    def test_get_goals(self, client, auth_headers):
        client.put("/api/v1/goals?weekly_distance_km=30&weekly_runs=4", headers=auth_headers)
        resp = client.get("/api/v1/goals", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["weekly_distance_km"] == 30


class TestWellness:
    def test_wellness_no_runs(self, client, auth_headers):
        resp = client.get("/api/v1/wellness", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"

    def test_stats(self, client, auth_headers):
        resp = client.get("/api/v1/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "run_count" in data
        assert data["ready_for_ml"] is False


class TestNotifications:
    def test_register_device(self, client, auth_headers):
        resp = client.post("/api/v1/notifications/register?token=fake-token-123&platform=web", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_schedule_and_list(self, client, auth_headers):
        resp = client.post("/api/v1/notifications/schedule?date=2026-06-15&time=07:30&title=Morning+Run&body=Time+to+go", headers=auth_headers)
        assert resp.status_code == 200
        n = resp.json()
        assert n["date"] == "2026-06-15"
        assert n["time"] == "07:30"

        resp = client.get("/api/v1/notifications/scheduled", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["notifications"]) == 1

    def test_delete_scheduled(self, client, auth_headers):
        r = client.post("/api/v1/notifications/schedule?date=2026-06-15&title=Test&body=Test", headers=auth_headers).json()
        resp = client.delete(f"/api/v1/notifications/schedule/{r['id']}", headers=auth_headers)
        assert resp.status_code == 200

    def test_test_notification(self, client, auth_headers):
        resp = client.post("/api/v1/notifications/test", headers=auth_headers)
        assert resp.status_code == 200
        assert "ok" in resp.json()


class TestChat:
    def test_chat(self, client, auth_headers):
        resp = client.get("/api/v1/chat?q=How+is+the+weather+this+week%3F", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data


class TestAverages:
    def test_averages_no_runs(self, client, auth_headers):
        resp = client.get("/api/v1/averages", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "pace" in data

    def test_averages_with_runs(self, client, auth_headers):
        client.post("/api/v1/runs?date=2026-06-10&distance_km=10&duration_min=50&rating=4", headers=auth_headers)
        resp = client.get("/api/v1/averages", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["distance_km"] > 0


class TestDocs:
    def test_openapi(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        assert spec["info"]["title"] == "PaceClimate"
        assert spec["info"]["version"] == "1.0.0"
        assert "/api/v1/forecast" in spec["paths"]
        assert "/api/v1/auth/register" in spec["paths"]
        assert "/api/v1/runs" in spec["paths"]
        assert "/api/v1/chat" in spec["paths"]
        assert "/api/v1/notifications/schedule" in spec["paths"]
