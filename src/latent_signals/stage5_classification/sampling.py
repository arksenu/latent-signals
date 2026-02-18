"""Representative post sampling for LLM extraction."""

from __future__ import annotations

from latent_signals.models import TopicAssignment, TopicInfo


def sample_representative_posts(
    assignments: list[TopicAssignment],
    topic_infos: list[TopicInfo],
    samples_per_cluster: int = 75,
    max_clusters: int = 50,
) -> dict[int, list[str]]:
    """Select representative doc IDs per topic cluster for LLM extraction.

    Returns mapping of topic_id -> list of doc_ids to sample.
    Selects by highest topic_probability within each cluster.
    """
    # Group assignments by topic
    topic_docs: dict[int, list[TopicAssignment]] = {}
    for a in assignments:
        if a.topic_id == -1:
            continue  # Skip outliers
        topic_docs.setdefault(a.topic_id, []).append(a)

    # Sort topics by size (largest first), take top max_clusters
    sorted_topics = sorted(topic_docs.keys(), key=lambda t: len(topic_docs[t]), reverse=True)
    selected_topics = sorted_topics[:max_clusters]

    samples: dict[int, list[str]] = {}
    for topic_id in selected_topics:
        docs = topic_docs[topic_id]
        # Sort by topic probability (highest first)
        docs.sort(key=lambda d: d.topic_probability, reverse=True)
        sample_ids = [d.doc_id for d in docs[:samples_per_cluster]]
        samples[topic_id] = sample_ids

    return samples
