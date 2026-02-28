# Design Constraints

**Status:** Active — engine constraints documented, input layer not yet built
**Last updated:** February 28, 2026

---

## Overview

These constraints govern the technical architecture. They are derived from strategic decisions (product brief), cost model requirements, and lessons learned during backtest validation. Any architectural change must satisfy all constraints listed here.

---

## Cost Constraints

### Prototype Cost Ceiling: <$50/month

The hybrid NLP pipeline exists specifically to meet this constraint. Traditional NLP handles bulk processing (embedding, clustering, sentiment); LLMs are used surgically on sampled subsets only (50-100 representative posts per cluster via GPT-4o-mini Batch API). Total LLM cost across all five backtest runs: $0.21.

Any change that pushes LLM calls to the full dataset rather than representative samples violates the cost model.

### Production Cost Ceiling: <$500/month

Production runs process larger corpora across more markets but must stay within this budget. The hybrid architecture scales linearly with corpus size for traditional NLP stages and sublinearly for LLM stages (sample size per cluster is capped, not proportional to cluster size).

---

## Signal Fidelity Constraints

### Emotional Signal Primacy

Sentiment intensity is the core product differentiator. The scoring formula weights pain intensity at 15%, but the product positioning leads with emotional signals. The pipeline must preserve intensity, urgency, and frustration gradients through the entire analysis chain.

**Violation condition:** If the pipeline ever reduces sentiment to a binary positive/negative classification, it has failed. VADER compound scores, zero-shot classification confidence scores, and LLM-extracted urgency/frustration fields must all preserve continuous intensity values.

### Data Separation

Competitor feature vectors describe actual product capabilities. User complaint vectors describe pain points and unmet needs. These are separate embedding collections in ChromaDB — they must never be collapsed into a single collection.

**Rationale:** The gap detection logic depends on measuring cosine distance between complaint clusters and feature vectors. Mixing them in a single collection would contaminate similarity calculations and make the unaddressedness score meaningless.

---

## Pipeline Input Constraints

### Discovery Layer Is a Prerequisite

The Exa discovery probe must run before every pipeline execution. Subreddit lists, keyword filters, and HN queries are derived from Exa results, not manually specified.

**Origin:** Decision log 2026-02-21. Six consecutive Linear backtest failures with hand-guessed subreddit inputs. One pass with Exa-derived inputs. The only variable that changed was running discovery first. Subreddits that Exa surfaced at high frequency (r/projectmanagement, r/atlassian, r/experienceddevs) were missing from all hand-guessed configs. Subreddits that were hand-guessed (r/webdev, r/softwareengineering) never appeared in Exa results for any project management frustration query.

**For historical backtests:** Exa searches current web data and cannot time-travel. The correct process is: run Exa against current data to derive sources, verify those sources existed and had sufficient volume in Arctic Shift for the target date range, then lock the config.

### Post-Level Market Relevance Filtering

Posts must pass a market relevance check (cosine similarity ≥ 0.20 to market anchor phrases) before entering the clustering pipeline. Without this, off-topic posts from broad subreddits form irrelevant clusters that score high on unaddressedness.

**Origin:** Decision log 2026-02-23. The email control backtest produced false positives (Firefox browsers, Android phones, Google politics) because broad subreddits like r/degoogle contributed off-topic posts that clustered independently and received high unaddressedness scores.

**Config:** `embedding.post_relevance_threshold` (default: 0.20)

---

## Architectural Constraints

### Hybrid NLP Only

LLMs process sampled subsets (50-100 posts per cluster). Traditional NLP handles bulk processing. This is a hard constraint driven by the cost ceiling, not an optimization preference.

| Processing Layer | Tool | Scope |
|-----------------|------|-------|
| Embedding | sentence-transformers (local) | All posts |
| Clustering | BERTopic + UMAP + HDBSCAN | All posts |
| Sentiment | VADER | All posts |
| Classification | Zero-shot (bart-large-mnli) | All posts |
| Extraction | GPT-4o-mini Batch API | 50-100 per cluster |

### No Batch-Only Lock-In

The architecture must not create dependencies that prevent a future shift to synchronous inference. V1 uses GPT-4o-mini Batch API (asynchronous). If the tool evolves toward interactive use (a startup founder querying during a strategy session), the batch processing model breaks. Groq or Cerebras deployment for low-latency LLM calls is a v2 consideration.

### Future-Proof for Time Series

Data storage and gap identity must be designed so v2 can track gaps over time. V1 produces snapshots. V2 must produce time series — tracked gaps across reporting periods, alerts when gaps close or new ones emerge. This means gap identity (how a gap is recognized as "the same gap" across runs) must be stable and deterministic.

### Sequential Script Orchestration (V1)

V1 runs as a sequential Python script (`run_pipeline.py`). No workflow orchestration framework (Prefect, Airflow, etc.) in V1. All six pipeline stages must be independently runnable for debugging, with intermediate outputs (embeddings, clusters, scores) stored for inspection.

---

## Scoring Constraints

### Unaddressedness Similarity Floor

Clusters with `max_similarity < 0.15` to any competitor feature are excluded from scoring. This prevents off-topic clusters from receiving artificially high unaddressedness scores.

**Origin:** Decision log 2026-02-23. The formula was treating "completely unrelated to any competitor" the same as "genuinely unaddressed by competitors."

**Config:** `scoring.unaddressedness_floor` (default: 0.15)

### Frequency P95 Cap

Mention counts are capped at the 95th percentile of cluster sizes before log normalization. This prevents mega-clusters (often generic discussion rather than specific pain) from inflating the frequency scale.

---

## V1 Scope Boundaries

These items are explicitly deferred and must not be introduced in v1:

- Job 2 (existing product analysis / expansion opportunities)
- Qdrant migration or native Discovery API
- Prefect or any workflow orchestration
- Web UI or interactive dashboard
- SparkToro, Glimpse, or Exploding Topics integrations
- Multi-tenant SaaS infrastructure, auth, or billing
- Opportunity Scale Classifier (deferred to v2 — see decision log 2026-02-26)
