"""Extract and validate data sources from Exa discovery results.

Parses Exa result URLs to identify subreddits and HN threads,
then verifies subreddit volume via Arctic Shift API.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

import httpx
import numpy as np

from latent_signals.stage0_input.exa_discovery import DiscoveryResults
from latent_signals.stage3_embedding.embedder import Embedder
from latent_signals.utils.logging import get_logger

log = get_logger("stage0.source_extraction")

ARCTIC_SHIFT_API = "https://arctic-shift.photon-reddit.com/api/posts/search"
ARCTIC_SHIFT_COMMENTS_API = "https://arctic-shift.photon-reddit.com/api/comments/search"


@dataclass
class ValidatedSources:
    """Sources extracted from Exa results and validated for volume."""

    subreddits: list[str] = field(default_factory=list)
    subreddit_volumes: dict[str, int] = field(default_factory=dict)
    hn_queries: list[str] = field(default_factory=list)
    hn_has_signal: bool = False
    dropped_subreddits: list[str] = field(default_factory=list)


def extract_and_validate_sources(
    discovery: DiscoveryResults,
    user_query: str,
    *,
    date_start: str,
    date_end: str,
    min_volume: int = 200,
    max_subreddits: int = 12,
    min_relevance: float = 0.15,
) -> ValidatedSources:
    """Extract subreddits and HN queries from Exa results, validate volume.

    Args:
        discovery: Raw Exa discovery results.
        user_query: Original user query (used to generate HN queries).
        date_start: Start date for volume check (YYYY-MM-DD).
        date_end: End date for volume check (YYYY-MM-DD).
        min_volume: Minimum posts+comments to keep a subreddit.
        max_subreddits: Maximum subreddits to include in config.
        min_relevance: Minimum cosine similarity between subreddit name
            and user query to accept a subreddit. Filters off-topic subs
            like r/mechanicalkeyboards from a web analytics query.
    """
    result = ValidatedSources()

    # Extract subreddits ranked by Exa frequency
    ranked_subs = discovery.subreddit_counts.most_common(max_subreddits + 10)
    candidate_subs = [sub for sub, _ in ranked_subs]

    log.info("sources.candidates", subreddits=candidate_subs)

    # Relevance filter: embed subreddit names and compare to user query.
    # Converts camelCase/joined names to readable phrases for better embeddings
    # (e.g. "mechanicalkeyboards" → "mechanical keyboards").
    relevant_subs = _filter_by_relevance(
        candidate_subs, user_query, min_relevance
    )

    # Verify volume via Arctic Shift (only for relevant subs)
    for sub in relevant_subs:
        if len(result.subreddits) >= max_subreddits:
            break

        volume = _check_subreddit_volume(sub, date_start, date_end)
        if volume >= min_volume:
            result.subreddits.append(sub)
            result.subreddit_volumes[sub] = volume
            log.info("sources.subreddit_accepted", subreddit=sub, volume=volume)
        else:
            result.dropped_subreddits.append(sub)
            log.info("sources.subreddit_dropped", subreddit=sub, volume=volume, min=min_volume)

    # Generate HN queries from user input
    result.hn_has_signal = len(discovery.hn_results) > 5
    if result.hn_has_signal:
        result.hn_queries = _build_hn_queries(user_query, discovery)

    log.info(
        "sources.complete",
        subreddits=len(result.subreddits),
        dropped=len(result.dropped_subreddits),
        hn_queries=len(result.hn_queries),
    )
    return result


def _subreddit_to_phrase(name: str) -> str:
    """Convert a subreddit name to a readable phrase for embedding.

    Examples: "mechanicalkeyboards" → "mechanical keyboards",
              "googleanalytics" → "google analytics",
              "bigseo" → "big seo", "webdev" → "web dev"
    """
    import re as _re
    # Insert spaces before uppercase letters (camelCase)
    spaced = _re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    # Insert spaces between lowercase-to-digit and digit-to-lowercase
    spaced = _re.sub(r"(?<=[a-z])(?=\d)", " ", spaced)
    spaced = _re.sub(r"(?<=\d)(?=[a-z])", " ", spaced)
    return spaced.lower()


def _filter_by_relevance(
    candidate_subs: list[str],
    user_query: str,
    min_relevance: float,
) -> list[str]:
    """Filter subreddits by semantic relevance to the user query.

    Embeds subreddit names (as readable phrases) and the user query,
    then keeps only subs with cosine similarity >= min_relevance.
    """
    if not candidate_subs or min_relevance <= 0:
        return candidate_subs

    embedder = Embedder()

    # Convert subreddit names to readable phrases
    sub_phrases = [_subreddit_to_phrase(s) for s in candidate_subs]
    sub_embeddings = embedder.embed(sub_phrases, batch_size=64)
    query_embedding = embedder.embed([user_query], batch_size=1)

    # Cosine similarity between each sub and the query
    similarities = np.dot(sub_embeddings, query_embedding.T).flatten()

    relevant = []
    for sub, phrase, sim in zip(candidate_subs, sub_phrases, similarities):
        if sim >= min_relevance:
            relevant.append(sub)
            log.info("sources.relevance_pass", subreddit=sub, phrase=phrase, similarity=round(float(sim), 3))
        else:
            log.info("sources.relevance_drop", subreddit=sub, phrase=phrase, similarity=round(float(sim), 3), threshold=min_relevance)

    return relevant


def _check_subreddit_volume(subreddit: str, date_start: str, date_end: str) -> int:
    """Check post+comment count for a subreddit in the date range via Arctic Shift.

    Returns estimated total volume. Uses limit=100 probe (same as
    scripts/arctic_shift_volume_check.py).
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            post_resp = client.get(
                ARCTIC_SHIFT_API,
                params={
                    "subreddit": subreddit,
                    "after": date_start,
                    "before": date_end,
                    "limit": 100,
                },
            )
            post_data = post_resp.json().get("data") or []
            post_count = len(post_data)

            comment_resp = client.get(
                ARCTIC_SHIFT_COMMENTS_API,
                params={
                    "subreddit": subreddit,
                    "after": date_start,
                    "before": date_end,
                    "limit": 100,
                },
            )
            comment_data = comment_resp.json().get("data") or []
            comment_count = len(comment_data)

        total = post_count + comment_count
        # If we hit the limit on either, there's likely more data
        if post_count == 100 or comment_count == 100:
            total = max(total, 200)  # Conservative floor when capped
        return total
    except Exception as e:
        log.warning("sources.volume_check_failed", subreddit=subreddit, error=str(e))
        return 0


def _build_hn_queries(query: str, discovery: DiscoveryResults) -> list[str]:
    """Build HN search queries from user input and discovery results.

    Uses short terms extracted from the query, not the full description.
    """
    # Use first few meaningful words if query is long
    short_query = " ".join(query.split()[:6]) if len(query.split()) > 6 else query
    queries = [short_query, f"{short_query} alternative", f"{short_query} frustration"]

    # Extract frequent words from HN titles for additional queries
    title_words: Counter = Counter()
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "to", "for", "of", "in",
        "on", "at", "by", "and", "or", "not", "with", "from", "that", "this",
        "it", "be", "as", "do", "does", "did", "has", "have", "had", "i", "my",
        "me", "we", "you", "your", "show", "hn", "ask",
    }
    short_words = set(short_query.lower().split())

    for r in discovery.hn_results:
        words = re.findall(r"\b[a-z]{3,}\b", r.title.lower())
        for w in words:
            if w not in stop_words and w not in short_words:
                title_words[w] += 1

    # Add top recurring terms as additional queries
    for word, count in title_words.most_common(3):
        if count >= 2:
            queries.append(f"{short_query} {word}")

    return queries[:6]  # Cap at 6 queries
