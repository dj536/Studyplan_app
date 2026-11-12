"""Planning endpoints backed by the temporary Member 3 adapter."""

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Availability, Chapter, Deadline, StudySession
from backend.schemas import SessionStatusUpdate, StudySessionOut
from backend.services.planning_service import generate_sessions

router = APIRouter(prefix="/api/planning", tags=["planning"])
calendar_router = APIRouter(prefix="/api", tags=["planning"])


@router.post("/generate", response_model=list[StudySessionOut], status_code=status.HTTP_201_CREATED)
def generate_planning(db: Session = Depends(get_db)) -> list[StudySession]:
    """Replace planned sessions with placeholder sessions from the service."""
    chapters = list(db.scalars(select(Chapter).order_by(Chapter.id)).all())
    availability = list(db.scalars(select(Availability).order_by(Availability.weekday, Availability.start_time)).all())
    if not chapters or not availability:
        raise HTTPException(status_code=400, detail="Il faut au moins un chapitre et une disponibilité")
    deadlines = list(db.scalars(select(Deadline)).all())
    chapter_input = [
        {
            "id": chapter.id,
            "title": chapter.title,
            "course_id": chapter.course_id,
            "estimated_hours": chapter.estimated_hours,
            "completed_hours": chapter.completed_hours,
            "difficulty": chapter.difficulty,
        }
        for chapter in chapters
    ]
    deadline_input = [
        {"course_id": item.course_id, "due_date": item.due_date, "coefficient": item.coefficient}
        for item in deadlines
    ]
    availability_input = [
        {"weekday": item.weekday, "start_time": item.start_time, "end_time": item.end_time}
        for item in availability
    ]
    proposed = generate_sessions(chapter_input, deadline_input, availability_input)

    old_planned = list(db.scalars(select(StudySession).where(StudySession.status == "planned")).all())
    for session in old_planned:
        db.delete(session)
    db.flush()
    created = [
        StudySession(
            chapter_id=item["chapter_id"],
            start_datetime=item["start_datetime"],
            end_datetime=item["end_datetime"],
            status="planned",
        )
        for item in proposed
    ]
    db.add_all(created)
    db.commit()
    for session in created:
        db.refresh(session)
    return created


@router.get("", response_model=list[StudySessionOut])
def list_planning(week: date | None = None, db: Session = Depends(get_db)) -> list[StudySession]:
    """List sessions, optionally restricted to the Monday-starting week."""
    statement = select(StudySession).order_by(StudySession.start_datetime)
    if week is not None:
        monday = week - timedelta(days=week.weekday())
        start = datetime.combine(monday, time.min)
        end = start + timedelta(days=7)
        statement = statement.where(StudySession.start_datetime >= start, StudySession.start_datetime < end)
    return list(db.scalars(statement).all())


@router.patch("/sessions/{session_id}/status", response_model=StudySessionOut)
def update_session_status(
    session_id: int,
    payload: SessionStatusUpdate,
    db: Session = Depends(get_db),
) -> StudySession:
    """Change a session status and keep chapter completion hours in sync."""
    session = db.get(StudySession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Séance introuvable")

    duration_hours = (session.end_datetime - session.start_datetime).total_seconds() / 3600
    if session.status != "done" and payload.status == "done":
        session.chapter.completed_hours += duration_hours
    elif session.status == "done" and payload.status != "done":
        session.chapter.completed_hours = max(0.0, session.chapter.completed_hours - duration_hours)
    session.status = payload.status
    db.commit()
    db.refresh(session)
    return session


def _escape_ics_text(value: str) -> str:
    """Escape text according to the iCalendar TEXT value rules."""
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n")


@calendar_router.get("/plan.ics")
def get_calendar(db: Session = Depends(get_db)) -> Response:
    """Export all study sessions as an iCalendar attachment."""
    sessions = list(db.scalars(select(StudySession).order_by(StudySession.start_datetime)).all())
    if not sessions:
        raise HTTPException(status_code=400, detail="Aucune séance à exporter")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//StudyPlan//FR", "CALSCALE:GREGORIAN"]
    for session in sessions:
        chapter = session.chapter
        summary = _escape_ics_text(f"{chapter.course.name} - {chapter.title}")
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:studyplan-session-{session.id}@studyplan.local",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{session.start_datetime.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{session.end_datetime.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:{summary}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return Response(
        content="\r\n".join(lines) + "\r\n",
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="studyplan.ics"'},
    )
