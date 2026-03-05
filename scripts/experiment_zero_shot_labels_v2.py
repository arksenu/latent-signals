"""
Zero-shot Label Test v2: Fix label descriptions that caused switching to absorb everything.

Problem in v1: "looking for alternatives" was too broad — BART classifies any
exploratory/questioning post as switching. Fix: make labels more specific and
use hypothesis-style descriptions (BART is an NLI model, it works best with
natural language hypotheses).

Run: .venv/bin/python scripts/experiment_zero_shot_labels_v2.py
"""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from transformers import pipeline

# NLI-style label descriptions — BART compares these as hypotheses against the text
# Key: make each label occupy a distinct semantic region
LABEL_SETS = {
    "v2_hypothesis": {
        "labels": [
            "This post complains about a specific product being bad or broken",     # complaint
            "This post describes a need that no existing product addresses",         # unmet_need
            "This post is about wanting to switch away from a current tool",         # switching
            "This post is about difficulty setting up or configuring software",      # friction
            "This post expresses satisfaction or recommends something positively",   # praise
        ],
        "keys": {
            "This post complains about a specific product being bad or broken": "complaint",
            "This post describes a need that no existing product addresses": "unmet_need",
            "This post is about wanting to switch away from a current tool": "switching",
            "This post is about difficulty setting up or configuring software": "friction",
            "This post expresses satisfaction or recommends something positively": "praise",
        },
    },
    "v2_short": {
        "labels": [
            "product complaint or criticism",
            "unfulfilled need or missing capability",
            "wanting to switch or replace current tool",
            "setup difficulty or configuration problem",
            "positive recommendation or satisfaction",
        ],
        "keys": {
            "product complaint or criticism": "complaint",
            "unfulfilled need or missing capability": "unmet_need",
            "wanting to switch or replace current tool": "switching",
            "setup difficulty or configuration problem": "friction",
            "positive recommendation or satisfaction": "praise",
        },
    },
}

# Sample sources
SAMPLE_SOURCES = {
    "7c16def9": ("Linear", 50),
    "b4612a0d": ("Notion", 50),
    "0fb9aed4": ("Plausible", 40),
    "0e03b7a3": ("Email", 30),
    "fa17ead6": ("VS Code", 30),
}


def load_sample_posts(target_total: int = 200) -> list[dict]:
    """Load stratified sample + wish posts."""
    all_posts = []
    wish_patterns = ["i wish", "it would be great if", "if only", "i really want"]

    for run_id, (label, n_sample) in SAMPLE_SOURCES.items():
        corpus_path = Path(f"data/preprocessed/{run_id}/corpus.jsonl")
        classified_path = Path(f"data/classified/{run_id}/classified.jsonl")
        if not corpus_path.exists():
            continue

        posts = {}
        with open(corpus_path) as f:
            for line in f:
                doc = json.loads(line)
                posts[doc["id"]] = doc

        old_labels = {}
        if classified_path.exists():
            with open(classified_path) as f:
                for line in f:
                    rec = json.loads(line)
                    old_labels[rec["doc_id"]] = rec.get("category", "unknown")

        post_ids = list(posts.keys())
        random.seed(42)
        sampled_ids = random.sample(post_ids, min(n_sample, len(post_ids)))

        for pid in sampled_ids:
            post = posts[pid]
            is_wish = any(p in post["text"].lower() for p in wish_patterns)
            all_posts.append({
                "id": pid,
                "text": post["text"],
                "source_corpus": label,
                "old_label": old_labels.get(pid, "unknown"),
                "is_wish_post": is_wish,
            })

    # Ensure we have at least 10 wish posts
    wish_count = sum(1 for p in all_posts if p.get("is_wish_post"))
    if wish_count < 10:
        extra_wish = _find_more_wish_posts(all_posts, 15 - wish_count)
        all_posts.extend(extra_wish)

    print(f"Total sample: {len(all_posts)} posts ({sum(1 for p in all_posts if p.get('is_wish_post'))} wish posts)")
    return all_posts


def _find_more_wish_posts(existing: set, target: int) -> list[dict]:
    """Find additional wish posts not already in sample."""
    existing_ids = {p["id"] for p in existing}
    wish_patterns = ["i wish", "it would be great if", "if only"]
    found = []

    for run_id, (label, _) in SAMPLE_SOURCES.items():
        corpus_path = Path(f"data/preprocessed/{run_id}/corpus.jsonl")
        if not corpus_path.exists():
            continue
        with open(corpus_path) as f:
            for line in f:
                doc = json.loads(line)
                if doc["id"] in existing_ids:
                    continue
                if any(p in doc["text"].lower() for p in wish_patterns):
                    found.append({
                        "id": doc["id"],
                        "text": doc["text"],
                        "source_corpus": label,
                        "old_label": "unknown",
                        "is_wish_post": True,
                    })
                    if len(found) >= target:
                        return found
    return found


def classify_batch(texts: list[str], classifier, labels: list[str], label_keys: dict, batch_size: int = 16) -> list[dict]:
    """Classify texts with given labels."""
    truncated = [t[:512] for t in texts]
    results = []
    for i in range(0, len(truncated), batch_size):
        batch = truncated[i:i + batch_size]
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
                "all_scores": {label_keys[l]: round(s, 4) for l, s in zip(r["labels"], r["scores"])},
            })
        if (i + batch_size) % 64 == 0 or i + batch_size >= len(truncated):
            print(f"    {min(i + batch_size, len(truncated))}/{len(truncated)} done...")
    return results


def analyze_and_print(name: str, posts: list[dict], results: list[dict]) -> dict:
    """Analyze and print results for one label set."""
    print(f"\n{'=' * 70}")
    print(f"LABEL SET: {name}")
    print(f"{'=' * 70}")

    # Distribution
    dist = Counter(r["top_label"] for r in results)
    total = len(results)

    conf_by_label = defaultdict(list)
    for r in results:
        conf_by_label[r["top_label"]].append(r["top_score"])

    print(f"\n  {'Label':<15} {'Count':<7} {'Pct':<7} {'AvgConf':<8} {'MinConf':<8}")
    print(f"  {'─'*15} {'─'*7} {'─'*7} {'─'*8} {'─'*8}")
    for label in ["complaint", "unmet_need", "switching", "friction", "praise"]:
        count = dist.get(label, 0)
        pct = count / total * 100
        confs = conf_by_label.get(label, [0])
        print(f"  {label:<15} {count:<7} {pct:<6.1f}% {sum(confs)/len(confs):<8.3f} {min(confs):<8.3f}")

    # Bleed
    bleed = defaultdict(Counter)
    for r in results:
        bleed[r["top_label"]][r["second_label"]] += 1

    print(f"\n  Bleed matrix (top → most common second):")
    for top, seconds in sorted(bleed.items()):
        top_second = max(seconds.items(), key=lambda x: x[1])
        print(f"    {top:<15} → {top_second[0]} ({top_second[1]}x)")

    # Complaint/friction bleed
    cf_bleed = sum(1 for r in results if r["top_label"] == "complaint" and r["second_label"] == "friction" and r["second_score"] > 0.2)
    fc_bleed = sum(1 for r in results if r["top_label"] == "friction" and r["second_label"] == "complaint" and r["second_score"] > 0.2)
    print(f"\n  Complaint↔Friction bleed (2nd score > 0.2): C→F={cf_bleed}, F→C={fc_bleed}")

    # Ambiguous
    ambiguous = [(posts[i], results[i]) for i in range(len(posts)) if results[i]["top_score"] < 0.4]
    print(f"  Ambiguous posts (conf < 0.4): {len(ambiguous)}")

    # Wish posts
    wish_labels = Counter()
    wish_examples = []
    for i, post in enumerate(posts):
        if post.get("is_wish_post"):
            wish_labels[results[i]["top_label"]] += 1
            if len(wish_examples) < 5:
                wish_examples.append((post["text"][:100], results[i]["top_label"], results[i]["top_score"]))

    print(f"\n  'I wish...' posts distribution: {dict(wish_labels)}")
    for text, label, conf in wish_examples:
        print(f"    [{label}/{conf:.2f}] \"{text}...\"")

    # Old→New migration
    migration = defaultdict(Counter)
    for i, post in enumerate(posts):
        migration[post.get("old_label", "unknown")][results[i]["top_label"]] += 1

    print(f"\n  Old → New migration:")
    for old, new_counts in sorted(migration.items()):
        new_str = ", ".join(f"{k}:{v}" for k, v in sorted(new_counts.items(), key=lambda x: -x[1]))
        print(f"    {old:<15} → {new_str}")

    return {
        "distribution": dict(dist),
        "bleed": {k: dict(v) for k, v in bleed.items()},
        "cf_bleed": cf_bleed,
        "fc_bleed": fc_bleed,
        "ambiguous_count": len(ambiguous),
        "wish_distribution": dict(wish_labels),
        "migration": {k: dict(v) for k, v in migration.items()},
    }


def main():
    print("Loading bart-large-mnli...")
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=-1)
    print("Loaded.\n")

    posts = load_sample_posts(200)
    texts = [p["text"] for p in posts]

    all_results = {}
    for name, label_set in LABEL_SETS.items():
        print(f"\nClassifying with {name}...")
        results = classify_batch(texts, classifier, label_set["labels"], label_set["keys"])
        analysis = analyze_and_print(name, posts, results)
        all_results[name] = {
            "analysis": analysis,
            "per_post": [
                {
                    "id": posts[i]["id"],
                    "text_preview": posts[i]["text"][:200],
                    "source": posts[i]["source_corpus"],
                    "old_label": posts[i].get("old_label"),
                    "is_wish": posts[i].get("is_wish_post", False),
                    **results[i],
                }
                for i in range(len(posts))
            ],
        }

    # Save
    out_path = Path("data/experiment_zero_shot_labels_v2.json")
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
