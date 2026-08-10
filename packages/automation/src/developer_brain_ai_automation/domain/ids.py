"""Typed identifiers do automation."""

from developer_brain_ai_shared.kernel.id import TypedId


class PipelineRunId(TypedId):
    """Identificador de um run de pipeline step (uma execucao por data/step)."""


__all__ = ["PipelineRunId"]
