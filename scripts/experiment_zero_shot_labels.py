"""
Zero-shot Label Test: Run 5 new gap-relevant labels on ~200 posts from existing corpora.

Labels: complaint, unmet_need, switching, friction, praise
(Replacing: pain_point, feature_request, praise, question, bug_report)

Pass criteria:
  - Labels produce clean separations with minimal bleed
  - Check complaint vs friction overlap
  - Check whether switching posts scatter across labels
  - Check where "I wish [product] could..." posts land

Run: python scripts/experiment_zero_shot_labels.py
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from transformers import pipeline

# New gap-relevant labels
NEW_LABELS = [
    "complaint about a product",           # complaint
    "unmet need with no solution",         # unmet_need
    "looking for alternatives",            # switching
    "setup or configuration friction",     # friction
    "praise or positive experience",       # praise
]

# Short keys for display
LABEL_KEYS = {
    "complaint about a product": "complaint",
    "unmet need with no solution": "unmet_need",
    "looking for alternatives": "switching",
    "setup or configuration friction": "friction",
    "praise or positive experience": "praise",
}

# Old labels for comparison
OLD_LABELS = ["pain point", "feature request", "praise", "question", "bug report"]
OLD_LABEL_KEYS = {
    "pain point": "pain_point",
    "feature request": "feature_request",
    "praise": "praise",
    "question": "question",
    "bug report": "bug_report",
}

# Sample sources: mix of corpora for diversity
SAMPLE_SOURCES = {
    "7c16def9": ("Linear", 50),
    "b4612a0d": ("Notion", 50),
    "0fb9aed4": ("Plausible", 40),
    "0e03b7a3": ("Email", 30),
    "fa17ead6": ("VS Code", 30),
}


def load_sample_posts(target_total: int = 200) -> list[dict]:
    """Load a stratified sample of posts from existing corpora."""
    all_posts = []

    for run_id, (label, n_sample) in SAMPLE_SOURCES.items():
        corpus_path = Path(f"data/preprocessed/{run_id}/corpus.jsonl")
        classified_path = Path(f"data/classified/{run_id}/classified.jsonl")

        if not corpus_path.exists():
            print(f"  SKIP: {corpus_path} not found")
            continue

        # Load corpus
        posts = {}
        with open(corpus_path) as f:
            for line in f:
                doc = json.loads(line)
                posts[doc["id"]] = doc

        # Load existing classifications for comparison
        old_labels = {}
        if classified_path.exists():
            with open(classified_path) as f:
                for line in f:
                    rec = json.loads(line)
                    old_labels[rec["doc_id"]] = rec.get("category", "unknown")

        # Sample random posts
        post_ids = list(posts.keys())
        random.seed(42)
        sampled_ids = random.sample(post_ids, min(n_sample, len(post_ids)))

        for pid in sampled_ids:
            post = posts[pid]
            all_posts.append({
                "id": pid,
                "text": post["text"],
                "source_corpus": label,
                "run_id": run_id,
                "old_label": old_labels.get(pid, "unknown"),
            })

    # Also add specific "I wish..." posts for aspiration gap testing
    wish_posts = find_wish_posts(15)
    all_posts.extend(wish_posts)

    print(f"Total sample: {len(all_posts)} posts ({len(wish_posts)} 'I wish...' posts)")
    return all_posts


def find_wish_posts(target: int = 15) -> list[dict]:
    """Find posts containing 'I wish' patterns for aspiration gap testing."""
    wish_patterns = ["i wish", "it would be great if", "if only", "i really want"]
    found = []

    for run_id, (label, _) in SAMPLE_SOURCES.items():
        corpus_path = Path(f"data/preprocessed/{run_id}/corpus.jsonl")
        classified_path = Path(f"data/classified/{run_id}/classified.jsonl")
        if not corpus_path.exists():
            continue

        old_labels = {}
        if classified_path.exists():
            with open(classified_path) as f:
                for line in f:
                    rec = json.loads(line)
                    old_labels[rec["doc_id"]] = rec.get("category", "unknown")

        with open(corpus_path) as f:
            for line in f:
                doc = json.loads(line)
                text_lower = doc["text"].lower()
                if any(p in text_lower for p in wish_patterns):
                    found.append({
                        "id": doc["id"],
                        "text": doc["text"],
                        "source_corpus": label,
                        "run_id": run_id,
                        "old_label": old_labels.get(doc["id"], "unknown"),
                        "is_wish_post": True,
                    })
                    if len(found) >= target * 3:  # collect extras, then sample
                        break

    # Sample down to target
    random.seed(42)
    if len(found) > target:
        found = random.sample(found, target)

    for p in found:
        p["is_wish_post"] = True

    print(f"Found {len(found)} 'I wish...' posts across corpora")
    return found


def classify_posts(posts: list[dict], classifier, labels: list[str], label_keys: dict) -> list[dict]:
    """Classify all posts with a given label set."""
    texts = [p["text"][:512] for p in posts]  # truncate for speed

    print(f"  Classifying {len(texts)} posts...")
    results = []
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_results = classifier(batch, labels, multi_label=False, batch_size=batch_size)
        if isinstance(batch_results, dict):
            batch_results = [batch_results]
        for r in batch_results:
            top_label = label_keys[r["labels"][0]]
            top_score = r["scores"][0]
            second_label = label_keys[r["labels"][1]]
            second_score = r["scores"][1]
            results.append({
                "top_label": top_label,
                "top_score": top_score,
                "second_label": second_label,
                "second_score": second_score,
                "all_labels": {label_keys[l]: round(s, 4) for l, s in zip(r["labels"], r["scores"])},
            })
        if (i + batch_size) % 64 == 0:
            print(f"    {min(i + batch_size, len(texts))}/{len(texts)} done...")

    return results


def analyze_results(posts: list[dict], new_results: list[dict]) -> dict:
    """Analyze label distribution, bleed, and co-assignment."""

    # Overall distribution
    label_dist = Counter(r["top_label"] for r in new_results)

    # Confidence stats per label
    confidence_by_label: dict[str, list[float]] = defaultdict(list)
    for r in new_results:
        confidence_by_label[r["top_label"]].append(r["top_score"])

    # Bleed analysis: when label X is top, what is second most common?
    bleed: dict[str, Counter] = defaultdict(Counter)
    for r in new_results:
        bleed[r["top_label"]][r["second_label"]] += 1

    # High-bleed pairs: cases where top confidence < 0.4 (ambiguous)
    ambiguous = [(posts[i], new_results[i]) for i in range(len(posts))
                 if new_results[i]["top_score"] < 0.4]

    # Complaint vs friction overlap specifically
    complaint_friction_bleed = 0
    friction_complaint_bleed = 0
    for r in new_results:
        if r["top_label"] == "complaint" and r["second_label"] == "friction":
            if r["second_score"] > 0.2:
                complaint_friction_bleed += 1
        elif r["top_label"] == "friction" and r["second_label"] == "complaint":
            if r["second_score"] > 0.2:
                friction_complaint_bleed += 1

    # Switching scatter: where do switching-classified posts' second labels go?
    switching_seconds = Counter()
    for r in new_results:
        if r["top_label"] == "switching":
            switching_seconds[r["second_label"]] += 1

    # "I wish..." posts analysis
    wish_results = []
    for i, post in enumerate(posts):
        if post.get("is_wish_post"):
            wish_results.append({
                "text_preview": post["text"][:120],
                "new_label": new_results[i]["top_label"],
                "new_confidence": new_results[i]["top_score"],
                "all_scores": new_results[i]["all_labels"],
            })

    # Old label → new label migration
    migration = defaultdict(Counter)
    for i, post in enumerate(posts):
        old = post.get("old_label", "unknown")
        new = new_results[i]["top_label"]
        migration[old][new] += 1

    return {
        "label_distribution": dict(label_dist),
        "confidence_stats": {
            k: {
                "mean": sum(v) / len(v),
                "min": min(v),
                "max": max(v),
                "count": len(v),
            }
            for k, v in confidence_by_label.items()
        },
        "bleed_matrix": {k: dict(v) for k, v in bleed.items()},
        "complaint_friction_bleed": complaint_friction_bleed,
        "friction_complaint_bleed": friction_complaint_bleed,
        "switching_second_labels": dict(switching_seconds),
        "ambiguous_count": len(ambiguous),
        "ambiguous_samples": [
            {
                "text": p["text"][:150],
                "top": r["top_label"],
                "top_score": r["top_score"],
                "second": r["second_label"],
                "second_score": r["second_score"],
            }
            for p, r in ambiguous[:10]
        ],
        "wish_posts": wish_results,
        "old_to_new_migration": {k: dict(v) for k, v in migration.items()},
    }


def print_analysis(analysis: dict) -> None:
    """Print formatted analysis."""
    print("\n" + "=" * 80)
    print("ZERO-SHOT LABEL TEST RESULTS")
    print("=" * 80)

    # Distribution
    print("\n1. LABEL DISTRIBUTION")
    print(f"   {'Label':<15} {'Count':<8} {'Pct':<8} {'Avg Conf':<10} {'Min Conf':<10}")
    print(f"   {'─'*15} {'─'*8} {'─'*8} {'─'*10} {'─'*10}")
    total = sum(analysis["label_distribution"].values())
    for label, count in sorted(analysis["label_distribution"].items(), key=lambda x: -x[1]):
        stats = analysis["confidence_stats"].get(label, {})
        pct = count / total * 100
        avg_conf = stats.get("mean", 0)
        min_conf = stats.get("min", 0)
        print(f"   {label:<15} {count:<8} {pct:<7.1f}% {avg_conf:<10.3f} {min_conf:<10.3f}")

    # Bleed matrix
    print("\n2. BLEED MATRIX (top label → most common second label)")
    for top_label, seconds in sorted(analysis["bleed_matrix"].items()):
        top_second = max(seconds.items(), key=lambda x: x[1])
        print(f"   {top_label:<15} → {top_second[0]} ({top_second[1]}x)")

    # Complaint/friction bleed
    print(f"\n3. COMPLAINT ↔ FRICTION BLEED")
    print(f"   complaint → friction (score > 0.2): {analysis['complaint_friction_bleed']}")
    print(f"   friction → complaint (score > 0.2): {analysis['friction_complaint_bleed']}")

    # Switching scatter
    print(f"\n4. SWITCHING SECOND-LABEL DISTRIBUTION")
    for label, count in sorted(analysis["switching_second_labels"].items(), key=lambda x: -x[1]):
        print(f"   {label}: {count}")

    # Ambiguous posts
    print(f"\n5. AMBIGUOUS POSTS (confidence < 0.4): {analysis['ambiguous_count']}")
    for s in analysis["ambiguous_samples"][:5]:
        print(f"   [{s['top']}/{s['top_score']:.2f} vs {s['second']}/{s['second_score']:.2f}]")
        print(f"   \"{s['text'][:100]}...\"")

    # Wish posts
    print(f"\n6. 'I WISH...' POSTS ({len(analysis['wish_posts'])} total)")
    wish_labels = Counter(w["new_label"] for w in analysis["wish_posts"])
    print(f"   Distribution: {dict(wish_labels)}")
    for w in analysis["wish_posts"][:5]:
        print(f"   [{w['new_label']}/{w['new_confidence']:.2f}] \"{w['text_preview'][:80]}...\"")

    # Migration matrix
    print(f"\n7. OLD → NEW LABEL MIGRATION")
    print(f"   {'Old Label':<15} → New Labels")
    print(f"   {'─'*15}   {'─'*40}")
    for old_label, new_counts in sorted(analysis["old_to_new_migration"].items()):
        new_str = ", ".join(f"{k}:{v}" for k, v in sorted(new_counts.items(), key=lambda x: -x[1]))
        print(f"   {old_label:<15} → {new_str}")


def main():
    print("Loading zero-shot classifier (bart-large-mnli)...")
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=-1)
    print("Model loaded.\n")

    # Load sample posts
    posts = load_sample_posts(200)

    # Classify with new labels
    print("\nClassifying with NEW labels...")
    new_results = classify_posts(posts, classifier, NEW_LABELS, LABEL_KEYS)

    # Analyze
    analysis = analyze_results(posts, new_results)
    print_analysis(analysis)

    # Save raw results
    out_path = Path("data/experiment_zero_shot_labels.json")
    out_data = {
        "analysis": analysis,
        "per_post": [
            {
                "id": posts[i]["id"],
                "text_preview": posts[i]["text"][:200],
                "source": posts[i]["source_corpus"],
                "old_label": posts[i].get("old_label"),
                "is_wish": posts[i].get("is_wish_post", False),
                **new_results[i],
            }
            for i in range(len(posts))
        ],
    }
    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\nRaw results saved to {out_path}")


if __name__ == "__main__":
    main()
