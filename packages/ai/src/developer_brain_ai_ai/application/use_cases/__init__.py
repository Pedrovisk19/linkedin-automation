"""Use cases do modulo ai (agentes concretos)."""

from developer_brain_ai_ai.application.use_cases.linkedin_agent import (
    LINKEDIN_AGENT,
    LINKEDIN_PROMPT,
    LinkedInAgent,
    LinkedInAgentConfig,
    LinkedInDraft,
)
from developer_brain_ai_ai.application.use_cases.news_digest_agent import (
    NEWS_DIGEST_AGENT,
    NEWS_DIGEST_PROMPT,
    NewsDigestAgent,
    NewsDigestAgentConfig,
    NewsDigestDraft,
)
from developer_brain_ai_ai.application.use_cases.summary_agent import (
    SUMMARY_AGENT,
    SUMMARY_PROMPT,
    SummaryAgent,
    SummaryAgentConfig,
)

__all__ = [
    "LINKEDIN_AGENT",
    "LINKEDIN_PROMPT",
    "NEWS_DIGEST_AGENT",
    "NEWS_DIGEST_PROMPT",
    "SUMMARY_AGENT",
    "SUMMARY_PROMPT",
    "LinkedInAgent",
    "LinkedInAgentConfig",
    "LinkedInDraft",
    "NewsDigestAgent",
    "NewsDigestAgentConfig",
    "NewsDigestDraft",
    "SummaryAgent",
    "SummaryAgentConfig",
]
