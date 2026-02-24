# Backtest Summary

**Date**: 2026-02-23
**Pipeline version**: Pre-v1 prototype (sequential pipeline, 6 stages)

## Overview

Four historical backtests were run against the pipeline to answer: "Can this architecture detect known market gaps from historical community data?"

**Result**: The pipeline consistently detects real signals (3/3 positive cases at rank 1) but has a critical false positive problem — the negative control produced 10 high-scoring gaps when it should have produced none.

## Results

| Case | Market | Target Signal | Expected | Run ID | Result |
|------|--------|--------------|----------|--------|--------|
| Linear | Project management | Jira frustration → Linear | Top 3 | `7c16def9` | Rank 1 (0.705). 7 gaps total. |
| Notion | Note-taking | Evernote frustration → Notion | Top 3 | `b4612a0d` | Rank 1 (0.646). 7 gaps total. |
| Plausible | Web analytics | GA privacy frustration → Plausible | Top 3 | `0fb9aed4` | Ranks 1-2 (0.725, 0.692). 4 gaps total. |
| Email (control) | Email clients | No gap expected | 0 gaps | `0e03b7a3` | **FAIL**: 10 gaps, top score 0.760. |

### Pass/Fail Assessment

Per the backtest plan: success requires 2/3 positive cases in top 3 + negative control produces no false positives.

- Positive cases: **3/3 PASS** (all at rank 1)
- Negative control: **FAIL** (10 false positives, top score exceeds all positive cases)
- Overall: **CONDITIONAL FAIL** — core detection works, false positive filtering does not.

## What Worked

1. **Signal detection is real.** The target gap ranked #1 in every positive case. The pipeline's combination of embedding + clustering + cosine similarity against competitor features reliably surfaces the known market gap.

2. **Discovery layer is essential.** All successful runs used Exa-derived subreddit selection. The Linear case failed 6 times with hand-guessed subreddits before the discovery probe was introduced (decision log 2026-02-21).

3. **Cost is within budget.** OpenAI costs per run: $0.02-0.03. Total backtest suite: ~$0.10. Well under the $50/month ceiling.

## What Failed

### 1. Negative control produced false positives (CRITICAL)

The email control case found 10 "gaps" scoring 0.640-0.760, including clusters about Firefox browsers, Android phones, and Google political controversies — none of which are email gaps. Root causes:

- **Market relevance filter too weak.** The `market_relevance_threshold: 0.45` allows clusters about browsers, phones, and general anti-Google sentiment to pass as "email client" gaps. Clusters like "firefox browser browsers mozilla" and "android privacy apps phones" should be filtered out entirely.
- **Broad subreddits inject off-topic noise.** r/degoogle, r/privacy, and r/selfhosted discuss everything from VPNs to search engines to phones. The pipeline has no mechanism to filter posts within a subreddit to only those relevant to the target market category.
- **Unaddressedness is inverted for off-topic clusters.** Comparing "android privacy apps" against Gmail's feature list produces low similarity (high unaddressedness) because they're completely different domains — but the pipeline interprets this as "unmet need."

### 2. VADER pain_intensity near-zero on mixed clusters (MODERATE)

Across all 4 cases, pain_intensity contributed little to scoring. VADER averages sentiment across entire clusters, so mixed clusters (pain posts + neutral posts) produce diluted scores. Gaps 3, 6, 7 in Linear scored 0.00 on pain_intensity. Gap 4 in Plausible scored 0.00.

The 15% scoring weight on pain_intensity is effectively inert for most clusters.

### 3. Mega-cluster frequency inflation (MODERATE)

Large clusters (500-1900+ mentions) dominate the frequency component (0.25 weight), pushing their overall scores up regardless of signal quality:
- Notion: 1935-mention cluster at rank 1
- Plausible: 1055 and 1117-mention clusters at ranks 1-2
- Email control: 653-mention cluster at rank 7

Frequency normalization uses `log(mention_count+1)`, but the log scale doesn't compress enough at these volumes.

### 4. Split and noisy clusters (MINOR)

- Plausible produced two separate privacy/GDPR clusters that should have been one
- Representative quotes frequently include off-topic content (Waze directions in the Plausible privacy cluster, Reddit username advice in the email spam cluster)

## Deficiencies to Fix (Priority Order)

| # | Issue | Severity | Fix Direction |
|---|-------|----------|---------------|
| 1 | Market relevance filter too weak | Critical | Raise threshold, add per-post relevance filtering before clustering, or embed market anchors as a hard gate |
| 2 | Off-topic clusters score high on unaddressedness | Critical | Unaddressedness should be undefined (not high) when a cluster is semantically distant from the market category |
| 3 | VADER pain_intensity near-zero | Moderate | Replace cluster-mean VADER with top-N most negative docs per cluster, or use LLM extraction urgency scores |
| 4 | Mega-cluster frequency inflation | Moderate | Cap frequency contribution or use percentile-based normalization |
| 5 | Noisy representative quotes | Minor | Filter quotes by cosine similarity to cluster centroid |
| 6 | Split clusters | Minor | Post-hoc merge clusters with >0.8 cosine similarity before scoring |

## Cost Summary

| Case | OpenAI Cost | Collection (s) | Classification (s) | Total (~min) |
|------|-------------|----------------|---------------------|--------------|
| Linear | $0.023 | 310 | 2921 | ~55 |
| Notion | $0.021 | 285 | 2650 | ~50 |
| Plausible | $0.023 | 310 | 2921 | ~55 |
| Email | $0.027 | 210 | 2512 | ~47 |

## Next Steps

1. Fix issues #1 and #2 (market relevance and unaddressedness inversion) — these are the critical path
2. Re-run all 4 backtests with fixes
3. Iterate until: 3/3 positive cases pass AND negative control produces no false positives
4. Then: fix VADER (#3) and frequency inflation (#4)
5. Then: revise product brief based on validated pipeline behavior
