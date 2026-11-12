"""SQLAlchemy models for StudyPlan's local, single-user database."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Course(Base):
    """A course and the documents, chapters, and deadlines that belong to it."""

    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("name", name="uq_courses_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)

    documents: Mapped[list["Document"]] = relationship(back_populates="course", cascade="all, delete-orphan", passive_deletes=True)
    chapters: Mapped[list["Chapter"]] = relationship(back_populates="course", cascade="all, delete-orphan", passive_deletes=True)
    deadlines: Mapped[list["Deadline"]] = relationship(back_populates="course", cascade="all, delete-orphan", passive_deletes=True)


class Document(Base):
    """An uploaded source document recorded for a course."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)

    course: Mapped[Course] = relationship(back_populates="documents")
    chapters: Mapped[list["Chapter"]] = relationship(back_populates="document", passive_deletes=True)


class Chapter(Base):
    """A course chapter, optionally nested under another chapter."""

    __tablename__ = "chapters"
    __table_args__ = (
        CheckConstraint("estimated_hours >= 0", name="ck_chapters_estimated_hours_nonnegative"),
        CheckConstraint("completed_hours >= 0", name="ck_chapters_completed_hours_nonnegative"),
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_chapters_difficulty_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    estimated_hours: Mapped[float] = mapped_column(Float, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    completed_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")

    course: Mapped[Course] = relationship(back_populates="chapters")
    document: Mapped[Document | None] = relationship(back_populates="chapters")
    parent: Mapped["Chapter | None"] = relationship(remote_side="Chapter.id", back_populates="children")
    children: Mapped[list["Chapter"]] = relationship(back_populates="parent", cascade="all, delete-orphan", passive_deletes=True)
    sessions: Mapped[list["StudySession"]] = relationship(back_populates="chapter", cascade="all, delete-orphan", passive_deletes=True)


class Deadline(Base):
    """An exam, assignment, or other due date associated with a course."""

    __tablename__ = "deadlines"
    __table_args__ = (CheckConstraint("coefficient > 0", name="ck_deadlines_coefficient_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    coefficient: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1")

    course: Mapped[Course] = relationship(back_populates="deadlines")


class Availability(Base):
    """A weekly availability window, where Monday is weekday zero."""

    __tablename__ = "availability"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_availability_weekday_range"),
        CheckConstraint("start_time < end_time", name="ck_availability_time_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)


class StudySession(Base):
    """A planned study interval for one chapter."""

    __tablename__ = "study_sessions"
    __table_args__ = (CheckConstraint("start_datetime < end_datetime", name="ck_sessions_datetime_order"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    start_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned", server_default="planned")

    chapter: Mapped[Chapter] = relationship(back_populates="sessions")
