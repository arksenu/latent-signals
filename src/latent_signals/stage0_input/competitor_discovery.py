"""Competitor discovery via Exa Answer API.

Takes the user's market description and extracts competitors + features
using Exa's Answer endpoint with a structured output schema.

This replaces the manual competitor feature YAML files used in backtests.
NER (Stage 5) is still used per-cluster for coverage/satisfaction gap detection —
this module handles competitor *identification*, not per-document entity counting.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import yaml
from exa_py import Exa

from latent_signals.models import CompetitorFeature
from latent_signals.utils.logging import get_logger

log = get_logger("competitor_discovery")


def discover_competitors(
    user_description: str,
    exa_api_key: str,
    *,
    cache_dir: Path | None = None,
    cache_ttl_days: int = 30,
) -> list[CompetitorFeature]:
    """Extract competitors and their features using Exa Answer.

    Args:
        user_description: Rich text description of the market/product/competitors.
        exa_api_key: Exa API key.
        cache_dir: Directory for caching competitor profiles. If None, no caching.
        cache_ttl_days: Cache staleness threshold in days.

    Returns:
        List of CompetitorFeature objects (one per feature per competitor).
    """
    # Check cache first
    if cache_dir:
        cached = _load_cache(user_description, cache_dir, cache_ttl_days)
        if cached is not None:
            log.info("competitor_discovery.cache_hit", n_features=len(cached))
            return cached

    # Build the Exa Answer query
    query = (
        f"What are the main competitor products in this market and what are "
        f"their key features? Context: {user_description}"
    )

    client = Exa(api_key=exa_api_key)

    schema = {
        "type": "object",
        "properties": {
            "competitors": {
                "type": "array",
                "description": "List of competitor products in this market",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Product or company name",
                        },
                        "features": {
                            "type": "array",
                            "description": "Key features and capabilities of this product",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["name", "features"],
                },
            },
        },
        "required": ["competitors"],
    }

    log.info("competitor_discovery.calling_exa_answer")
    try:
        result = client.answer(
            query,
            output_schema=schema,
        )
    except Exception as e:
        log.error("competitor_discovery.exa_answer_failed", error=str(e))
        return []

    # Parse the structured response
    features = _parse_answer_response(result)
    log.info(
        "competitor_discovery.complete",
        n_competitors=len({f.competitor_name for f in features}),
        n_features=len(features),
    )

    # Cache results
    if cache_dir and features:
        _save_cache(user_description, features, cache_dir)

    return features


def _parse_answer_response(result) -> list[CompetitorFeature]:
    """Parse Exa Answer response into CompetitorFeature objects."""
    features: list[CompetitorFeature] = []

    # Exa Answer returns a result object with an `answer` field (JSON string)
    answer_data = None
    if hasattr(result, "answer"):
        answer_raw = result.answer
        if isinstance(answer_raw, str):
            try:
                answer_data = json.loads(answer_raw)
            except json.JSONDecodeError:
                log.warning("competitor_discovery.json_parse_failed", raw=answer_raw[:200])
                return []
        elif isinstance(answer_raw, dict):
            answer_data = answer_raw
    elif isinstance(result, dict) and "answer" in result:
        answer_raw = result["answer"]
        if isinstance(answer_raw, str):
            try:
                answer_data = json.loads(answer_raw)
            except json.JSONDecodeError:
                return []
        elif isinstance(answer_raw, dict):
            answer_data = answer_raw

    if not answer_data:
        log.warning("competitor_discovery.no_answer_data")
        return []

    competitors = answer_data.get("competitors", [])
    for comp in competitors:
        name = comp.get("name", "").strip()
        if not name:
            continue
        for i, feat_desc in enumerate(comp.get("features", [])):
            if isinstance(feat_desc, str) and feat_desc.strip():
                features.append(
                    CompetitorFeature(
                        feature_id=f"{name}_{i}",
                        competitor_name=name,
                        description=feat_desc.strip(),
                    )
                )

    return features


def save_features_yaml(
    features: list[CompetitorFeature],
    output_path: Path,
) -> Path:
    """Save competitor features to a multi-competitor YAML file.

    Format compatible with the existing load_features() in stage6.
    Uses a list of competitor blocks instead of single-competitor format.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Group by competitor
    by_competitor: dict[str, list[str]] = {}
    for f in features:
        by_competitor.setdefault(f.competitor_name, []).append(f.description)

    data = {
        "competitors": [
            {"competitor_name": name, "features": feats}
            for name, feats in by_competitor.items()
        ]
    }

    with open(output_path, "w") as fh:
        yaml.dump(data, fh, default_flow_style=False, allow_unicode=True)

    log.info("competitor_discovery.saved_yaml", path=str(output_path))
    return output_path


# --- Caching ---


def _cache_key(description: str) -> str:
    """Deterministic cache key from user description."""
    normalized = description.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _cache_path(description: str, cache_dir: Path) -> Path:
    """Path to cached competitor features file."""
    key = _cache_key(description)
    return cache_dir / f"competitors_{key}.json"


def _load_cache(
    description: str, cache_dir: Path, ttl_days: int
) -> list[CompetitorFeature] | None:
    """Load cached competitor features if fresh enough."""
    path = _cache_path(description, cache_dir)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    cached_at = data.get("cached_at", 0)
    age_days = (time.time() - cached_at) / 86400
    if age_days > ttl_days:
        log.info("competitor_discovery.cache_stale", age_days=round(age_days, 1))
        return None

    features = []
    for entry in data.get("features", []):
        features.append(CompetitorFeature(**entry))
    return features


def _save_cache(
    description: str,
    features: list[CompetitorFeature],
    cache_dir: Path,
) -> None:
    """Save competitor features to cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(description, cache_dir)

    data = {
        "cached_at": time.time(),
        "description": description,
        "features": [f.model_dump() for f in features],
    }
    path.write_text(json.dumps(data, indent=2))
    log.info("competitor_discovery.cached", path=str(path))
