# Latent Signals — Sprint Roadmap

**Updated:** 2026-02-28
**Current milestone:** Stage 0 — Automated Input Layer
**End goal:** A user types a sentence → gets a scored gap report. No manual input construction.

---

## Milestone: Engine Validation (COMPLETE)

Pipeline stages 1-6 validated across 5 backtest cases. 3/3 positive cases pass. Engine works.

- [x] Post-level market relevance filter (round 2 fix)
- [x] Unaddressedness similarity floor (round 2 fix)
- [x] VADER top-N pain intensity (round 2 fix)
- [x] Frequency P95 cap (round 2 fix)
- [x] Backtest validation — Linear rank 2 (0.723), Notion rank 3 (0.657), Plausible ranks 1-2 (0.776, 0.745)
- [x] Control cases — Email and VS Code surface genuine gaps
- [x] Pain-to-question ratio analysis — signal absent, closed

---

## Milestone: Stage 0 — Automated Input Layer (CURRENT)

The engine is validated but has no front door. Every backtest required hand-written Exa queries, manually curated subreddit lists, hand-authored market anchors, manually identified competitors, and hand-written competitor feature files. Stage 0 automates all of this.

**Done means:** You can type `"project management"` and get a gap report equivalent to the Linear backtest — no YAML config, no discovery scripts, no competitor feature files.

### Phase 1: Experiments (parallel, do first)

Validate the three highest-uncertainty assumptions before building anything.

- [x] **NER experiment** — PASS. All known competitors in top 1-2 by frequency with clear cliffs (6-9x drops). Results: `data/experiment_ner_results.json`
  - Linear: Jira rank 1 (1550, next 235). Notion: OneNote rank 1 (2730), Evernote rank 2 (2431). Plausible: GA rank 2 (1903). Email: Gmail rank 2 (1942). VS Code: rank 1 (4045).
  - spaCy NER viable for competitor extraction. Use `en_core_web_lg` in production (10x faster, sufficient for product names).
- [x] **Zero-shot label test** — FAILED (3 attempts). BART zero-shot cannot reliably separate 5 gap-relevant labels. One label always absorbs 65-87% of posts regardless of phrasing.
  - v1: "switching" absorbed 64.7%. v2 hypothesis-style: "praise" absorbed 87%. v2 short-style: "unmet_need" absorbed 75%.
  - Results: `data/experiment_zero_shot_labels.json`, `data/experiment_zero_shot_labels_v2.json`
  - **Decision needed:** (a) try DeBERTa model, (b) pivot to VADER-only branching (dissatisfaction ratio works without labels), (c) accept and work around it
- [x] **Scoring formula spec** — Drafted with key revision. Original replacement formula produces values 10x too low. Additive boost formula works: `new_unaddressedness = min(1.0, (1-max_sim) + max_sim * dissatisfaction_ratio)`
  - Spec: `latent-signals/02_requirements/scoring_formula_spec_v2.md`
  - Satisfaction gaps get largest boosts (OneNote +0.067, Evernote +0.053). Off-topic gaps get minimal boost. No rank inversions.
  - Coverage gap floor (0.8) still applies. Branching is really just the floor — the additive boost is always-on.
  - **Thresholds for coverage gap flag still TBD** — depends on how we resolve the zero-shot label failure

### Phase 2: Stage 0a — Input Automation (after Phase 1 passes)

Automate everything except competitor discovery. This gets a partially functional Stage 0 — coverage gaps work end-to-end without NER.

- [x] **Exa passthrough** — User description → Exa semantic search (direct, no LLM intermediary). Neutral queries, no frustration bias.
- [x] **Auto-extract sources** — Exa results → extract subreddits + HN threads, filter by volume via Arctic Shift
- [x] **Market anchor generation** — Extracted terms → frustration anchors; supplementary anchors from Exa result n-grams (non-optional)
- [x] **Additive boost scoring** — `min(1.0, (1-max_sim) + max_sim * dissatisfaction_ratio)` where `dissatisfaction_ratio = (neg+1)/(pos+neg+2)` using VADER compound thresholds (>= 0.05 pos, <= -0.05 neg). Always-on, no branching trigger.
- [x] **NER entity counting per cluster** — spaCy `en_core_web_lg` on all docs, ORG/PRODUCT entities stored in `ClassifiedDocument.entities`. Count per cluster used for coverage gap detection.
- [x] **Coverage gap handling** — Clusters with < 3 or < 5% NER entity mentions → `is_coverage_gap=True` → `max(0.8, unaddressedness)` floor applied.
- [x] **Granular gap_type field (tier 2)** — `gap_type` added to `FeedbackAnalysis` schema: workflow_friction, capability_limitation, reliability_failure, integration_gap, economic_barrier, trust_deficit, regulatory_friction, customization_deficit, learning_curve, other. Stored in `ClassifiedDocument.llm_gap_type`.

### Phase 3: Stage 0b — Competitor Discovery (after 0a works)

Automate competitor identification and feature extraction. This completes Stage 0 — satisfaction gaps work end-to-end.

- [x] **Exa Answer competitor+feature extraction** — Single `client.answer()` call with structured JSON schema → competitors + features. Output saved as multi-competitor YAML, loaded by Stage 6 via updated `load_features()`. Module: `stage0_input/competitor_discovery.py`.
- [x] **Competitor profile caching** — JSON cache keyed by SHA-256 of normalized query, 30-day TTL. Cache dir: `data/cache/competitors/`.
- [x] **Market source map caching** — Full discovery+sources+anchors cached as JSON, 7-day TTL. Avoids re-running Exa probes and Arctic Shift checks for repeat queries. Module: `stage0_input/source_cache.py`.

### Phase 4: Stage 0 Validation

Prove the automated path produces equivalent results to manual input construction.

- [ ] **Re-run backtests with automated inputs** — Replace manual configs with single query string per test case ("project management", "note-taking apps", "web analytics"). Compare rankings to manual-input results
  - Pass: automated path produces equivalent or better rankings on all 3 positive cases
  - Target signal must appear in top 3 for each case
- [ ] **Score distribution analysis** — Verify branching scorer separates satisfaction gaps from coverage gaps correctly across all test cases

### Phase 5: Documentation (after Stage 0 validated)

Update docs to reflect the actual product architecture, not just the engine.

- [ ] **Product brief rewrite** — Structural rewrite: distinguish engine validation from product readiness, add Stage 0, update pipeline description to 7 stages
- [ ] **CLAUDE.md final update** — Stage 0 section, branching scorer formula, updated pipeline description
- [ ] **Scoring function spec** — Full spec with validated thresholds from experiments + backtest results
- [ ] **Architecture docs** — Add Stage 0 to architecture.md and data_pipeline.md
- [ ] **README** — Write after product brief is corrected

---

## Backlog (no timeline, pick up as relevant)

- [ ] **Pattern matching supplement** — Keyword/pattern heuristics on cluster-level representative samples (alongside GPT-4o-mini extraction, not separate stage). Free, deterministic, catches obvious cases
- [ ] **Filter representative quotes by relevance** — Quotes should be cosine-similar to cluster centroid
- [ ] **Merge semantically similar clusters** — Post-hoc merge clusters with >0.8 cosine similarity before scoring
- [ ] **Gap age / temporal persistence** — Does complaint duration correlate with opportunity magnitude?
- [ ] **Incumbent coverage completeness** — Do competitor feature description semantics predict fixability?
- [ ] **Tier-1 label distribution as magnitude proxy** — High `switching` + `complaint` = new-product-scale. High `friction` + `complaint` = incumbent-fixable. Evaluate after Stage 0

---

## v2 (deferred)

- [ ] **Opportunity Scale Classifier** — Three-tier LLM classification (new-product / feature / polish) in GPT-4o-mini schema. Only fires where tier-1 label distributions are ambiguous
- [ ] **Continuous magnitude score** — 0-1 score with configurable label thresholds
- [ ] **Job 2 user flow** — Existing product expansion analysis
- [ ] **Report rendering by job-to-be-done** — Job 1 filters to new-product-scale, Job 2 shows all
- [ ] **Qdrant migration** — Native Discovery API for dissimilarity search
- [ ] **Web UI / dashboard**
- [ ] **Multi-tenant SaaS, auth, billing**
