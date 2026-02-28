# User Flows

**Status:** Active — engine workflow documented, user-facing input layer not yet built
**Last updated:** February 28, 2026

---

## Overview

Latent Signals serves two jobs to be done. Job 1 (Discovery) is implemented in v1. Job 2 (Expansion) is designed but deferred to v2.

---

## Job 1 — Discovery (V1, Implemented)

**User goal:** "I'm entering a market. What underserved problems exist?"

The user defines a market category. The pipeline scrapes community discussions, extracts and clusters unmet needs, maps them against competitor coverage, scores the gaps, and delivers a ranked opportunity index.

### Flow

#### Step 1: Define Market Category

The user selects a market domain (e.g., "project management tools," "privacy-focused analytics," "note-taking apps"). This defines the target for all subsequent steps.

#### Step 2: Run Exa Discovery Probe

A discovery script queries Exa's semantic search API with frustration-oriented queries about the target market. The output identifies which online communities (subreddits, HN threads, review sites) contain signal for this market.

**Output:** `data/discovery_probe_<case>.json` — ranked list of sources with frequency counts.

**Why this step exists:** Six consecutive backtest failures demonstrated that hand-guessed community sources produce no usable signal. Discovery-derived sources are required. See decision log 2026-02-21.

#### Step 3: Verify Source Volume (Arctic Shift)

For each candidate source identified by Exa, the user verifies it has sufficient post volume in the target date range using Arctic Shift (for Reddit) or equivalent volume checks. Sources with fewer than ~200 posts are dropped.

**Purpose:** Prevents the pipeline from running against sources too small to produce meaningful clusters.

#### Step 4: Write Pipeline Configuration

The user creates a YAML config file specifying:
- Market category and description
- Discovery-derived subreddit list (with Exa frequency annotations)
- Date range for data collection
- Market anchor phrases (realistic frustration statements for the target market)
- Competitor names and feature file references

Each subreddit in the config is sourced from the discovery probe, not guessed.

**Output:** `config/backtest_<case>.yaml`

#### Step 5: Configure Competitor Features

The user creates or verifies a competitor features YAML file listing the incumbent's capabilities. These features are embedded and used to compute unaddressedness scores.

**Output:** `config/competitor_features/<competitor>_<year>.yaml`

#### Step 6: Run Pipeline

The user executes the six-stage pipeline:

1. **Data Collection** — Exa semantic search + Serper.dev keyword search + Apify bulk Reddit scraping gather posts from the configured sources within the date range.
2. **Preprocessing** — HTML cleanup, language detection, MinHash deduplication, and length filtering remove noise.
3. **Embedding** — Posts are embedded using sentence-transformers (`all-MiniLM-L6-v2` or `bge-base-en-v1.5`). Posts below the market relevance threshold (cosine similarity < 0.20 to market anchors) are filtered out.
4. **Topic Clustering** — BERTopic with UMAP + HDBSCAN groups posts into thematic clusters. KeyBERTInspired generates topic labels.
5. **Classification & Extraction** — VADER sentiment analysis + zero-shot classification (`bart-large-mnli`) categorize all posts. GPT-4o-mini Batch API extracts structured pain points, feature requests, and urgency signals from 50-100 sampled posts per cluster.
6. **Gap Detection & Scoring** — Cluster centroids are compared against competitor feature embeddings in ChromaDB. The composite gap_score formula ranks detected gaps. Clusters below the unaddressedness floor (max similarity < 0.15) are excluded.

**Command:** `python run_pipeline.py --config config/backtest_<case>.yaml`

#### Step 7: Review Report

The pipeline produces a ranked gap report with 5-10 opportunities. Each gap includes:
- Gap score (composite of six weighted components)
- Cluster size (number of posts)
- Topic label and representative keywords
- Pain intensity score
- Unaddressedness score against each competitor
- Representative quotes from community posts

**Output:** `data/reports/<run_id>/gap_report.md`

The user evaluates the report to identify actionable market opportunities. Gaps ranked highest represent the most painful, frequent, and unaddressed needs in the market.

---

## Job 2 — Expansion (V2, Designed but Deferred)

**User goal:** "I have an existing product. Where should I expand?"

The user inputs their own product alongside the market category. The pipeline analyzes their users' sentiment alongside the broader market, identifies needs that both their product and competitors fail to address, and surfaces expansion opportunities ranked by gap score.

### Designed Flow (Not Yet Implemented)

#### Step 1: Define Product and Market

The user provides their product name, feature set, and the broader market category they operate in.

#### Step 2: Collect User Feedback

In addition to the community scraping from Job 1, the pipeline ingests the user's own product feedback channels — support tickets, review site mentions, community forums — to build a product-specific complaint corpus.

#### Step 3: Run Pipeline with Product Context

The pipeline runs the same six stages as Job 1, but with the user's product added as an additional competitor. Gap detection compares community needs against both the user's features and competitor features.

#### Step 4: Identify Expansion Opportunities

The report highlights gaps that the user's product and all competitors fail to address — these are expansion opportunities. It also surfaces gaps where competitors have coverage but the user does not — these are competitive catch-up areas.

#### Step 5: Recurring Reports

Job 2 is the higher-retention use case. Users return monthly as the market evolves to track:
- New gaps emerging
- Existing gaps closing (competitors or the user addressing them)
- Trend shifts in gap urgency and frequency

### Why Deferred

Job 2 requires:
- Stable gap identity across runs (recognizing "the same gap" over time)
- Time-series storage and comparison logic
- Product-specific feedback ingestion beyond community scraping
- The Opportunity Scale Classifier (to prioritize expansion opportunities by magnitude)

These are all v2 requirements. V1 validates that gap detection works at all. Job 2 builds on that foundation.
