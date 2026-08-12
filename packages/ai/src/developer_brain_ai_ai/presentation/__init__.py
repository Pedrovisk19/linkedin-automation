"""Composition helper do ai. Monta SummaryAgent + router."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from developer_brain_ai_identity.presentation.dependencies import CurrentUserDependency
from fastapi import APIRouter
from openai import AsyncOpenAI

from developer_brain_ai_ai.application.prompt_engine import PromptEngine
from developer_brain_ai_ai.application.use_cases import SummaryAgent
from developer_brain_ai_ai.domain.repositories import AgentRunRepository
from developer_brain_ai_ai.infrastructure.openai_provider import OpenAIProvider
from developer_brain_ai_ai.presentation.routers import build_router


def mount_ai(
    *,
    openai_client: AsyncOpenAI,
    prompts_dir: Path,
    journal_list_fn: Callable[..., Awaitable[list[dict[str, Any]]]],
    summary_runs_repo: AgentRunRepository,
    current_user_dep: CurrentUserDependency,
    chat_model: str = "gpt-4o-mini",
    embedding_model: str = "text-embedding-3-large",
) -> APIRouter:
    provider = OpenAIProvider(
        client=openai_client,
        chat_model=chat_model,
        embedding_model=embedding_model,
    )
    engine = PromptEngine(prompts_dir)
    summary_agent = SummaryAgent(provider=provider, prompt_engine=engine, runs=summary_runs_repo)

    return build_router(
        summary_agent=summary_agent,
        journal_list_fn=journal_list_fn,
        current_user_dep=current_user_dep,
    )


__all__ = ["mount_ai"]
