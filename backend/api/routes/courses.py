"""Course CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Course
from backend.schemas import CourseCreate, CourseOut, CourseUpdate

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, db: Session = Depends(get_db)) -> Course:
    """Create a course, returning 409 when its name is already in use."""
    if db.scalar(select(Course.id).where(Course.name == payload.name)) is not None:
        raise HTTPException(status_code=409, detail="Un cours porte déjà ce nom")
    course = Course(**payload.model_dump())
    db.add(course)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Un cours porte déjà ce nom") from exc
    db.refresh(course)
    return course


@router.get("", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db)) -> list[Course]:
    """List all courses in creation order."""
    return list(db.scalars(select(Course).order_by(Course.id)).all())


@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: int, db: Session = Depends(get_db)) -> Course:
    """Retrieve one course by identifier."""
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Cours introuvable")
    return course


@router.put("/{course_id}", response_model=CourseOut)
def update_course(course_id: int, payload: CourseUpdate, db: Session = Depends(get_db)) -> Course:
    """Replace a course's editable fields."""
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Cours introuvable")
    duplicate = db.scalar(select(Course.id).where(Course.name == payload.name, Course.id != course_id))
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Un cours porte déjà ce nom")
    for key, value in payload.model_dump().items():
        setattr(course, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Un cours porte déjà ce nom") from exc
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int, db: Session = Depends(get_db)) -> Response:
    """Delete a course and its dependent records."""
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Cours introuvable")
    db.delete(course)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
