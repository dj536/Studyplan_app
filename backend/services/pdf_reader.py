"""Rule-based PDF text and chapter extraction using PyMuPDF."""

from __future__ import annotations

from io import BytesIO
import re
import statistics
from typing import Any

import fitz


class DocumentAnalysisError(ValueError):
    """Raised when a document is empty, corrupted, or cannot be analyzed."""


_NUMBERED_HEADING = re.compile(
    r"^(?:\d+(?:\.\d+)*[.)]?\s+\S|chapitre\s+\w+(?:\s+.*)?)$",
    re.IGNORECASE,
)
_HOURS_PER_PAGE = 0.5


def analyze_pdf(content: bytes) -> list[dict[str, Any]]:
    """Extract chapter proposals from PDF bytes without writing to disk.

    Heading candidates are identified from font size, bold styling, or common
    chapter-numbering patterns. Hours use a fixed words-per-hour estimate.
    PDFs without an extractable text layer are rejected instead of OCR'd.
    """
    if not content:
        raise DocumentAnalysisError("Le fichier PDF est vide")
    try:
        document = fitz.open(stream=BytesIO(content), filetype="pdf")
        if document.is_encrypted:
            raise DocumentAnalysisError("Le PDF est protégé et ne peut pas être analysé")
        pages: list[list[tuple[str, float, bool]]] = []
        sizes: list[float] = []
        for page in document:
            extracted: list[tuple[str, float, bool]] = []
            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    text = "".join(str(span.get("text", "")) for span in spans).strip()
                    if not text:
                        continue
                    size = max((float(span.get("size", 0)) for span in spans), default=0.0)
                    bold = any("bold" in str(span.get("font", "")).lower() for span in spans)
                    sizes.extend(float(span.get("size", 0)) for span in spans if span.get("text", "").strip())
                    extracted.append((text, size, bold))
            pages.append(extracted)
        document.close()
    except DocumentAnalysisError:
        raise
    except Exception as exc:
        raise DocumentAnalysisError("Le PDF est corrompu ou illisible") from exc

    if not any(text.strip() for page in pages for text, _, _ in page):
        raise DocumentAnalysisError("PDF scanné sans texte détectable : l'OCR n'est pas pris en charge")

    typical_size = statistics.median(sizes) if sizes else 0.0
    proposals: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    preamble_pages: set[int] = set()
    for page_number, lines in enumerate(pages, start=1):
        for text, size, bold in lines:
            normalized = " ".join(text.split())
            numbered = bool(_NUMBERED_HEADING.match(normalized))
            is_heading = numbered or (size >= typical_size * 1.18 and size > 0) or bold
            if is_heading and len(normalized) <= 180:
                level = 2 if re.match(r"^\d+\.\d+(?:\.|\s)", normalized) else 1
                title = re.sub(r"^\d+(?:\.\d+)*[.)]?\s*", "", normalized).strip()
                if title:
                    current = {"title": title, "level": level, "page": page_number, "_pages": set()}
                    if not proposals:
                        current["_pages"].update(preamble_pages)
                    proposals.append(current)
                    continue
            if current is None:
                preamble_pages.add(page_number)
            else:
                current["_pages"].add(page_number)

    if not proposals:
        content_pages = {index for index, page in enumerate(pages, start=1) if page}
        proposals = [{"title": "Document", "level": 1, "page": 1, "_pages": content_pages}]

    # Estimate PDF workload from the number of pages assigned to each section.
    for proposal in proposals:
        section_pages = proposal.pop("_pages", set())
        proposal["estimated_hours"] = round(max(_HOURS_PER_PAGE, len(section_pages) * _HOURS_PER_PAGE), 2)
    return proposals
