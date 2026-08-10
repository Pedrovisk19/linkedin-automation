"""Value objects do automation: PipelineStep + PipelineRunStatus."""

from __future__ import annotations

from enum import StrEnum


class PipelineStep(StrEnum):
    """Steps do pipeline diario. A chave de idempotencia e (tenant, date, step)."""

    SUMMARY = "summary"
    LINKEDIN = "linkedin"
    GITHUB_README = "github_readme"
    PUBLISH_LINKEDIN = "publish_linkedin"


class PipelineRunStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


__all__ = ["PipelineRunStatus", "PipelineStep"]
