"""Stage 5: Classification — sentiment, zero-shot categories, LLM extraction."""

from __future__ import annotations

from pathlib import Path

from latent_signals.config import Config
from latent_signals.models import ClassifiedDocument, CleanedDocument, TopicAssignment, TopicInfo
from latent_signals.stage5_classification.llm_extraction import extract_batch
from latent_signals.stage5_classification.sampling import sample_representative_posts
from latent_signals.stage5_classification.sentiment import batch_sentiment
from latent_signals.stage5_classification.zero_shot import ZeroShotClassifier
from latent_signals.utils.cost_tracker import CostTracker
from latent_signals.utils.io import read_json, read_jsonl, write_json, write_jsonl
from latent_signals.utils.logging import get_logger

log = get_logger("stage5")


import re

# Keyword patterns that strongly indicate a feature request, regardless of sentiment.
# These catch polite requests ("I wish Jira had...") that VADER scores as neutral/positive.
_FEATURE_REQUEST_PATTERNS = [
    r"\bi wish\b.*\bhad\b",
    r"\bi wish\b.*\bcould\b",
    r"\bi wish\b.*\bwould\b",
    r"\bit would be (?:nice|great|awesome|cool)\b.+\bif\b",
    r"\bwould be (?:nice|great|awesome|cool)\b.+\bif\b",
    r"\bwhy (?:can't|doesn't|isn't|won't)\b",
    r"\bwhy is there no\b",
    r"\bneeds? (?:a |an |to )\b",
    r"\bshould (?:have|support|add|allow|include|provide)\b",
    r"\bplease add\b",
    r"\bfeature request\b",
    r"\bcan we get\b",
    r"\bwhen will .+ support\b",
    r"\bwanting .+ feature\b",
    r"\blacking .+ feature\b",
    r"\bmissing .+ feature\b",
    r"\bdoesn't (?:have|support|allow)\b",
    r"\bcan't even\b",
    r"\bno way to\b",
    r"\bno option to\b",
    r"\bno ability to\b",
]
_FR_RE = re.compile("|".join(_FEATURE_REQUEST_PATTERNS), re.IGNORECASE)

# Keyword patterns that indicate a pain point, even with neutral/positive VADER.
_PAIN_POINT_PATTERNS = [
    r"\bfrustrat(?:ing|ed|ion)\b",
    r"\bbloat(?:ed|ware)?\b",
    r"\bslow (?:as|and)\b",
    r"\bterrible\b",
    r"\bawful\b",
    r"\bunusable\b",
    r"\bdumpster fire\b",
    r"\bnightmare\b",
    r"\bhate (?:using|this|it|jira)\b",
    r"\bpain(?:ful| point| in the)\b",
    r"\boverwhel?m(?:ing|ed)\b",
    r"\boverly complex\b",
    r"\btoo complicated\b",
    r"\bsteep learning curve\b",
]
_PP_RE = re.compile("|".join(_PAIN_POINT_PATTERNS), re.IGNORECASE)


def _vader_heuristic(compound: float, text: str = "") -> tuple[str, float]:
    """Assign category from VADER compound score + keyword overrides.

    Conservative heuristic — used for bulk docs that don't get zero-shot.
    Keyword patterns override sentiment when feature-request or pain-point
    language is detected regardless of VADER polarity.
    """
    # Keyword overrides take precedence
    if text and _FR_RE.search(text):
        return "feature_request", 0.7
    if text and _PP_RE.search(text):
        return "pain_point", 0.7

    if compound <= -0.3:
        return "pain_point", min(abs(compound), 0.9)
    elif compound >= 0.3:
        return "praise", min(compound, 0.9)
    else:
        return "question", 0.5


def run(config: Config, run_id: str, cost_tracker: CostTracker) -> list[ClassifiedDocument]:
    """Run sentiment analysis, zero-shot classification, and LLM extraction."""
    base_dir = Path(config.pipeline.output_dir)
    corpus_path = base_dir / "preprocessed" / run_id / "corpus.jsonl"
    assignments_path = base_dir / "clusters" / run_id / "topic_assignments.jsonl"
    topic_info_path = base_dir / "clusters" / run_id / "topic_info.json"
    output_dir = base_dir / "classified" / run_id

    docs = read_jsonl(corpus_path, CleanedDocument)
    assignments = read_jsonl(assignments_path, TopicAssignment)
    topic_infos_raw = read_json(topic_info_path)
    topic_infos = [TopicInfo(**t) for t in topic_infos_raw]

    doc_map = {d.id: d for d in docs}
    log.info("stage5.loaded", n_docs=len(docs), n_topics=len(topic_infos))

    # Step 1: VADER sentiment on all documents (fast — ~100k texts/sec)
    texts = [d.text for d in docs]
    sentiments = batch_sentiment(texts)
    log.info("stage5.vader_complete", count=len(sentiments))

    # Step 2: Sample representative posts per cluster (before zero-shot)
    samples = sample_representative_posts(
        assignments, topic_infos,
        samples_per_cluster=config.classification.llm_extraction.samples_per_cluster,
        max_clusters=config.classification.llm_extraction.max_clusters,
    )
    sampled_ids: set[str] = set()
    for doc_ids in samples.values():
        sampled_ids.update(doc_ids)
    log.info("stage5.sampled", total_sampled=len(sampled_ids))

    # Step 3: Zero-shot classification on sampled subset only
    # VADER heuristic covers bulk docs; zero-shot gives precision on the subset that matters
    sampled_texts_for_zs: list[str] = []
    sampled_doc_ids_for_zs: list[str] = []
    for doc_id in sampled_ids:
        if doc_id in doc_map:
            sampled_texts_for_zs.append(doc_map[doc_id].text)
            sampled_doc_ids_for_zs.append(doc_id)

    zs_results: dict[str, tuple[str, float]] = {}
    if sampled_texts_for_zs:
        classifier = ZeroShotClassifier(
            model_name=config.classification.zero_shot.model_name
        )
        categories = classifier.classify_batch(
            sampled_texts_for_zs, batch_size=config.classification.zero_shot.batch_size
        )
        for doc_id, (cat, conf) in zip(sampled_doc_ids_for_zs, categories):
            zs_results[doc_id] = (cat, conf)
        log.info("stage5.zero_shot_complete", count=len(zs_results))

    # Step 4: Build classified documents — zero-shot for sampled, VADER heuristic for rest
    classified: dict[str, ClassifiedDocument] = {}
    for i, doc in enumerate(docs):
        sent = sentiments[i]
        if doc.id in zs_results:
            cat, conf = zs_results[doc.id]
        else:
            cat, conf = _vader_heuristic(sent["compound"], doc.text)

        classified[doc.id] = ClassifiedDocument(
            doc_id=doc.id,
            vader_compound=sent["compound"],
            vader_pos=sent["pos"],
            vader_neg=sent["neg"],
            vader_neu=sent["neu"],
            category=cat,
            category_confidence=conf,
        )

    # Step 5: LLM extraction on sampled posts per cluster
    llm_cfg = config.classification.llm_extraction
    if llm_cfg.enabled and config.openai_api_key:
        sampled_texts: dict[str, str] = {}
        for topic_id, doc_ids in samples.items():
            for doc_id in doc_ids:
                if doc_id in doc_map:
                    sampled_texts[doc_id] = doc_map[doc_id].text

        log.info("stage5.llm_extraction", total_sampled=len(sampled_texts))

        if sampled_texts:
            extractions = extract_batch(
                sampled_texts,
                api_key=config.openai_api_key,
                model=llm_cfg.model,
                use_batch_api=llm_cfg.use_batch_api,
                output_dir=output_dir,
            )

            # Merge LLM results into classified documents
            for doc_id, extraction in extractions.items():
                if doc_id in classified:
                    classified[doc_id].llm_pain_points = extraction.pain_points
                    classified[doc_id].llm_feature_requests = extraction.feature_requests
                    classified[doc_id].llm_urgency = extraction.urgency
                    classified[doc_id].llm_products_mentioned = extraction.products_mentioned
                    if hasattr(extraction, "gap_type"):
                        classified[doc_id].llm_gap_type = extraction.gap_type

            avg_tokens = sum(len(t.split()) * 1.3 for t in sampled_texts.values()) / max(len(sampled_texts), 1)
            estimated_cost = (avg_tokens * len(sampled_texts) / 1_000_000) * 0.075
            cost_tracker.add("openai", estimated_cost)
            log.info("stage5.llm_complete", extracted=len(extractions), estimated_cost=f"${estimated_cost:.4f}")

    # Step 6: NER entity extraction (product/company names for branching trigger)
    # Uses en_core_web_lg (fast, sufficient for product names) on all docs.
    try:
        import spacy
        nlp = spacy.load("en_core_web_lg", disable=["parser", "lemmatizer", "textcat"])
        log.info("stage5.ner_starting", n_docs=len(docs))
        ner_entity_types = {"ORG", "PRODUCT"}
        for doc_batch in _batch_iter(docs, batch_size=500):
            texts_for_ner = [d.text[:1000] for d in doc_batch]  # Cap text length for speed
            for spacy_doc, orig_doc in zip(nlp.pipe(texts_for_ner, batch_size=64), doc_batch):
                entities = [
                    {"text": ent.text, "label": ent.label_}
                    for ent in spacy_doc.ents
                    if ent.label_ in ner_entity_types
                ]
                if entities and orig_doc.id in classified:
                    classified[orig_doc.id].entities = entities
        n_with_entities = sum(1 for c in classified.values() if c.entities)
        log.info("stage5.ner_complete", docs_with_entities=n_with_entities)
    except (ImportError, OSError) as e:
        log.warning("stage5.ner_skipped", reason=str(e))

    # Write output
    classified_list = list(classified.values())
    write_jsonl(output_dir / "classified.jsonl", classified_list)
    write_json(output_dir / "classification_stats.json", {
        "total_docs": len(classified_list),
        "category_distribution": _count_categories(classified_list),
        "avg_sentiment": sum(c.vader_compound for c in classified_list) / max(len(classified_list), 1),
        "zero_shot_count": len(zs_results),
        "vader_heuristic_count": len(classified_list) - len(zs_results),
    })

    log.info("stage5.complete", count=len(classified_list))
    return classified_list


def _count_categories(docs: list[ClassifiedDocument]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in docs:
        counts[d.category] = counts.get(d.category, 0) + 1
    return counts


def _batch_iter(items: list, batch_size: int = 500):
    """Yield successive batches from items list."""
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]
