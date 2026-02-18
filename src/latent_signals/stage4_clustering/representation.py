"""Topic label extraction and refinement."""

from __future__ import annotations

from bertopic import BERTopic

from latent_signals.models import TopicInfo


def extract_topic_info(topic_model: BERTopic, docs: list[str], doc_ids: list[str], topics: list[int]) -> list[TopicInfo]:
    """Extract structured topic info from a fitted BERTopic model."""
    topic_info_df = topic_model.get_topic_info()
    result: list[TopicInfo] = []

    for _, row in topic_info_df.iterrows():
        topic_id = row["Topic"]
        if topic_id == -1:
            continue  # Skip outlier topic

        # Get representative doc IDs for this topic
        topic_doc_indices = [i for i, t in enumerate(topics) if t == topic_id]
        rep_ids = [doc_ids[i] for i in topic_doc_indices[:10]]

        # Get keywords
        topic_words = topic_model.get_topic(topic_id)
        keywords = [word for word, _ in topic_words] if topic_words else []

        label = row.get("Name", f"Topic_{topic_id}")
        # Clean up BERTopic's default naming (e.g., "0_word1_word2_word3")
        if label.startswith(f"{topic_id}_"):
            label = label[len(f"{topic_id}_"):]
        label = label.replace("_", " ")

        result.append(
            TopicInfo(
                topic_id=topic_id,
                label=label,
                size=row.get("Count", len(topic_doc_indices)),
                representative_doc_ids=rep_ids,
                keywords=keywords[:10],
            )
        )

    return result
