"""Backend and Streamlit-adapter integration regression tests."""

from datetime import date, datetime, timedelta
from urllib.parse import urlsplit

import requests

from frontend import api_client as frontend_api


def create_course(client, name="Révisions"):
    response = client.post("/api/courses", json={"name": name})
    assert response.status_code == 201
    return response.json()


def test_health_courses_and_duplicate_name(api_client):
    assert api_client.get("/health").json() == {"status": "ok"}
    created = create_course(api_client)
    assert api_client.get("/api/courses").json()[0]["id"] == created["id"]
    duplicate = api_client.post("/api/courses", json={"name": "Révisions"})
    assert duplicate.status_code == 409


def test_deadline_accepts_iso_datetime(api_client):
    course = create_course(api_client)
    response = api_client.post(
        "/api/deadlines",
        json={
            "course_id": course["id"],
            "title": "Examen",
            "type": "exam",
            "due_date": "2027-01-15T09:30:00",
            "coefficient": 2.0,
        },
    )
    assert response.status_code == 201
    assert response.json()["due_date"].startswith("2027-01-15T09:30:00")


def test_invalid_deadline_and_availability_are_rejected(api_client):
    course = create_course(api_client)
    deadline = api_client.post(
        "/api/deadlines",
        json={
            "course_id": course["id"],
            "title": "Examen",
            "type": "invalid",
            "due_date": "not-a-date",
        },
    )
    availability = api_client.post(
        "/api/availability",
        json={"weekday": 7, "start_time": "12:00", "end_time": "09:00"},
    )
    assert deadline.status_code == 422
    assert availability.status_code == 422


def test_markdown_analysis_does_not_persist(api_client):
    course = create_course(api_client)
    result = api_client.post(
        "/api/documents/analyze",
        data={"course_id": str(course["id"])},
        files={"file": ("notes.md", b"# Chapitre\nQuelques mots de cours.", "text/markdown")},
    )
    assert result.status_code == 200
    assert result.json()[0]["title"] == "Chapitre"
    assert api_client.get(f"/api/chapters?course_id={course['id']}").json() == []


def test_frontend_adapter_full_connected_flow(api_client, monkeypatch):
    """Exercise upload, deadlines, availability, planning, status, and ICS via frontend calls."""

    def transport(method, url, **kwargs):
        parsed = urlsplit(url)
        result = api_client.request(
            method,
            parsed.path,
            params=kwargs.get("params"),
            json=kwargs.get("json"),
            data=kwargs.get("data"),
            files=kwargs.get("files"),
        )
        response = requests.Response()
        response.status_code = result.status_code
        response._content = result.content
        response.headers.update(result.headers)
        response.url = url
        response.reason = "OK" if result.status_code < 400 else "Error"
        return response

    monkeypatch.setattr(frontend_api, "API_BASE_URL", "http://testserver")
    monkeypatch.setattr(frontend_api, "API_PREFIX", "/api")
    monkeypatch.setattr(frontend_api.requests, "request", transport)

    course = frontend_api.upload_course("Analyse_notes.md", b"# Chapitre 1\nQuelques notions importantes.")
    courses = frontend_api.get_courses()
    assert courses[0]["name"] == course["name"]
    assert "Chapitre 1" in courses[0]["chapters"]

    deadline = frontend_api.add_deadline(course["id"], "Examen", date.today() + timedelta(days=5), 3)
    assert deadline["weight"] == 3.0
    assert deadline["date"] == (date.today() + timedelta(days=5)).isoformat()

    slot = {"weekday": datetime.now().weekday(), "start": "00:00", "end": "23:59"}
    frontend_api.save_availability([slot])
    assert frontend_api.get_availability()[0]["start"] == "00:00"

    sessions = frontend_api.generate_plan()
    assert sessions
    week = datetime.now().date().strftime("%G-W%V")
    visible_sessions = frontend_api.get_plan(week)
    assert visible_sessions and visible_sessions[0]["title"] == "Chapitre 1"
    updated = frontend_api.update_session(visible_sessions[0]["id"], True)
    assert updated["done"] is True
    assert b"BEGIN:VCALENDAR" in frontend_api.get_calendar()
