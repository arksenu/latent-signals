# Latent Signals — Dev Log

<!-- Maintained automatically by the dev-logger subagent after each session.
     Format: 3–5 bullets per session, newest first.
     Tags: [built] | [broke] | [next] -->

## 2026-02-19 · Session 12

- [broke] Root cause identified: **missing discovery layer**. Pipeline uses hardcoded source configs (wrong subreddits, wrong anchors) instead of Exa/Serper API to dynamically discover relevant forums — explains why every backtest run (sessions 2–12) surfaced r/projectmanagement PMP/MBA noise over Jira workflow gaps
- [broke] JSON serialization errors and subreddit structural bias are downstream symptoms; the fundamental architecture problem is upstream: no query→source discovery step, only hand-guessed source selection
- [built] Extensive bash analysis across runs 821b8e51 and 6ae277d5 confirmed document distribution issues; config tuning (backtest_linear.yaml, jira_2019.yaml) insufficient because root cause is architectural, not configurational
- [next] **Implement discovery layer**: user query → Exa/Serper API calls → candidate sources → domain filtering → dynamic collection; replace hardcoded source configs with data-driven source selection; re-test Linear backtest

## 2026-02-19 · Session 11

- [broke] Linear backtest still fails post-Session 10: pipeline surfaces r/projectmanagement noise (PMP/MBA at ranks 1–5) instead of Jira workflow gaps — subreddit structural bias overwhelms config fixes; syntax errors in gap report JSON/markdown indicate serialization issue downstream of scoring
- [built] Further tuned `backtest_linear.yaml` and `jira_2019.yaml` with additional source filtering and competitor feature refinements; diagnosed root cause via bash analysis of doc distribution (r/projectmanagement 91% career content, unfixable by config alone)
- [built] Discovered superior validation methodology: reverse-engineer signals from real YC-backed companies with known traction (e.g., MochaCare) — test whether pipeline would have detected the pain signal pre-launch; provides hundreds of test cases with ground truth vs. current 4-case backtest
- [next] Implement reverse-engineer validation framework; apply to real case study; refactor gap scoring or add content-category filtering to suppress generic career/certification signals that overwhelm product-pain signal

## 2026-02-19 · Session 10

- [broke] Six-run diagnosis: every session (2–9) had at least one major config error — wrong subreddits, complaint-phrased competitor features, swapped scoring weights, HDBSCAN params that collapsed 10K docs into 2 topics. Pipeline architecture untested; only misconfigured runs analyzed.
- [built] Comprehensive bash analysis of source distribution across all runs — confirmed r/projectmanagement is ~91% career content; traced why PMP/MBA rank #1,5 instead of Jira workflow gaps
- [built] Further refined `backtest_linear.yaml` and `jira_2019.yaml` — tightened source filtering and converted complaint-phrased features to actual capability descriptions
- [next] Execute clean Linear backtest with corrected configs; verify Jira workflow frustration surfaces in top 3 gaps; if successful, run Notion, Plausible, Email control validation tests

## 2026-02-19 · Session 9

- [broke] JSON serialization persists: truncated gap_score JSON and malformed report markdown — error occurs upstream of final report output
- [broke] Root cause confirmed via document analysis: r/projectmanagement is ~91% career content (PMP/MBA ranks 1,5), overwhelming domain filtering — HDBSCAN tuning alone insufficient
- [built] Detailed bash diagnosis of document sources and clustering impact; further refined `backtest_linear.yaml` and `jira_2019.yaml` competitor features to suppress generic career signals
- [next] Fix JSON serialization in report generation; refactor gap scoring or apply explicit content category filtering to exclude career/certification topics; re-run Linear backtest and verify Jira workflow frustration surfaces in top 3

## 2026-02-19 · Session 8

- [broke] HDBSCAN clustering catastrophe: `min_cluster_size=50` produced only 2 topics (58-doc spam + 10,702-doc mega-cluster), causing 0 valid gaps in backtest runs 821b8e51 and 6ae277d5 — overcorrection from `min_cluster_size=5`
- [broke] Mega-cluster ("devops agile team development") comprises 99.5% of corpus and is too broad to pass market relevance gate, explaining why Jira workflow gap doesn't surface in top 3
- [built] Diagnosed via bash analysis of document distribution and subreddit breakdown across runs — confirmed mega-cluster phenomenon and HDBSCAN parameter impact
- [next] Tune HDBSCAN to `min_cluster_size=15, min_samples=5` (identified sweet spot); re-run Linear backtest and verify Jira workflow frustration surfaces in top 3 gaps

## 2026-02-19 · Session 7

- [built] Disabled automatic dev-logger invocation — modified agent `description` field to remove auto-trigger language; dev-logger now runs only on explicit user request
- [built] Updated `.claude/agents/dev-logger.md` protocol documentation
- [next] Continue with Linear backtest re-run and proceed to Notion, Plausible, Email control validation tests (from Session 6)

## 2026-02-18 · Session 6

- [broke] Linear backtest (821b8e51, 6ae277d5) still produces subreddit noise (PMP/MBA at ranks 1,5) despite Session 4 weight fix — root cause traced to `jira_2019.yaml`: last 4 entries were complaint-phrased ("Jira is known for being slow") instead of actual feature descriptions, inflating similarity scores
- [built] Fixed `jira_2019.yaml`: converted complaint phrases to actual Jira capabilities (workflow management, permission controls, automation, reporting)
- [built] Refined `backtest_linear.yaml`: tuned search parameters and source filtering to reduce generic career/certification signals
- [next] Re-run Linear backtest; verify Jira workflow frustration surfaces in top 3; if successful, run Notion and Plausible validation tests

## 2026-02-18 · Session 5

- [broke] Backtest failure persists: runs 821b8e51 and 6ae277d5 show top-ranked gaps are PMP/MBA career advice (ranks 1,5) despite Session 4 scoring weight fix — root cause is not data volume but content category bias
- [broke] Gap report output truncation: malformed JSON in score_breakdown and incomplete markdown in ranked opportunities table suggest serialization error downstream of scoring
- [broke] Per-subreddit capping verified in code (2,500 per sub ceiling) but insufficient — r/projectmanagement's 91% career content structurally overruns domain filtering
- [next] Refactor gap scoring to down-weight generic career/certification signals; add source-type enforcement (whitelist product-pain subreddits only); re-run Linear backtest and verify Jira workflow gap surfaces in top 3

## 2026-02-18 · Session 4

- [broke] Scoring weights bug in `backtest_linear.yaml`: frequency (0.25) and pain_intensity (0.15) are swapped vs. CLAUDE.md spec (should be frequency: 0.15, pain_intensity: 0.25)
- [broke] Competitor features misconfiguration: `jira_2019.yaml` last 4 entries are complaint-phrased ("Jira is known for being slow") instead of actual capabilities — inflates similarity scores and masks true gaps
- [built] Fixed scoring weights in `backtest_linear.yaml` config
- [next] Fix `jira_2019.yaml` competitor feature descriptions (convert complaints to capabilities); re-run Linear backtest and verify Jira workflow frustration surfaces in top 3 gaps

## 2026-02-18 · Session 3

- [broke] Linear backtest failure persists (runs 821b8e51, 6ae277d5): top-ranked gaps are r/projectmanagement noise (PMP/MBA career advice at ranks 1, 5) instead of Jira workflow gaps — root cause is subreddit content distribution (91% career content in r/projectmanagement), not query-level overfitting
- [built] Refined `backtest_linear.yaml`: removed r/projectmanagement and r/agile subreddits entirely; retained r/jira, r/devops, r/programming, r/webdev with max_items: 12000
- [built] Root cause insight documented: subreddit-level structural bias overwhelms gap scoring formula — hybrid filtering (source whitelist + query focus) needed for historical backtest accuracy
- [next] Re-run Linear backtest with pruned subreddit config; verify Jira workflow frustration surfaces in top 3 gaps; if successful, proceed to Notion, Plausible, Email control validation runs

## 2026-02-18 · Session 2

- [broke] Linear backtest runs (ff9bca61, 821b8e51) show top-ranked gaps are noisy: HN Algolia queries ("project management", etc.) match thousands of tangential discussions (Emacs org-mode, Clojure deps, Google Maps bugs) — Jira workflow frustration buried at #7–8
- [built] Disabled HN data source in `config/backtest_linear.yaml` (`hackernews.enabled: false`); trimmed to 3 focused subreddits (jira, projectmanagement, agile) with max_items: 12000
- [built] Architectural decision documented: use Reddit-only corpus for historical backtests; subreddit filtering provides cleaner signal than keyword-based HN queries
- [built] Fixed dev-logger infrastructure: corrected `dev-logger-hook.sh` parser, established global session numbering (no longer reset per date), updated protocol in `dev-logger.md` to read log first before logging
- [next] Re-run full Linear backtest with HN disabled and evaluate whether Jira workflow frustration surfaces in top 3; if successful, run Notion, Plausible, and Email control backtests to validate against success criteria (2/3 positive in top 3 + no false positives)

## 2026-02-16 · Session 1

- [built] Full 6-stage directory structure and module scaffolding created — `src/latent_signals/{stage1_collection,stage2_preprocessing,stage3_embedding,stage4_clustering,stage5_classification,stage6_scoring}`
- [built] Core infrastructure: `pyproject.toml`, `PipelineConfig` class, `run_pipeline.py` entry point, and `backtest_linear.yaml` configuration file
- [broke] Initial smoke test failed with `ModuleNotFoundError: No module named 'latent_signals.stage6_scoring.scoring'` — fixed by properly exporting `GapScorer` in `stage6_scoring/__init__.py`
- [built] Gap scoring implementation complete with 6-component formula (unaddressedness, frequency, sentiment intensity, competitor coverage, market size, trend) — `src/latent_signals/stage6_scoring/scoring.py`
- [next] Implement stage1 (data collection via Exa, Serper, Apify), stage2 (preprocessing + dedup), stage3 (embeddings), and stage4 (BERTopic clustering); then integrate end-to-end and test against backtest spec
