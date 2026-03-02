# TODO

Tracked work items for Latent Signals pipeline. Updated 2026-03-02.

## Completed (Engine validation milestone)

- [x] **Post-level market relevance filter** — Fixed in round 2. Drops docs below cosine 0.20 to market anchors before clustering. Config: `embedding.post_relevance_threshold`.
- [x] **Unaddressedness similarity floor** — Fixed in round 2. Clusters with max_sim < 0.15 excluded from scoring. Config: `scoring.unaddressedness_floor`.
- [x] **Fix VADER pain_intensity** — Fixed in round 2. Top-20 most negative VADER compounds per cluster instead of cluster mean.
- [x] **Cap frequency inflation from mega-clusters** — Fixed in round 2. P95 cap on mention counts before log normalization.
- [x] **Backtest validation** — 3/3 positive cases pass (Linear rank 2/0.723, Notion rank 3/0.657, Plausible ranks 1-2/0.776/0.745). 2 control cases (email, VS Code) confirm pipeline detects real gaps. Validation gate passed.
- [x] **Documentation finalized** — backtest_summary.md, CLAUDE.md, decision_log.md, product_brief.md all updated.

## Opportunity Magnitude Signals

- [x] **Pain-to-question ratio analysis** — Signal absent. All opportunity groups land in 0.77–0.89 P2Q band; CMake (polish) has P2Q=1.33 while Jira (new-product) has P2Q=0.55 — inverted from hypothesis. Classifier responds to emotional temperature, not magnitude. See decision log 2026-02-27.
- [ ] **Gap age / temporal persistence** — Explore whether complaint duration (how long frustration persists across the observation window) correlates with opportunity magnitude. Requires timestamp analysis of posts within clusters.
- [ ] **Incumbent coverage completeness** — Explore whether the semantics of competitor feature descriptions (is the feature space comprehensive?) predict fixability. A comprehensive feature list + low similarity = architectural gap. A sparse feature list + low similarity = just hasn't been built yet.

## Minor (polish, no timeline)

- [ ] **Filter representative quotes by relevance** — Quotes should be cosine-similar to cluster centroid. Currently includes off-topic content.
- [ ] **Merge semantically similar clusters** — Post-hoc merge clusters with >0.8 cosine similarity before scoring. Plausible produced two separate privacy/GDPR clusters that should have been one.

## v2 — Opportunity Scale Classifier (deferred)

- [ ] **Three-tier LLM classification** — Add `opportunity_scale` field (new-product / feature / polish) to GPT-4o-mini structured extraction schema. Only fires on clusters where derived signals (v1.1) are ambiguous. Design documented in decision log 2026-02-26.
- [ ] **Continuous magnitude score** — Continuous 0-1 opportunity magnitude with configurable label thresholds, rather than hard bins.
- [ ] **Report rendering by job-to-be-done** — Job 1 (Discovery) filters to new-product-scale. Job 2 (Expansion) shows all scales.
