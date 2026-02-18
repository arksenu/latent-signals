"""Pydantic schemas for GPT-4o-mini Structured Outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FeedbackAnalysis(BaseModel):
    """Structured output schema for LLM feedback extraction."""

    pain_points: list[str] = Field(
        default_factory=list,
        description="Specific user pain points mentioned in the text",
    )
    feature_requests: list[str] = Field(
        default_factory=list,
        description="Features or capabilities the user wants",
    )
    urgency: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How urgent the need is, from 0 (not urgent) to 1 (critical)",
    )
    products_mentioned: list[str] = Field(
        default_factory=list,
        description="Product or company names referenced in the text",
    )
