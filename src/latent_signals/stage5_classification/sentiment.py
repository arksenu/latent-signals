"""VADER sentiment analysis with intensity preservation."""

from __future__ import annotations

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


_analyzer: SentimentIntensityAnalyzer | None = None


def get_analyzer() -> SentimentIntensityAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentIntensityAnalyzer()
    return _analyzer


def analyze_sentiment(text: str) -> dict[str, float]:
    """Analyze sentiment preserving full intensity gradients.

    Returns dict with keys: compound, pos, neg, neu.
    """
    scores = get_analyzer().polarity_scores(text)
    return {
        "compound": scores["compound"],
        "pos": scores["pos"],
        "neg": scores["neg"],
        "neu": scores["neu"],
    }


def batch_sentiment(texts: list[str]) -> list[dict[str, float]]:
    """Analyze sentiment for a batch of texts."""
    analyzer = get_analyzer()
    return [analyzer.polarity_scores(t) for t in texts]
