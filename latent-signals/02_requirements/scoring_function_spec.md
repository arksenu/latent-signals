# Scoring Function Spec

**Status:** Active — documents current engine scoring
**Last updated:** February 27, 2026

---

## Overview

The composite `gap_score` ranks detected market gaps by combining six weighted components into a single [0, 1] score. Higher scores indicate larger, more painful, less addressed opportunities.

---

## Formula

```
gap_score = 0.30 * unaddressedness
          + 0.25 * frequency
          + 0.15 * pain_intensity
          + 0.15 * competitive_whitespace
          + 0.10 * market_size
          + 0.05 * trend_direction
```

All components are normalized to [0, 1] before weighting.

---

## Component Definitions

### Unaddressedness (30%)

**What it measures:** How poorly existing competitor features cover a detected need.

**Computation:** `1 - max_similarity`, where `max_similarity` is the highest cosine similarity between the cluster centroid embedding and any competitor feature embedding.

**Normalization:** Direct inversion — already bounded [0, 1].

**Floor filter:** Clusters with `max_similarity < 0.15` are excluded entirely. These represent off-topic clusters that are semantically unrelated to any competitor feature. Without this floor, completely unrelated clusters (e.g., "firefox browsers" in an email pipeline run) receive artificially high unaddressedness scores because comparing unrelated domains produces low similarity. See decision log 2026-02-23.

**Config:** `scoring.unaddressedness_floor` (default: 0.15)

### Frequency (25%)

**What it measures:** How often the need is mentioned in community discussions.

**Computation:** Log-normalized mention count: `log(count + 1) / log(max_count + 1)`.

**Normalization:** Log transform compresses the range so that a cluster with 2000 mentions doesn't score 4x higher than one with 500 mentions — the marginal information value of additional mentions diminishes.

**P95 cap:** Before normalization, mention counts are capped at the 95th percentile of all cluster sizes in the run. The `max_count` denominator uses this capped value. This prevents mega-clusters (often generic discussion clusters) from inflating the frequency scale and compressing scores for all other clusters. Computed dynamically per-run.

**Config:** Cap is automatic (P95 of cluster sizes per run).

### Pain Intensity (15%)

**What it measures:** The emotional intensity of frustration expressed in the cluster.

**Computation:** Average of the top-20 most negative VADER compound scores among posts classified as `pain_point` or `bug_report` within the cluster. Result is mapped to [0, 1] via `abs(min(avg, 0))`.

**Normalization:** VADER compound scores range [-1, 1]. Taking the absolute value of the negative average maps it to [0, 1] where 1 = maximum pain.

**Why top-N instead of cluster mean:** Mixed clusters contain both pain posts and neutral/informational posts. Averaging across all posts dilutes genuine frustration signals to near-zero. The top-N approach (N=20) measures the intensity of the pain that exists, not the fraction of the cluster that's painful. See decision log 2026-02-20.

**Known limitation:** VADER responds to emotional temperature of language, not opportunity magnitude. Intense frustration language ("I cannot for the life of me get this to work") scores higher than measured help-seeking language ("how do I configure workflows for my team"), regardless of whether the underlying problem represents a billion-dollar opportunity or a documentation fix. See decision log 2026-02-27 (P2Q analysis).

### Competitive Whitespace (15%)

**What it measures:** The fraction of competitors that fail to address the detected need.

**Computation:** `1 - coverage_ratio`, where `coverage_ratio` is the proportion of competitors whose feature embeddings exceed a similarity threshold against the cluster centroid.

**Normalization:** Direct inversion — already bounded [0, 1].

### Market Size (10%)

**What it measures:** Proxy for the addressable market size of the detected need.

**Computation:** Linear normalization of a market size proxy value: `proxy / max_value`.

**Normalization:** Linear scaling against the maximum observed value in the run.

### Trend Direction (5%)

**What it measures:** Whether mentions of the need are increasing, stable, or declining over the analysis window.

**Computation:** Bipolar mapping of mention frequency slope: `(slope / max_abs_slope + 1.0) / 2.0`.

**Normalization:** Maps the slope to [0, 1] where 0.5 = flat trend, 1.0 = maximum growth, 0.0 = maximum decline.

---

## Pre-Scoring Filters

Two filters exclude clusters before scoring:

### Post-Level Market Relevance Filter (Stage 3)

Individual posts with cosine similarity below 0.20 to market anchor phrases are dropped before clustering. This prevents off-topic posts from broad subreddits (e.g., r/degoogle discussing phones, browsers, VPNs alongside email) from forming irrelevant clusters.

**Config:** `embedding.post_relevance_threshold` (default: 0.20)

**Origin:** Decision log 2026-02-23. The email control backtest produced false positives (Firefox, Android, Google politics) because off-topic posts from broad subreddits were embedded and clustered alongside on-topic content.

### Unaddressedness Similarity Floor (Stage 6)

Clusters with `max_similarity < 0.15` to any competitor feature are excluded from scoring entirely. This catches off-topic clusters that survive the post-level filter but still aren't semantically related to the market.

**Config:** `scoring.unaddressedness_floor` (default: 0.15)

**Origin:** Decision log 2026-02-23. The scoring formula was treating "completely unrelated" the same as "genuinely unaddressed."

---

## Weight Rationale

| Component | Weight | Rationale |
|-----------|--------|-----------|
| Unaddressedness | 0.30 | The primary signal — a gap only matters if no competitor addresses it. Highest weight because this is the core value proposition. |
| Frequency | 0.25 | Volume validates that the pain is widespread, not idiosyncratic. Second highest because frequency without unaddressedness is just a popular topic, not a gap. |
| Pain intensity | 0.15 | Emotional urgency separates "nice to have" from "hair on fire." Lower weight than frequency because VADER has known limitations on mixed clusters. |
| Competitive whitespace | 0.15 | Breadth of competitive failure — a gap ignored by all competitors is more actionable than one ignored by only one. Equal to pain because both qualify the gap rather than define it. |
| Market size | 0.10 | Proxy signal with lower confidence than direct measurements. Included to prevent surfacing gaps in tiny niches. |
| Trend direction | 0.05 | Lowest weight because trend data from forum mentions is noisy and the analysis window (typically 12 months) may be too short for reliable slope estimation. |

---

## Backtest Score Distributions

Scores from validated backtest runs (Round 2, after all four fixes):

| Case | Target Gap | Rank | Score | Top Score in Run |
|------|-----------|------|-------|------------------|
| Linear (Jira frustration) | Rank 2 | 0.723 | 0.756 |
| Notion (Evernote frustration) | Rank 3 | 0.657 | 0.736 |
| Plausible (GA privacy, gap 1) | Rank 1 | 0.776 | 0.776 |
| Plausible (GA privacy, gap 2) | Rank 2 | 0.745 | 0.776 |

Score improvements from Round 1 to Round 2 (after the four fixes):

| Case | R1 Score | R2 Score | Delta |
|------|----------|----------|-------|
| Linear | 0.705 | 0.723 | +0.018 |
| Notion | 0.646 | 0.657 | +0.011 |
| Plausible (gap 1) | 0.725 | 0.776 | +0.051 |
| Plausible (gap 2) | 0.692 | 0.745 | +0.053 |

---

## Known Limitations

1. **Opportunity magnitude blindness.** The formula treats all frustration equally regardless of whether the underlying gap represents a new-product opportunity or a polish fix. "Jira's workflow is broken" (0.723) scores similarly to "VS Code Python setup is painful" (0.740). Deferred to v2 Opportunity Scale Classifier.

2. **VADER emotional temperature bias.** Pain intensity measures language intensity, not problem severity. Intense frustration language scores higher than measured help-seeking language regardless of the underlying opportunity. The P2Q ratio (pain-to-question) was tested as a derived signal to address this — it does not separate opportunity magnitudes (decision log 2026-02-27).

3. **Trend noise.** Forum mention frequency is a noisy proxy for demand trends. The 5% weight reflects low confidence in this signal.

---

## Implementation

- Scoring logic: `src/latent_signals/stage6_scoring/scoring.py`
- Normalization functions: `src/latent_signals/stage6_scoring/normalization.py`
- Gap detection: `src/latent_signals/stage6_scoring/gap_detection.py`
