"""BERTopic topic modeling with UMAP + HDBSCAN."""

from __future__ import annotations

import numpy as np
from bertopic import BERTopic
from hdbscan import HDBSCAN
from umap import UMAP

from latent_signals.config import ClusteringConfig
from latent_signals.utils.logging import get_logger

log = get_logger("topic_model")


def build_topic_model(
    config: ClusteringConfig, random_seed: int = 42, embedding_model_name: str = "all-MiniLM-L6-v2"
) -> BERTopic:
    """Create a BERTopic instance with configured UMAP + HDBSCAN."""
    from sentence_transformers import SentenceTransformer

    umap_model = UMAP(
        n_neighbors=config.umap.n_neighbors,
        n_components=config.umap.n_components,
        min_dist=config.umap.min_dist,
        metric=config.umap.metric,
        random_state=random_seed,
    )

    hdbscan_model = HDBSCAN(
        min_cluster_size=config.hdbscan.min_cluster_size,
        min_samples=config.hdbscan.min_samples,
        metric=config.hdbscan.metric,
        prediction_data=True,
    )

    from bertopic.representation import KeyBERTInspired

    representation_model = KeyBERTInspired()

    nr_topics = config.nr_topics
    if isinstance(nr_topics, str) and nr_topics != "auto":
        nr_topics = int(nr_topics)

    embedding_model = SentenceTransformer(embedding_model_name)

    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        representation_model=representation_model,
        top_n_words=config.top_n_words,
        nr_topics=nr_topics if nr_topics != "auto" else None,
        verbose=True,
    )

    return topic_model


def fit_topics(
    topic_model: BERTopic, docs: list[str], embeddings: np.ndarray
) -> tuple[list[int], np.ndarray]:
    """Fit BERTopic on pre-computed embeddings. Returns (topics, probs)."""
    log.info("topic_model.fitting", n_docs=len(docs))
    topics, probs = topic_model.fit_transform(docs, embeddings)
    n_topics = len(set(topics)) - (1 if -1 in topics else 0)
    n_outliers = sum(1 for t in topics if t == -1)
    log.info("topic_model.fit_complete", n_topics=n_topics, n_outliers=n_outliers)
    return topics, probs
