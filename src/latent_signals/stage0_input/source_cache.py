"""Cache for Exa discovery + source extraction results.

Caches the full discovery → sources → anchors pipeline output keyed by
normalized user query. Avoids re-running Exa probes and Arctic Shift
volume checks for repeat queries on the same market.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from pathlib import Path

from latent_signals.stage0_input.exa_discovery import DiscoveryResults, ExaResult
from latent_signals.stage0_input.source_extraction import ValidatedSources
from latent_signals.utils.logging import get_logger

log = get_logger("source_cache")

# Default TTL: 7 days. Source maps change less often than competitor features
# but more often than you'd think (subreddits go private, volumes shift).
DEFAULT_TTL_DAYS = 7


def _cache_key(query: str) -> str:
    normalized = query.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _cache_path(query: str, cache_dir: Path) -> Path:
    return cache_dir / f"sources_{_cache_key(query)}.json"


def load_source_cache(
    query: str,
    cache_dir: Path,
    ttl_days: int = DEFAULT_TTL_DAYS,
) -> tuple[DiscoveryResults, ValidatedSources, list[str]] | None:
    """Load cached discovery results if fresh enough.

    Returns (discovery, sources, anchors) or None if cache miss/stale.
    """
    path = _cache_path(query, cache_dir)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    cached_at = data.get("cached_at", 0)
    age_days = (time.time() - cached_at) / 86400
    if age_days > ttl_days:
        log.info("source_cache.stale", age_days=round(age_days, 1))
        return None

    try:
        discovery = _deserialize_discovery(data["discovery"])
        sources = _deserialize_sources(data["sources"])
        anchors = data["anchors"]
    except (KeyError, TypeError) as e:
        log.warning("source_cache.deserialize_failed", error=str(e))
        return None

    log.info("source_cache.hit", subreddits=len(sources.subreddits))
    return discovery, sources, anchors


def save_source_cache(
    query: str,
    discovery: DiscoveryResults,
    sources: ValidatedSources,
    anchors: list[str],
    cache_dir: Path,
) -> None:
    """Save discovery results to cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(query, cache_dir)

    data = {
        "cached_at": time.time(),
        "query": query,
        "discovery": _serialize_discovery(discovery),
        "sources": _serialize_sources(sources),
        "anchors": anchors,
    }
    path.write_text(json.dumps(data, indent=2))
    log.info("source_cache.saved", path=str(path))


def _serialize_discovery(d: DiscoveryResults) -> dict:
    def _result(r: ExaResult) -> dict:
        return {"url": r.url, "title": r.title, "snippet": r.snippet, "published_date": r.published_date}

    return {
        "general_results": [_result(r) for r in d.general_results],
        "reddit_results": [_result(r) for r in d.reddit_results],
        "hn_results": [_result(r) for r in d.hn_results],
        "subreddit_counts": dict(d.subreddit_counts),
        "domain_counts": dict(d.domain_counts),
    }


def _deserialize_discovery(data: dict) -> DiscoveryResults:
    def _result(d: dict) -> ExaResult:
        return ExaResult(
            url=d["url"], title=d["title"],
            snippet=d["snippet"], published_date=d.get("published_date", ""),
        )

    dr = DiscoveryResults()
    dr.general_results = [_result(r) for r in data.get("general_results", [])]
    dr.reddit_results = [_result(r) for r in data.get("reddit_results", [])]
    dr.hn_results = [_result(r) for r in data.get("hn_results", [])]
    dr.subreddit_counts = Counter(data.get("subreddit_counts", {}))
    dr.domain_counts = Counter(data.get("domain_counts", {}))
    return dr


def _serialize_sources(s: ValidatedSources) -> dict:
    return {
        "subreddits": s.subreddits,
        "subreddit_volumes": s.subreddit_volumes,
        "hn_queries": s.hn_queries,
        "hn_has_signal": s.hn_has_signal,
        "dropped_subreddits": s.dropped_subreddits,
    }


def _deserialize_sources(data: dict) -> ValidatedSources:
    return ValidatedSources(
        subreddits=data["subreddits"],
        subreddit_volumes=data.get("subreddit_volumes", {}),
        hn_queries=data.get("hn_queries", []),
        hn_has_signal=data.get("hn_has_signal", False),
        dropped_subreddits=data.get("dropped_subreddits", []),
    )
