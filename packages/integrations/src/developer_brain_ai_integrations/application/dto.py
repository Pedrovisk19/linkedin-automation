"""DTOs do LinkedIn (OAuth2 + Marketing API)."""

from __future__ import annotations

from pydantic import BaseModel


class LinkedInAuthUrlOutput(BaseModel):
    authorization_url: str


class LinkedInStatusOutput(BaseModel):
    connected: bool
    member_name: str | None = None
    member_urn: str | None = None
    access_expires_at: str | None = None


__all__ = ["LinkedInAuthUrlOutput", "LinkedInStatusOutput"]
