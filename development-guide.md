# Latent Signals — Development Guide

## Prerequisites

- **Python 3.11+** (3.12 recommended)
- **uv** — Python package manager ([docs](https://docs.astral.sh/uv/))
- **API Keys** — Required for data collection:
  - `EXA_API_KEY` — Exa semantic search
  - `SERPER_API_KEY` — Serper.dev keyword search
  - `APIFY_API_TOKEN` — Apify Reddit scraping
  - `OPENAI_API_KEY` — GPT-4o-mini extraction

## Environment Setup

### 1. Clone and install

```bash
git clone <repository-url>
cd gapfinder
uv sync
```

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env and add your API keys:
# EXA_API_KEY=...
# SERPER_API_KEY=...
# APIFY_API_TOKEN=...
# OPENAI_API_KEY=...
```

### 3. Verify installation

```bash
uv run latent-signals --help
```

## Running the Pipeline

### Full pipeline run

```bash
uv run latent-signals run --config config/default.yaml
```

### Run specific stages

```bash
# Run only stages 1-3 (collection, preprocessing, embedding)
uv run latent-signals run --config config/default.yaml --stages 1,2,3

# Run only scoring (stage 6) — requires prior stages to have completed
uv run latent-signals run --config config/default.yaml --stages 6
```

### Override run ID

```bash
uv run latent-signals run --config config/default.yaml --run-id my-test-run
```

### Run backtests

```bash
# Linear backtest (Sept 2018 - Aug 2019)
uv run latent-signals run --config config/backtest_linear.yaml

# Notion backtest (Mar 2017 - Feb 2018)
uv run latent-signals run --config config/backtest_notion.yaml

# Plausible backtest (Jan 2018 - Dec 2018)
uv run latent-signals run --config config/backtest_plausible.yaml
```

### Discovery probes (pre-pipeline)

Before running a new market category, execute an Exa discovery probe to identify quality data sources:

```bash
# Edit the script with your target market queries, then:
uv run python scripts/exa_discovery_probe.py

# Validate subreddit volumes in Arctic Shift:
uv run python scripts/arctic_shift_volume_check.py
```

## Pipeline Output Structure

After a full run, outputs are organized by stage and run ID:

```
data/
├── raw/{run_id}/
│   ├── documents.jsonl          # Raw collected documents
│   └── collection_stats.json    # Per-source collection stats
├── preprocessed/{run_id}/
│   ├── corpus.jsonl             # Cleaned, filtered documents
│   └── preprocessing_stats.json # Filtering statistics
├── embeddings/{run_id}/
│   ├── embeddings.npy           # Dense vector embeddings (N x 384)
│   └── doc_ids.json             # Embedding metadata
├── clusters/{run_id}/
│   ├── topic_assignments.jsonl  # Per-document topic assignments
│   ├── topic_info.json          # Topic cluster summaries
│   └── bertopic_model/          # Saved BERTopic model
├── classified/{run_id}/
│   ├── classified.jsonl         # Classified documents
│   └── classification_stats.json
└── reports/{run_id}/
    ├── gap_report.md            # Human-readable gap report
    └── gap_scores.json          # Structured gap scores
```

## Configuration

Pipeline behavior is controlled entirely through YAML config files. See `config/default.yaml` for the full template.

**Key configuration areas:**

| Section | Key Settings |
|---------|-------------|
| `pipeline` | market_category, output_dir, random_seed |
| `collection` | date_range, per-source enable/disable, subreddit lists |
| `preprocessing` | min/max_length, language, minhash_threshold |
| `embedding` | model_name, batch_size, device |
| `clustering` | UMAP params, HDBSCAN params, nr_topics |
| `classification` | zero_shot model, LLM model, samples_per_cluster |
| `scoring` | 6 component weights, similarity_threshold, market_anchors |
| `report` | format, max_quotes_per_gap |

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=latent_signals

# Run specific test file
uv run pytest tests/test_models.py
```

**Note:** Tests are currently minimal. The project relies on backtest validation for correctness verification. See `latent-signals/05_validation/results/historical_backtest_plan.md` for the formal validation framework.

## Development Conventions

- **Package manager:** Always use `uv` (not pip)
- **Config:** All pipeline parameters in YAML — no hardcoded values
- **Models:** Use Pydantic v2 BaseModel for all data contracts
- **Logging:** Use `structlog` via `get_logger(name)` — never `print()`
- **I/O:** Use `utils/io.py` helpers (write_jsonl, read_jsonl, etc.)
- **Cost tracking:** Register API costs via `CostTracker.add(service, amount)`
- **Intermediate outputs:** Every stage writes to disk for inspection and debugging
- **Stage independence:** Each stage should be independently runnable
- **Data separation:** Never collapse user complaint vectors with competitor feature vectors

## Common Development Tasks

### Add a new data collector

1. Create `src/latent_signals/stage1_collection/my_collector.py`
2. Extend `Collector` base class, implement `collect()`, `estimate_cost()`, `source_name`
3. Add collector config model to `config.py`
4. Register in `stage1_collection/__init__.py`

### Modify the scoring formula

1. Edit weights in `config.py` → `ScoringWeights`
2. Edit normalization in `stage6_scoring/normalization.py`
3. Edit scoring logic in `stage6_scoring/scoring.py`
4. Update `CLAUDE.md` if the formula changes

### Add a new backtest case

**MUST follow this order — do NOT skip steps.**

1. **Exa discovery probe** — Create `scripts/exa_discovery_<case>.py` modeled on existing probes (see `scripts/exa_discovery_plausible.py`). Run it. This determines which subreddits actually contain signal. Output goes to `data/discovery_probe_<case>.json`.
2. **Arctic Shift volume check** — Run `scripts/arctic_shift_volume_check.py` against the candidate subreddits from step 1 to verify they have enough posts in the date range. Drop any subreddit with < ~200 posts.
3. **Write backtest config** — Create `config/backtest_<case>.yaml` using discovery-derived subreddits (NOT guesses). Comment each subreddit with its Exa frequency. Set market_anchors to realistic frustration statements for the target market.
4. **Competitor features file** — Verify `config/competitor_features/<competitor>_<year>.yaml` exists and accurately represents the incumbent's capabilities at that point in time.
5. **Run pipeline** — `uv run latent-signals run --config config/backtest_<case>.yaml`
6. **Analyze report** — Review `data/reports/<run_id>/gap_report.md` against expected signal.

## Key Files for Quick Reference

| File | Purpose |
|------|---------|
| `src/latent_signals/cli.py` | CLI entry point |
| `src/latent_signals/run_pipeline.py` | Pipeline orchestrator |
| `src/latent_signals/config.py` | Config loading, all Pydantic config models |
| `src/latent_signals/models.py` | All shared data models |
| `config/default.yaml` | Default config template |
| `latent-signals/04_decisions/decision_log.md` | Architecture decisions (source of truth) |
| `CLAUDE.md` | AI assistant instructions |
