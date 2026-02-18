"""Stage 2: Preprocessing — clean, filter, deduplicate documents."""

from __future__ import annotations

from pathlib import Path

from latent_signals.config import Config
from latent_signals.models import CleanedDocument, RawDocument
from latent_signals.stage2_preprocessing.deduplication import find_duplicates
from latent_signals.stage2_preprocessing.html_cleanup import clean_text
from latent_signals.stage2_preprocessing.language_filter import detect_language
from latent_signals.stage2_preprocessing.length_filter import passes_length_filter
from latent_signals.stage2_preprocessing.noise_filter import is_noise
from latent_signals.utils.io import read_jsonl, write_json, write_jsonl
from latent_signals.utils.logging import get_logger

log = get_logger("stage2")


def run(config: Config, run_id: str) -> list[CleanedDocument]:
    """Preprocess raw documents: clean, filter, deduplicate."""
    input_path = Path(config.pipeline.output_dir) / "raw" / run_id / "documents.jsonl"
    output_dir = Path(config.pipeline.output_dir) / "preprocessed" / run_id
    cfg = config.preprocessing

    raw_docs = read_jsonl(input_path, RawDocument)
    log.info("stage2.loaded", count=len(raw_docs))

    # Step 1: Noise filter (bots, gratitude, [deleted]) — applied on raw docs
    # so we still have access to author field
    pre_noise = len(raw_docs)
    raw_docs = [d for d in raw_docs if not is_noise(d.body, d.author)]
    log.info("stage2.noise_filter", before=pre_noise, after=len(raw_docs))

    # Step 2: Clean text
    cleaned: list[CleanedDocument] = []
    for doc in raw_docs:
        text = clean_text(doc.body)
        cleaned.append(
            CleanedDocument(
                id=doc.id,
                source=doc.source,
                text=text,
                created_at=doc.created_at,
                score=doc.score,
                metadata=doc.metadata,
                char_count=len(text),
            )
        )

    # Step 2: Language filter
    pre_lang = len(cleaned)
    for doc in cleaned:
        doc.language = detect_language(doc.text)
    cleaned = [d for d in cleaned if d.language == cfg.language]
    log.info("stage2.language_filter", before=pre_lang, after=len(cleaned))

    # Step 3: Length filter
    pre_len = len(cleaned)
    cleaned = [d for d in cleaned if passes_length_filter(d.text, cfg.min_length, cfg.max_length)]
    log.info("stage2.length_filter", before=pre_len, after=len(cleaned))

    # Step 4: MinHash deduplication
    texts = {d.id: d.text for d in cleaned}
    duplicate_ids = find_duplicates(texts, cfg.minhash_threshold, cfg.minhash_num_perm)
    for doc in cleaned:
        if doc.id in duplicate_ids:
            doc.is_duplicate = True
    non_dup = [d for d in cleaned if not d.is_duplicate]
    log.info("stage2.dedup", duplicates=len(duplicate_ids), remaining=len(non_dup))

    # Write output (only non-duplicates)
    count = write_jsonl(output_dir / "corpus.jsonl", non_dup)
    write_json(
        output_dir / "dedup_stats.json",
        {
            "raw_count": len(raw_docs),
            "after_language": pre_lang - (pre_lang - len([d for d in cleaned if not d.is_duplicate])),
            "after_length": pre_len,
            "duplicates_flagged": len(duplicate_ids),
            "final_count": count,
        },
    )

    log.info("stage2.complete", final_count=count)
    return non_dup
