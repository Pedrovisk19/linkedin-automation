"""DTOs do modulo journal (Pydantic)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, HttpUrl


class CreateJournalEntryInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    entry_date: date
    study_minutes: int = Field(ge=0, le=1440)
    technologies: list[str] = Field(default_factory=list, max_length=50)
    project: str = Field(default="", max_length=200)
    book: str = Field(default="", max_length=200)
    course: str = Field(default="", max_length=200)
    videos: list[str] = Field(default_factory=list, max_length=50)
    links: list[HttpUrl] = Field(default_factory=list, max_length=50)
    difficulties: str = Field(default="", max_length=20000)
    learnings: str = Field(default="", max_length=20000)
    bugs_found: list[str] = Field(default_factory=list, max_length=100)
    resolutions: list[str] = Field(default_factory=list, max_length=100)
    next_steps: str = Field(default="", max_length=20000)
    notes: str = Field(default="", max_length=20000)
    tags: list[str] = Field(default_factory=list, max_length=50)


class UpdateJournalEntryInput(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    entry_date: date | None = None
    study_minutes: int | None = Field(default=None, ge=0, le=1440)
    technologies: list[str] | None = Field(default=None, max_length=50)
    project: str | None = Field(default=None, max_length=200)
    book: str | None = Field(default=None, max_length=200)
    course: str | None = Field(default=None, max_length=200)
    videos: list[str] | None = Field(default=None, max_length=50)
    links: list[HttpUrl] | None = Field(default=None, max_length=50)
    difficulties: str | None = Field(default=None, max_length=20000)
    learnings: str | None = Field(default=None, max_length=20000)
    bugs_found: list[str] | None = Field(default=None, max_length=100)
    resolutions: list[str] | None = Field(default=None, max_length=100)
    next_steps: str | None = Field(default=None, max_length=20000)
    notes: str | None = Field(default=None, max_length=20000)
    tags: list[str] | None = Field(default=None, max_length=50)


class JournalEntryOut(BaseModel):
    id: str
    title: str
    entry_date: date
    study_minutes: int
    technologies: list[str]
    project: str
    book: str
    course: str
    videos: list[str]
    links: list[str]
    difficulties: str
    learnings: str
    bugs_found: list[str]
    resolutions: list[str]
    next_steps: str
    notes: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime


__all__ = [
    "CreateJournalEntryInput",
    "UpdateJournalEntryInput",
    "JournalEntryOut",
]