# Source Tree Analysis

## Directory Structure

```
gapfinder/                              # Project root
├── .env                                # API keys (EXA, SERPER, APIFY, OPENAI)
├── .env.example                        # Environment template
├── .gitignore                          # Ignores data/, .env, .venv, __pycache__
├── pyproject.toml                      # Project config (hatchling build, dependencies)
├── uv.lock                             # Locked dependencies (uv package manager)
├── CLAUDE.md                           # AI assistant project instructions
│
├── config/                             # Pipeline configuration
│   ├── default.yaml                    # Default pipeline config (production template)
│   ├── backtest_linear.yaml            # Linear backtest (Sept 2018 - Aug 2019)
│   ├── backtest_notion.yaml            # Notion backtest (Mar 2017 - Feb 2018)
│   ├── backtest_plausible.yaml         # Plausible backtest (Jan 2018 - Dec 2018)
│   ├── backtest_email_control.yaml     # Email control (Jan 2018 - Dec 2019)
│   ├── backtest_email.yaml            # Email backtest (alternate config)
│   ├── backtest_vscode_control.yaml   # VS Code control (Jan 2019 - Dec 2019)
│   └── competitor_features/            # Curated competitor capability sets
│       ├── jira_2019.yaml              # Jira features (10 capabilities)
│       ├── evernote_2017.yaml          # Evernote features (8 capabilities)
│       ├── google_analytics_2018.yaml  # GA features (8 capabilities)
│       ├── gmail_2018.yaml             # Gmail features (8 capabilities)
│       └── vscode_2019.yaml            # VS Code features
│
├── src/                                # Source code root
│   └── latent_signals/                 # Main Python package
│       ├── __init__.py                 # Package init (version 0.1.0)
│       ├── cli.py                      # ** ENTRY POINT ** Click CLI
│       ├── run_pipeline.py             # Pipeline orchestrator (stages 1-6)
│       ├── config.py                   # Pydantic config loading (YAML + env)
│       ├── models.py                   # Shared data models (RawDocument → GapOpportunity)
│       │
│       ├── stage1_collection/          # Stage 1: Data Collection
│       │   ├── __init__.py             # Orchestrator — runs all collectors, merges, deduplicates
│       │   ├── base.py                 # Abstract Collector base class
│       │   ├── exa_collector.py        # Exa semantic search (paid, ~$5/1k)
│       │   ├── serper_collector.py     # Serper.dev keyword search (paid, ~$1/1k)
│       │   ├── apify_collector.py      # Apify bulk Reddit scraping (paid, ~$2/1k)
│       │   ├── arctic_shift.py         # Arctic Shift historical Reddit (free)
│       │   └── hackernews.py           # HN Algolia API (free)
│       │
│       ├── stage2_preprocessing/       # Stage 2: Preprocessing
│       │   ├── __init__.py             # Orchestrator — clean, filter, deduplicate
│       │   ├── html_cleanup.py         # HTML/markdown stripping, whitespace normalization
│       │   ├── language_filter.py      # Language detection (langdetect)
│       │   ├── deduplication.py        # MinHash LSH near-duplicate detection
│       │   ├── length_filter.py        # Character length bounds (50-10,000)
│       │   └── noise_filter.py         # Bot detection, gratitude removal
│       │
│       ├── stage3_embedding/           # Stage 3: Embedding
│       │   ├── __init__.py             # Orchestrator — embed corpus, save .npy
│       │   └── embedder.py             # SentenceTransformer wrapper (MiniLM-L6-v2)
│       │
│       ├── stage4_clustering/          # Stage 4: Topic Clustering
│       │   ├── __init__.py             # Orchestrator — fit BERTopic, extract topics
│       │   ├── topic_model.py          # BERTopic + UMAP + HDBSCAN construction
│       │   └── representation.py       # Topic label/keyword extraction
│       │
│       ├── stage5_classification/      # Stage 5: Classification & Extraction
│       │   ├── __init__.py             # Orchestrator — VADER + zero-shot + LLM
│       │   ├── sentiment.py            # VADER sentiment (intensity preservation)
│       │   ├── zero_shot.py            # facebook/bart-large-mnli classifier
│       │   ├── sampling.py             # Representative post sampling per cluster
│       │   ├── schemas.py              # Pydantic schema for OpenAI Structured Outputs
│       │   └── llm_extraction.py       # GPT-4o-mini Batch API extraction
│       │
│       ├── stage6_scoring/             # Stage 6: Gap Detection & Scoring
│       │   ├── __init__.py             # Orchestrator — score gaps, generate report
│       │   ├── vector_store.py         # ChromaDB wrapper (separate collections)
│       │   ├── competitor_features.py  # Load/embed competitor feature YAML
│       │   ├── gap_detection.py        # Cosine similarity, cluster centroids
│       │   ├── normalization.py        # Score component normalization [0,1]
│       │   ├── scoring.py              # 6-component composite gap scoring
│       │   └── report_generator.py     # Markdown report generation
│       │
│       └── utils/                      # Shared utilities
│           ├── __init__.py
│           ├── io.py                   # JSONL/JSON/numpy I/O helpers
│           ├── cost_tracker.py         # Per-service API cost tracking
│           └── logging.py             # structlog setup (ISO timestamps)
│
├── scripts/                            # Standalone discovery scripts
│   ├── exa_discovery_probe.py          # PM market discovery (original)
│   ├── exa_discovery_probe_reddit.py   # Reddit/HN-focused PM discovery
│   ├── exa_discovery_notion.py         # Notion backtest discovery probe
│   ├── exa_discovery_plausible.py      # Plausible backtest discovery probe
│   ├── exa_discovery_email.py         # Email backtest discovery probe
│   ├── exa_discovery_vscode.py        # VS Code backtest discovery probe
│   ├── arctic_shift_volume_check.py    # Validate subreddit data volumes
│   └── arctic_shift_volume_check_vscode.py  # VS Code subreddit volume check
│
├── data/                               # Pipeline outputs (gitignored)
│   ├── raw/{run_id}/                   # Stage 1 output: documents.jsonl
│   ├── preprocessed/{run_id}/          # Stage 2 output: corpus.jsonl
│   ├── embeddings/{run_id}/            # Stage 3 output: embeddings.npy, doc_ids.json
│   ├── clusters/{run_id}/              # Stage 4 output: topic_assignments.jsonl, topic_info.json
│   ├── classified/{run_id}/            # Stage 5 output: classified.jsonl
│   ├── reports/{run_id}/               # Stage 6 output: gap_report.md, gap_scores.json
│   ├── discovery_probe_results.json    # PM discovery probe results
│   ├── discovery_probe_reddit_hn.json  # Reddit/HN discovery results
│   ├── discovery_probe_notion.json     # Notion discovery results
│   ├── discovery_probe_plausible.json  # Plausible discovery results
│   ├── discovery_probe_email.json     # Email discovery results
│   └── discovery_probe_vscode.json    # VS Code discovery results
│
├── tests/                              # Test directory (empty — tests not yet written)
│
├── latent-signals/                     # Planning & strategy documentation
│   ├── 01_strategy/                    # Product brief, positioning, competitive landscape
│   ├── 02_requirements/                # User flows, design constraints, scoring spec
│   ├── 03_architecture/                # Technical stack, data pipeline, infrastructure
│   ├── 04_decisions/                   # Decision log (source of truth)
│   ├── 05_validation/                  # Backtest plan and results
│   ├── 06_business/                    # Pricing model, GTM plan
│   └── dev_log.md                      # Development session log
│
└── .claude/                            # Claude Code configuration
    └── agents/                         # Custom subagent definitions
```

## Critical Directories

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| `src/latent_signals/` | Core pipeline package | `cli.py` (entry), `run_pipeline.py` (orchestrator), `models.py` (schemas), `config.py` (YAML loading) |
| `config/` | Pipeline and backtest configurations | `default.yaml`, `backtest_*.yaml`, `competitor_features/*.yaml` |
| `data/` | All pipeline intermediate and final outputs | `{stage}/{run_id}/` subdirectories |
| `scripts/` | One-time discovery probes | `exa_discovery_*.py`, `arctic_shift_volume_check.py` |
| `latent-signals/` | Strategy and planning documentation | `04_decisions/decision_log.md` (source of truth) |

## Entry Points

- **CLI:** `latent-signals run --config config/default.yaml` (via `latent_signals.cli:main`)
- **Direct:** `python -m latent_signals.run_pipeline` (with config loading)
- **Per-stage:** `latent-signals run --config config/backtest_linear.yaml --stages 1,2,3`

## Data Flow

```
Config YAML → Stage 1 (Collection) → data/raw/{run_id}/documents.jsonl
                                    ↓
                     Stage 2 (Preprocessing) → data/preprocessed/{run_id}/corpus.jsonl
                                    ↓
                     Stage 3 (Embedding) → data/embeddings/{run_id}/embeddings.npy
                                    ↓
                     Stage 4 (Clustering) → data/clusters/{run_id}/topic_assignments.jsonl
                                    ↓
                     Stage 5 (Classification) → data/classified/{run_id}/classified.jsonl
                                    ↓
                     Stage 6 (Scoring) → data/reports/{run_id}/gap_report.md
```
