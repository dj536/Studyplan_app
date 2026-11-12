import os

import requests

import mock_data


API_BASE_URL = os.getenv("STUDYPLAN_API_URL", "").rstrip("/")
REQUEST_TIMEOUT = 10


class ApiError(Exception):
    """Erreur lisible renvoyée par le serveur StudyPlan."""


def using_mock_data():
    return not API_BASE_URL


def _request(method, path, **kwargs):
    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{path}",
            timeout=REQUEST_TIMEOUT,
            **kwargs,
        )
        response.raise_for_status()
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


def get_courses():
    if using_mock_data():
        return mock_data.get_courses()
    return _list(_request("GET", "/courses"), "des cours")


def upload_course(file_name, file_content):
    if using_mock_data():
        return mock_data.add_course(file_name, file_content)
    response = _request(
        "POST",
        "/courses",
        files={"file": (file_name, file_content)},
    )
    course = _json(response)
    if not isinstance(course, dict):
        raise ApiError("Réponse invalide après l'import du cours.")
    return course


def get_deadlines():
    if using_mock_data():
        return mock_data.get_deadlines()
    return _list(_request("GET", "/deadlines"), "des échéances")


def add_deadline(course_id, title, deadline_date, weight):
    payload = {
        "course_id": course_id,
        "title": title,
        "date": deadline_date.isoformat(),
        "weight": weight,
    }
    if using_mock_data():
        return mock_data.add_deadline(course_id, title, deadline_date, weight)
    _request("POST", "/deadlines", json=payload)


def get_availability():
    if using_mock_data():
        return mock_data.get_availability()
    return []


def save_availability(slots):
    if using_mock_data():
        mock_data.save_availability(slots)
        return
    _request("PUT", "/availability", json={"slots": slots})


def generate_plan():
    if using_mock_data():
        return mock_data.generate_plan()
    return _list(_request("POST", "/plan/generate"), "des séances")


def get_plan(week):
    if using_mock_data():
        return mock_data.get_plan(week)
    return _list(_request("GET", "/plan", params={"week": week}), "des séances")


def update_session(session_id, done):
    if using_mock_data():
        return mock_data.update_session(session_id, done)
    _request("PATCH", f"/sessions/{session_id}", json={"done": done})


def get_calendar():
    if using_mock_data():
        return mock_data.get_calendar()
    return _request("GET", "/plan.ics").content
