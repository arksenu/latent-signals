"""Stage 6: Gap Detection, Scoring, and Report Generation."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from latent_signals.config import Config
from latent_signals.models import ClassifiedDocument, CleanedDocument, TopicAssignment, TopicInfo
from latent_signals.stage3_embedding.embedder import Embedder
from latent_signals.stage6_scoring.competitor_features import embed_features, load_features
from latent_signals.stage6_scoring.report_generator import generate_report
from latent_signals.stage6_scoring.scoring import score_gaps
from latent_signals.utils.io import read_json, read_jsonl, read_numpy, write_json
from latent_signals.utils.logging import get_logger

log = get_logger("stage6")


def run(config: Config, run_id: str) -> None:
    """Run gap detection, scoring, and report generation."""
    base_dir = Path(config.pipeline.output_dir)

    # Load all intermediate data
    corpus = read_jsonl(base_dir / "preprocessed" / run_id / "corpus.jsonl", CleanedDocument)
    embeddings = read_numpy(base_dir / "embeddings" / run_id / "embeddings.npy")
    embed_meta = read_json(base_dir / "embeddings" / run_id / "doc_ids.json")
    doc_ids = embed_meta["doc_ids"]
    assignments = read_jsonl(base_dir / "clusters" / run_id / "topic_assignments.jsonl", TopicAssignment)
    topic_infos_raw = read_json(base_dir / "clusters" / run_id / "topic_info.json")
    topic_infos = [TopicInfo(**t) for t in topic_infos_raw]
    classified = read_jsonl(base_dir / "classified" / run_id / "classified.jsonl", ClassifiedDocument)

    log.info(
        "stage6.loaded",
        n_docs=len(corpus),
        n_topics=len(topic_infos),
        n_classified=len(classified),
    )

    # Load and embed competitor features
    features_path = config.scoring.competitor_features_file
    if not features_path:
        log.warning("stage6.no_features", msg="No competitor features file specified")
        return

    features = load_features(features_path)
    embedder = Embedder(model_name=config.embedding.model_name, device=config.embedding.device)
    features, feature_embeddings = embed_features(features, embedder)

    # Embed market anchor phrases for relevance pre-filtering.
    # Clusters with max cosine similarity below market_relevance_threshold are excluded
    # from scoring — this prevents off-topic clusters (CSS, CORS, SSL certs) from
    # outscoring relevant project-management clusters.
    market_anchor_embeddings: np.ndarray | None = None
    anchors = config.scoring.market_anchors
    if anchors:
        market_anchor_embeddings = embedder.embed(anchors, batch_size=64)
        log.info("stage6.market_anchors", n_anchors=len(anchors))

    # Build text and date lookups
    doc_texts = {d.id: d.text for d in corpus}
    doc_dates = {d.id: d.created_at for d in corpus}

    # Score gaps
    opportunities = score_gaps(
        topic_infos=topic_infos,
        assignments=assignments,
        classified_docs=classified,
        embeddings=embeddings,
        doc_ids=doc_ids,
        feature_embeddings=feature_embeddings,
        features=features,
        doc_texts=doc_texts,
        doc_dates=doc_dates,
        weights=config.scoring.weights,
        top_n=config.scoring.top_n_opportunities,
        market_anchor_embeddings=market_anchor_embeddings,
        market_relevance_threshold=config.scoring.market_relevance_threshold,
        min_signal_ratio=config.scoring.min_signal_ratio,
        unaddressedness_floor=config.scoring.unaddressedness_floor,
    )

    # Generate report
    output_dir = base_dir / "reports" / run_id
    report = generate_report(
        opportunities=opportunities,
        market_category=config.pipeline.market_category,
        run_id=run_id,
        output_path=output_dir / "gap_report.md",
        max_quotes_per_gap=config.report.max_quotes_per_gap,
        weights=config.scoring.weights.model_dump(),
    )

    # Save structured scores
    write_json(
        output_dir / "gap_scores.json",
        [g.model_dump() for g in opportunities],
    )

    log.info("stage6.complete", n_opportunities=len(opportunities))
