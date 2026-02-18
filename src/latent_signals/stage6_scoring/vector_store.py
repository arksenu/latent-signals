"""ChromaDB vector store with two separate collections."""

from __future__ import annotations

import chromadb
import numpy as np

from latent_signals.utils.logging import get_logger

log = get_logger("vector_store")


class VectorStore:
    """Manage ChromaDB collections for user needs and competitor features."""

    def __init__(self, persist_dir: str | None = None) -> None:
        if persist_dir:
            self.client = chromadb.PersistentClient(path=persist_dir)
        else:
            self.client = chromadb.Client()

    def create_collection(self, name: str) -> chromadb.Collection:
        """Create or get a collection."""
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_embeddings(
        self,
        collection: chromadb.Collection,
        ids: list[str],
        embeddings: np.ndarray,
        metadatas: list[dict] | None = None,
        documents: list[str] | None = None,
    ) -> None:
        """Add embeddings to a collection in batches."""
        batch_size = 5000
        for i in range(0, len(ids), batch_size):
            end = min(i + batch_size, len(ids))
            kwargs: dict = {
                "ids": ids[i:end],
                "embeddings": embeddings[i:end].tolist(),
            }
            if metadatas:
                kwargs["metadatas"] = metadatas[i:end]
            if documents:
                kwargs["documents"] = documents[i:end]
            collection.add(**kwargs)
        log.info("vector_store.added", collection=collection.name, count=len(ids))

    def query(
        self,
        collection: chromadb.Collection,
        query_embeddings: np.ndarray,
        n_results: int = 10,
    ) -> dict:
        """Query a collection with embedding vectors."""
        return collection.query(
            query_embeddings=query_embeddings.tolist(),
            n_results=n_results,
            include=["distances", "metadatas", "documents"],
        )
