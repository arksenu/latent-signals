# Latent Signals — Data Models

All data models are defined in `src/latent_signals/models.py` using Pydantic v2 BaseModel. They represent the typed data contracts between pipeline stages.

## Model Hierarchy by Pipeline Stage

### Stage 1: Collection

#### RawDocument
A single scraped post/comment from any source.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique document ID (prefixed by source: `exa_`, `arctic_`, `hn_`, etc.) |
| `source` | `Literal["reddit", "hackernews", "g2", "capterra", "producthunt", "web"]` | Source platform |
| `platform_id` | `str` | Platform-specific ID (Reddit post ID, HN objectID, etc.) |
| `title` | `str \| None` | Post title (None for comments) |
| `body` | `str` | Full text content |
| `author` | `str \| None` | Username |
| `url` | `str \| None` | Source URL |
| `created_at` | `datetime` | Original publication time |
| `score` | `int \| None` | Platform score (upvotes, points) |
| `subreddit` | `str \| None` | Subreddit name (Reddit only) |
| `metadata` | `dict[str, Any]` | Collector-specific metadata (query, num_comments, etc.) |
| `collection_timestamp` | `datetime` | When this document was collected |

### Stage 2: Preprocessing

#### CleanedDocument
Filtered, deduplicated, normalized document ready for embedding.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Same as RawDocument.id |
| `source` | `str` | Source platform |
| `text` | `str` | Cleaned text (HTML stripped, URLs removed, whitespace normalized) |
| `created_at` | `datetime` | Original publication time |
| `score` | `int \| None` | Platform score |
| `metadata` | `dict[str, Any]` | Preserved from raw |
| `is_duplicate` | `bool` | MinHash duplicate flag (default: False) |
| `language` | `str` | Detected language (ISO 639-1, default: "en") |
| `char_count` | `int` | Character count after cleaning |

### Stage 3: Embedding

#### EmbeddingMeta
Mapping between document IDs and embedding array indices.

| Field | Type | Description |
|-------|------|-------------|
| `doc_ids` | `list[str]` | Ordered list of document IDs matching embedding rows |
| `model_name` | `str` | Embedding model name (e.g., "all-MiniLM-L6-v2") |
| `dimensions` | `int` | Embedding dimensionality (384 for MiniLM) |
| `count` | `int` | Total number of embedded documents |

### Stage 4: Clustering

#### TopicAssignment
Per-document topic cluster assignment.

| Field | Type | Description |
|-------|------|-------------|
| `doc_id` | `str` | Document ID |
| `topic_id` | `int` | Assigned topic cluster (-1 = outlier) |
| `topic_label` | `str` | Human-readable topic label |
| `topic_probability` | `float` | Confidence of assignment (0.0 - 1.0) |

#### TopicInfo
Summary metadata for a single topic cluster.

| Field | Type | Description |
|-------|------|-------------|
| `topic_id` | `int` | Topic cluster ID |
| `label` | `str` | Descriptive label (top keywords) |
| `size` | `int` | Number of documents in cluster |
| `representative_doc_ids` | `list[str]` | Top-10 most representative documents |
| `keywords` | `list[str]` | Top-10 keywords for this topic |

### Stage 5: Classification

#### ClassifiedDocument
Document with sentiment scores, category, and optional LLM extraction.

| Field | Type | Description |
|-------|------|-------------|
| `doc_id` | `str` | Document ID |
| `vader_compound` | `float` | VADER compound score (-1.0 to 1.0) |
| `vader_pos` | `float` | Positive sentiment proportion |
| `vader_neg` | `float` | Negative sentiment proportion |
| `vader_neu` | `float` | Neutral sentiment proportion |
| `category` | `Literal[...]` | Content type: pain_point, feature_request, praise, question, bug_report |
| `category_confidence` | `float` | Classification confidence (0.0 - 1.0) |
| `llm_pain_points` | `list[str] \| None` | LLM-extracted pain points (sampled docs only) |
| `llm_feature_requests` | `list[str] \| None` | LLM-extracted feature requests (sampled docs only) |
| `llm_urgency` | `float \| None` | LLM-assessed urgency (0.0 - 1.0, sampled docs only) |
| `llm_products_mentioned` | `list[str] \| None` | Product/company names (sampled docs only) |
| `keyphrases` | `list[str] \| None` | Extracted keyphrases |
| `entities` | `list[dict[str, str]] \| None` | Named entities |

#### FeedbackAnalysis (OpenAI Structured Output schema)
Schema used for GPT-4o-mini extraction.

| Field | Type | Description |
|-------|------|-------------|
| `pain_points` | `list[str]` | Identified pain points in the text |
| `feature_requests` | `list[str]` | Feature requests or wishes |
| `urgency` | `float` | 0.0 (no urgency) to 1.0 (critical) |
| `products_mentioned` | `list[str]` | Product/company names referenced |

### Stage 6: Scoring

#### CompetitorFeature
One feature from a curated competitor feature set.

| Field | Type | Description |
|-------|------|-------------|
| `feature_id` | `str` | Unique feature identifier |
| `competitor_name` | `str` | Competitor company/product name |
| `description` | `str` | Feature description (used for embedding) |
| `category` | `str \| None` | Feature category |

#### GapOpportunity
One scored gap in the final report.

| Field | Type | Description |
|-------|------|-------------|
| `gap_id` | `str` | Stable ID (SHA-256 of centroid, 16 chars) |
| `label` | `str` | Human-readable gap label (from topic keywords) |
| `gap_score` | `float` | Composite score (0.0 - 1.0) |
| `score_breakdown` | `dict[str, float]` | Per-component scores |
| `max_similarity_to_features` | `float` | Highest cosine similarity to any competitor feature |
| `mention_count` | `int` | Number of documents in this gap's cluster(s) |
| `avg_sentiment_intensity` | `float` | Average negative VADER compound |
| `competitor_coverage_ratio` | `float` | Fraction of competitors covering this area |
| `market_size_proxy` | `float` | Cluster size as market size proxy |
| `trend_slope` | `float` | Linear regression slope of monthly mentions |
| `representative_quotes` | `list[str]` | Evidence quotes from cluster documents |
| `source_doc_ids` | `list[str]` | Document IDs in this gap |
| `topic_ids` | `list[int]` | Contributing topic cluster IDs |
| `competitive_whitespace` | `dict[str, float]` | Per-competitor similarity scores |

### Pipeline Metadata

#### PipelineRunMeta
Metadata about a full pipeline run.

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `str` | Unique run identifier (8-char UUID) |
| `market_category` | `str` | Target market (e.g., "project management") |
| `started_at` | `datetime` | Pipeline start time |
| `completed_at` | `datetime \| None` | Pipeline completion time |
| `config_hash` | `str` | SHA-256 of config (12 chars, excluding run_id) |
| `stage_durations` | `dict[str, float]` | Per-stage wall-clock time in seconds |
| `document_counts` | `dict[str, int]` | Document counts at each stage |
| `api_costs` | `dict[str, float]` | Per-service API costs |

## Configuration Models

Defined in `src/latent_signals/config.py`:

```
Config
├── PipelineConfig (market_category, run_id, output_dir, random_seed)
├── CollectionConfig
│   ├── date_range: dict[str, str]
│   ├── ExaConfig (enabled, max_results, domains, queries)
│   ├── SerperConfig (enabled, max_results, site_filters, queries)
│   ├── ApifyConfig (enabled, subreddits, max_items)
│   ├── ArcticShiftConfig (enabled, subreddits, max_items)
│   └── HackerNewsConfig (enabled, queries, max_items)
├── PreprocessingConfig (min_length, max_length, language, minhash_threshold, minhash_num_perm)
├── EmbeddingConfig (model_name, batch_size, device, post_relevance_threshold)
├── ClusteringConfig
│   ├── UMAPConfig (n_neighbors, n_components, min_dist, metric)
│   └── HDBSCANConfig (min_cluster_size, min_samples, metric)
├── ClassificationConfig
│   ├── ZeroShotConfig (model_name, categories, batch_size)
│   └── LLMExtractionConfig (enabled, model, samples_per_cluster, max_clusters, use_batch_api)
├── ScoringConfig
│   ├── ScoringWeights (6 component weights summing to 1.0)
│   ├── similarity_threshold, top_n_opportunities
│   ├── competitor_features_file
│   ├── market_relevance_threshold, market_anchors, min_signal_ratio, unaddressedness_floor
└── ReportConfig (format, max_quotes_per_gap)
```

## Serialization Format

| Stage | Format | File |
|-------|--------|------|
| Collection | JSONL (one JSON object per line) | `documents.jsonl` |
| Preprocessing | JSONL | `corpus.jsonl` |
| Embeddings | NumPy binary + JSON metadata | `embeddings.npy`, `doc_ids.json` |
| Clustering | JSONL + JSON | `topic_assignments.jsonl`, `topic_info.json` |
| Classification | JSONL + JSON | `classified.jsonl`, `classification_stats.json` |
| Scoring | Markdown + JSON | `gap_report.md`, `gap_scores.json` |

All JSONL files use Pydantic's `model_dump()` for serialization and `model_validate()` for deserialization, ensuring type safety across stage boundaries.
