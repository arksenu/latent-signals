"""Market anchor generation from user query + Exa results.

Primary anchor: user query string (embedded as-is).
Supplementary anchors: recurring frustration phrases from Exa result
titles and snippets, extracted via TF-IDF-like frequency analysis.

Supplementary anchors are non-optional (Decision 1, 2026-02-28):
a single user string is too narrow a relevance boundary.
"""

from __future__ import annotations

import re
from collections import Counter

from latent_signals.stage0_input.exa_discovery import DiscoveryResults
from latent_signals.utils.logging import get_logger

log = get_logger("stage0.anchor_generation")

# Frustration signal words — used to identify pain-relevant phrases
_FRUSTRATION_MARKERS = {
    "frustrated", "frustrating", "frustration", "annoying", "annoyed",
    "hate", "hated", "horrible", "terrible", "awful", "worst",
    "broken", "buggy", "slow", "bloated", "complicated", "complex",
    "confusing", "painful", "unusable", "unreliable", "expensive",
    "alternative", "alternatives", "switch", "switching", "replace",
    "replacing", "migrate", "migrating", "looking for", "instead of",
    "wish", "wished", "missing", "lacks", "lacking", "need", "needs",
    "problem", "problems", "issue", "issues", "complaint", "complaints",
}

# Stop words for n-gram extraction
_STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "to", "for", "of", "in",
    "on", "at", "by", "and", "or", "not", "with", "from", "that", "this",
    "it", "be", "as", "do", "does", "did", "has", "have", "had", "i", "my",
    "me", "we", "you", "your", "he", "she", "they", "them", "its", "but",
    "so", "if", "all", "any", "can", "just", "about", "what", "how", "why",
    "when", "will", "would", "could", "should", "been", "being", "more",
    "very", "too", "also", "than", "then", "here", "there", "where", "which",
    "who", "whom", "some", "each", "every", "both", "few", "many", "much",
    "no", "nor", "own", "same", "other", "such", "only", "into", "over",
    "after", "before", "between", "through", "during", "above", "below",
    "up", "down", "out", "off", "again", "further", "once", "like", "get",
    "got", "use", "used", "using", "one", "two", "new", "now", "way",
    "even", "well", "back", "still", "make", "made", "think", "know",
    "want", "try", "see", "come", "take", "find", "give", "tell", "say",
    "let", "put", "keep", "set", "run", "show", "help", "turn", "start",
    "might", "going", "really", "right", "good", "best", "better", "great",
    "work", "thing", "things", "time", "people", "something", "anything",
    "nothing", "lot", "feel", "look", "seem",
}


def generate_anchors(
    user_description: str,
    discovery: DiscoveryResults,
    *,
    max_anchors: int = 7,
) -> list[str]:
    """Generate market anchor phrases from user description + Exa discovery results.

    Returns a list of 5-7 short anchor phrases. Each anchors is a concise
    frustration statement (1 sentence) that defines part of the problem space.

    For rich descriptions, the description is decomposed into focused statements
    rather than used whole — the embedding model works better with short,
    specific phrases than with long paragraphs.
    """
    anchors = []

    # Step 1: Generate anchors from the user description itself
    description_anchors = _decompose_description(user_description)
    anchors.extend(description_anchors)

    # Step 2: Extract frustration phrases from Exa results
    all_texts = []
    for r in discovery.general_results + discovery.reddit_results:
        all_texts.append(r.title)
        all_texts.append(r.snippet)

    supplementary = _extract_frustration_phrases(all_texts, user_description)

    for phrase in supplementary:
        if len(anchors) >= max_anchors:
            break
        if not _is_too_similar(phrase, anchors):
            anchors.append(phrase)

    # Step 3: Fallbacks if we still don't have enough
    if len(anchors) < 4:
        key_terms = _extract_market_terms(user_description)
        fallbacks = []
        for term in key_terms[:4]:
            fallbacks.append(f"frustrated with {term}")
            fallbacks.append(f"{term} is too complicated and bloated")
            fallbacks.append(f"looking for {term} alternative")
        for fb in fallbacks:
            if len(anchors) >= max_anchors:
                break
            if not _is_too_similar(fb, anchors):
                anchors.append(fb)

    log.info("anchors.generated", count=len(anchors))
    return anchors


def _decompose_description(description: str) -> list[str]:
    """Break a rich description into focused anchor statements.

    Extracts product/market terms and generates short frustration statements
    from them, rather than using the full description as one anchor.
    """
    anchors = []
    terms = _extract_market_terms(description)

    if not terms:
        # If no terms extracted, use first ~15 words as anchor
        short = " ".join(description.split()[:15])
        return [short]

    # Generate focused frustration anchors from extracted terms
    for term in terms[:3]:
        anchors.append(f"{term} is slow and frustrating to use")

    # Also add a switching/alternative anchor if we have terms
    if terms:
        anchors.append(f"switching from {terms[0]} to something better")

    return anchors


def _extract_market_terms(description: str) -> list[str]:
    """Extract product names and market terms from a description.

    Looks for capitalized words (product names) and words near
    frustration/competitor markers.
    """
    import re as _re

    # Find capitalized words that might be product names
    # (skip sentence starters by requiring preceding space/punctuation)
    product_candidates = _re.findall(
        r"(?:^|[.!?,;]\s+|\s)([A-Z][a-zA-Z]+(?:'s)?)", description
    )

    # Find words after "with", "from", "than" (often competitor names)
    after_prep = _re.findall(
        r"(?:with|from|than|versus|vs|like)\s+([A-Z][a-zA-Z]+)",
        description,
        _re.IGNORECASE,
    )

    stop = {
        "the", "a", "an", "we", "our", "my", "i", "they", "their", "its",
        "this", "that", "these", "those", "is", "are", "was", "were", "be",
        "been", "being", "has", "have", "had", "do", "does", "did", "will",
        "would", "could", "should", "can", "may", "might", "shall", "must",
        "re", "building", "looking", "want", "need", "also", "but", "and",
        "or", "not", "for", "to", "of", "in", "on", "at", "by", "so",
        "if", "as", "than", "then", "too", "very", "just", "about", "how",
        "what", "when", "where", "which", "who", "why", "all", "each",
        "every", "both", "few", "many", "much", "some", "any", "no",
        "we're",
    }

    terms = []
    for t in after_prep + product_candidates:
        t_clean = t.strip().rstrip("'s").lower()
        if t_clean not in stop and len(t_clean) > 2:
            if t_clean not in terms:
                terms.append(t_clean)

    return terms


def _extract_frustration_phrases(texts: list[str], user_description: str) -> list[str]:
    """Extract recurring frustration-relevant phrases from Exa result texts.

    Uses bigram/trigram frequency analysis weighted by frustration markers.
    Returns short anchor-style statements, never the full description.
    """
    key_terms = _extract_market_terms(user_description)
    key_term_set = set(key_terms)
    bigram_counts: Counter = Counter()
    trigram_counts: Counter = Counter()

    for text in texts:
        words = re.findall(r"\b[a-z][a-z'-]+\b", text.lower())
        words = [w for w in words if w not in _STOP_WORDS and len(w) > 2]

        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i + 1]}"
            bigram_counts[bigram] += 1

        for i in range(len(words) - 2):
            trigram = f"{words[i]} {words[i + 1]} {words[i + 2]}"
            trigram_counts[trigram] += 1

    # Score n-grams: boost those containing frustration markers or key terms
    scored_phrases: list[tuple[str, float]] = []

    for phrase, count in bigram_counts.most_common(100):
        if count < 2:
            continue
        words = phrase.split()
        score = count
        if any(w in _FRUSTRATION_MARKERS for w in words):
            score *= 3
        if any(w in key_term_set for w in words):
            score *= 2
        scored_phrases.append((phrase, score))

    for phrase, count in trigram_counts.most_common(100):
        if count < 2:
            continue
        words = phrase.split()
        score = count * 1.5
        if any(w in _FRUSTRATION_MARKERS for w in words):
            score *= 3
        if any(w in key_term_set for w in words):
            score *= 2
        scored_phrases.append((phrase, score))

    scored_phrases.sort(key=lambda x: x[1], reverse=True)

    anchors = []
    for phrase, score in scored_phrases[:20]:
        anchor = _phrase_to_anchor(phrase, key_terms)
        if anchor and len(anchor) < 80:  # Cap anchor length
            anchors.append(anchor)

    return anchors


def _phrase_to_anchor(phrase: str, key_terms: list[str]) -> str | None:
    """Convert an n-gram phrase into a short anchor statement."""
    words = phrase.split()
    # Use first key term as context, or the phrase itself
    context = key_terms[0] if key_terms else ""

    if any(w in _FRUSTRATION_MARKERS for w in words):
        if context:
            return f"{context} {phrase}"
        return phrase

    if context:
        return f"{phrase} problems with {context}"
    return f"{phrase} frustration"


def _is_too_similar(candidate: str, existing: list[str], threshold: float = 0.6) -> bool:
    """Check if candidate anchor is too similar to existing ones (word overlap)."""
    candidate_words = set(candidate.lower().split())
    for existing_anchor in existing:
        existing_words = set(existing_anchor.lower().split())
        if not candidate_words or not existing_words:
            continue
        overlap = len(candidate_words & existing_words) / min(
            len(candidate_words), len(existing_words)
        )
        if overlap > threshold:
            return True
    return False
