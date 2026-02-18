"""Stage 1: Data Collection — fetch documents from multiple sources."""

from __future__ import annotations

from pathlib import Path

from latent_signals.config import Config
from latent_signals.models import RawDocument
from latent_signals.stage1_collection.arctic_shift import ArcticShiftCollector
from latent_signals.stage1_collection.apify_collector import ApifyCollector
from latent_signals.stage1_collection.exa_collector import ExaCollector
from latent_signals.stage1_collection.hackernews import HackerNewsCollector
from latent_signals.stage1_collection.serper_collector import SerperCollector
from latent_signals.utils.cost_tracker import CostTracker
from latent_signals.utils.io import write_json, write_jsonl
from latent_signals.utils.logging import get_logger

log = get_logger("stage1")


def run(config: Config, run_id: str, cost_tracker: CostTracker) -> list[RawDocument]:
    """Run all enabled collectors, merge results, write to disk."""
    output_dir = Path(config.pipeline.output_dir) / "raw" / run_id

    collectors = [
        ArcticShiftCollector(config, cost_tracker),
        HackerNewsCollector(config, cost_tracker),
        ExaCollector(config, cost_tracker),
        SerperCollector(config, cost_tracker),
        ApifyCollector(config, cost_tracker),
    ]

    all_docs: list[RawDocument] = []
    stats: dict[str, int] = {}

    for collector in collectors:
        try:
            docs = collector.collect()
            all_docs.extend(docs)
            stats[collector.source_name] = len(docs)
            log.info("collector.done", source=collector.source_name, count=len(docs))
        except Exception as e:
            log.error("collector.failed", source=collector.source_name, error=str(e))
            stats[collector.source_name] = 0

    # Deduplicate across sources by platform_id + source
    seen: set[str] = set()
    unique: list[RawDocument] = []
    for doc in all_docs:
        key = f"{doc.source}:{doc.platform_id}"
        if key not in seen:
            seen.add(key)
            unique.append(doc)

    count = write_jsonl(output_dir / "documents.jsonl", unique)
    stats["total"] = count
    stats["duplicates_removed"] = len(all_docs) - count
    write_json(output_dir / "collection_stats.json", stats)

    log.info("stage1.complete", total=count, stats=stats)
    return unique
