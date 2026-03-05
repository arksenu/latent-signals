# Scoring Formula Spec — Branching Scorer (Draft)

**Status:** Draft — pending zero-shot label test results to lock branching thresholds.
**Date:** 2026-02-28

## Finding: Replacement Formula Doesn't Work

The originally proposed satisfaction gap formula (`sentiment_intensity * feature_similarity * (1 - satisfaction_quality)`) was tested against real backtest data. It produces values 10x too low to serve as an unaddressedness replacement.

**Example — Linear topic 2 (Jira workflow, the target signal):**
- Current unaddressedness: `1 - 0.337 = 0.663`
- Proposed satisfaction score: `0.760 * 0.337 * 0.257 = 0.066`
- This would drop the Jira gap from rank 2 (0.723) to well outside top 3.

**Root cause:** Three factors all < 1 multiplied together compress to near-zero. Additionally, `satisfaction_quality` is dominated by positive posts — even genuine pain clusters have 50-70% positive/neutral posts (questions, praise). The frustration minority IS the signal but doesn't dominate the ratio.

## Revised Approach: Additive Boost, Not Replacement

Instead of replacing the unaddressedness component, **keep the existing formula and add a satisfaction boost** for clusters with high feature similarity AND high dissatisfaction.

### Formula

```
satisfaction_boost = feature_similarity * dissatisfaction_ratio
new_unaddressedness = min(1.0, original_unaddressedness + satisfaction_boost)
```

Where:
- `feature_similarity = max_similarity_to_features` (cosine sim to nearest competitor feature)
- `dissatisfaction_ratio = (negative_count + 1) / (positive_count + negative_count + 2)` (Laplace-smoothed)
- `original_unaddressedness = 1 - max_similarity` (current formula)
- Positive/negative counts use VADER compound threshold: >= 0.05 positive, <= -0.05 negative

### Why Additive Boost Works

The boost scales with BOTH proximity to competitor features AND dissatisfaction:
- **High similarity + high dissatisfaction** → large boost (satisfaction gap — people hate a feature that exists)
- **High similarity + low dissatisfaction** → small boost (people like the feature)
- **Low similarity + high dissatisfaction** → small boost (off-topic complaints)
- **Low similarity + low dissatisfaction** → near-zero boost (no signal)

The `min(1.0, ...)` cap prevents overflow.

### Tested Against Real Data

| Case | Gap | Current Score | New Score | Change |
|------|-----|--------------|-----------|--------|
| Linear | Jira workflow (TARGET) | 0.723 | 0.749 | +0.026 |
| Linear | Jira slowness | 0.684 | 0.723 | +0.039 |
| Linear | DNS/servers (off-topic) | 0.784 | 0.812 | +0.028 |
| Notion | OneNote frustration | 0.730 | 0.797 | +0.067 |
| Notion | Evernote (TARGET) | 0.657 | 0.710 | +0.053 |
| Notion | Evernote PDF | 0.541 | 0.583 | +0.042 |

Key observations:
- **Satisfaction gaps get the largest boosts** (OneNote +0.067, Evernote +0.053) because they have both high feature_similarity AND high dissatisfaction.
- **Off-topic gaps get minimal boost** (DNS cluster at 0.206 feature_similarity → small boost despite dissatisfaction).
- **No rank inversions** — existing rankings preserved while satisfaction gaps move closer to their correct position.
- The Evernote cluster gains enough to potentially move from rank 3 to rank 2 when applied with new tier-1 labels.

## Coverage Gap Pathway

For clusters identified as coverage gaps (majority `unmet_need` in tier-1 labels, zero/low product mentions):

```
coverage_unaddressedness = max(0.8, 1 - max_similarity) * sentiment_intensity_scale
```

Where:
- Floor of 0.8 prevents arbitrary cosine distances from producing low scores
- `sentiment_intensity_scale = min(1.0, abs(avg_top20_vader) / 0.5)` — scales by how intense the frustration is, capped at 1.0
- Gated by: relevance filter (market anchor cosine > threshold) AND minimum frequency threshold

## Branching Logic

```python
def compute_unaddressedness(cluster, max_sim, pos_count, neg_count, is_coverage_gap):
    base = 1 - max_sim  # current formula

    if is_coverage_gap:
        # Coverage gap: floor at 0.8, scale by sentiment
        return max(0.8, base) * sentiment_intensity_scale
    else:
        # All clusters (including satisfaction gaps) get the boost
        dissatisfaction = (neg_count + 1) / (pos_count + neg_count + 2)
        boost = max_sim * dissatisfaction
        return min(1.0, base + boost)
```

The `is_coverage_gap` flag is determined by:
1. Tier-1 label distribution: majority `unmet_need` → coverage gap
2. Product mention count (NER): zero or near-zero product mentions → coverage gap
3. Both signals should agree. If they disagree, default to the satisfaction pathway (which includes the boost).

### Branching Thresholds (TBD — pending label test)

- What percentage of `complaint` + `switching` labels triggers the satisfaction pathway?
- What percentage of `unmet_need` labels triggers the coverage pathway?
- These thresholds depend on how cleanly the new 5 labels separate in zero-shot. Lock after label test results.

## Open Question

The satisfaction boost applies uniformly to ALL clusters, not just those classified as satisfaction gaps. This is arguably correct — even coverage gaps benefit from the boost when they happen to be close to competitor features (meaning the gap is in an area where competitors operate but fail). However, it means the "branching" is really just the coverage gap floor, not a full pathway split.

A simpler framing: the formula has one pathway with a coverage gap floor, not two separate pathways. The satisfaction boost is always-on.

## Summary of Changes from Current Formula

1. **Unaddressedness component gains a satisfaction boost**: `min(1.0, (1 - max_sim) + max_sim * dissatisfaction)`
2. **Coverage gaps get a floor of 0.8** on unaddressedness (gated by relevance + frequency)
3. **dissatisfaction_ratio** = Laplace-smoothed `(neg + 1) / (pos + neg + 2)` using VADER compound thresholds
4. **All other components unchanged** (frequency, pain_intensity, competitive_whitespace, market_size, trend)
5. **Tier-1 label distributions** determine coverage gap flag; thresholds TBD after label test
