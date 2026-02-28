# Latent Signals — Project Overview

**Type:** Data Pipeline (NLP/Competitive Intelligence)
**Language:** Python 3.11+
**Architecture:** Sequential 6-stage pipeline with CLI orchestration
**Package Manager:** uv + hatchling
**Repository Type:** Monolith

## Purpose

Latent Signals is a B2B competitive intelligence tool that detects underserved market opportunities by:
1. Collecting community sentiment from forums and review sites (Reddit, Hacker News)
2. Mapping signals against competitor feature coverage via vector similarity
3. Scoring gaps using a 6-component composite metric
4. Producing ranked, evidence-backed gap reports

**Target users:** Startups in fast-moving markets where historical data is scarce.

## Executive Summary

The pipeline processes 5,000-30,000 community posts through six sequential stages: data collection (Exa, Serper, Apify, Arctic Shift, HN Algolia), preprocessing (HTML cleanup, language detection, MinHash dedup), embedding (sentence-transformers), topic clustering (BERTopic + UMAP + HDBSCAN), classification (VADER sentiment + zero-shot + GPT-4o-mini extraction), and gap scoring (ChromaDB vector similarity + composite formula).

**Current status (2026-02-27):** Engine validated, backtest gate passed. All 5 backtest cases complete (3 positive + 2 controls). Pipeline reliably detects genuine market gaps. Known limitation: scoring formula treats all frustration equally regardless of opportunity magnitude (deferred to v2 Opportunity Scale Classifier).

## Technology Stack

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| Language | Python | 3.11+ | Core language |
| Package Mgmt | uv + hatchling | latest | Dependency management, build system |
| Data Collection | exa-py | >=1.0 | Semantic search API |
| Data Collection | httpx | >=0.27 | HTTP client (Serper, Arctic Shift, HN) |
| Data Collection | apify-client | >=1.0 | Bulk Reddit scraping |
| Preprocessing | BeautifulSoup4 | >=4.12 | HTML cleanup |
| Preprocessing | langdetect | >=1.0 | Language detection |
| Preprocessing | datasketch | >=1.6 | MinHash deduplication |
| Embeddings | sentence-transformers | >=3.0 | all-MiniLM-L6-v2 (384d) |
| Embeddings | torch | >=2.2,<2.3 | PyTorch backend |
| Clustering | BERTopic | >=0.16 | Topic modeling |
| Clustering | umap-learn | >=0.5 | Dimensionality reduction |
| Clustering | hdbscan | >=0.8 | Density-based clustering |
| Sentiment | vaderSentiment | >=3.3 | Rule-based sentiment analysis |
| Classification | transformers | >=4.40 | facebook/bart-large-mnli zero-shot |
| LLM Extraction | openai | >=1.30 | GPT-4o-mini Batch API |
| LLM Framework | dspy | >=2.4 | Typed LLM signatures |
| NER/Keyphrases | keybert, keyphrase-vectorizers | >=0.8 | POS-pattern keyphrase extraction |
| NER | spacy | >=3.7 | Product name extraction |
| Vector Store | chromadb | >=0.5 | Embedded vector DB (cosine similarity) |
| Data Models | pydantic | >=2.5 | Typed schemas with validation |
| Config | pyyaml, python-dotenv | >=6.0 | YAML config, environment variables |
| CLI | click | >=8.1 | Command-line interface |
| Logging | structlog | >=24.0 | Structured logging (ISO timestamps) |
| Reporting | jinja2 | >=3.1 | Markdown report generation |
| Testing | pytest, pytest-cov | >=8.0 | Unit testing |

## Architecture Pattern

**Sequential data pipeline** — Each stage reads from disk, processes data, and writes results to disk. No orchestration framework (Prefect deferred to post-V1). Stages can be run independently for debugging via CLI flags.

**Hybrid NLP** — Traditional NLP handles bulk processing (VADER at ~100k texts/sec, MinHash dedup, zero-shot classification). LLMs (GPT-4o-mini Batch API) operate only on sampled subsets (50-100 posts per cluster) for nuanced extraction.

**Data separation** — User complaint vectors and competitor feature vectors are stored in separate ChromaDB collections. Never collapsed.

## Cost Model

- **Prototype target:** <$50/month
- **Per-run costs:** ~$0.50 LLM extraction per 10,000 posts + API costs for collection
- **Free sources:** Arctic Shift (historical Reddit), HN Algolia
- **Paid sources:** Exa (~$5/1k searches), Serper (~$1/1k queries), Apify (~$2/1k results)

## Validation Status

| Test Case | Target Gap | Status | Result |
|-----------|-----------|--------|--------|
| Linear (Sept 2018 - Aug 2019) | Jira workflow frustration | **PASS** | Rank 2, score 0.723 |
| Notion (Mar 2017 - Feb 2018) | Evernote frustration | **PASS** | Rank 3, score 0.657 |
| Plausible (Jan 2018 - Dec 2018) | GA privacy gap | **PASS** | Ranks 1-2, scores 0.776/0.745 |
| Email (Jan 2018 - Dec 2019) | Real gaps detected | Complete | HEY, ProtonMail, Tutanota later addressed these |
| VS Code (Jan 2019 - Dec 2019) | Real gaps detected | Complete | Python setup, C++ toolchain, Java support friction |

**Success criteria:** 2/3 positive cases detected in top 3. Achieved: 3/3. Control cases surfaced genuine gaps (negative control concept abandoned).

## Known Deficiencies

1. **Opportunity magnitude classification:** Scoring formula treats all frustration equally regardless of opportunity magnitude. "Jira's workflow is fundamentally broken" (spawned Linear) scores similarly to "VS Code Python setup is painful" (fixed by a better extension). LLM-based Opportunity Scale Classifier deferred to v2.
2. **Source concentration bias:** Single-community sources produce different clustering behavior than multi-community.
3. **Discovery layer dependency:** Pipeline requires Exa discovery probe before execution to derive quality source inputs.
4. **Noisy representative quotes:** Some evidence quotes are tangential or low-signal (cosmetic, deferred).
5. **Split clusters:** Related pain points sometimes fragment across multiple clusters (cosmetic, deferred).

## Links to Detailed Documentation

- [Source Tree Analysis](./source-tree-analysis.md)
- [Architecture](./architecture.md)
- [Data Models](./data-models.md)
- [Development Guide](./development-guide.md)
- [Decision Log](./latent-signals/04_decisions/decision_log.md)
- [Backtest Plan](./latent-signals/05_validation/results/historical_backtest_plan.md)
- [Backtest Summary](./latent-signals/05_validation/results/backtest_summary.md)
