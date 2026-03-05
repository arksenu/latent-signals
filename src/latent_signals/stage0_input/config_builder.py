"""Build a pipeline Config from Stage 0 discovery outputs.

Takes user query + discovery/source/anchor results and produces
a fully populated Config object ready for run_pipeline().
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

from latent_signals.config import (
    ArcticShiftConfig,
    ClassificationConfig,
    ClusteringConfig,
    CollectionConfig,
    Config,
    EmbeddingConfig,
    ExaConfig,
    HackerNewsConfig,
    PipelineConfig,
    ScoringConfig,
    SerperConfig,
)
from latent_signals.stage0_input.source_extraction import ValidatedSources
from latent_signals.utils.logging import get_logger

log = get_logger("stage0.config_builder")

load_dotenv()


def build_config(
    user_query: str,
    sources: ValidatedSources,
    anchors: list[str],
    *,
    date_start: str | None = None,
    date_end: str | None = None,
    output_dir: str = "data",
    competitor_features_file: str = "",
) -> Config:
    """Build a complete pipeline Config from Stage 0 outputs.

    Args:
        user_query: Original user query string.
        sources: Validated subreddits and HN queries from source extraction.
        anchors: Market anchor phrases from anchor generation.
        date_start: Collection start date (default: 12 months ago).
        date_end: Collection end date (default: today).
        output_dir: Base output directory.
        competitor_features_file: Path to competitor features YAML (from Stage 0b).
    """
    # Default date range: last 12 months
    if not date_end:
        date_end = datetime.now().strftime("%Y-%m-%d")
    if not date_start:
        end_dt = datetime.strptime(date_end, "%Y-%m-%d")
        start_dt = end_dt - timedelta(days=365)
        date_start = start_dt.strftime("%Y-%m-%d")

    # Determine Arctic Shift max_items based on number of subreddits
    n_subs = len(sources.subreddits)
    # ~1500 items per subreddit, capped at 20k total
    arctic_max = min(n_subs * 1500, 20000) if n_subs > 0 else 0

    # Extract a short market label from the description
    market_label = _extract_market_label(user_query)

    config = Config(
        pipeline=PipelineConfig(
            market_category=market_label,
            output_dir=output_dir,
        ),
        collection=CollectionConfig(
            date_range={"start": date_start, "end": date_end},
            exa=ExaConfig(
                enabled=False,  # Exa already used in discovery; don't double-collect
            ),
            serper=SerperConfig(
                enabled=False,  # Not needed when Arctic Shift provides Reddit data
            ),
            arctic_shift=ArcticShiftConfig(
                enabled=n_subs > 0,
                subreddits=sources.subreddits,
                max_items=arctic_max,
            ),
            hackernews=HackerNewsConfig(
                enabled=sources.hn_has_signal,
                queries=sources.hn_queries,
                max_items=5000,
            ),
        ),
        embedding=EmbeddingConfig(
            post_relevance_threshold=0.20,  # Validated default from backtests
        ),
        clustering=ClusteringConfig(
            nr_topics=60,  # Fixed across all backtests
        ),
        scoring=ScoringConfig(
            market_anchors=anchors,
            market_relevance_threshold=0.30,  # Tightened from 0.20 to filter off-topic clusters
            min_signal_ratio=0.15,
            unaddressedness_floor=0.15,
            competitor_features_file=competitor_features_file,
        ),
        # API keys from environment
        exa_api_key=os.environ.get("EXA_API_KEY", ""),
        serper_api_key=os.environ.get("SERPER_API_KEY", ""),
        apify_api_token=os.environ.get("APIFY_API_TOKEN", ""),
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
    )

    log.info(
        "config.built",
        market=market_label,
        subreddits=len(sources.subreddits),
        hn_enabled=sources.hn_has_signal,
        anchors=len(anchors),
        date_range=f"{date_start} to {date_end}",
        has_competitors=bool(competitor_features_file),
    )
    return config


def _extract_market_label(description: str) -> str:
    """Extract a short market category label from a rich description.

    Uses simple heuristics — no LLM. Falls back to first few words.
    """
    desc_lower = description.lower()

    import re

    # Look for "the X space/market/industry" — greedy to capture "project management and bug tracking"
    m = re.search(r"\bthe\s+([\w\s]{3,40}?)\s+(?:space|market|industry|sector|category)\b", desc_lower)
    if m:
        return m.group(1).strip()

    # Look for "X space/market is"
    m = re.search(r"\b(\w+(?:\s+\w+){0,3}?)\s+(?:space|market|industry|sector)\s+is\b", desc_lower)
    if m:
        return m.group(1).strip()

    # Look for "building a/an X for"
    m = re.search(r"building\s+(?:a|an)\s+(.+?)(?:\s+for\b|\s+that\b|\s+to\b|[.,])", desc_lower)
    if m:
        label = m.group(1).strip()
        # Cap at 5 words
        words = label.split()[:5]
        return " ".join(words)

    # Fall back to first 4 meaningful words
    stop = {"we", "we're", "i", "i'm", "our", "my", "the", "a", "an", "is", "are"}
    words = [w for w in description.split() if w.lower().strip(".,!?") not in stop]
    return " ".join(words[:4]).lower().strip(".,!?")
