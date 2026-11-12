"""Rule-based Markdown heading and study-hour extraction."""

from __future__ import annotations

from pathlib import PurePath
import re
from typing import Any

from backend.services.pdf_reader import DocumentAnalysisError

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_WORDS_PER_HOUR = 200


def analyze_markdown(content: bytes, filename: str = "document.md") -> list[dict[str, Any]]:
    """Return chapter proposals from UTF-8 Markdown bytes.

    H1 headings are chapters; deeper headings are mapped to subchapters. Each
    proposal's estimated time is based on the words up to the next heading.
    """
    if not content:
        raise DocumentAnalysisError("Le fichier Markdown est vide")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentAnalysisError("Le fichier Markdown n'est pas encodé en UTF-8") from exc
    if not text.strip():
        raise DocumentAnalysisError("Le fichier Markdown est vide")

    sections: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    preamble: list[str] = []
    for line in text.splitlines():
        match = _HEADING.match(line.strip())
        if match:
            if active is not None:
                active["_body"] = " ".join(active["_body"])
            active = {"title": match.group(2).strip(), "level": 1 if len(match.group(1)) == 1 else 2, "_body": []}
            sections.append(active)
        elif active is None:
            preamble.append(line)
        else:
            active["_body"].append(line)

    if not sections:
        title = PurePath(filename).stem.strip() or "Document"
        sections = [{"title": title, "level": 1, "_body": [text]}]
    elif preamble and " ".join(preamble).strip():
        # Introductory content belongs to the first detected chapter.
        first_body = sections[0]["_body"]
        sections[0]["_body"] = [" ".join(preamble), *first_body]

    result: list[dict[str, Any]] = []
    for section in sections:
        body = section.pop("_body")
        if isinstance(body, list):
            body = " ".join(body)
        word_count = len(re.findall(r"\b[\w'-]+\b", body))
        result.append({
            "title": section["title"],
            "level": section["level"],
            "page": None,
            "estimated_hours": round(max(0.25, word_count / _WORDS_PER_HOUR), 2),
        })
    return result
