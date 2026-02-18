"""Stage 3: Embedding — compute document embeddings with sentence-transformers."""

from __future__ import annotations

from pathlib import Path

from latent_signals.config import Config
from latent_signals.models import CleanedDocument, EmbeddingMeta
from latent_signals.stage3_embedding.embedder import Embedder
from latent_signals.utils.io import read_jsonl, write_json, write_numpy
from latent_signals.utils.logging import get_logger

log = get_logger("stage3")


def run(config: Config, run_id: str) -> None:
    """Embed all preprocessed documents."""
    input_path = Path(config.pipeline.output_dir) / "preprocessed" / run_id / "corpus.jsonl"
    output_dir = Path(config.pipeline.output_dir) / "embeddings" / run_id
    cfg = config.embedding

    docs = read_jsonl(input_path, CleanedDocument)
    log.info("stage3.loaded", count=len(docs))

    embedder = Embedder(model_name=cfg.model_name, device=cfg.device)
    texts = [d.text for d in docs]
    embeddings = embedder.embed(texts, batch_size=cfg.batch_size)

    write_numpy(output_dir / "embeddings.npy", embeddings)

    meta = EmbeddingMeta(
        doc_ids=[d.id for d in docs],
        model_name=cfg.model_name,
        dimensions=embedder.dimensions,
        count=len(docs),
    )
    write_json(output_dir / "doc_ids.json", meta.model_dump())

    log.info("stage3.complete", count=len(docs), dimensions=embedder.dimensions)
