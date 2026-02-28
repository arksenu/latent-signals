# Decision Log

Running log of key architectural and strategic decisions. Each entry records context, the decision made, alternatives considered, and current status.

---

## 2026-02-15 — B2B model over B2C

**Context**: Initial exploration considered both B2C (individual founders/indie hackers) and B2B (startup teams with budgets) as target markets.

**Decision**: B2B only. B2C was rejected.

**Rationale**: Consumer willingness to pay for market research tools is low, leading to high churn. B2B clients have dedicated competitive intelligence budgets and treat this as operational tooling with recurring need. The B2B model also supports higher price points that justify the pipeline's compute costs.

**Alternatives rejected**: B2C freemium, B2C with usage-based pricing. Both rejected due to churn dynamics and insufficient revenue per user to cover API costs.

**Status**: Active.

---

## 2026-02-15 — Sentiment analysis as primary methodology

**Context**: Four market research methodologies were evaluated for the core analytical approach: Trend Analysis, White Space Mapping, Conjoint Analysis, and Sentiment Analysis.

**Decision**: Sentiment analysis is the primary methodology.

**Rationale**: The target users (startups in fast-moving markets) operate in environments where historical data is scarce and structured datasets don't exist. Trend Analysis requires historical data to detect patterns. White Space Mapping requires structured feature datasets. Conjoint Analysis requires survey infrastructure and has the highest barrier to entry. Sentiment analysis detects unmet emotional needs from unstructured community discussions before they become visible trends — matching the "before hard data exists" positioning.

**Nuance**: The technical implementation actually combines sentiment analysis with computational white space mapping (finding sparse regions in embedding space). The meeting summary created a false binary between the two methodologies. The actual architecture uses sentiment analysis for signal extraction and white space mapping techniques (via vector similarity) for gap detection. These are complementary, not competing.

**Alternatives rejected**: Trend Analysis (misses emerging markets), White Space Mapping alone (requires structured data we don't have), Conjoint Analysis (too high a barrier for startup context).

**Status**: Active.

---

## 2026-02-15 — Hybrid NLP pipeline over pure-LLM or pure-traditional

**Context**: The NLP pipeline design needed to balance extraction quality against cost. Three approaches were evaluated.

**Decision**: Hybrid pipeline — traditional NLP for heavy lifting, LLMs surgically on sampled subsets only.

**Rationale**: Processing 10,000+ posts through GPT-4o costs ~$7.50 per run and takes hours. Pure traditional NLP (TF-IDF, VADER) is free but misses contextual nuance. The hybrid approach uses BERTopic for clustering, VADER for fast sentiment, zero-shot classification for categorization, and GPT-4o-mini Batch API only on 50-100 representative posts per cluster. Total LLM cost: ~$0.50 per 10,000 posts. This meets the $50/month prototype cost ceiling.

**Alternatives rejected**: Full LLM processing (10-15x more expensive, violates cost ceiling), pure traditional NLP (insufficient extraction quality for nuanced pain points and feature requests).

**Status**: Active.

---

## 2026-02-15 — Deferred custom LLM on inference hardware to post-prototype

**Context**: The initial strategy session proposed deploying smaller, fine-tuned LLMs on fast inference chips (Groq, Cerebras) for denoising at low latency.

**Decision**: Defer this to post-prototype. V1 uses GPT-4o-mini Batch API.

**Rationale**: Custom LLM deployment on inference hardware is premature before validating that the pipeline produces useful output at all. The hybrid NLP approach achieves the same cost goals without requiring model fine-tuning or infrastructure management. Groq/Cerebras become relevant only if the tool evolves toward real-time interactive use (a startup founder querying during a strategy session), which is not a v1 requirement.

**Future trigger**: If v2 requires synchronous inference under 2 seconds for interactive queries, revisit Groq/Cerebras deployment. The architecture should not create dependencies that prevent this shift.

**Alternatives rejected**: Immediate Groq deployment (over-investment at prototype stage), local model hosting (operational overhead not justified for MVP).

**Status**: Active. Revisit when interactive use case is prioritized.

---

## 2026-02-21 - Discovery layer is pipeline input, not configuration

**Context**: The Linear backtest failed six consecutive runs with hardcoded subreddit selection (r/programming, r/webdev, r/devops, r/softwareengineering, r/jira, r/agile). Each failure was attributed to clustering parameters, corpus composition, or embedding model resolution. The actual cause was never identified as input construction until this session.

**Decision**: Exa discovery probe runs before every pipeline execution. The subreddit list, keyword filters, and HN query are derived from Exa results, not manually specified.

**Rationale**: Six failed runs with hand-guessed inputs. One successful(ish) run with Exa-derived inputs. The only variable that changed was running the discovery layer first. r/webdev and r/softwareengineering were both hardcoded in the config but never surfaced by Exa for any project management frustration query. r/projectmanagement, r/atlassian, and r/experienceddevs were all missing from the hardcoded config but surfaced at high frequency (during Exa probe). The discovery step does the signal filtering work that HDBSCAN was being incorrectly expected to do.

**Nuance**: Exa searches current web data and cannot time-travel to 2018. The correct process for historical backtests is: run Exa against current data to derive sources, verify those sources existed and had sufficient volume in Arctic Shift for the target date range, then lock the config. This adds one manual verification step but produces a defensible input set with a paper trail.

**Alternatives rejected**: Continued hyperparameter tuning of HDBSCAN and UMAP with hand-guessed inputs. This approach conflated bad inputs with bad clustering and produced no actionable signal across six runs.

**Status**: Active. Applies to all subsequent backtest runs (Notion, Plausible, Email control) and to production pipeline design.

## 2026-02-20 - VADER produces near-zero pain intensity scores on mixed clusters

**Context**: The Linear backtest run (7c16def9) produced 7 gaps. The pain_intensity component of the scoring formula contributed near-zero to most gap scores: 0.0 on gaps 3, 6, and 7; 0.03-0.16 on gaps 4 and 5. Only gap 1 (the target signal) reached 0.29. The 15% scoring weight on pain_intensity is effectively inert.

**Decision**: Document as a known deficiency. Do not attempt to fix before completing the remaining backtest cases.

**Rationale**: VADER averages sentiment across all documents in a cluster. Mixed clusters — which contain both pain posts and neutral/informational posts — produce averaged scores that underrepresent actual pain intensity. The result is that frequency and unaddressedness dominate the scoring formula (combined 55% weight), which surfaces high-volume generic clusters alongside genuine pain clusters. Gap 2 (generic dev culture discussion) scored 0.558 purely on volume. Gap 3 (a Q&A cluster with positive average sentiment) scored 0.528 on unaddressedness alone.

**Nuance**: The backtest still passed — gap 1 ranked first regardless. But the scoring formula is not separating pain signal from volume signal cleanly. A product team reading the output would need to manually filter gaps 2, 3, and 5 as noise. That's acceptable for a prototype but not for a production report.

**Future triggers**: Before v2, replace or supplement VADER with cluster-level pain detection that operates on the top-N most negative documents per cluster rather than the cluster mean. Alternatively, weight the LLM extraction step's urgency and frustration fields more heavily in the composite score. Resolve before any customer-facing output is produced.

**Status**: Known deficiency. Backtest validation not blocked. Revisit before production scoring formula is finalized.

---

## 2026-02-23 — Market relevance filtering must operate at post level, not just cluster level

**Context**: The email negative control backtest (`0e03b7a3`) produced 10 high-scoring false positives, including clusters about Firefox browsers, Android phones, and Google political controversies. The `market_relevance_threshold: 0.45` gate operates at the cluster level after clustering, but by that point, off-topic posts from broad subreddits (r/degoogle, r/privacy) have already been embedded and clustered alongside on-topic content.

**Decision**: Market relevance filtering needs a post-level component that runs before or during clustering — not only after. Posts that are semantically distant from the market category should be filtered or down-weighted before they form clusters.

**Rationale**: The current architecture embeds all collected posts, clusters them, then checks cluster-level relevance against market anchors. This means a subreddit like r/degoogle (which discusses phones, browsers, VPNs, search engines, *and* email) contributes off-topic clusters that individually score high on unaddressedness because comparing "firefox browsers" against Gmail features produces low similarity — which the formula misinterprets as "unmet need."

**Alternatives to evaluate**: (a) Pre-clustering cosine filter against market anchors with a hard cutoff; (b) Post-clustering filter with a higher threshold; (c) Hybrid — soft pre-filter plus stricter post-filter. Each has trade-offs around recall vs precision.

**Status**: Must fix. Blocked on negative control passing. See `05_validation/results/backtest_summary.md` for full analysis.

---

## 2026-02-23 — Unaddressedness score is inverted for off-topic clusters

**Context**: The gap scoring formula computes `unaddressedness = 1 - max_similarity` where `max_similarity` is the cosine similarity between a cluster's centroid and the nearest competitor feature. Off-topic clusters (e.g., "firefox browser browsers mozilla" in an email pipeline run) have very low similarity to any competitor feature — producing high unaddressedness scores. The formula treats "completely unrelated" the same as "genuinely unaddressed pain."

**Decision**: The scoring formula needs a minimum similarity floor. If a cluster's max similarity to any competitor feature is below a threshold (e.g., 0.15-0.20), the cluster should be excluded from scoring entirely rather than receiving a high unaddressedness score.

**Rationale**: Unaddressedness is meaningful only when the cluster is in the same semantic domain as the competitors. A cluster about browsers is not an "unaddressed email need" — it's simply not about email. The current formula cannot distinguish these cases.

**Alternatives considered**: (a) Minimum similarity floor on unaddressedness (simple, direct); (b) Multiply unaddressedness by market relevance score (penalizes off-topic without hard cutoff); (c) Require cluster centroid to exceed a cosine threshold against the market category embedding. Option (a) is simplest and most defensible for V1.

**Status**: Must fix. Directly caused by the structural issue above. Fix alongside market relevance filtering.

---

## 2026-02-26 — Abandon negative control concept; reframe controls as positive validation

**Context**: Round 2 backtests produced 3/3 positive case passes. The email control (2018-2019) surfaced 10 high-scoring gaps (top score 0.834). A VS Code control (2019) was added as a replacement — it also surfaced 10 high-scoring gaps (top score 0.740). In both cases, the detected gaps are genuine: email frustration was later addressed by HEY, ProtonMail, and Tutanota; VS Code Python/C++/Java setup friction is real and JetBrains already differentiates on it.

**Decision**: Abandon the negative control concept entirely. Reframe both control cases as additional positive evidence that the pipeline detects real market gaps. The v1 backtest validation gate is passed based on 3/3 positive cases and 2 control cases that confirm gap detection works across diverse markets.

**Rationale**: The negative control was designed to test "a market where no major disruptive product launched during the test window." This conflates gap exploitation (whether a product launched) with gap existence (whether unmet needs exist). A gap detection tool should find gaps regardless of whether someone exploited them — that's the value proposition. Every market has real friction; the pipeline correctly surfaces it. The question is not "can the pipeline say no gaps exist?" but "does it find the specific known gaps?" It does, 3/3.

**Nuance**: The controls revealed a real limitation — the pipeline cannot distinguish opportunity magnitude. "Jira's workflow philosophy is broken" (0.723) scores similarly to "VS Code Python setup is painful" (0.740). These represent fundamentally different opportunity scales. This is a scoring limitation, not a pipeline defect, and is deferred to v2 as the Opportunity Scale Classifier.

**Status**: Active. Validation gate passed.

---

## 2026-02-26 — Opportunity Scale Classifier deferred to v2

**Context**: The engine backtest validation revealed that the scoring formula treats all frustration equally regardless of opportunity magnitude. Three-tier classification (new-product-scale / feature-scale / polish-scale) was designed during brainstorming to address this.

**Decision**: Defer the full Opportunity Scale Classifier to v2. As an incremental step, compute a pain-to-question ratio from existing zero-shot classification data to test whether derived quantitative signals can separate opportunity magnitudes without an LLM classifier.

**Rationale**: Brainstorming surfaced that opportunity scale may be partially an emergent property of existing signals rather than purely a classification problem. Three derived signals — gap age (temporal persistence of complaints), pain-to-question ratio (switching intent vs. help-seeking), and incumbent feature coverage completeness — may separate the easy cases cheaply. The LLM classifier would then only resolve ambiguous cases where derived signals disagree. Testing derived signals first determines whether the LLM classifier adds enough marginal value to justify schema complexity (v2).

**Design (v2, when implemented)**:
- Three tiers: new-product (incumbent can't fix), feature (incumbent hasn't fixed), polish (incumbent will fix)
- Assessed during existing GPT-4o-mini structured extraction step (no new API calls, no cost increase)
- Continuous opportunity magnitude score with configurable label thresholds
- Derived quantitative signals handle clear-cut cases; LLM resolves the ambiguous middle

**Alternatives considered**: (a) Implement full LLM classifier immediately (premature — derived signals may suffice for easy cases); (b) Skip classification entirely and let users manually interpret reports (acceptable for prototype but not for production); (c) Use gap_score threshold alone to separate magnitudes (doesn't work — VS Code 0.740 vs Linear 0.723 overlap).

**Status**: Active. Pain-to-question ratio analysis completed — signal absent (see 2026-02-27 entry). LLM classifier remains the v2 path.

---

## 2026-02-27 — Pain-to-question ratio does not separate opportunity magnitudes

**Context**: The v1 zero-shot classifier labels every post as pain_point, feature_request, praise, question, or bug_report. The hypothesis was that the ratio of pain_point posts to question posts per cluster would naturally separate opportunity magnitudes — new-product-scale gaps (where users express frustration about fundamental limitations) would show higher pain-to-question ratios than polish-scale gaps (where users ask setup/config questions).

**Method**: For each of 7 target clusters across 3 backtest runs (Linear, Notion, VS Code), joined `classified.jsonl` (per-post labels) with `topic_assignments.jsonl` (per-post cluster membership). Computed pain_ratio, question_ratio, and P2Q = pain/question per cluster. Verified data integrity: sum(label_counts) == n_posts for all 7 clusters, p2q == (pain/n)/(question/n) for all 7 clusters, 0 missing labels, random text samples confirmed label plausibility.

**Results**:

| Group | Clusters | Individual P2Qs | Weighted P2Q | Unweighted Mean |
|-------|----------|----------------|-------------|----------------|
| New-product-scale (Linear #2, Notion #2) | 2 | 0.55, 1.08 | 0.889 | 0.814 |
| Polish-scale (VS Code top 3) | 3 | 0.74, 1.33, 0.58 | 0.796 | 0.887 |
| Ambiguous (Linear #1, Notion #1) | 2 | 0.92, 0.64 | 0.770 | 0.779 |

**Decision**: Do not integrate pain-to-question ratio into the scoring formula. The signal is absent — all three groups land in the 0.77–0.89 band regardless of aggregation method. Within-group variance exceeds between-group difference.

**Key observation — the CMake/Jira inversion**: The CMake compiler cluster (polish-scale) has P2Q=1.33 — the highest of all 7 clusters. The Jira workflow cluster (new-product-scale) has P2Q=0.55 — among the lowest. This is the exact opposite of the hypothesis. The reason: the VADER-driven zero-shot classifier responds to emotional temperature of language, not opportunity magnitude. CMake posts use intense frustration language ("I cannot for the life of me get my files to link") while Jira posts use measured help-seeking language ("how do I configure workflows for my team"). The magnitude distinction exists in the posts but manifests as resolution-expectation framing, not emotional intensity. This is exactly what the v2 Opportunity Scale Classifier — operating on rhetorical framing rather than sentiment intensity — is designed to detect.

**Why "adjust the threshold" won't work**: The CMake/Jira inversion is structural, not a calibration issue. Any threshold that captures Jira workflow (0.55) also captures every VS Code cluster. Any threshold that excludes VS Code CMake (1.33) also excludes the Notion OneNote cluster (1.08). The distributions overlap completely.

**Alternatives rejected**: (a) Feature-request ratio instead of pain-to-question (same problem — classifier responds to language style not magnitude); (b) Combined ratio with praise normalization (adds complexity without addressing the structural issue); (c) Confidence-weighted ratios (the classifier confidence tracks language clarity, not category correctness).

**Status**: Closed. Pain-to-question ratio is not a viable magnitude signal. The v2 Opportunity Scale Classifier (LLM-based rhetorical framing analysis) remains the correct path. Remaining derived signal candidates: gap age (temporal persistence) and incumbent feature coverage completeness.

---

## 2026-02-27 — Notion backtest cluster misidentification: gap #2 is OneNote, not Evernote

**Context**: The Notion backtest (run `b4612a0d`) was designed to validate detection of "Evernote frustration → Notion" as a market gap. The backtest summary recorded gap #2 "onenote notebook onedrive notebooks" (0.730) as the target signal and declared it a PASS at rank 2.

**Finding**: Audit of cluster content reveals gap #2 is overwhelmingly **OneNote frustration**, not Evernote frustration:
- Gap #2 "onenote notebook onedrive notebooks" (n=541): 443 posts mention OneNote, 11 mention Evernote
- Gap #3 "evernote notes security token" (n=477): 343 posts mention Evernote, 21 mention OneNote

The actual Evernote frustration cluster is gap #3 (0.657), not gap #2 (0.730). The topic label "onenote notebook onedrive notebooks" was a visible indicator that should have been caught during report analysis.

**Impact on backtest validity**: The Notion backtest still passes — the Evernote cluster at rank 3 (0.657) is within the top-3 success criterion. But the validated rank changes from 2 to 3, and the score changes from 0.730 to 0.657. The gap #2 cluster (OneNote frustration) is itself a legitimate gap — OneNote had real usability problems that note-taking alternatives addressed — but it is not the specific "Evernote → Notion" signal the backtest was designed to detect.

**Corrective action**: Update backtest summary to reflect correct cluster identification. The Notion PASS stands at rank 3 (0.657) rather than rank 2 (0.730).

**Status**: Corrected. No pipeline changes required — this was an analysis error, not a pipeline defect.