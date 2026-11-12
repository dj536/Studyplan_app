"""Strict Pydantic v2 request and response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InputModel(BaseModel):
    """Base for strict API input validation; unknown keys are rejected."""

    model_config = ConfigDict(extra="forbid", strict=True)


class OutputModel(BaseModel):
    """Base for serializing SQLAlchemy model instances."""

    model_config = ConfigDict(from_attributes=True)


class CourseCreate(InputModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Le nom du cours ne peut pas être vide")
        return value


class CourseUpdate(CourseCreate):
    pass


class CourseOut(OutputModel):
    id: int
    name: str
    description: str | None
    created_at: datetime


class ChapterCreate(InputModel):
    course_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    estimated_hours: float = Field(ge=0, allow_inf_nan=False)
    difficulty: int = Field(default=3, ge=1, le=5)
    parent_id: int | None = Field(default=None, gt=0)
    document_id: int | None = Field(default=None, gt=0)

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Le titre ne peut pas être vide")
        return value


class ChapterUpdate(InputModel):
    course_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    estimated_hours: float = Field(ge=0, allow_inf_nan=False)
    difficulty: int = Field(ge=1, le=5)
    completed_hours: float = Field(ge=0, allow_inf_nan=False)
    parent_id: int | None = Field(default=None, gt=0)
    document_id: int | None = Field(default=None, gt=0)


class ChapterOut(OutputModel):
    id: int
    course_id: int
    document_id: int | None
    parent_id: int | None
    title: str
    estimated_hours: float
    difficulty: int
    completed_hours: float


class DeadlineCreate(InputModel):
    course_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    type: Literal["exam", "assignment", "other"]
    due_date: datetime = Field(strict=False)
    coefficient: float = Field(default=1.0, gt=0, allow_inf_nan=False)


class DeadlineUpdate(InputModel):
    course_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    type: Literal["exam", "assignment", "other"]
    due_date: datetime = Field(strict=False)
    coefficient: float = Field(gt=0, allow_inf_nan=False)


class DeadlineOut(OutputModel):
    id: int
    course_id: int
    title: str
    type: str
    due_date: datetime
    coefficient: float


class AvailabilityCreate(InputModel):
    weekday: int = Field(ge=0, le=6)
    start_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")

    @model_validator(mode="after")
    def validate_order(self) -> "AvailabilityCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time doit être strictement après start_time")
        return self


class AvailabilityUpdate(AvailabilityCreate):
    pass


class AvailabilityOut(OutputModel):
    id: int
    weekday: int
    start_time: str
    end_time: str


class StudySessionOut(OutputModel):
    id: int
    chapter_id: int
    start_datetime: datetime
    end_datetime: datetime
    status: Literal["planned", "done", "skipped"]


class SessionStatusUpdate(InputModel):
    """Request body for changing a study session's status."""

    status: Literal["planned", "done", "skipped"]


class ExtractedChapter(BaseModel):
    """Chapter proposal returned by document analysis; it is not persisted."""

    title: str
    level: int = Field(ge=1, le=2)
    page: int | None = Field(default=None, ge=1)
    estimated_hours: float = Field(ge=0, allow_inf_nan=False)
