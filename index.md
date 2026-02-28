# Latent Signals — Project Documentation Index

> Generated: 2026-02-23 | Updated: 2026-02-27 | Scan Level: Exhaustive

## Project Overview

- **Type:** Monolith — Data Pipeline (NLP/Competitive Intelligence)
- **Primary Language:** Python 3.11+
- **Architecture:** Sequential 6-stage pipeline with CLI orchestration
- **Package Manager:** uv + hatchling
- **Status:** Engine validated, backtest gate passed (5/5 complete)

## Quick Reference

- **Tech Stack:** Python 3.11+, sentence-transformers, BERTopic, VADER, GPT-4o-mini, ChromaDB, Click
- **Entry Point:** `src/latent_signals/cli.py` → `latent-signals run --config config/default.yaml`
- **Architecture Pattern:** Hybrid NLP pipeline (traditional bulk + LLM sampled subsets)
- **Cost Ceiling:** <$50/month prototype

## Generated Documentation

- [Project Overview](./project-overview.md) — Executive summary, tech stack table, validation status, known deficiencies
- [Architecture](./architecture.md) — System design, stage details, configuration hierarchy, cross-cutting concerns
- [Source Tree Analysis](./source-tree-analysis.md) — Full annotated directory tree, entry points, data flow
- [Data Models](./data-models.md) — All Pydantic models by pipeline stage, serialization formats
- [Development Guide](./development-guide.md) — Setup, running, testing, development conventions

## Existing Project Documentation

### Strategy & Planning (latent-signals/)

- [Product Brief](./latent-signals/01_strategy/product_brief.md) — V1 scope and product positioning (PRE-VALIDATION)
- [Positioning](./latent-signals/01_strategy/positioning.md) — Market positioning
- [Competitive Landscape](./latent-signals/01_strategy/competitive_landscape.md) — Competitor analysis
- [Strategy Session Notes](./latent-signals/01_strategy/meeting_notes/2026-02-15_strategy_session.md) — Initial strategy meeting

### Requirements

- [User Flows](./latent-signals/02_requirements/user_flows.md) — User interaction flows
- [Design Constraints](./latent-signals/02_requirements/design_constraints.md) — Hard constraints
- [Scoring Function Spec](./latent-signals/02_requirements/scoring_function_spec.md) — Gap scoring formula specification

### Architecture

- [Technical Stack](./latent-signals/03_architecture/technical_stack.md) — Full technical stack research
- [Data Pipeline](./latent-signals/03_architecture/data_pipeline.md) — Pipeline architecture design
- [Infrastructure](./latent-signals/03_architecture/infrastructure.md) — Infrastructure plan

### Decisions & Validation

- [Decision Log](./latent-signals/04_decisions/decision_log.md) — **Source of truth** for all architectural decisions
- [Historical Backtest Plan](./latent-signals/05_validation/results/historical_backtest_plan.md) — Formal validation spec (5 test cases)
- [Backtest Summary](./latent-signals/05_validation/results/backtest_summary.md) — Cross-case analysis and final verdict
- [Development Log](./latent-signals/dev_log.md) — Session-by-session development activity

### Business

- [Pricing Model](./latent-signals/06_business/pricing_model.md) — Pricing strategy
- [GTM Plan](./latent-signals/06_business/gtm_plan.md) — Go-to-market plan

### Root-Level Reference

- [Building a Market Gap Finder](./Building_a_Market_Gap_Finder.md) — Full technical stack research document
- [CLAUDE.md](./CLAUDE.md) — AI assistant project instructions

## Backtest Results

| Test Case | Config | Report | Status |
|-----------|--------|--------|--------|
| Linear (PM/Jira) | [backtest_linear.yaml](./config/backtest_linear.yaml) | [gap_report.md](./data/reports/7c16def9/gap_report.md) | **PASS** — Rank 2, score 0.723 |
| Notion (Evernote) | [backtest_notion.yaml](./config/backtest_notion.yaml) | [gap_report.md](./data/reports/b4612a0d/gap_report.md) | **PASS** — Rank 3, score 0.657 |
| Plausible (GA) | [backtest_plausible.yaml](./config/backtest_plausible.yaml) | [gap_report.md](./data/reports/0fb9aed4/gap_report.md) | **PASS** — Ranks 1-2, scores 0.776/0.745 |
| Email | [backtest_email_control.yaml](./config/backtest_email_control.yaml) | [gap_report.md](./data/reports/0e03b7a3/gap_report.md) | Real gaps detected (HEY, ProtonMail addressed) |
| VS Code | [backtest_vscode_control.yaml](./config/backtest_vscode_control.yaml) | [gap_report.md](./data/reports/fa17ead6/gap_report.md) | Real gaps detected (Python, C++, Java friction) |

## Getting Started

1. **Understand the project:** Read this index, then [Project Overview](./project-overview.md)
2. **Set up development:** Follow [Development Guide](./development-guide.md) for environment setup
3. **Understand architecture:** Read [Architecture](./architecture.md) for system design
4. **Review decisions:** Read [Decision Log](./latent-signals/04_decisions/decision_log.md) for what works and what doesn't
5. **Run a backtest:** `uv run latent-signals run --config config/backtest_linear.yaml`

## AI-Assisted Development

When using AI assistants (Claude Code, Cursor, etc.) with this project:

1. **Start with** `CLAUDE.md` — Contains all project instructions, constraints, and conventions
2. **Source of truth** for decisions: `latent-signals/04_decisions/decision_log.md`
3. **Custom agents** are defined in `.claude/agents/` for specialized tasks
4. **Key constraint:** Hybrid NLP only — LLMs on sampled subsets (50-100 per cluster), traditional NLP for bulk
5. **Cost ceiling:** Prototype < $50/month, production < $500/month
