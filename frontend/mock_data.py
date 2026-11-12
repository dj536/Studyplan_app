from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone

import streamlit as st


def _new_demo_data():
    today = date.today()
    courses = [
        {
            "id": 1,
            "name": "Programmation Python",
            "chapters": ["Variables et types", "Fonctions", "Fichiers"],
            "estimated_hours": 12,
            "progress": 35,
        },
        {
            "id": 2,
            "name": "Bases de données",
            "chapters": ["SQL", "Modélisation", "Jointures"],
            "estimated_hours": 10,
            "progress": 20,
        },
        {
            "id": 3,
            "name": "Gestion de projet",
            "chapters": ["Planning", "Risques", "Agilité"],
            "estimated_hours": 8,
            "progress": 60,
        },
    ]
    deadlines = [
        {
            "id": 1,
            "course_id": 1,
            "title": "Examen Python",
            "date": (today + timedelta(days=3)).isoformat(),
            "weight": 3,
        },
        {
            "id": 2,
            "course_id": 2,
            "title": "Rendu SQL",
            "date": (today + timedelta(days=6)).isoformat(),
            "weight": 2,
        },
        {
            "id": 3,
            "course_id": 3,
            "title": "Présentation du projet",
            "date": (today + timedelta(days=12)).isoformat(),
            "weight": 1,
        },
    ]
    availability = [
        {"weekday": 0, "start": "09:00", "end": "12:00"},
        {"weekday": 2, "start": "14:00", "end": "17:00"},
        {"weekday": 4, "start": "09:00", "end": "12:00"},
    ]
    return {
        "courses": courses,
        "deadlines": deadlines,
        "availability": availability,
        "sessions": [],
        "next_course_id": 4,
        "next_deadline_id": 4,
        "next_session_id": 1,
    }


def _state():
    if "studyplan_demo_data" not in st.session_state:
        st.session_state.studyplan_demo_data = _new_demo_data()
    return st.session_state.studyplan_demo_data


def get_courses():
    return deepcopy(_state()["courses"])


def get_deadlines():
    return deepcopy(_state()["deadlines"])


def get_availability():
    return deepcopy(_state()["availability"])


def get_plan(week):
    return deepcopy(
        [
            session
            for session in _state()["sessions"]
            if datetime.fromisoformat(session["start"]).date().strftime("%G-W%V") == week
        ]
    )


def add_course(file_name, file_content):
    state = _state()
    name = file_name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
    chapters = []
    if file_name.lower().endswith((".md", ".markdown")):
        text = file_content.decode("utf-8", errors="replace")
        chapters = [
            line.lstrip("# ").strip()
            for line in text.splitlines()
            if line.startswith("#") and line.lstrip("# ").strip()
        ]
    if not chapters:
        chapters = ["Chapitres à extraire par le serveur"]

    course = {
        "id": state["next_course_id"],
        "name": name or "Nouveau cours",
        "chapters": chapters,
        "estimated_hours": 0,
        "progress": 0,
    }
    state["next_course_id"] += 1
    state["courses"].append(course)
    return deepcopy(course)


def add_deadline(course_id, title, deadline_date, weight):
    state = _state()
    deadline = {
        "id": state["next_deadline_id"],
        "course_id": course_id,
        "title": title,
        "date": deadline_date.isoformat(),
        "weight": weight,
    }
    state["next_deadline_id"] += 1
    state["deadlines"].append(deadline)
    return deepcopy(deadline)


def save_availability(slots):
    _state()["availability"] = deepcopy(slots)


def generate_plan():
    state = _state()
    today = date.today()
    available_days = {}
    for slot in state["availability"]:
        available_days.setdefault(slot["weekday"], []).append(slot)

    ordered_courses = sorted(
        state["courses"],
        key=lambda course: min(
            (
                deadline["date"]
                for deadline in state["deadlines"]
                if deadline["course_id"] == course["id"]
            ),
            default="9999-12-31",
        ),
    )
    new_sessions = []
    day_offset = 0
    course_index = 0
    days_left_in_week = 7 - today.weekday()
    while (
        course_index < len(ordered_courses)
        and day_offset < days_left_in_week
    ):
        session_date = today + timedelta(days=day_offset)
        slots = available_days.get(session_date.weekday(), [])
        if slots:
            slot = slots[0]
            start_time = time.fromisoformat(slot["start"])
            start = datetime.combine(session_date, start_time)
            end_time = time.fromisoformat(slot["end"])
            available_minutes = (
                datetime.combine(session_date, end_time) - start
            ).total_seconds() // 60
            if available_minutes < 15:
                day_offset += 1
                continue
            end = start + timedelta(minutes=min(60, int(available_minutes)))
            course = ordered_courses[course_index]
            new_sessions.append(
                {
                    "id": state["next_session_id"],
                    "course_id": course["id"],
                    "course_name": course["name"],
                    "title": course["chapters"][0] if course["chapters"] else course["name"],
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "done": False,
                }
            )
            state["next_session_id"] += 1
            course_index += 1
        day_offset += 1

    state["sessions"] = new_sessions
    return deepcopy(new_sessions)


def update_session(session_id, done):
    for session in _state()["sessions"]:
        if session["id"] == session_id:
            session["done"] = done
            return deepcopy(session)
    raise ValueError(f"Séance démo introuvable : {session_id}")


def get_calendar():
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//StudyPlan//FR"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for session in _state()["sessions"]:
        start = datetime.fromisoformat(session["start"])
        end = datetime.fromisoformat(session["end"])
        summary = f"{session['course_name']} - {session['title']}"
        summary = (
            summary.replace("\\", "\\\\")
            .replace(",", "\\,")
            .replace(";", "\\;")
            .replace("\n", "\\n")
        )
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:studyplan-session-{session['id']}@studyplan.local",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:{summary}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
