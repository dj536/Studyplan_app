"""Frontend adapter for either demo data or the StudyPlan REST API."""

from datetime import date, datetime, time
import os
from pathlib import Path

import requests

try:
    from frontend import mock_data
except ImportError:
    import mock_data


API_BASE_URL = os.getenv("STUDYPLAN_API_URL", "").rstrip("/")
API_PREFIX = "" if API_BASE_URL.endswith("/api") else "/api"
REQUEST_TIMEOUT = 10


class ApiError(Exception):
    """Readable error returned by or while contacting the StudyPlan server."""


def using_mock_data():
    return not API_BASE_URL


def _request(method, path, **kwargs):
    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{API_PREFIX}{path}",
            timeout=REQUEST_TIMEOUT,
            **kwargs,
        )
        response.raise_for_status()
    except requests.HTTPError as error:
        response = error.response
        try:
            detail = response.json().get("detail")
        except (AttributeError, ValueError):
            detail = None
        message = detail if isinstance(detail, str) else f"Erreur HTTP {response.status_code}"
        raise ApiError(message) from error
    except requests.RequestException as error:
        raise ApiError(f"Le serveur StudyPlan est inaccessible : {error}") from error
    return response


def _json(response):
    try:
        return response.json()
    except ValueError as error:
        raise ApiError("Le serveur a renvoyé une réponse JSON invalide.") from error


def _list(response, label):
    data = _json(response)
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ApiError(f"Réponse invalide pour la liste {label}.")
    return data


def _normalize_deadline(item):
    due_date = datetime.fromisoformat(item["due_date"]).date().isoformat()
    return {
        **item,
        "date": due_date,
        "weight": item["coefficient"],
    }


def _normalize_availability(item):
    return {
        **item,
        "start": item["start_time"],
        "end": item["end_time"],
    }


def _normalize_sessions(items):
    chapters = _list(_request("GET", "/chapters"), "des chapitres")
    courses = _list(_request("GET", "/courses"), "des cours")
    chapter_by_id = {item["id"]: item for item in chapters}
    course_by_id = {item["id"]: item for item in courses}
    sessions = []
    for item in items:
        chapter = chapter_by_id.get(item["chapter_id"], {})
        course = course_by_id.get(chapter.get("course_id"), {})
        sessions.append(
            {
                **item,
                "title": chapter.get("title", "Chapitre"),
                "course_name": course.get("name", "Cours"),
                "start": item["start_datetime"],
                "end": item["end_datetime"],
                "done": item["status"] == "done",
            }
        )
    return sessions


def _monday_for_week(week):
    try:
        year, week_number = (int(part) for part in week.split("-W", maxsplit=1))
        return date.fromisocalendar(year, week_number, 1).isoformat()
    except (AttributeError, ValueError) as error:
        raise ApiError("La semaine doit être au format AAAA-Www.") from error


def get_courses():
    if using_mock_data():
        return mock_data.get_courses()
    courses = _list(_request("GET", "/courses"), "des cours")
    chapters = _list(_request("GET", "/chapters"), "des chapitres")
    chapters_by_course = {}
    for chapter in chapters:
        chapters_by_course.setdefault(chapter["course_id"], []).append(chapter)
    for course in courses:
        course_chapters = chapters_by_course.get(course["id"], [])
        estimated = sum(chapter["estimated_hours"] for chapter in course_chapters)
        completed = sum(chapter["completed_hours"] for chapter in course_chapters)
        course["chapters"] = [chapter["title"] for chapter in course_chapters]
        course["estimated_hours"] = estimated
        course["progress"] = round(completed / estimated * 100) if estimated else 0
    return courses


def upload_course(file_name, file_content):
    if using_mock_data():
        return mock_data.add_course(file_name, file_content)

    course_name = Path(file_name).stem.replace("_", " ").replace("-", " ").strip() or "Nouveau cours"
    course = _json(_request("POST", "/courses", json={"name": course_name}))
    try:
        proposals = _list(
            _request(
                "POST",
                "/documents/analyze",
                data={"course_id": course["id"]},
                files={"file": (file_name, file_content)},
            ),
            "des chapitres analysés",
        )
        parent_by_level = {}
        for proposal in proposals:
            level = proposal["level"]
            payload = {
                "course_id": course["id"],
                "title": proposal["title"],
                "estimated_hours": proposal["estimated_hours"],
                "difficulty": 3,
            }
            if level == 2 and 1 in parent_by_level:
                payload["parent_id"] = parent_by_level[1]
            created = _json(_request("POST", "/chapters", json=payload))
            parent_by_level[level] = created["id"]
            if level == 1:
                parent_by_level.pop(2, None)
    except (ApiError, KeyError) as error:
        try:
            _request("DELETE", f"/courses/{course['id']}")
        except ApiError:
            pass
        if isinstance(error, ApiError):
            raise
        raise ApiError("Réponse invalide après l'import du cours.") from error
    return course


def get_deadlines():
    if using_mock_data():
        return mock_data.get_deadlines()
    return [_normalize_deadline(item) for item in _list(_request("GET", "/deadlines"), "des échéances")]


def add_deadline(course_id, title, deadline_date, weight):
    if using_mock_data():
        return mock_data.add_deadline(course_id, title, deadline_date, weight)
    if isinstance(deadline_date, datetime):
        due_date = deadline_date
    else:
        due_date = datetime.combine(deadline_date, time.min)
    response = _request(
        "POST",
        "/deadlines",
        json={
            "course_id": course_id,
            "title": title,
            "type": "exam",
            "due_date": due_date.isoformat(),
            "coefficient": float(weight),
        },
    )
    return _normalize_deadline(_json(response))


def get_availability():
    if using_mock_data():
        return mock_data.get_availability()
    return [
        _normalize_availability(item)
        for item in _list(_request("GET", "/availability"), "des disponibilités")
    ]


def save_availability(slots):
    if using_mock_data():
        mock_data.save_availability(slots)
        return

    requested = {
        (int(slot["weekday"]), slot.get("start", slot.get("start_time")), slot.get("end", slot.get("end_time")))
        for slot in slots
    }
    current = _list(_request("GET", "/availability"), "des disponibilités")
    existing = {
        (item["weekday"], item["start_time"], item["end_time"]): item
        for item in current
    }
    for key, item in existing.items():
        if key not in requested:
            _request("DELETE", f"/availability/{item['id']}")
    for weekday, start_time, end_time in requested - existing.keys():
        _request(
            "POST",
            "/availability",
            json={"weekday": weekday, "start_time": start_time, "end_time": end_time},
        )


def generate_plan():
    if using_mock_data():
        return mock_data.generate_plan()
    items = _list(_request("POST", "/planning/generate"), "des séances")
    return _normalize_sessions(items)


def get_plan(week):
    if using_mock_data():
        return mock_data.get_plan(week)
    items = _list(
        _request("GET", "/planning", params={"week": _monday_for_week(week)}),
        "des séances",
    )
    return _normalize_sessions(items)


def update_session(session_id, done):
    if using_mock_data():
        return mock_data.update_session(session_id, done)
    response = _request(
        "PATCH",
        f"/planning/sessions/{session_id}/status",
        json={"status": "done" if done else "planned"},
    )
    return _normalize_sessions([_json(response)])[0]


def get_calendar():
    if using_mock_data():
        return mock_data.get_calendar()
    return _request("GET", "/plan.ics").content
