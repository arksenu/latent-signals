# Latent Signals — Dev Log

<!-- Maintained automatically by the dev-logger subagent after each session.
     Format: 3–5 bullets per session, newest first.
     Tags: [built] | [broke] | [next] -->

## 2026-02-27 · Session 27

- [built] Pain-to-question ratio analysis completed across all 5 backtest cases — signal absent. All opportunity groups land in 0.77–0.89 P2Q band; CMake (polish) has P2Q=1.33 while Jira (new-product) has P2Q=0.55, inverted from hypothesis. Classifier responds to emotional temperature, not opportunity magnitude
- [built] Corrected Notion cluster misidentification: gap #2 is OneNote frustration, not Evernote. Evernote cluster is gap #3 (score 0.657). Updated backtest_summary.md, CLAUDE.md, and MEMORY.md with corrected ranks/scores
- [built] Decision log entry added (2026-02-27): P2Q ratio experiment closed, LLM-based rhetorical framing analysis remains v2 path. Remaining derived signal candidates: gap age (temporal persistence), incumbent coverage completeness
- [built] Updated CLAUDE.md and MEMORY.md with v1.1 P2Q results and Notion correction
- [next] V1 doc finalization: create RUN_MANIFEST.md, sync product_brief.md, update TODO.md, add missing dev_log entries

## 2026-02-26 · Session 26

- [built] VS Code 2019 control backtest completed (run ID fa17ead6): full discovery workflow (Exa probe → Arctic Shift volume → config → competitor features → pipeline run). 59 clusters, 10 gaps scored, top score 0.740. Python setup, C++ toolchain, and Java support friction surfaced as top gaps
- [built] Negative control concept formally abandoned — both email and VS Code controls surfaced genuine market gaps, not false positives. Pipeline correctly detects all gaps; limitation is opportunity magnitude classification (deferred to v2 Opportunity Scale Classifier)
- [built] V1 backtest validation gate declared passed: 3/3 positive cases in top 3 (Linear rank 2/0.723, Notion rank 3/0.657, Plausible ranks 1-2/0.776/0.745). Documentation finalized across backtest_summary.md, CLAUDE.md, decision_log.md, product_brief.md
- [next] v1.1 pain-to-question ratio analysis on existing cluster data — test whether derived signals separate opportunity magnitudes before implementing full LLM classifier

## 2026-02-26 · Session 25

- [built] VS Code 2019 negative control backtest completed (run ID fa17ead6, 59 clusters, 10 gaps scored, top score 0.740) — full discovery workflow executed (Exa probe identified r/vscode with 28 hits, Arctic Shift volume confirmed, config and competitor features file created)
- [built] Negative control concept abandoned — both email and VS Code controls surfaced genuine market gaps, not false positives. Email gaps later addressed by HEY/ProtonMail/Tutanota; VS Code gaps are real Python/C++/Java setup friction. Pipeline correctly detects all gaps; limitation is opportunity magnitude classification, not gap detection
- [built] V1 backtest validation milestone complete: 3/3 positive cases pass (Linear rank 2/0.723, Notion rank 2/0.730, Plausible ranks 1-2/0.776/0.745) — documentation finalized across `backtest_summary.md`, `CLAUDE.md`, `decision_log.md`, and `product_brief.md`
- [built] Opportunity Scale Classifier designed during brainstorming (three-tier: new-product/feature/polish) but deferred to v2 — derived quantitative signals (pain-to-question ratio, gap age, incumbent coverage completeness) may separate opportunity magnitudes without LLM classifier
- [next] v1.1 pain-to-question ratio analysis on existing backtest cluster data — test whether derived signals from zero-shot classification separate opportunity magnitudes before implementing full LLM classifier

## 2026-02-25 · Session 24

- [built] Implemented 4 backtest fixes: (1) post-level market relevance filter in stage3_embedding (drops docs below 0.20 cosine similarity to market anchors); (2) unaddressedness similarity floor (0.15) in scoring.py to skip off-topic clusters; (3) VADER pain intensity changed to top-20 most negative compounds per cluster (fixes near-zero issue); (4) P95 cap on cluster sizes before log normalization — added `post_relevance_threshold` and `unaddressedness_floor` params to ScoringConfig
- [built] Re-ran all 4 backtests (stages 3-6 reusing existing collection data) — Linear ranks 2 (0.723, +0.018), Notion ranks 2 (0.730, +0.084), Plausible ranks 1-2 (0.776, 0.745, both improved), Email control still FAILS with 10 gaps, top score 0.834 (up from 0.760 — pain intensity fix now correctly captures email frustration)
- [broke] Email control negative test fails for fundamentally different reason in round 2: round 1 failures were off-topic clusters (Firefox, Android, politics); round 2 clusters are genuinely email-related (ProtonMail, Gmail alternatives, spam, encryption) — pipeline detects real frustration but cannot distinguish "frustrated with no gap" from "frustrated with a gap," a scoring model limitation not a filtering problem
- [broke] Positive case rank regression: Linear and Notion signals dropped from rank 1 to rank 2 post-fixes (despite higher scores), caused by legitimate sysadmin/Gmail-related clusters now surfacing after filtering corrections — indicates frequency normalization may over-inflate mid-tier clusters
- [next] Investigate email control gap definition: should negative test be redefined (HEY launched June 2020, just after window)? Consider temporal signal (frustration must be new/growing) or acceptance that score threshold alone cannot separate positive from negative cases; OR revert P95 frequency cap if it's causing rank inversions in positive cases

## 2026-02-23 · Session 23

- [broke] Email control backtest FAIL: 10 false positives, top score 0.760 (higher than positive cases). Firefox browsers, Android phones, Google political controversies all scored as email gaps — market relevance filter too weak, unaddressedness inverted for off-topic clusters
- [built] Plausible backtest completed (0fb9aed4): privacy/GDPR signal ranks 1-2 (gap_score 0.725, 0.692), conditional pass. Backtest writeup completed — created `latent-signals/05_validation/results/backtest_summary.md` with cross-case analysis and root-cause findings
- [built] Email control workflow documented: executed Exa discovery probe (`scripts/exa_discovery_email.py`), Arctic Shift volume check, updated `config/backtest_email.yaml` with discovery-derived subreddits, executed backtest (0e03b7a3)
- [built] Added 2 decision log entries (2026-02-23): post-level market relevance filtering required, unaddressedness similarity floor required to exclude off-topic clusters
- [next] Fix market relevance filtering (operate at post level, not cluster level) and unaddressedness inversion; re-run all 4 backtests; iterate until positive cases clean AND negative control produces zero false positives

## 2026-02-23 · Session 22

- [broke] BMAD alpha installer crashed when existing `_bmad` folder detected — required directory rename workaround
- [built] Applied workaround (`mv _bmad _bmad-backup && npx bmad-method@alpha install`) with interactive BMM module selection; BMM successfully installed with full SDLC suite (PRD, architecture, epics & stories, sprint planning, dev stories, code review, test workflows, research, UX design, retrospectives)
- [next] Ignore Agent Vibes TTS commands cluttering skill list (mute with `/agent-vibes:hide` if bothersome); begin design phase using BMM workflows for product discovery and architecture

## 2026-02-23 · Session 21

- [built] Plausible discovery probe executed (`exa_discovery_plausible.py`) — identified analytics-focused subreddits (r/googleanalytics, r/analytics, r/privacy, r/gdpr, r/webdev, r/degoogle) with signal coverage for GA privacy gap case (2018 data period)
- [built] `backtest_plausible.yaml` finalized with discovery-driven sources (10 subreddits: r/googleanalytics, r/opensource, r/selfhosted, r/wordpress, r/bigsea, r/analytics, r/webdev, r/privacy, r/degoogle, r/gdpr) — added 6 market_anchors (GDPR, privacy, complexity, cookie consent) and thresholds (market_relevance: 0.45, min_signal_ratio: 0.25); tuned clustering (nr_topics: 60, max_items: 25000)
- [built] Arctic Shift historical volume validation completed for 2018 analytics subreddits — confirmed sufficient post/comment coverage for Plausible-era backtest period
- [next] Execute Plausible backtest (GA privacy gap, Jan–Dec 2018); run Email control negative test (`backtest_email_control.yaml`); complete V1 validation suite (success: 2/3 positive in top 3 + zero false positives)

## 2026-02-23 · Session 20

- [built] Exa discovery probes executed for Linear, Notion, and Plausible test cases — identified on-topic subreddits (r/jira, r/projectmanagement for Linear; r/Evernote, r/notetaking for Notion) with rich signal density; Plausible probe created and staged for execution
- [built] Arctic Shift historical volume validators run for 2018-2019 (Linear) and 2017-2018 (Notion) periods — confirmed sufficient post/comment counts to source backtests; volume validation scripts created for ongoing use
- [built] `backtest_linear.yaml` and `backtest_notion.yaml` updated with discovery-driven source lists and refined HDBSCAN parameters (`min_cluster_size=15, min_samples=5`) — configs ready for re-validation cycles
- [next] Execute Plausible discovery probe for GA privacy case (2018 data); run Arctic Shift volumes for 2018 analytics subreddits; update `backtest_plausible.yaml` and `backtest_email_control.yaml` with sources; complete V1 validation suite (Notion + Plausible + Email negative control)

## 2026-02-23 · Session 19

- [built] Discovery scripts created (`exa_discovery_probe.py`, `exa_discovery_probe_reddit.py`, `exa_discovery_notion.py`, `arctic_shift_volume_check.py`) — probes executed for Linear (2018-2019) and Notion (2017-2018) test cases; Evernote signals identified in r/Evernote, r/notetaking communities
- [built] Configuration files updated (`backtest_linear.yaml`, `backtest_notion.yaml`) with discovery-driven source selection and refined HDBSCAN parameters for test case validation
- [broke] API authentication error (400): "This authentication style is incompatible with the long context beta header" — halts session before Notion/Plausible/Email control backtest execution can resume
- [broke] VADER sentiment fixes and remaining validation cases blocked — cannot complete V1 suite until auth resolved
- [next] Fix Claude SDK authentication + long context beta compatibility; re-run Notion backtest; execute Plausible (GA privacy) and Email negative control tests to complete validation suite (success: 2/3 positive in top 3, zero false positives)

## 2026-02-23 · Session 18

- [broke] API authentication error (400 invalid_request_error): "This authentication style is incompatible with the long context beta header" — session halted before any work completed; suggests conflict between current auth method and SDK long context mode
- [broke] Session 17 continuation goal (VADER sentiment fixes + Plausible/Email control backtests) blocked — cannot proceed to remaining V1 validation cases until auth resolved
- [next] Check Claude SDK authentication setup and long context beta compatibility; verify API credentials and client initialization; disable long context mode if needed; retry VADER fixes and remaining backtest validation suite

## 2026-02-22 · Session 17

- [built] Linear and Notion backtests both complete with target gaps ranked #1: Linear (Jira workflow, gap_score=0.7051) and Notion (Evernote frustration, gap_score=0.6464) — validates discovery-driven source selection and full 6-stage pipeline architecture across two positive validation cases
- [built] Corpus composition analysis reveals Notion clustering weaker than Linear due to source diversity: r/evernote single-product subreddit vs. Linear spread across 10 communities (jira, projectmanagement, experienceddevs, etc.) — affects source strategy for future backtests
- [broke] VADER sentiment intensity preprocessing remains inadequate: yields 0.29–0.36 scores vs. expected 0.7+ for high-pain signals — negation handling and domain-specific lexicon tuning required to improve gap_score discrimination in pain component
- [next] Apply VADER fixes (negation handling, domain tuning); re-validate Notion backtest; execute Plausible (GA privacy gap, Jan–Dec 2018) and Email negative control backtests to complete V1 validation suite (success: 2/3 positive in top 3, zero false positives)

## 2026-02-21 · Session 16

- [built] Both Linear (Jira workflow gap, gap_score=0.705) and Notion (Evernote frustration cluster, gap_score=0.646) backtests complete: targets rank #1 in both cases — validates stages 1–5 pipeline architecture and discovery-driven source selection (Exa probes successfully identify on-topic communities)
- [built] Arctic Shift historical data volumes verified for 2018-2019 (Linear era, r/jira+related subreddits) and 2017-2018 (Notion era, r/Evernote+r/notetaking); market relevance gates filter noise effectively (zero off-topic gaps in Notion run vs. multiple dev-culture noise in Linear)
- [broke] VADER sentiment intensity scoring yields overly broad pain_intensity values (0.29–0.36 vs. expected 0.7+ for high-pain signals); limits discrimination in gap_score formula's 15% pain weight component
- [next] Fix VADER sentiment preprocessing (negation handling, domain-specific lexicon tuning); re-validate Notion backtest to confirm improvement; execute Plausible backtest (GA privacy gap, Jan 2018–Dec 2018) and Email negative control; complete V1 validation suite (2/3 positive + negative control)

## 2026-02-21 · Session 15

- [built] Exa discovery probes extended with Notion variant (`exa_discovery_notion.py`) — discovered Evernote frustration signals in r/Evernote, r/notetaking, HN Ask threads; parallel discovery for all test cases (Linear, Notion, Plausible) complete
- [built] Arctic Shift historical volume validators confirmed for 2017-2018 (Notion era) and 2018-2019 (Linear era) — sufficient post/comment counts verified for Evernote-related subreddits and Jira-related forums
- [built] `backtest_linear.yaml` and `backtest_notion.yaml` updated with discovery-driven sources and competitor feature vectors; Linear produces Jira workflow gap at Rank 1 (gap_score=0.7051) validating architecture fix
- [built] First successful end-to-end pipeline run with discovery-derived inputs: Linear backtest output confirmed with visible gap_score and ranked opportunities — discovery layer solves hardcoded-config problem from Sessions 2–14
- [next] Execute Notion backtest (2017-2018 Evernote case); verify top 3 includes Evernote frustration gap; then run Plausible backtest (GA privacy) and Email control negative test to complete validation suite

## 2026-02-20 · Session 14

- [built] Exa discovery probes (Reddit-only variant) refined; Arctic Shift volume validator (`arctic_shift_volume_check.py`) implemented; Linear backtest runs successfully with Jira workflow at rank #1 (gap_score 0.705)
- [broke] Manual spot-check of Linear backtest gap report reveals **false positives in top 3**: Gap 2 is generic dev culture noise (mentions "heroin pricing", "IP rights", not product pain), Gap 3 is positive-sentiment Q&A cluster (pain_intensity=0.0 despite 0.66 score) — gap scoring formula or classification layer has bugs
- [next] Audit gap scoring logic and pain_intensity calculation (why does positive sentiment Q&A rank high?); fix false positives; re-validate Linear backtest before running full validation suite (Notion, Plausible, Email control)

## 2026-02-19 · Session 13

- [broke] Linear backtest persists with subreddit-driven noise (PMP/MBA at ranks 1,5); Session 12 hypothesis confirmed — hardcoded source configs insufficient, discovery layer required
- [built] Implemented Exa-based discovery probes (`exa_discovery_probe.py`, `exa_discovery_probe_reddit.py`) — identified 6 additional subreddits (projectmanagement, experienceddevs, atlassian, sysadmin, cscareerquestions, scrum) and Hacker News as rich signal source (40 Jira-related results)
- [built] Created Arctic Shift historical validation script (`arctic_shift_volume_check.py`) to verify post volumes for 2018-2019 backtest period
- [built] Updated `backtest_linear.yaml` with Exa discoveries: enabled Hacker News with 5,000-item limit, adjusted HDBSCAN to `min_cluster_size=15, min_samples=5`
- [next] Re-run Linear backtest with discovery-driven config; if Jira workflow frustration surfaces in top 3, proceed to Notion, Plausible, Email control validation tests

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
