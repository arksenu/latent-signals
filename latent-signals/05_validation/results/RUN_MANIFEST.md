# Run Manifest

Maps every pipeline run ID to its test case, round, date, status, and config.

**Last updated:** 2026-02-27

## Canonical Runs (Round 2, post-scoring-fixes)

These are the authoritative runs referenced in backtest_summary.md and CLAUDE.md.

| Run ID | Test Case | Market Category | Date | Config | Gaps | Notes |
|--------|-----------|-----------------|------|--------|------|-------|
| `7c16def9` | Linear | project management | 2026-02-23 | `backtest_linear.yaml` | 10 | Jira frustration at rank 2, score 0.723 |
| `b4612a0d` | Notion | note-taking and workspace | 2026-02-24 | `backtest_notion.yaml` | 10 | Evernote frustration at rank 3, score 0.657 |
| `0fb9aed4` | Plausible | web analytics | 2026-02-24 | `backtest_plausible.yaml` | 10 | GA privacy at ranks 1-2, scores 0.776/0.745 |
| `0e03b7a3` | Email (control) | email clients | 2026-02-25 | `backtest_email_control.yaml` | 10 | Real gaps surfaced (HEY, ProtonMail, Tutanota) |
| `fa17ead6` | VS Code (control) | code editors | 2026-02-25 | `backtest_vscode_control.yaml` | 10 | Real gaps surfaced (Python, C++, Java setup) |

## Superseded Runs (Round 1, pre-scoring-fixes)

Early Linear iterations from sessions 1-17. All superseded by `7c16def9`.

| Run ID | Test Case | Date | Gaps | Notes |
|--------|-----------|------|------|-------|
| `bc5693c1` | Linear | 2026-02-16 | 2 | Session 1 first attempt, minimal gaps |
| `6ae277d5` | Linear | 2026-02-16 | 10 | Session 1, PMP/MBA noise in top ranks |
| `9227eee4` | Linear | 2026-02-17 | 10 | Iteration, subreddit bias persists |
| `ff9bca61` | Linear | 2026-02-18 | 10 | Session 2, HN noise (Jira at rank 7-8) |
| `821b8e51` | Linear | 2026-02-18 | 10 | Session 2-3, config tuning iterations |
| `90d6e06b` | Linear | 2026-02-18 | 0 | HDBSCAN catastrophe (min_cluster_size=50 → 2 topics) |

## Aborted Runs (no report generated)

Incomplete pipeline runs from Linear iteration cycle. Clusters and/or embeddings exist but no final report.

| Run ID | Artifacts | Notes |
|--------|-----------|-------|
| `211b15d7` | clusters + embeddings | Linear iteration, pipeline halted before scoring |
| `6375e961` | clusters + embeddings | Linear iteration, pipeline halted before scoring |
| `de2b7b1f` | clusters + embeddings | Linear iteration, pipeline halted before scoring |
| `e3fec985` | embeddings only | Linear iteration, pipeline halted before clustering |

## Directory Summary

| Directory | Run IDs | Count |
|-----------|---------|-------|
| `data/reports/` | All canonical + all superseded | 11 |
| `data/clusters/` | All canonical + all superseded + 211b15d7, 6375e961, de2b7b1f | 14 |
| `data/embeddings/` | All canonical + all superseded + 211b15d7, 6375e961, de2b7b1f, e3fec985 | 15 |
