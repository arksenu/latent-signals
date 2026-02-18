"""Sentence-transformers embedding wrapper."""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from latent_signals.utils.logging import get_logger

log = get_logger("embedder")


class Embedder:
    """Embed texts using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu") -> None:
        log.info("embedder.loading", model=model_name, device=device)
        self.model = SentenceTransformer(model_name, device=device)
        self.dimensions = self.model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str], batch_size: int = 256) -> np.ndarray:
        """Embed a list of texts. Returns array of shape (N, D)."""
        log.info("embedder.encoding", count=len(texts), batch_size=batch_size)
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
        )
        return np.array(embeddings)
