"""Pydantic schemas for GPT-4o-mini Structured Outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# Granular gap type taxonomy (tier 2). These are mutually exclusive categories
# describing the nature of the gap opportunity. The tier-1 labels (pain_point,
# feature_request, etc.) come from zero-shot/VADER classification and describe
# the post sentiment. gap_type describes what KIND of gap the post reveals.
GapType = Literal[
    "workflow_friction",       # Process is slow, cumbersome, or has too many steps
    "capability_limitation",   # Product can't do something users need
    "reliability_failure",     # Crashes, bugs, data loss, downtime
    "integration_gap",         # Doesn't connect with tools users need
    "economic_barrier",        # Too expensive, pricing model mismatch
    "trust_deficit",           # Privacy, security, vendor lock-in concerns
    "regulatory_friction",     # Compliance, GDPR, industry regulation issues
    "customization_deficit",   # Can't configure or extend to fit workflow
    "learning_curve",          # Too complex to learn or onboard
    "other",                   # Doesn't fit other categories
]


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
    gap_type: GapType = Field(
        default="other",
        description="The primary type of gap this post reveals: workflow_friction, capability_limitation, reliability_failure, integration_gap, economic_barrier, trust_deficit, regulatory_friction, customization_deficit, learning_curve, or other",
    )
