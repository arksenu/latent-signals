# Backtest Summary

**Date**: 2026-02-23 (round 1), 2026-02-25 (round 2)
**Pipeline version**: Pre-v1 prototype (sequential pipeline, 6 stages)

## Overview

Four historical backtests were run against the pipeline to answer: "Can this architecture detect known market gaps from historical community data?"

Two rounds have been completed. Round 1 identified deficiencies; round 2 applied targeted fixes and re-ran all 4 cases.

## Round 2 Results (2026-02-25)

Fixes applied: post-level market relevance filter, unaddressedness similarity floor, VADER top-N pain intensity, frequency p95 cap.

| Case | Market | Target Signal | Expected | Run ID | Round 1 | Round 2 |
|------|--------|--------------|----------|--------|---------|---------|
| Linear | Project management | Jira frustration → Linear | Top 3 | `7c16def9` | Rank 1 (0.705) | Rank 2 (0.723). Score improved, rank dropped 1 due to sysadmin cluster. |
| Notion | Note-taking | Evernote frustration → Notion | Top 3 | `b4612a0d` | Rank 1 (0.646) | Rank 2 (0.730). Score improved, rank dropped 1 due to generic bugs cluster. |
| Plausible | Web analytics | GA privacy frustration → Plausible | Top 3 | `0fb9aed4` | Ranks 1-2 (0.725, 0.692) | Ranks 1-2 (0.776, 0.745). Both scores improved. |
| Email (control) | Email clients | No gap expected | 0 gaps | `0e03b7a3` | **FAIL**: 10 gaps, top 0.760 | **FAIL**: 10 gaps, top 0.834 |

### Round 2 Pass/Fail Assessment

- Positive cases: **3/3 PASS** (all signal in top 3, scores improved across the board)
- Negative control: **FAIL** (10 false positives, top score now 0.834)
- Overall: **CONDITIONAL FAIL** — same verdict as round 1, but for a different reason (see analysis below)

### What Round 2 Fixed

1. **Pain intensity is now working.** VADER top-N (20 most negative) replaced cluster-mean. Scores improved significantly across all positive cases — e.g. Linear gap #2 pain went from ~0.00 to 0.76, Notion gap #2 from ~0.00 to 0.91.
2. **Frequency cap prevents mega-cluster dominance.** P95 cap on mention counts compresses the frequency component for outlier clusters.
3. **Unaddressedness floor gates irrelevant clusters.** Clusters with max_sim < 0.15 to competitor features are excluded from scoring.
4. **Post-level market relevance filter exists.** Individual documents below cosine similarity threshold (0.20) to market anchors are dropped before clustering.

### Why the Negative Control Still Fails

The round 1 email control failure was caused by off-topic clusters (Firefox, Android, politics) scoring high. The round 2 fixes successfully address that class of failure — those off-topic clusters would now be filtered.

However, the email control clusters in round 2 are **genuinely email-related**: ProtonMail frustration (max_sim 0.276), Gmail alternatives (0.344), spam filtering (0.559), attachments (0.251), encryption (0.292). These are real frustrations with real email products that the pipeline correctly detects.

The pipeline cannot distinguish between:
- "Frustrated users with an unaddressed gap" (positive signal → a product like HEY could fill this)
- "Frustrated users in a market where frustration exists but no disruptive product emerged" (false positive)

This is a **fundamental scoring model limitation**, not a filtering problem. The fixes addressed the filterable false positives; the remaining false positives are semantically valid but historically didn't produce a market gap.

**Email control scores increased** in round 2 because the pain intensity fix now correctly captures email frustration sentiment that was previously diluted to 0.00.

## Round 1 Results (2026-02-23)

| Case | Market | Target Signal | Expected | Run ID | Result |
|------|--------|--------------|----------|--------|--------|
| Linear | Project management | Jira frustration → Linear | Top 3 | `7c16def9` | Rank 1 (0.705). 7 gaps total. |
| Notion | Note-taking | Evernote frustration → Notion | Top 3 | `b4612a0d` | Rank 1 (0.646). 7 gaps total. |
| Plausible | Web analytics | GA privacy frustration → Plausible | Top 3 | `0fb9aed4` | Ranks 1-2 (0.725, 0.692). 4 gaps total. |
| Email (control) | Email clients | No gap expected | 0 gaps | `0e03b7a3` | **FAIL**: 10 gaps, top score 0.760. |

### Round 1 Deficiencies (status after round 2)

| # | Issue | Severity | Status | Notes |
|---|-------|----------|--------|-------|
| 1 | Market relevance filter too weak | Critical | **Fixed** | Added post-level filter in stage 3 + cluster-level threshold raised |
| 2 | Off-topic clusters score high on unaddressedness | Critical | **Fixed** | Added `unaddressedness_floor` config param (0.15) |
| 3 | VADER pain_intensity near-zero | Moderate | **Fixed** | Top-20 most negative VADER compounds per cluster |
| 4 | Mega-cluster frequency inflation | Moderate | **Fixed** | P95 cap on mention counts before log normalization |
| 5 | Noisy representative quotes | Minor | Deferred | Not in scope for round 2 |
| 6 | Split clusters | Minor | Deferred | Not in scope for round 2 |

## What Worked (Both Rounds)

1. **Signal detection is real and improving.** Target gaps ranked in top 2 in every positive case across both rounds. Round 2 scores improved across the board.
2. **Discovery layer is essential.** All successful runs used Exa-derived subreddit selection.
3. **Cost is within budget.** OpenAI costs per run: $0.02-0.03. Total across both rounds: ~$0.20.
4. **Fixes are composable.** Four independent changes improved positive case scores without breaking signal detection.

## Open Questions

1. **Should the negative control be redefined?** The email market has real frustration — HEY launched June 2020, just after the control window closed. A better negative control might use a market with genuinely no frustration (mature commodity).
2. **Is a score threshold viable?** If positive cases score 0.45-0.78 and email control scores 0.67-0.83, there's no clean separation. A threshold-based approach won't work without additional signal dimensions.
3. **Does "gap detection" require a temporal component?** The pipeline detects frustration, not gaps. A true gap might require evidence that frustration is *new* or *growing* relative to the market — which the trend component partially captures but doesn't gate on.

## Cost Summary (Both Rounds)

| Case | Round 1 Cost | Round 2 Cost | Notes |
|------|-------------|-------------|-------|
| Linear | $0.023 | $0.023 | Round 2 re-ran stages 3-6 only |
| Notion | $0.021 | $0.020 | Round 2 re-ran stages 3-6 only |
| Plausible | $0.023 | $0.022 | Round 2 re-ran stages 3-6 only |
| Email | $0.027 | $0.025 | Round 2 re-ran stages 3-6 only |
| **Total** | **$0.094** | **$0.090** | |

## Next Steps

1. Decide on negative control strategy (redefine control case, add temporal gating, or accept current limitation and document)
2. Fix minor issues (#5 quotes, #6 split clusters) if pursuing further rounds
3. Revise product brief based on validated pipeline behavior
4. Update CLAUDE.md validation status
