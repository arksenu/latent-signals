"""Entry point for automated gap analysis.

Usage:
    python run_query.py "We're building a lightweight issue tracker for small dev teams. Our main competitor is Jira. The project management space is dominated by enterprise tools."
    python run_query.py "We sell privacy-focused web analytics. Our competitor is Google Analytics. We target GDPR-conscious businesses in Europe." --date-start 2018-01-01 --date-end 2018-12-31

Describe your company, product, market, and competitors. You don't need to
mention pain points or gaps — that's what the pipeline discovers.
Exa is a semantic search engine — the more context you give it, the better
it discovers relevant communities and discussions.

This is Stage 0 + the existing pipeline (stages 1-6).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Run market gap analysis from a single query."
    )
    parser.add_argument("query", help="Market description (e.g., 'lightweight issue tracker for dev teams frustrated with Jira')")
    parser.add_argument("--date-start", default=None, help="Collection start date (YYYY-MM-DD). Default: 12 months ago.")
    parser.add_argument("--date-end", default=None, help="Collection end date (YYYY-MM-DD). Default: today.")
    parser.add_argument("--output-dir", default="data", help="Output directory (default: data)")
    parser.add_argument("--discovery-only", action="store_true", help="Run Stage 0 only (discovery + config), skip pipeline.")
    parser.add_argument("--stages", type=str, default=None, help="Pipeline stages to run (e.g., '1,2,3'). Default: all.")
    args = parser.parse_args()

    # Check for Exa API key
    if not os.environ.get("EXA_API_KEY"):
        print("ERROR: EXA_API_KEY environment variable required.", file=sys.stderr)
        print("Set it in .env or export EXA_API_KEY=your_key", file=sys.stderr)
        sys.exit(1)

    print(f"{'=' * 60}")
    print(f"Latent Signals — Market Gap Analysis")
    print(f"Query: \"{args.query}\"")
    print(f"{'=' * 60}\n")

    # ── Stage 0: Input Construction ──────────────────────────────
    print("Stage 0: Discovering sources and building config...")
    t0 = time.time()

    from latent_signals.stage0_input.exa_discovery import run_exa_discovery
    from latent_signals.stage0_input.source_extraction import extract_and_validate_sources
    from latent_signals.stage0_input.anchor_generation import generate_anchors
    from latent_signals.stage0_input.config_builder import build_config
    from latent_signals.stage0_input.source_cache import load_source_cache, save_source_cache
    from latent_signals.stage0_input.competitor_discovery import discover_competitors, save_features_yaml

    # Step 1: Competitor discovery (Exa Answer) — runs FIRST so competitor
    # names can be used as search terms in the Exa discovery probes.
    print("\n  [1/5] Discovering competitors and features...")
    competitor_cache_dir = Path(args.output_dir) / "cache" / "competitors"
    competitor_features = discover_competitors(
        args.query,
        os.environ["EXA_API_KEY"],
        cache_dir=competitor_cache_dir,
    )

    competitor_features_file = ""
    competitor_names: list[str] = []
    if competitor_features:
        features_path = Path(args.output_dir) / "competitor_features.yaml"
        save_features_yaml(competitor_features, features_path)
        competitor_features_file = str(features_path)
        competitor_names = sorted({f.competitor_name for f in competitor_features})
        print(f"        Found {len(competitor_names)} competitors: {competitor_names}")
        print(f"        Total features: {len(competitor_features)}")
    else:
        print("        No competitors discovered (pipeline will run without competitor features)")

    # Check source cache (keyed by query — competitor names don't change per query)
    source_cache_dir = Path(args.output_dir) / "cache" / "sources"
    cached_sources = load_source_cache(args.query, source_cache_dir)

    if cached_sources:
        print("\n  Using cached discovery results (source map cache hit)")
        discovery, sources, anchors = cached_sources
        print(f"        Subreddits: {sources.subreddits}")
        print(f"        Anchors: {len(anchors)}")
    else:
        # Step 2: Exa discovery — now enriched with competitor names
        print("\n  [2/5] Running Exa discovery probes...")
        discovery = run_exa_discovery(
            args.query,
            os.environ["EXA_API_KEY"],
            date_start=args.date_start,
            date_end=args.date_end,
            competitor_names=competitor_names,
        )
        print(f"        Found {len(discovery.subreddit_counts)} subreddits, "
              f"{len(discovery.general_results)} general results, "
              f"{len(discovery.hn_results)} HN results")

        # Step 3: Source extraction + volume validation
        date_start = args.date_start
        date_end = args.date_end
        if not date_end:
            from datetime import datetime
            date_end = datetime.now().strftime("%Y-%m-%d")
        if not date_start:
            from datetime import datetime, timedelta
            end_dt = datetime.strptime(date_end, "%Y-%m-%d")
            date_start = (end_dt - timedelta(days=365)).strftime("%Y-%m-%d")

        print(f"\n  [3/5] Validating source volumes ({date_start} to {date_end})...")
        sources = extract_and_validate_sources(
            discovery, args.query, date_start=date_start, date_end=date_end,
        )
        print(f"        Accepted: {sources.subreddits}")
        if sources.dropped_subreddits:
            print(f"        Dropped (low volume): {sources.dropped_subreddits}")
        if sources.hn_has_signal:
            print(f"        HN queries: {sources.hn_queries}")

        # Step 4: Anchor generation
        print(f"\n  [4/5] Generating market anchors...")
        anchors = generate_anchors(args.query, discovery)
        print(f"        Anchors ({len(anchors)}):")
        for a in anchors:
            print(f"          - \"{a}\"")

        # Cache discovery results for repeat queries
        save_source_cache(args.query, discovery, sources, anchors, source_cache_dir)

    # Step 5: Build config
    print(f"\n  [5/5] Building pipeline config...")
    config = build_config(
        args.query, sources, anchors,
        date_start=args.date_start, date_end=args.date_end,
        output_dir=args.output_dir,
        competitor_features_file=competitor_features_file,
    )

    stage0_duration = time.time() - t0
    print(f"\n  Stage 0 complete ({stage0_duration:.1f}s)")

    # Save discovery results for inspection
    discovery_out = Path(args.output_dir) / "stage0_discovery.json"
    discovery_out.parent.mkdir(parents=True, exist_ok=True)
    with open(discovery_out, "w") as f:
        json.dump({
            "query": args.query,
            "subreddits": sources.subreddits,
            "subreddit_volumes": sources.subreddit_volumes,
            "dropped_subreddits": sources.dropped_subreddits,
            "hn_queries": sources.hn_queries,
            "anchors": anchors,
            "competitors": [
                {"name": name, "n_features": len(feats)}
                for name, feats in _group_features(competitor_features).items()
            ],
            "competitor_features_file": competitor_features_file,
            "domain_counts": dict(discovery.domain_counts.most_common(30)),
            "subreddit_counts": dict(discovery.subreddit_counts.most_common(30)),
        }, f, indent=2)
    print(f"  Discovery results saved to {discovery_out}")

    if args.discovery_only:
        print("\n--discovery-only: skipping pipeline stages 1-6.")
        _print_config_summary(config)
        return

    # ── Stages 1-6: Run pipeline ─────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"Running pipeline stages 1-6...")
    print(f"{'=' * 60}\n")

    stages = None
    if args.stages:
        stages = [int(s.strip()) for s in args.stages.split(",")]

    from latent_signals.run_pipeline import run_pipeline
    run_pipeline(config, stages=stages)

    print(f"\n{'=' * 60}")
    print(f"Done. Check {args.output_dir}/reports/ for gap report.")
    print(f"{'=' * 60}")


def _group_features(features):
    """Group CompetitorFeature list by competitor name."""
    grouped = {}
    for f in features:
        grouped.setdefault(f.competitor_name, []).append(f.description)
    return grouped


def _print_config_summary(config):
    """Print a summary of the auto-generated config."""
    print(f"\n{'─' * 40}")
    print(f"Auto-generated config summary:")
    print(f"  Market: {config.pipeline.market_category}")
    print(f"  Date range: {config.collection.date_range}")
    print(f"  Subreddits: {config.collection.arctic_shift.subreddits}")
    print(f"  Arctic Shift max items: {config.collection.arctic_shift.max_items}")
    print(f"  HN enabled: {config.collection.hackernews.enabled}")
    print(f"  HN queries: {config.collection.hackernews.queries}")
    print(f"  Market anchors: {config.scoring.market_anchors}")
    print(f"  Relevance threshold: {config.embedding.post_relevance_threshold}")
    print(f"  Competitor features: {'(none — no competitors discovered)' if not config.scoring.competitor_features_file else config.scoring.competitor_features_file}")
    print(f"{'─' * 40}")


if __name__ == "__main__":
    main()
