"""Exa discovery: user description → Exa semantic search → raw results.

No LLM intermediary. The user's text goes directly to Exa as semantic queries.
This automates what scripts/exa_discovery_*.py did manually.

User input is a rich text description (1-3 sentences) of their company,
product, market, and competitors. No frustration language needed — the
user describes WHAT they're building, not what gaps exist.
Example: "We're building a lightweight issue tracker for small dev teams.
Our main competitor is Jira. The project management space is dominated
by enterprise tools like Asana and Monday."
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from exa_py import Exa

from latent_signals.utils.logging import get_logger

log = get_logger("stage0.exa_discovery")


@dataclass
class ExaResult:
    """A single result from Exa search."""

    url: str
    title: str
    snippet: str
    published_date: str | None = None


@dataclass
class DiscoveryResults:
    """Aggregated discovery results from all Exa probes."""

    general_results: list[ExaResult] = field(default_factory=list)
    reddit_results: list[ExaResult] = field(default_factory=list)
    hn_results: list[ExaResult] = field(default_factory=list)
    subreddit_counts: Counter = field(default_factory=Counter)
    domain_counts: Counter = field(default_factory=Counter)


def _extract_subreddit(url: str) -> str | None:
    """Extract subreddit name from a Reddit URL."""
    m = re.search(r"reddit\.com/r/(\w+)", url)
    return m.group(1).lower() if m else None


def _extract_domain(url: str) -> str:
    """Extract domain from a URL."""
    m = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1) if m else url


def _extract_key_terms(description: str) -> list[str]:
    """Extract product names and domain terms from user description.

    Three extraction strategies:
    1. Capitalized words (product names like Jira, Notion, Asana)
    2. Words after prepositions (competitor references)
    3. Domain noun phrases ("issue tracker", "project management", "web analytics")
    No LLM — just regex and pattern matching.
    """
    desc_lower = description.lower()

    # 1. Capitalized words that might be product names (not sentence starters)
    product_candidates = re.findall(r"(?<=[.!?\s])\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", description)

    # 2. Words after prepositions (e.g., "frustrated with Jira")
    after_prepositions = re.findall(r"(?:with|from|than|like|versus|vs)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)", description, re.IGNORECASE)

    # 3. Domain noun phrases — "building a/an X", "X space/market", "X tool/app/platform"
    domain_phrases = []
    # "building a/an X for" or "building a/an X that"
    m = re.search(r"building\s+(?:a|an)\s+(.+?)(?:\s+for\b|\s+that\b|\s+to\b|[.,])", desc_lower)
    if m:
        domain_phrases.append(m.group(1).strip())
    # "the X space/market/industry"
    m = re.search(r"\bthe\s+([\w\s-]{3,30}?)\s+(?:space|market|industry|sector)\b", desc_lower)
    if m:
        domain_phrases.append(m.group(1).strip())
    # "X tool/app/platform/software"
    for m in re.finditer(r"\b((?:\w+[\s-]){0,4}\w+)\s+(?:tool|app|platform|software|solution|service)\b", desc_lower):
        phrase = m.group(1).strip()
        if len(phrase) > 3:
            domain_phrases.append(phrase)
    # "focus on X" — extracts what the product does
    m = re.search(r"focus(?:ed)?\s+on\s+(.+?)(?:[.,]|$)", desc_lower)
    if m:
        focus = m.group(1).strip()
        # Take first 3-4 words
        words = focus.split()[:4]
        if len(words) >= 1:
            domain_phrases.append(" ".join(words))

    stop = {
        "the", "a", "an", "is", "are", "was", "were", "to", "for", "of", "in",
        "on", "at", "by", "and", "or", "not", "with", "from", "that", "this",
        "it", "we", "our", "my", "i", "they", "their", "its", "be", "has",
        "have", "had", "do", "does", "did", "will", "would", "could", "should",
        "but", "so", "if", "as", "than", "then", "too", "also", "just", "about",
        "more", "very", "can", "all", "any", "which", "who", "where", "when",
        "what", "how", "why", "re", "building", "looking", "want", "need",
        "small", "large", "new", "existing", "current", "main", "fully",
    }

    terms = []
    # Add domain phrases first (highest signal)
    for phrase in domain_phrases:
        phrase_clean = phrase.strip().lower()
        # Remove leading stop words
        words = phrase_clean.split()
        while words and words[0] in stop:
            words.pop(0)
        phrase_clean = " ".join(words)
        if phrase_clean and len(phrase_clean) > 2 and phrase_clean not in stop:
            if phrase_clean not in terms:
                terms.append(phrase_clean)

    # Then add product names and preposition matches
    for t in product_candidates + after_prepositions:
        t_clean = t.strip().lower()
        if t_clean not in stop and len(t_clean) > 2:
            if t_clean not in terms:
                terms.append(t_clean)

    return terms


def run_exa_discovery(
    description: str,
    exa_api_key: str,
    *,
    num_results: int = 20,
    date_start: str | None = None,
    date_end: str | None = None,
    competitor_names: list[str] | None = None,
) -> DiscoveryResults:
    """Run Exa probes (general, Reddit-only, HN-only, Answer source discovery).

    The user's description is used directly as an Exa search query for some probes
    (Exa is a semantic search engine — it handles natural language well).
    Additional queries are generated from extracted key terms AND competitor names
    (if provided from a prior Exa Answer competitor discovery call).
    """
    client = Exa(api_key=exa_api_key)
    results = DiscoveryResults()

    key_terms = _extract_key_terms(description)

    # Merge competitor names into key terms — these are high-signal search terms
    # that find product-specific subreddits (r/jira, r/evernote, r/googleanalytics)
    if competitor_names:
        for name in competitor_names:
            name_lower = name.strip().lower()
            if name_lower and name_lower not in key_terms:
                key_terms.append(name_lower)

    log.info("discovery.key_terms", terms=key_terms)

    general_queries = _build_general_queries(description, key_terms)
    reddit_queries = _build_reddit_queries(description, key_terms)
    hn_queries = _build_hn_queries(description, key_terms)

    date_kwargs = {}
    if date_start:
        date_kwargs["start_published_date"] = date_start
    if date_end:
        date_kwargs["end_published_date"] = date_end

    # Probe 1: General (all domains)
    log.info("discovery.general_probe", n_queries=len(general_queries))
    for q in general_queries:
        try:
            response = client.search_and_contents(
                query=q, num_results=num_results, text=True, **date_kwargs
            )
        except Exception as e:
            log.warning("discovery.query_failed", query=q, error=str(e))
            continue

        for r in response.results:
            result = ExaResult(
                url=r.url,
                title=r.title or "",
                snippet=(r.text or "")[:500],
                published_date=r.published_date,
            )
            results.general_results.append(result)
            results.domain_counts[_extract_domain(r.url)] += 1
            sub = _extract_subreddit(r.url)
            if sub:
                results.subreddit_counts[sub] += 1

    # Probe 2: Reddit-only
    log.info("discovery.reddit_probe", n_queries=len(reddit_queries))
    for q in reddit_queries:
        try:
            response = client.search_and_contents(
                query=q,
                num_results=num_results,
                include_domains=["reddit.com"],
                text=True,
                **date_kwargs,
            )
        except Exception as e:
            log.warning("discovery.query_failed", query=q, error=str(e))
            continue

        for r in response.results:
            result = ExaResult(
                url=r.url,
                title=r.title or "",
                snippet=(r.text or "")[:500],
                published_date=r.published_date,
            )
            results.reddit_results.append(result)
            sub = _extract_subreddit(r.url)
            if sub:
                results.subreddit_counts[sub] += 1

    # Probe 3: Hacker News
    log.info("discovery.hn_probe", n_queries=len(hn_queries))
    for q in hn_queries:
        try:
            response = client.search_and_contents(
                query=q,
                num_results=10,
                include_domains=["news.ycombinator.com"],
                text=True,
                **date_kwargs,
            )
        except Exception as e:
            log.warning("discovery.query_failed", query=q, error=str(e))
            continue

        for r in response.results:
            results.hn_results.append(
                ExaResult(
                    url=r.url,
                    title=r.title or "",
                    snippet=(r.text or "")[:500],
                    published_date=r.published_date,
                )
            )

    # Probe 4: Exa Answer source discovery — finds discussion communities
    # that Exa Search misses (HN threads, niche forums, etc.)
    answer_sources = _discover_sources_via_answer(
        description, competitor_names or [], client
    )
    for url in answer_sources:
        results.domain_counts[_extract_domain(url)] += 1
        sub = _extract_subreddit(url)
        if sub:
            # Boost Answer-discovered subreddits — they're high-confidence
            results.subreddit_counts[sub] += 3

    log.info(
        "discovery.complete",
        general=len(results.general_results),
        reddit=len(results.reddit_results),
        hn=len(results.hn_results),
        subreddits=len(results.subreddit_counts),
        answer_sources=len(answer_sources),
    )
    return results


def _build_general_queries(description: str, key_terms: list[str]) -> list[str]:
    """Build general Exa queries from user description + extracted terms.

    Pure semantic discovery — find where people discuss this market.
    No frustration bias. Pain detection is the pipeline's job (stages 4-6).
    """
    queries = [
        description,  # User's description IS the best semantic query
    ]

    # Add term-specific queries to widen discovery
    for term in key_terms[:4]:
        queries.append(f"{term} discussion")
        queries.append(f"{term} review")

    return queries[:8]  # Cap total queries


def _build_reddit_queries(description: str, key_terms: list[str]) -> list[str]:
    """Build Reddit-targeted queries.

    Finds communities where people discuss this market/product space.
    No frustration pre-filtering — just semantic relevance.
    """
    queries = [
        description,  # Full description — Exa's semantic search handles it
    ]

    for term in key_terms[:4]:
        queries.append(term)  # Bare term finds the broadest community match
        queries.append(f"{term} experience")

    return queries[:8]


def _build_hn_queries(description: str, key_terms: list[str]) -> list[str]:
    """Build HN-targeted queries (fewer, more focused).

    Uses key terms, not the full description — HN search works better
    with concise queries.
    """
    queries = []
    for term in key_terms[:3]:
        queries.append(term)
        queries.append(f"{term} review")

    # If no key terms extracted, use first 10 words of description
    if not queries:
        short = " ".join(description.split()[:10])
        queries.append(short)

    return queries[:5]


def _discover_sources_via_answer(
    description: str,
    competitor_names: list[str],
    client: Exa,
) -> list[str]:
    """Use Exa Answer to discover discussion communities for this market.

    Returns a list of URLs where users discuss problems in this space.
    These get fed into the existing subreddit/domain extraction — we don't
    replace the data collectors, just give them better inputs.
    """
    competitors_str = ", ".join(competitor_names[:5]) if competitor_names else "products in this space"

    query = (
        f"What online communities, forums, subreddits, and Hacker News threads "
        f"discuss problems and frustrations with {competitors_str}? "
        f"Context: {description}"
    )

    schema = {
        "type": "object",
        "properties": {
            "sources": {
                "type": "array",
                "description": "Online communities and discussion threads where users discuss this market",
                "items": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL of the community or discussion thread",
                        },
                        "platform": {
                            "type": "string",
                            "description": "Platform type: reddit, hackernews, forum, review_site, other",
                        },
                    },
                    "required": ["url", "platform"],
                },
            },
        },
        "required": ["sources"],
    }

    log.info("discovery.answer_source_probe")
    try:
        result = client.answer(query, output_schema=schema)
    except Exception as e:
        log.warning("discovery.answer_source_failed", error=str(e))
        return []

    # Parse URLs from the structured answer
    urls = _parse_answer_sources(result)
    log.info("discovery.answer_sources", count=len(urls))
    return urls


def _parse_answer_sources(result) -> list[str]:
    """Extract URLs from an Exa Answer source discovery response."""
    import json as _json

    answer_data = None
    if hasattr(result, "answer"):
        raw = result.answer
        if isinstance(raw, str):
            try:
                answer_data = _json.loads(raw)
            except _json.JSONDecodeError:
                return []
        elif isinstance(raw, dict):
            answer_data = raw
    elif isinstance(result, dict) and "answer" in result:
        raw = result["answer"]
        if isinstance(raw, str):
            try:
                answer_data = _json.loads(raw)
            except _json.JSONDecodeError:
                return []
        elif isinstance(raw, dict):
            answer_data = raw

    if not answer_data:
        return []

    urls = []
    for source in answer_data.get("sources", []):
        url = source.get("url", "").strip()
        if url and url.startswith("http"):
            urls.append(url)

    return urls
