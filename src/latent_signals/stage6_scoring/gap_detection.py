"""Gap detection via cosine similarity between cluster centroids and competitor features."""

from __future__ import annotations

import numpy as np

from latent_signals.utils.logging import get_logger

log = get_logger("gap_detection")


def compute_cluster_centroids(
    embeddings: np.ndarray,
    doc_ids: list[str],
    topic_assignments: dict[str, int],
) -> dict[int, np.ndarray]:
    """Compute centroid embedding for each topic cluster.

    Args:
        embeddings: (N, D) embedding matrix
        doc_ids: ordered list of doc IDs matching embedding rows
        topic_assignments: mapping doc_id -> topic_id

    Returns:
        Mapping of topic_id -> centroid embedding (1, D)
    """
    id_to_idx = {doc_id: i for i, doc_id in enumerate(doc_ids)}
    cluster_vecs: dict[int, list[int]] = {}

    for doc_id, topic_id in topic_assignments.items():
        if topic_id == -1:
            continue
        if doc_id in id_to_idx:
            cluster_vecs.setdefault(topic_id, []).append(id_to_idx[doc_id])

    centroids: dict[int, np.ndarray] = {}
    for topic_id, indices in cluster_vecs.items():
        cluster_embeddings = embeddings[indices]
        centroids[topic_id] = cluster_embeddings.mean(axis=0)

    log.info("centroids.computed", n_clusters=len(centroids))
    return centroids


def compute_max_similarity(
    centroid: np.ndarray, feature_embeddings: np.ndarray
) -> float:
    """Compute max cosine similarity between a cluster centroid and all competitor features."""
    if feature_embeddings.shape[0] == 0:
        return 0.0

    # Normalize
    centroid_norm = centroid / (np.linalg.norm(centroid) + 1e-10)
    feature_norms = feature_embeddings / (
        np.linalg.norm(feature_embeddings, axis=1, keepdims=True) + 1e-10
    )

    similarities = feature_norms @ centroid_norm
    return float(similarities.max())


def compute_per_competitor_coverage(
    centroid: np.ndarray,
    feature_embeddings: np.ndarray,
    competitor_names: list[str],
    threshold: float = 0.5,
) -> dict[str, float]:
    """Compute per-competitor coverage ratio for a cluster centroid.

    Returns mapping of competitor_name -> max similarity score.
    """
    if feature_embeddings.shape[0] == 0:
        return {}

    centroid_norm = centroid / (np.linalg.norm(centroid) + 1e-10)
    feature_norms = feature_embeddings / (
        np.linalg.norm(feature_embeddings, axis=1, keepdims=True) + 1e-10
    )
    similarities = feature_norms @ centroid_norm

    coverage: dict[str, float] = {}
    for i, name in enumerate(competitor_names):
        sim = float(similarities[i])
        coverage[name] = max(coverage.get(name, 0.0), sim)

    return coverage
