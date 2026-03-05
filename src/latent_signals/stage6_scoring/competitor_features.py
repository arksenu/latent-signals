"""Load and embed competitor feature sets from YAML config."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

from latent_signals.models import CompetitorFeature
from latent_signals.stage3_embedding.embedder import Embedder
from latent_signals.utils.logging import get_logger

log = get_logger("competitor_features")


def load_features(features_path: str | Path) -> list[CompetitorFeature]:
    """Load competitor features from a YAML file.

    Supports two formats:
      - Single-competitor (backtest): {competitor_name: "X", features: [...]}
      - Multi-competitor (Stage 0b): {competitors: [{competitor_name: "X", features: [...]}, ...]}
    """
    path = Path(features_path)
    if not path.exists():
        raise FileNotFoundError(f"Competitor features file not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    features: list[CompetitorFeature] = []

    if "competitors" in data:
        # Multi-competitor format (from Exa Answer / Stage 0b)
        for comp in data["competitors"]:
            competitor_name = comp.get("competitor_name", "unknown")
            for i, feat in enumerate(comp.get("features", [])):
                features.append(
                    CompetitorFeature(
                        feature_id=f"{competitor_name}_{i}",
                        competitor_name=competitor_name,
                        description=feat if isinstance(feat, str) else feat.get("description", ""),
                        category=feat.get("category") if isinstance(feat, dict) else None,
                    )
                )
        log.info("features.loaded", n_competitors=len(data["competitors"]), count=len(features))
    else:
        # Single-competitor format (backtest YAML files)
        competitor_name = data.get("competitor_name", "unknown")
        for i, feat in enumerate(data.get("features", [])):
            features.append(
                CompetitorFeature(
                    feature_id=f"{competitor_name}_{i}",
                    competitor_name=competitor_name,
                    description=feat if isinstance(feat, str) else feat.get("description", ""),
                    category=feat.get("category") if isinstance(feat, dict) else None,
                )
            )
        log.info("features.loaded", competitor=competitor_name, count=len(features))

    return features


def embed_features(
    features: list[CompetitorFeature], embedder: Embedder
) -> tuple[list[CompetitorFeature], np.ndarray]:
    """Embed competitor feature descriptions."""
    texts = [f.description for f in features]
    embeddings = embedder.embed(texts, batch_size=64)
    return features, embeddings
