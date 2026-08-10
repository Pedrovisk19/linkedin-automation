"""DTOs do content."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateLinkedInDraftInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    gancho: str = Field(default="", max_length=400)
    texto: str = Field(min_length=1, max_length=20000)
    conclusao: str = Field(default="", max_length=2000)
    pergunta: str = Field(default="", max_length=400)
    cta: str = Field(default="", max_length=400)
    hashtags: list[str] = Field(default_factory=list, max_length=10)
    source_entry_ids: list[str] = Field(default_factory=list)


class GenerateLinkedInInput(BaseModel):
    entries: list[dict] = Field(default_factory=list)
    ai_writing_tone: str = Field(default="desenvolvedor-compartilhando-evolucao", max_length=200)
    ai_language: str = Field(default="pt-BR", max_length=20)


class LinkedInDraftOutput(BaseModel):
    draft_id: str
    title: str
    gancho: str
    texto: str
    conclusao: str
    pergunta: str
    cta: str
    hashtags: list[str]
    status: str
    created_at: datetime
    updated_at: datetime


class ListDraftsOutput(BaseModel):
    id: str
    content_type: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime


__all__ = [
    "CreateLinkedInDraftInput",
    "GenerateLinkedInInput",
    "LinkedInDraftOutput",
    "ListDraftsOutput",
]
