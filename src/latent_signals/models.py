"""Pydantic data models shared across all pipeline stages."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# --- Stage 1: Collection ---


class RawDocument(BaseModel):
    """Single scraped post/comment from any source."""

    id: str
    source: Literal["reddit", "hackernews", "g2", "capterra", "producthunt", "web"]
    platform_id: str
    title: str | None = None
    body: str
    author: str | None = None
    url: str | None = None
    created_at: datetime
    score: int | None = None
    subreddit: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    collection_timestamp: datetime = Field(default_factory=datetime.now)


# --- Stage 2: Preprocessing ---


class CleanedDocument(BaseModel):
    """Filtered, deduplicated, normalized document."""

    id: str
    source: str
    text: str
    created_at: datetime
    score: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_duplicate: bool = False
    language: str = "en"
    char_count: int = 0


# --- Stage 3: Embedding ---


class EmbeddingMeta(BaseModel):
    """Mapping between document IDs and embedding indices."""

    doc_ids: list[str]
    model_name: str
    dimensions: int
    count: int


# --- Stage 4: Clustering ---


class TopicAssignment(BaseModel):
    """Per-document topic assignment."""

    doc_id: str
    topic_id: int
    topic_label: str = ""
    topic_probability: float = 0.0


class TopicInfo(BaseModel):
    """Summary of a single topic cluster."""

    topic_id: int
    label: str
    size: int
    representative_doc_ids: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


# --- Stage 5: Classification ---


class ClassifiedDocument(BaseModel):
    """Document with sentiment, category, and optional LLM extraction."""

    doc_id: str
    # VADER sentiment (always populated)
    vader_compound: float = 0.0
    vader_pos: float = 0.0
    vader_neg: float = 0.0
    vader_neu: float = 0.0
    # Zero-shot classification
    category: Literal[
        "pain_point", "feature_request", "praise", "question", "bug_report"
    ] = "question"
    category_confidence: float = 0.0
    # LLM extraction (only for sampled docs)
    llm_pain_points: list[str] | None = None
    llm_feature_requests: list[str] | None = None
    llm_urgency: float | None = None
    llm_products_mentioned: list[str] | None = None
    # Keyphrase / NER
    keyphrases: list[str] | None = None
    entities: list[dict[str, str]] | None = None


# --- Stage 6: Scoring ---


class CompetitorFeature(BaseModel):
    """One feature from a curated competitor feature set."""

    feature_id: str
    competitor_name: str
    description: str
    category: str | None = None


class GapOpportunity(BaseModel):
    """One scored gap in the final report."""

    gap_id: str
    label: str
    gap_score: float
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    max_similarity_to_features: float = 0.0
    mention_count: int = 0
    avg_sentiment_intensity: float = 0.0
    competitor_coverage_ratio: float = 0.0
    market_size_proxy: float = 0.0
    trend_slope: float = 0.0
    representative_quotes: list[str] = Field(default_factory=list)
    source_doc_ids: list[str] = Field(default_factory=list)
    topic_ids: list[int] = Field(default_factory=list)
    competitive_whitespace: dict[str, float] = Field(default_factory=dict)

    @staticmethod
    def compute_gap_id(embedding_values: list[float]) -> str:
        """Stable gap ID from hash of representative embeddings."""
        raw = ",".join(f"{v:.6f}" for v in embedding_values)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# --- Pipeline metadata ---


class PipelineRunMeta(BaseModel):
    """Metadata about a full pipeline run."""

    run_id: str
    market_category: str
    started_at: datetime
    completed_at: datetime | None = None
    config_hash: str = ""
    stage_durations: dict[str, float] = Field(default_factory=dict)
    document_counts: dict[str, int] = Field(default_factory=dict)
    api_costs: dict[str, float] = Field(default_factory=dict)
