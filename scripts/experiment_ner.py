"""
NER Experiment: Extract product/company entities from 5 backtest corpora.

Pass criteria:
  1. Known competitors appear in top 5 entities by frequency
  2. Identify minimum frequency cutoff that captures all known competitors
  3. Full frequency distribution (positions 1-20+) for natural cliff vs long tail

Run: python scripts/experiment_ner.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import spacy

# Backtest cases: run_id -> (label, known_competitors)
CASES = {
    "7c16def9": ("Linear", ["jira"]),
    "b4612a0d": ("Notion", ["evernote", "onenote"]),
    "0fb9aed4": ("Plausible", ["google analytics"]),
    "0e03b7a3": ("Email", ["gmail"]),
    "fa17ead6": ("VS Code", ["vs code", "visual studio code", "vscode"]),
}

# Normalize entity text for matching
ENTITY_ALIASES: dict[str, str] = {
    "visual studio code": "vs code",
    "vscode": "vs code",
    "visual studio": "vs code",
    "ga": "google analytics",
    "g suite": "gmail",
    "google mail": "gmail",
    "one note": "onenote",
}


def normalize_entity(text: str) -> str:
    """Normalize entity text: lowercase, strip, apply aliases."""
    t = text.lower().strip()
    return ENTITY_ALIASES.get(t, t)


def run_ner_experiment(run_id: str, label: str, known_competitors: list[str], nlp) -> dict:
    """Run NER on a single backtest corpus."""
    corpus_path = Path(f"data/preprocessed/{run_id}/corpus.jsonl")
    if not corpus_path.exists():
        print(f"  SKIP: {corpus_path} not found")
        return {}

    # Load corpus
    texts = []
    with open(corpus_path) as f:
        for line in f:
            doc = json.loads(line)
            texts.append(doc["text"])

    print(f"  Corpus size: {len(texts)} posts")

    # Run NER in batches (spaCy pipe is efficient)
    entity_counter: Counter = Counter()
    entity_types: dict[str, set[str]] = {}

    # Only process ORG, PRODUCT, and WORK_OF_ART entities
    target_labels = {"ORG", "PRODUCT", "WORK_OF_ART"}

    batch_size = 256
    processed = 0
    for doc in nlp.pipe(
        (t[:1000] for t in texts),  # truncate long posts
        batch_size=batch_size,
        disable=["tagger", "parser", "lemmatizer", "attribute_ruler"],
    ):
        for ent in doc.ents:
            if ent.label_ in target_labels:
                normalized = normalize_entity(ent.text)
                # Skip very short entities (1-2 chars) and purely numeric
                if len(normalized) < 3 or normalized.isdigit():
                    continue
                entity_counter[normalized] += 1
                if normalized not in entity_types:
                    entity_types[normalized] = set()
                entity_types[normalized].add(ent.label_)
        processed += 1
        if processed % 1000 == 0:
            print(f"  Processed {processed}/{len(texts)} posts...")

    print(f"  Unique entities found: {len(entity_counter)}")

    # Analyze results
    top_25 = entity_counter.most_common(25)

    # Find where known competitors rank
    known_lower = [k.lower() for k in known_competitors]
    competitor_ranks = {}
    for rank, (entity, count) in enumerate(entity_counter.most_common(), 1):
        if entity in known_lower:
            competitor_ranks[entity] = {"rank": rank, "count": count}

    # Check pass condition 1: all known competitors in top 5
    all_in_top5 = all(
        any(entity in known_lower for entity, _ in top_25[:5])
        for _ in [None]  # dummy - check if ANY known competitor is in top 5
    )
    # More precise: check each known competitor
    found_competitors = {k: competitor_ranks.get(k, {"rank": "NOT FOUND", "count": 0}) for k in known_lower}

    # Find minimum frequency that captures all known competitors
    if competitor_ranks:
        min_competitor_freq = min(v["count"] for v in competitor_ranks.values())
    else:
        min_competitor_freq = 0

    # Count how many entities above and below that threshold
    entities_above_threshold = sum(1 for _, c in entity_counter.items() if c >= min_competitor_freq)
    entities_below_threshold = len(entity_counter) - entities_above_threshold

    return {
        "label": label,
        "run_id": run_id,
        "corpus_size": len(texts),
        "unique_entities": len(entity_counter),
        "top_25": [(e, c, list(entity_types.get(e, set()))) for e, c, in top_25],
        "known_competitors": found_competitors,
        "min_competitor_freq": min_competitor_freq,
        "entities_above_min_freq": entities_above_threshold,
        "entities_below_min_freq": entities_below_threshold,
    }


def print_results(results: list[dict]) -> None:
    """Print formatted experiment results."""
    print("\n" + "=" * 80)
    print("NER EXPERIMENT RESULTS")
    print("=" * 80)

    all_pass = True

    for r in results:
        if not r:
            continue
        print(f"\n{'─' * 60}")
        print(f"Case: {r['label']} (run {r['run_id']})")
        print(f"Corpus: {r['corpus_size']} posts, {r['unique_entities']} unique entities")
        print(f"{'─' * 60}")

        # Top 25 entities
        print(f"\n  {'Rank':<6} {'Entity':<35} {'Count':<8} {'Types'}")
        print(f"  {'─'*6} {'─'*35} {'─'*8} {'─'*15}")
        for i, (entity, count, types) in enumerate(r["top_25"], 1):
            marker = ""
            for comp, info in r["known_competitors"].items():
                if entity == comp:
                    marker = " ◄ KNOWN COMPETITOR"
            print(f"  {i:<6} {entity:<35} {count:<8} {', '.join(types)}{marker}")

        # Known competitor positions
        print(f"\n  Known competitors:")
        case_pass = True
        for comp, info in r["known_competitors"].items():
            rank = info["rank"]
            count = info["count"]
            in_top5 = isinstance(rank, int) and rank <= 5
            status = "PASS" if in_top5 else "FAIL"
            if not in_top5:
                case_pass = False
                all_pass = False
            print(f"    {comp}: rank {rank}, count {count} [{status}]")

        # Frequency threshold analysis
        min_freq = r["min_competitor_freq"]
        above = r["entities_above_min_freq"]
        below = r["entities_below_min_freq"]
        print(f"\n  Frequency threshold analysis:")
        print(f"    Min frequency to capture all competitors: {min_freq}")
        print(f"    Entities at or above threshold: {above}")
        print(f"    Entities below threshold: {below}")
        if above > 0:
            print(f"    Ratio (above/total): {above}/{above + below} = {above / (above + below):.1%}")

        print(f"\n  Case verdict: {'PASS' if case_pass else 'FAIL'}")

    # Overall verdict
    print(f"\n{'=' * 80}")
    print(f"OVERALL: {'PASS' if all_pass else 'FAIL'} — known competitors in top 5 by frequency")
    print(f"{'=' * 80}")


def main():
    print("Loading spaCy model (en_core_web_trf)...")
    nlp = spacy.load("en_core_web_trf")
    print("Model loaded.\n")

    results = []
    for run_id, (label, known_competitors) in CASES.items():
        print(f"\n{'=' * 60}")
        print(f"Running NER: {label} ({run_id})")
        print(f"Known competitors: {known_competitors}")
        print(f"{'=' * 60}")
        result = run_ner_experiment(run_id, label, known_competitors, nlp)
        results.append(result)

    print_results(results)

    # Save raw results
    out_path = Path("data/experiment_ner_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nRaw results saved to {out_path}")


if __name__ == "__main__":
    main()
