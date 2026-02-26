"""Stage 3: Embedding — compute document embeddings with sentence-transformers."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from latent_signals.config import Config
from latent_signals.models import CleanedDocument, EmbeddingMeta
from latent_signals.stage3_embedding.embedder import Embedder
from latent_signals.utils.io import read_jsonl, write_json, write_jsonl, write_numpy
from latent_signals.utils.logging import get_logger

log = get_logger("stage3")


def _filter_by_market_relevance(
    docs: list[CleanedDocument],
    embeddings: np.ndarray,
    embedder: Embedder,
    market_anchors: list[str],
    threshold: float,
) -> tuple[list[CleanedDocument], np.ndarray]:
    """Drop documents whose max cosine similarity to market anchors is below threshold.

    This prevents off-topic posts from broad subreddits (r/degoogle, r/privacy)
    from forming garbage clusters about browsers, Android, politics, etc.
    """
    anchor_embeddings = embedder.embed(market_anchors, batch_size=64)

    # Normalize both matrices for cosine similarity via dot product
    doc_norms = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-10)
    anchor_norms = anchor_embeddings / (
        np.linalg.norm(anchor_embeddings, axis=1, keepdims=True) + 1e-10
    )

    # (N_docs, N_anchors) similarity matrix
    similarities = doc_norms @ anchor_norms.T
    max_sims = similarities.max(axis=1)  # best anchor match per doc

    keep_mask = max_sims >= threshold
    n_dropped = int((~keep_mask).sum())

    filtered_docs = [d for d, keep in zip(docs, keep_mask) if keep]
    filtered_embeddings = embeddings[keep_mask]

    log.info(
        "stage3.post_relevance_filter",
        threshold=threshold,
        n_anchors=len(market_anchors),
        n_before=len(docs),
        n_after=len(filtered_docs),
        n_dropped=n_dropped,
    )

    return filtered_docs, filtered_embeddings


def run(config: Config, run_id: str) -> None:
    """Embed all preprocessed documents, optionally filtering by market relevance."""
    input_path = Path(config.pipeline.output_dir) / "preprocessed" / run_id / "corpus.jsonl"
    output_dir = Path(config.pipeline.output_dir) / "embeddings" / run_id
    cfg = config.embedding

    docs = read_jsonl(input_path, CleanedDocument)
    log.info("stage3.loaded", count=len(docs))

    embedder = Embedder(model_name=cfg.model_name, device=cfg.device)
    texts = [d.text for d in docs]
    embeddings = embedder.embed(texts, batch_size=cfg.batch_size)

    # Post-level market relevance filter: drop off-topic documents before clustering.
    # Uses market_anchors from scoring config and threshold from embedding config.
    market_anchors = config.scoring.market_anchors
    threshold = cfg.post_relevance_threshold
    if market_anchors and threshold > 0:
        docs, embeddings = _filter_by_market_relevance(
            docs, embeddings, embedder, market_anchors, threshold
        )
        # Write filtered corpus so downstream stages (4, 5, 6) use consistent doc set
        filtered_corpus_path = Path(config.pipeline.output_dir) / "preprocessed" / run_id / "corpus.jsonl"
        write_jsonl(filtered_corpus_path, docs)
        log.info("stage3.filtered_corpus_written", path=str(filtered_corpus_path))

    write_numpy(output_dir / "embeddings.npy", embeddings)

    meta = EmbeddingMeta(
        doc_ids=[d.id for d in docs],
        model_name=cfg.model_name,
        dimensions=embedder.dimensions,
        count=len(docs),
    )
    write_json(output_dir / "doc_ids.json", meta.model_dump())

    log.info("stage3.complete", count=len(docs), dimensions=embedder.dimensions)
