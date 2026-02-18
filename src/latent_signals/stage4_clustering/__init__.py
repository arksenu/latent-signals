"""Stage 4: Topic Clustering — group documents into topics with BERTopic."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from latent_signals.config import Config
from latent_signals.models import CleanedDocument, TopicAssignment
from latent_signals.stage4_clustering.representation import extract_topic_info
from latent_signals.stage4_clustering.topic_model import build_topic_model, fit_topics
from latent_signals.utils.io import read_json, read_jsonl, read_numpy, write_json, write_jsonl
from latent_signals.utils.logging import get_logger

log = get_logger("stage4")


def run(config: Config, run_id: str) -> None:
    """Cluster documents into topics using BERTopic."""
    base_dir = Path(config.pipeline.output_dir)
    corpus_path = base_dir / "preprocessed" / run_id / "corpus.jsonl"
    embed_path = base_dir / "embeddings" / run_id / "embeddings.npy"
    meta_path = base_dir / "embeddings" / run_id / "doc_ids.json"
    output_dir = base_dir / "clusters" / run_id

    docs = read_jsonl(corpus_path, CleanedDocument)
    embeddings = read_numpy(embed_path)
    meta = read_json(meta_path)
    doc_ids = meta["doc_ids"]
    texts = [d.text for d in docs]

    log.info("stage4.loaded", n_docs=len(docs), embed_shape=embeddings.shape)

    # Build and fit topic model
    topic_model = build_topic_model(
        config.clustering, config.pipeline.random_seed, config.embedding.model_name
    )
    topics, probs = fit_topics(topic_model, texts, embeddings)

    # Extract topic info
    topic_infos = extract_topic_info(topic_model, texts, doc_ids, topics)

    # Build per-document assignments
    assignments: list[TopicAssignment] = []
    topic_label_map = {ti.topic_id: ti.label for ti in topic_infos}
    for i, (doc_id, topic_id) in enumerate(zip(doc_ids, topics)):
        prob = float(probs[i]) if isinstance(probs[i], (float, np.floating)) else float(probs[i].max()) if hasattr(probs[i], 'max') else 0.0
        assignments.append(
            TopicAssignment(
                doc_id=doc_id,
                topic_id=int(topic_id),
                topic_label=topic_label_map.get(int(topic_id), "outlier"),
                topic_probability=prob,
            )
        )

    # Save outputs
    write_jsonl(output_dir / "topic_assignments.jsonl", assignments)
    write_json(output_dir / "topic_info.json", [ti.model_dump() for ti in topic_infos])

    # Save BERTopic model for inspection
    model_dir = output_dir / "bertopic_model"
    model_dir.mkdir(parents=True, exist_ok=True)
    topic_model.save(str(model_dir), serialization="safetensors", save_ctfidf=True)

    log.info("stage4.complete", n_topics=len(topic_infos), n_assignments=len(assignments))
