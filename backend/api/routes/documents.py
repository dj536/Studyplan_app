"""Non-persistent document analysis endpoint."""

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Course
from backend.schemas import ExtractedChapter
from backend.services.markdown_reader import analyze_markdown
from backend.services.pdf_reader import DocumentAnalysisError, analyze_pdf

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/analyze", response_model=list[ExtractedChapter])
async def analyze_document(
    course_id: int = Form(..., gt=0),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    """Analyze an uploaded PDF or Markdown document without persisting it."""
    if db.get(Course, course_id) is None:
        raise HTTPException(status_code=404, detail="Cours introuvable")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".md", ".markdown"}:
        raise HTTPException(status_code=415, detail="Format refusé : seuls les fichiers PDF et Markdown sont acceptés")
    content = await file.read()
    try:
        if suffix == ".pdf":
            result = analyze_pdf(content)
        else:
            result = analyze_markdown(content, file.filename or "document.md")
    except DocumentAnalysisError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result
