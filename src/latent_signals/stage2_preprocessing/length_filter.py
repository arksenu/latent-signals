"""Length-based document filtering."""

from __future__ import annotations


def passes_length_filter(text: str, min_length: int = 50, max_length: int = 10000) -> bool:
    """Check if text length is within acceptable bounds."""
    return min_length <= len(text) <= max_length
