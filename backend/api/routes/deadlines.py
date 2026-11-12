"""Deadline CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Course, Deadline
from backend.schemas import DeadlineCreate, DeadlineOut, DeadlineUpdate

router = APIRouter(prefix="/api/deadlines", tags=["deadlines"])


def _require_course(db: Session, course_id: int) -> None:
    if db.get(Course, course_id) is None:
        raise HTTPException(status_code=404, detail="Cours introuvable")


@router.post("", response_model=DeadlineOut, status_code=status.HTTP_201_CREATED)
def create_deadline(payload: DeadlineCreate, db: Session = Depends(get_db)) -> Deadline:
    """Create a deadline associated with an existing course."""
    _require_course(db, payload.course_id)
    deadline = Deadline(**payload.model_dump())
    db.add(deadline)
    db.commit()
    db.refresh(deadline)
    return deadline


@router.get("", response_model=list[DeadlineOut])
def list_deadlines(course_id: int | None = None, db: Session = Depends(get_db)) -> list[Deadline]:
    """List deadlines in due-date order, optionally filtered by course."""
    statement = select(Deadline).order_by(Deadline.due_date)
    if course_id is not None:
        statement = statement.where(Deadline.course_id == course_id)
    return list(db.scalars(statement).all())


@router.get("/{deadline_id}", response_model=DeadlineOut)
def get_deadline(deadline_id: int, db: Session = Depends(get_db)) -> Deadline:
    """Retrieve a deadline by identifier."""
    deadline = db.get(Deadline, deadline_id)
    if deadline is None:
        raise HTTPException(status_code=404, detail="Échéance introuvable")
    return deadline


@router.put("/{deadline_id}", response_model=DeadlineOut)
def update_deadline(deadline_id: int, payload: DeadlineUpdate, db: Session = Depends(get_db)) -> Deadline:
    """Replace a deadline's editable fields."""
    deadline = db.get(Deadline, deadline_id)
    if deadline is None:
        raise HTTPException(status_code=404, detail="Échéance introuvable")
    _require_course(db, payload.course_id)
    for key, value in payload.model_dump().items():
        setattr(deadline, key, value)
    db.commit()
    db.refresh(deadline)
    return deadline


@router.delete("/{deadline_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deadline(deadline_id: int, db: Session = Depends(get_db)) -> Response:
    """Delete a deadline."""
    deadline = db.get(Deadline, deadline_id)
    if deadline is None:
        raise HTTPException(status_code=404, detail="Échéance introuvable")
    db.delete(deadline)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
