"""Temporary adapter for the independent planning module (Member 3)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import TypedDict


class ChapterInput(TypedDict):
    id: int
    title: str
    course_id: int
    estimated_hours: float
    completed_hours: float
    difficulty: int


class DeadlineInput(TypedDict):
    course_id: int
    due_date: datetime
    coefficient: float


class AvailabilityInput(TypedDict):
    weekday: int
    start_time: str
    end_time: str


class PlannedSession(TypedDict):
    chapter_id: int
    start_datetime: datetime
    end_datetime: datetime


def generate_sessions(
    chapters: list[ChapterInput],
    deadlines: list[DeadlineInput],
    availability: list[AvailabilityInput],
    *,
    now: datetime | None = None,
) -> list[PlannedSession]:
    """Return simple placeholder sessions using the planner's standard input.

    The implementation deliberately does not optimize priority or redistribute
    time; it creates at most one short illustrative slot per unfinished chapter.
    Replace this body when planner/scheduler.py is integrated.
    """
    del deadlines  # Accepted as part of the stable planner contract.
    if not chapters or not availability:
        return []

    current = now or datetime.now().replace(second=0, microsecond=0)
    sessions: list[PlannedSession] = []
    occupied: set[tuple[date, int]] = set()
    for chapter in chapters:
        remaining = max(0.0, chapter["estimated_hours"] - chapter["completed_hours"])
        if remaining <= 0:
            continue
        for offset in range(14):
            day = (current + timedelta(days=offset)).date()
            for slot in availability:
                if day.weekday() != slot["weekday"] or (day, slot["weekday"]) in occupied:
                    continue
                start_clock = time.fromisoformat(slot["start_time"])
                end_clock = time.fromisoformat(slot["end_time"])
                start = datetime.combine(day, start_clock)
                end_limit = datetime.combine(day, end_clock)
                if start < current:
                    start = current.replace(second=0, microsecond=0)
                    if start.date() != day:
                        continue
                duration = min(remaining, 1.0)
                end = start + timedelta(hours=duration)
                if end > end_limit:
                    continue
                sessions.append({"chapter_id": chapter["id"], "start_datetime": start, "end_datetime": end})
                occupied.add((day, slot["weekday"]))
                break
            if any(session["chapter_id"] == chapter["id"] for session in sessions):
                break
    return sessions
