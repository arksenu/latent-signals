"""Normalization functions for gap score components. All normalize to [0, 1]."""

from __future__ import annotations

import math

import numpy as np


def normalize_unaddressedness(max_similarity: float) -> float:
    """1 - max_similarity. Already in [0, 1]."""
    return max(0.0, min(1.0, 1.0 - max_similarity))


def normalize_frequency(mention_count: int, max_count: int) -> float:
    """Log-normalized frequency: log(count+1) / log(max_count+1)."""
    if max_count <= 0:
        return 0.0
    return math.log(mention_count + 1) / math.log(max_count + 1)


def normalize_pain_intensity(avg_sentiment: float) -> float:
    """Map negative sentiment intensity to [0, 1].

    VADER compound is [-1, 1]. More negative = more pain.
    We use abs(compound) for negative sentiments, scaled.
    """
    # Negative sentiment: compound < 0, intensity = abs(compound)
    # Neutral/positive: low pain
    return max(0.0, min(1.0, abs(min(avg_sentiment, 0.0))))


def normalize_competitive_whitespace(coverage_ratio: float) -> float:
    """1 - coverage_ratio. Already in [0, 1]."""
    return max(0.0, min(1.0, 1.0 - coverage_ratio))


def normalize_market_size(proxy_value: float, max_value: float) -> float:
    """Linear normalization of market size proxy."""
    if max_value <= 0:
        return 0.0
    return max(0.0, min(1.0, proxy_value / max_value))


def normalize_trend_slope(slope: float, max_abs_slope: float) -> float:
    """Normalize trend slope from [-max, max] to [0, 1].

    Positive slope (growing) maps to > 0.5.
    Negative slope (declining) maps to < 0.5.
    """
    if max_abs_slope <= 0:
        return 0.5
    normalized = (slope / max_abs_slope + 1.0) / 2.0
    return max(0.0, min(1.0, normalized))
