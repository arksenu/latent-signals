# Latent Signals — Architecture

## Executive Summary

Latent Signals is a sequential 6-stage NLP/data pipeline that processes community discussion data to detect underserved market opportunities. The architecture prioritizes cost efficiency (hybrid NLP with LLMs on sampled subsets only), inspectability (all intermediate outputs written to disk), and future-proofing (gap identity designed for time-series tracking in V2).

## Architecture Pattern

**Sequential Data Pipeline with CLI Orchestration**

- No orchestration framework (Prefect/Airflow deferred to post-V1)
- Each stage is independently runnable via CLI flags (`--stages 1,2,3`)
- Stages communicate via filesystem artifacts (JSONL, numpy arrays, JSON)
- Pipeline state is implicit in the filesystem — if `data/embeddings/{run_id}/` exists, Stage 3 has completed

## System Architecture

```
                    ┌──────────────────────────────┐
                    │         CLI (Click)           │
                    │   latent-signals run          │
                    │   --config backtest.yaml      │
                    └──────────┬───────────────────┘
                               │
                    ┌──────────▼───────────────────┐
                    │    Pipeline Orchestrator       │
                    │    run_pipeline.py             │
                    │    (sequential stage dispatch) │
                    └──────────┬───────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
  ┌─────▼─────┐         ┌─────▼─────┐         ┌─────▼─────┐
  │  Stage 1   │         │  Stage 2   │         │  Stage 3   │
  │ Collection │───────▶│ Preprocess │───────▶│ Embedding  │
  │ (5 sources)│  JSONL  │ (5 filters)│  JSONL  │ (MiniLM)   │
  └────────────┘         └────────────┘         └─────┬─────┘
                                                      │ .npy
        ┌─────────────────────────────────────────────┘
        │
  ┌─────▼─────┐         ┌────────────┐         ┌────────────┐
  │  Stage 4   │         │  Stage 5   │         │  Stage 6   │
  │ Clustering │───────▶│ Classify   │───────▶│ Scoring &  │
  │ (BERTopic) │  JSONL  │ (Hybrid)   │  JSONL  │ Reporting  │
  └────────────┘         └────────────┘         └────────────┘
                                                      │
                                               gap_report.md
```

## Stage Details

### Stage 1: Data Collection

**Purpose:** Fetch community discussion data from multiple sources.

**Collectors (all extend abstract `Collector` base class):**

| Collector | Source | API | Cost | Use Case |
|-----------|--------|-----|------|----------|
| `ExaCollector` | Web (semantic) | exa-py | ~$5/1k searches | Discovery probes, semantic search |
| `SerperCollector` | Web (keyword) | httpx → REST | ~$1/1k queries | Targeted keyword search |
| `ApifyCollector` | Reddit (bulk) | apify-client | ~$2/1k results | Production Reddit scraping |
| `ArcticShiftCollector` | Reddit (historical) | httpx → REST | Free | Historical backtests |
| `HackerNewsCollector` | Hacker News | httpx → Algolia | Free | HN discussion data |

**Output:** `data/raw/{run_id}/documents.jsonl` (RawDocument objects)

**Design decisions:**
- Cross-source deduplication by `source:platform_id` key
- Per-subreddit item caps in Arctic Shift to prevent corpus domination
- Cost tracking per collector via `CostTracker`

### Stage 2: Preprocessing

**Purpose:** Clean, filter, and deduplicate raw documents.

**Pipeline (sequential):**
1. **Noise filter** — Remove bot posts, gratitude messages, [deleted]/[removed]
2. **HTML cleanup** — Strip HTML tags, markdown formatting, URLs
3. **Language filter** — Keep only target language (default: English)
4. **Length filter** — Remove documents outside 50-10,000 character bounds
5. **MinHash deduplication** — LSH-based near-duplicate detection (threshold 0.8, 128 permutations, word 3-grams)

**Output:** `data/preprocessed/{run_id}/corpus.jsonl` (CleanedDocument objects)

### Stage 3: Embedding

**Purpose:** Compute dense vector representations for all documents.

**Model:** `all-MiniLM-L6-v2` (384 dimensions, sentence-transformers)
**Batch processing:** 256 documents per batch with progress bar
**Device:** CPU (default, configurable)

**Post-level market relevance filter:** Before clustering, individual documents whose max cosine similarity to any market anchor phrase falls below `embedding.post_relevance_threshold` (default: 0.0, disabled) are dropped. This prevents off-topic posts from broad subreddits forming garbage clusters. Uses the same market anchor phrases defined in `scoring.market_anchors`.

**Output:** `data/embeddings/{run_id}/embeddings.npy` + `doc_ids.json` metadata

### Stage 4: Topic Clustering

**Purpose:** Group semantically similar documents into topic clusters.

**Stack:**
- **UMAP** — Dimensionality reduction (15 neighbors, 5 components, cosine metric)
- **HDBSCAN** — Density-based clustering (min_cluster_size=15, min_samples=5)
- **BERTopic** — Topic modeling with KeyBERTInspired representation
- **nr_topics** — Configurable (integer or "auto")

**Output:** `data/clusters/{run_id}/topic_assignments.jsonl` + `topic_info.json`

**Design decisions:**
- Outliers (topic_id=-1) tracked but excluded from scoring
- Topic labels cleaned from BERTopic's default format ("0_word1_word2" → "word1 word2 word3")

### Stage 5: Classification & Extraction

**Purpose:** Classify sentiment, categorize content type, and extract structured insights.

**Three-layer hybrid approach:**

| Layer | Tool | Scope | Speed |
|-------|------|-------|-------|
| VADER sentiment | vaderSentiment | ALL documents | ~100k/sec |
| Zero-shot classification | bart-large-mnli | Sampled subset only | ~32/batch |
| LLM extraction | GPT-4o-mini Batch API | Sampled subset only | Async batch |

**Categories:** pain_point, feature_request, praise, question, bug_report

**Sampling strategy:**
- Top N largest clusters (max 50)
- Within each: top 75 docs by topic_probability
- Zero-shot and LLM run only on these sampled docs
- Remaining docs classified by VADER heuristic with keyword pattern overrides

**Keyword pattern overrides:**
- Feature request patterns: "I wish", "it would be nice", "should support", "missing feature", etc.
- Pain point patterns: "frustrated", "bloat", "slow", "terrible", "nightmare", etc.

**LLM extraction schema (Pydantic → OpenAI Structured Outputs):**
```python
class FeedbackAnalysis(BaseModel):
    pain_points: list[str]
    feature_requests: list[str]
    urgency: float  # 0.0 to 1.0
    products_mentioned: list[str]
```

**Output:** `data/classified/{run_id}/classified.jsonl` (ClassifiedDocument objects)

### Stage 6: Gap Detection & Scoring

**Purpose:** Score and rank market gap opportunities.

**Sub-components:**

1. **Competitor feature loading** — Parse YAML files, embed descriptions
2. **Market anchor embedding** — Embed market relevance anchor phrases
3. **Cluster centroid computation** — Average embedding per topic cluster
4. **Pre-filtering gates:**
   - Market relevance: cluster centroid similarity to anchor phrases (threshold configurable)
   - Signal ratio: minimum fraction of pain/feature_request/bug_report docs per cluster
   - Unaddressedness floor: clusters with max cosine similarity to competitor features below `scoring.unaddressedness_floor` (default: 0.15) are excluded — high unaddressedness in these clusters is an artifact of being completely unrelated to the market, not a signal
5. **Gap scoring** — 6-component weighted formula
   - Pain intensity uses top-N (default 20) most negative VADER compounds per cluster, not cluster mean — prevents mixed clusters from diluting pain signal
   - Frequency component applies P95 cap on mention counts before log normalization — prevents mega-clusters from dominating on frequency alone
6. **Report generation** — Markdown with summary table, per-gap sections, evidence quotes

**Gap Scoring Formula:**
```
gap_score = 0.30 * (1 - max_similarity)           # unaddressedness
          + 0.25 * normalize(log(mention_count+1)) # frequency
          + 0.15 * avg_sentiment_intensity          # pain intensity
          + 0.15 * (1 - competitor_coverage_ratio)  # competitive whitespace
          + 0.10 * normalize(market_size_proxy)     # market size
          + 0.05 * trend_slope_normalized           # trend direction
```

**Vector store:** ChromaDB (embedded mode, cosine metric). Two separate collections:
- User needs (cluster centroids from community data)
- Competitor features (embedded from curated YAML)

**Output:** `data/reports/{run_id}/gap_report.md` + `gap_scores.json`

## Data Models

All data models defined in `src/latent_signals/models.py` using Pydantic v2:

| Model | Stage | Fields |
|-------|-------|--------|
| `RawDocument` | 1 | id, source, platform_id, title, body, author, url, created_at, score, subreddit, metadata |
| `CleanedDocument` | 2 | id, source, text, created_at, score, is_duplicate, language, char_count |
| `EmbeddingMeta` | 3 | doc_ids, model_name, dimensions, count |
| `TopicAssignment` | 4 | doc_id, topic_id, topic_label, topic_probability |
| `TopicInfo` | 4 | topic_id, label, size, representative_doc_ids, keywords |
| `ClassifiedDocument` | 5 | doc_id, vader_*, category, category_confidence, llm_*, keyphrases, entities |
| `CompetitorFeature` | 6 | feature_id, competitor_name, description, category |
| `GapOpportunity` | 6 | gap_id, label, gap_score, score_breakdown, mention_count, representative_quotes, ... |
| `PipelineRunMeta` | All | run_id, market_category, started_at, stage_durations, api_costs |

## Configuration Architecture

**YAML-driven** — All pipeline parameters defined in YAML files:
- `config/default.yaml` — Production template
- `config/backtest_*.yaml` — Per-test-case overrides

**Pydantic config hierarchy:**
```
Config
├── PipelineConfig (market_category, run_id, output_dir, random_seed)
├── CollectionConfig
│   ├── ExaConfig, SerperConfig, ApifyConfig, ArcticShiftConfig, HackerNewsConfig
├── PreprocessingConfig (min_length, max_length, language, minhash_*)
├── EmbeddingConfig (model_name, batch_size, device, post_relevance_threshold)
├── ClusteringConfig
│   ├── UMAPConfig, HDBSCANConfig
├── ClassificationConfig
│   ├── ZeroShotConfig, LLMExtractionConfig
├── ScoringConfig
│   ├── ScoringWeights (6 component weights)
│   ├── similarity_threshold, top_n_opportunities, competitor_features_file
│   ├── market_anchors, market_relevance_threshold, min_signal_ratio, unaddressedness_floor
└── ReportConfig (format, max_quotes_per_gap)
```

**Environment variables:** API keys loaded from `.env` via python-dotenv (EXA_API_KEY, SERPER_API_KEY, APIFY_API_TOKEN, OPENAI_API_KEY).

## Cross-Cutting Concerns

### Cost Tracking
- `CostTracker` accumulates per-service costs (openai, exa, serper, apify)
- Logged at pipeline completion with per-stage durations

### Structured Logging
- `structlog` with ISO timestamps, ConsoleRenderer
- Named loggers per module (e.g., `collector.exa`, `stage1`)
- Context variables for structured event data

### Error Handling
- Collector failures are caught and logged — pipeline continues with remaining collectors
- LLM Batch API has polling with timeout and fallback to synchronous extraction
- MinHash LSH handles exact duplicate keys gracefully

### Reproducibility
- Config hash computed at pipeline start for run tracking
- Random seed configurable (default: 42)
- Gap IDs computed from centroid embeddings for stable identity across runs

## Known Architectural Constraints

1. **No real-time capability** — Batch-only pipeline, but architecture avoids lock-in to batch patterns
2. **ChromaDB limitations** — No native dissimilarity search; Qdrant migration planned for V2
3. **Single-threaded** — No parallel stage execution; acceptable for V1 prototype
4. **Discovery dependency** — Pipeline requires pre-run Exa discovery probe for quality source selection
5. **VADER top-N approach** — Pain intensity uses top-N most negative compounds (mitigates but doesn't fully eliminate dilution in mixed clusters)
6. **Coverage gaps only** — `gap_detection.py` only detects coverage gaps (low similarity = unaddressed need). Satisfaction gaps — clusters with HIGH similarity to competitor features but NEGATIVE sentiment, indicating poorly implemented features — are not yet implemented. This means the pipeline misses a distinct gap type: features competitors claim to offer but users find broken or inadequate. Requires combining cosine similarity with sentiment polarity in the scoring path.

## Future Architecture Considerations (V2)

- **Qdrant migration** — Native dissimilarity search, better scaling
- **Prefect orchestration** — DAG-based pipeline with retry, caching, monitoring
- **Time-series tracking** — Gap identity (stable IDs) enables tracking gaps over time
- **Custom LLM deployment** — Groq/Cerebras for real-time interactive queries
- **Web UI/dashboard** — Replace static Markdown reports
