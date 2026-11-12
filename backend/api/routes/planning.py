"""Planning endpoints backed by the temporary Member 3 adapter."""

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Availability, Chapter, Deadline, StudySession
from backend.schemas import StudySessionOut
from backend.services.planning_service import generate_sessions

router = APIRouter(prefix="/api/planning", tags=["planning"])


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
