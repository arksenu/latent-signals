# Initial Prompt: GapFinder MVP

Use this prompt with a coding agent to scaffold the project.

---

## Prompt

Build "GapFinder" — a Python CLI tool that takes a product niche as input and outputs a ranked list of market gaps by analyzing community sentiment and competitor features.

### Architecture

The pipeline has 6 sequential stages:

1. **Data Collection** — Query Exa (semantic search) and Serper.dev (keyword search) to discover Reddit/forum posts about the niche. Use `google-play-scraper` for app store data. Scrape competitor features from AlternativeTo and Product Hunt. Output: `list[RawDocument]` and `list[CompetitorRecord]`.

2. **Preprocessing & Embedding** — Clean HTML with `bleach`, detect language with `langdetect`, deduplicate with MinHash (`datasketch`), embed with `sentence-transformers` model `all-MiniLM-L6-v2` (384-dim). Output: `list[ProcessedDocument]` with embeddings.

3. **Topic Clustering** — Run BERTopic with UMAP + HDBSCAN on the pre-computed embeddings. Use `KeyBERTInspired` for topic labels. Output: `list[TopicCluster]` with labels, keywords, and document assignments.

4. **Fast Classification** — Score sentiment with VADER (`vaderSentiment`). Classify each post as pain_point / feature_request / praise / question / bug_report using zero-shot classification (`facebook/bart-large-mnli`). Output: `list[ClassifiedDocument]`.

5. **LLM Extraction** — Sample 50-100 representative posts per topic cluster. Send to OpenAI GPT-5-nano Batch API with Structured Outputs (Pydantic schema). Extract pain_points, feature_requests, urgency scores, products mentioned. Use DSPy typed signatures. Output: `list[ClusterInsight]`.

6. **Gap Detection & Scoring** — Store need embeddings and feature embeddings in ChromaDB (prototype) or Qdrant (production). For each need, find max cosine similarity to any feature. Compute composite gap score:
   ```
   gap_score = 0.30 * (1 - max_similarity)
             + 0.25 * normalize(log(mention_count + 1))
             + 0.15 * avg_sentiment_intensity
             + 0.15 * (1 - competitor_coverage_ratio)
             + 0.10 * normalize(market_size_proxy)
             + 0.05 * trend_slope_normalized
   ```
   Output: ranked `list[MarketGap]` with scores, evidence quotes, and competitor coverage.

### Project Structure

```
gapfinder/
├── pyproject.toml
├── gapfinder/
│   ├── __init__.py
│   ├── cli.py                 # Typer CLI entry point
│   ├── config.py              # Settings via pydantic-settings (env vars)
│   ├── pipeline.py            # run_pipeline() orchestrator
│   ├── models.py              # All Pydantic data models (see SPEC.md)
│   ├── stages/
│   │   ├── __init__.py
│   │   ├── collect.py         # Stage 1
│   │   ├── preprocess.py      # Stage 2
│   │   ├── cluster.py         # Stage 3
│   │   ├── classify.py        # Stage 4
│   │   ├── extract.py         # Stage 5
│   │   └── score.py           # Stage 6
│   └── utils/
│       ├── __init__.py
│       ├── dedup.py            # MinHash deduplication
│       └── normalize.py        # Min-max scaling helpers
└── tests/
    └── ...
```

### Key Constraints

- Use `pydantic` v2 for all data models (strict schemas between stages)
- Use `typer` for the CLI
- Use `pydantic-settings` for config (API keys from env vars: `EXA_API_KEY`, `SERPER_API_KEY`, `OPENAI_API_KEY`)
- ChromaDB for prototype vector storage; code behind an abstract interface so Qdrant swap is trivial
- All stage functions should accept and return typed dataclasses/Pydantic models — no raw dicts crossing stage boundaries
- Each stage should be independently testable with fixture data
- Log progress with `structlog`
- Target Python 3.11+

### MVP Scope (build this first)

For the MVP, implement Stages 1-4 and Stage 6 with a simplified scorer (skip Stage 5 LLM extraction — use the VADER + zero-shot outputs directly). Use ChromaDB. Support Reddit as the only community source and manual competitor feature input via a JSON file. This validates the core loop: collect → process → cluster → classify → detect gaps.

### What NOT to build yet

- No web UI (CLI only)
- No Prefect/Dagster orchestration (sequential `run_pipeline()` is fine)
- No Qdrant (ChromaDB first)
- No DSPy / LLM extraction (Stage 5 comes after MVP validation)
- No Apify integration (Exa + Serper only for MVP)
- No Crunchbase/SimilarWeb enrichment
