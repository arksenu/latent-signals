"""Composite gap scoring with 6 weighted components."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime

import numpy as np

from latent_signals.config import ScoringWeights
from latent_signals.models import (
    ClassifiedDocument,
    CompetitorFeature,
    GapOpportunity,
    TopicAssignment,
    TopicInfo,
)
from latent_signals.stage6_scoring.gap_detection import (
    compute_cluster_centroids,
    compute_max_similarity,
    compute_per_competitor_coverage,
)
from latent_signals.stage6_scoring.normalization import (
    normalize_competitive_whitespace,
    normalize_frequency,
    normalize_market_size,
    normalize_pain_intensity,
    normalize_trend_slope,
    normalize_unaddressedness,
)
from latent_signals.utils.logging import get_logger

log = get_logger("scoring")


def _market_relevance(
    centroid: np.ndarray, market_anchor_embeddings: np.ndarray
) -> float:
    """Max cosine similarity between cluster centroid and market anchor phrases."""
    return compute_max_similarity(centroid, market_anchor_embeddings)


def score_gaps(
    topic_infos: list[TopicInfo],
    assignments: list[TopicAssignment],
    classified_docs: list[ClassifiedDocument],
    embeddings: np.ndarray,
    doc_ids: list[str],
    feature_embeddings: np.ndarray,
    features: list[CompetitorFeature],
    doc_texts: dict[str, str],
    doc_dates: dict[str, datetime],
    weights: ScoringWeights,
    top_n: int = 10,
    market_anchor_embeddings: np.ndarray | None = None,
    market_relevance_threshold: float = 0.0,
    min_signal_ratio: float = 0.0,
) -> list[GapOpportunity]:
    """Score all topic clusters and return ranked gap opportunities."""

    # Build lookups
    assignment_map = {a.doc_id: a.topic_id for a in assignments}
    classified_map = {c.doc_id: c for c in classified_docs}
    competitor_names = [f.competitor_name for f in features]
    unique_competitors = set(competitor_names)

    # Compute cluster centroids
    centroids = compute_cluster_centroids(embeddings, doc_ids, assignment_map)

    # Group docs by topic
    topic_doc_ids: dict[int, list[str]] = defaultdict(list)
    for a in assignments:
        if a.topic_id != -1:
            topic_doc_ids[a.topic_id].append(a.doc_id)

    # Compute global stats for normalization
    max_mention_count = max((len(dids) for dids in topic_doc_ids.values()), default=1)

    # Compute market size proxies (total score/upvotes in cluster)
    market_sizes: dict[int, float] = {}
    for topic_id, dids in topic_doc_ids.items():
        market_sizes[topic_id] = float(len(dids))  # Simple proxy: cluster size
    max_market_size = max(market_sizes.values(), default=1.0)

    # Compute trend slopes per cluster
    trend_slopes = _compute_trend_slopes(topic_doc_ids, doc_dates)
    max_abs_slope = max((abs(s) for s in trend_slopes.values()), default=1.0)

    # Score each cluster
    opportunities: list[GapOpportunity] = []
    for topic_info in topic_infos:
        tid = topic_info.topic_id
        if tid not in centroids:
            continue

        centroid = centroids[tid]
        dids = topic_doc_ids.get(tid, [])
        if not dids:
            continue

        # Market relevance gate: skip clusters that don't resemble the target market.
        # This prevents large off-topic clusters (CSS, CORS, SSL certs, Terraform)
        # from outscoring relevant project-management clusters on frequency alone.
        if market_anchor_embeddings is not None and market_relevance_threshold > 0:
            relevance = _market_relevance(centroid, market_anchor_embeddings)
            if relevance < market_relevance_threshold:
                log.debug(
                    "scoring.skipped_irrelevant",
                    topic_id=tid,
                    label=topic_info.label,
                    relevance=round(relevance, 3),
                    threshold=market_relevance_threshold,
                )
                continue

        # Signal ratio gate: skip clusters where too few docs express pain or need.
        # A "gap" requires people complaining or requesting features, not just asking
        # career questions or sharing book recommendations.
        if min_signal_ratio > 0:
            signal_categories = {"pain_point", "feature_request", "bug_report"}
            cluster_classified = [classified_map[d] for d in dids if d in classified_map]
            if cluster_classified:
                n_signal = sum(1 for c in cluster_classified if c.category in signal_categories)
                ratio = n_signal / len(cluster_classified)
                if ratio < min_signal_ratio:
                    log.debug(
                        "scoring.skipped_low_signal",
                        topic_id=tid,
                        label=topic_info.label,
                        signal_ratio=round(ratio, 3),
                        threshold=min_signal_ratio,
                    )
                    continue

        # Component 1: Unaddressedness
        max_sim = compute_max_similarity(centroid, feature_embeddings)
        unaddressedness = normalize_unaddressedness(max_sim)

        # Component 2: Frequency
        frequency = normalize_frequency(len(dids), max_mention_count)

        # Component 3: Pain intensity
        pain_docs = [classified_map[d] for d in dids if d in classified_map]
        pain_sentiments = [c.vader_compound for c in pain_docs if c.category in ("pain_point", "bug_report")]
        avg_sentiment = np.mean(pain_sentiments).item() if pain_sentiments else 0.0
        pain_intensity = normalize_pain_intensity(avg_sentiment)

        # Component 4: Competitive whitespace
        # Use continuous max similarity across all competitors as coverage_ratio.
        # The prior binary threshold (>0.5 = covered) was broken for single-competitor
        # scenarios where MiniLM similarities rarely exceed 0.5.
        per_competitor = compute_per_competitor_coverage(
            centroid, feature_embeddings, competitor_names
        )
        coverage_ratio = max(per_competitor.values()) if per_competitor else 0.0
        comp_whitespace = normalize_competitive_whitespace(coverage_ratio)

        # Component 5: Market size
        market_size = normalize_market_size(market_sizes.get(tid, 0), max_market_size)

        # Component 6: Trend
        slope = trend_slopes.get(tid, 0.0)
        trend = normalize_trend_slope(slope, max_abs_slope)

        # Composite score
        gap_score = (
            weights.unaddressedness * unaddressedness
            + weights.frequency * frequency
            + weights.pain_intensity * pain_intensity
            + weights.competitive_whitespace * comp_whitespace
            + weights.market_size * market_size
            + weights.trend_direction * trend
        )

        # Representative quotes
        quotes = []
        for did in dids[:weights_to_quotes(weights)]:
            if did in doc_texts:
                text = doc_texts[did]
                quotes.append(text[:300])

        # Stable gap ID
        centroid_flat = centroid.flatten().tolist()[:20]
        gap_id = GapOpportunity.compute_gap_id(centroid_flat)

        opportunities.append(
            GapOpportunity(
                gap_id=gap_id,
                label=topic_info.label,
                gap_score=round(gap_score, 4),
                score_breakdown={
                    "unaddressedness": round(unaddressedness, 4),
                    "frequency": round(frequency, 4),
                    "pain_intensity": round(pain_intensity, 4),
                    "competitive_whitespace": round(comp_whitespace, 4),
                    "market_size": round(market_size, 4),
                    "trend_direction": round(trend, 4),
                },
                max_similarity_to_features=round(max_sim, 4),
                mention_count=len(dids),
                avg_sentiment_intensity=round(avg_sentiment, 4),
                competitor_coverage_ratio=round(coverage_ratio, 4),
                market_size_proxy=market_sizes.get(tid, 0),
                trend_slope=round(slope, 6),
                representative_quotes=quotes,
                source_doc_ids=dids[:50],
                topic_ids=[tid],
                competitive_whitespace=per_competitor,
            )
        )

    # Sort by gap_score descending, take top N
    opportunities.sort(key=lambda g: g.gap_score, reverse=True)
    opportunities = opportunities[:top_n]

    log.info("scoring.complete", n_gaps=len(opportunities))
    return opportunities


def weights_to_quotes(weights: ScoringWeights) -> int:
    """Return number of quotes to include based on pain intensity weight."""
    return 20


def _compute_trend_slopes(
    topic_doc_ids: dict[int, list[str]],
    doc_dates: dict[str, datetime],
) -> dict[int, float]:
    """Compute linear trend slope of monthly mention counts per topic."""
    slopes: dict[int, float] = {}

    for topic_id, dids in topic_doc_ids.items():
        # Group by month
        monthly: dict[str, int] = defaultdict(int)
        for did in dids:
            if did in doc_dates:
                dt = doc_dates[did]
                key = f"{dt.year}-{dt.month:02d}"
                monthly[key] += 1

        if len(monthly) < 2:
            slopes[topic_id] = 0.0
            continue

        # Sort by month and compute linear regression
        sorted_months = sorted(monthly.keys())
        x = np.arange(len(sorted_months), dtype=float)
        y = np.array([monthly[m] for m in sorted_months], dtype=float)

        # Simple linear regression: slope = cov(x,y) / var(x)
        x_mean = x.mean()
        y_mean = y.mean()
        cov_xy = ((x - x_mean) * (y - y_mean)).sum()
        var_x = ((x - x_mean) ** 2).sum()
        slope = cov_xy / var_x if var_x > 0 else 0.0
        slopes[topic_id] = float(slope)

    return slopes
