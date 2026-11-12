"""Chapter CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Chapter, Course, Document
from backend.schemas import ChapterCreate, ChapterOut, ChapterUpdate

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


def _validate_references(db: Session, course_id: int, parent_id: int | None, document_id: int | None, chapter_id: int | None = None) -> None:
    if db.get(Course, course_id) is None:
        raise HTTPException(status_code=404, detail="Cours introuvable")
    if parent_id is not None:
        parent = db.get(Chapter, parent_id)
        if parent is None or parent.course_id != course_id or parent_id == chapter_id:
            raise HTTPException(status_code=404, detail="Chapitre parent introuvable pour ce cours")
    if document_id is not None:
        document = db.get(Document, document_id)
        if document is None or document.course_id != course_id:
            raise HTTPException(status_code=404, detail="Document introuvable pour ce cours")


@router.post("", response_model=ChapterOut, status_code=status.HTTP_201_CREATED)
def create_chapter(payload: ChapterCreate, db: Session = Depends(get_db)) -> Chapter:
    """Create a chapter after validating its course and optional references."""
    _validate_references(db, payload.course_id, payload.parent_id, payload.document_id)
    chapter = Chapter(**payload.model_dump())
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


@router.get("", response_model=list[ChapterOut])
def list_chapters(course_id: int | None = None, db: Session = Depends(get_db)) -> list[Chapter]:
    """List chapters, optionally filtered by course."""
    statement = select(Chapter).order_by(Chapter.id)
    if course_id is not None:
        statement = statement.where(Chapter.course_id == course_id)
    return list(db.scalars(statement).all())


@router.get("/{chapter_id}", response_model=ChapterOut)
def get_chapter(chapter_id: int, db: Session = Depends(get_db)) -> Chapter:
    """Retrieve a chapter by identifier."""
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapitre introuvable")
    return chapter


@router.put("/{chapter_id}", response_model=ChapterOut)
def update_chapter(chapter_id: int, payload: ChapterUpdate, db: Session = Depends(get_db)) -> Chapter:
    """Replace a chapter's editable fields."""
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapitre introuvable")
    _validate_references(db, payload.course_id, payload.parent_id, payload.document_id, chapter_id)
    for key, value in payload.model_dump().items():
        setattr(chapter, key, value)
    db.commit()
    db.refresh(chapter)
    return chapter


@router.delete("/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chapter(chapter_id: int, db: Session = Depends(get_db)) -> Response:
    """Delete a chapter and its study sessions and descendants."""
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapitre introuvable")
    db.delete(chapter)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
