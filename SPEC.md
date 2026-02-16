# GapFinder Technical Specification

## Architecture Diagram

```
                         USER INPUT
                         (product idea / niche keyword)
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 1: DATA COLLECTION                               │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Exa API      │  │ Serper.dev   │  │ Apify         │  │
│  │ (semantic)   │  │ (keyword)    │  │ (bulk scrape) │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘  │
│         └─────────────┬───┘                 │           │
│                       ▼                     ▼           │
│              raw_posts[]              raw_reviews[]     │
│              raw_competitors[]        raw_features[]    │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 2: PREPROCESSING & EMBEDDING                     │
│  ┌────────────┐  ┌────────────┐  ┌───────────────────┐  │
│  │ Clean HTML │→ │ Dedup      │→ │ Embed             │  │
│  │ Lang detect│  │ (MinHash)  │  │ (all-MiniLM-L6-v2)│  │
│  │ Filter len │  │            │  │ 384-dim vectors   │  │
│  └────────────┘  └────────────┘  └───────────────────┘  │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 3: TOPIC CLUSTERING                              │
│  ┌─────────────────────────────────────────────────┐    │
│  │ BERTopic (UMAP + HDBSCAN + KeyBERTInspired)    │    │
│  │ Input:  embeddings[]                             │    │
│  │ Output: topic_clusters[] with labels & hierarchy │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 4: FAST CLASSIFICATION                           │
│  ┌──────────────────┐  ┌────────────────────────────┐   │
│  │ VADER sentiment  │  │ Zero-shot classification   │   │
│  │ (~100K texts/sec)│  │ (bart-large-mnli)          │   │
│  │                  │  │ → pain_point | feature_req │   │
│  │                  │  │   | praise | question | bug│   │
│  └────────┬─────────┘  └─────────────┬──────────────┘   │
│           └───────────┬───────────────┘                  │
│                       ▼                                  │
│              classified_posts[]                          │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 5: LLM EXTRACTION (surgical, sampled)            │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Sample 50-100 posts per topic cluster            │    │
│  │ GPT-5-nano Batch API + Structured Outputs        │    │
│  │ DSPy typed signatures for extraction             │    │
│  │ Output: structured insights per cluster          │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 6: GAP DETECTION & SCORING                       │
│  ┌─────────────────────┐  ┌──────────────────────────┐  │
│  │ Qdrant              │  │ Scoring Engine           │  │
│  │ Collection A: needs │  │ gap_score formula        │  │
│  │ Collection B: feats │  │ cluster + rank + report  │  │
│  │ Dissimilarity search│  │                          │  │
│  └──────────┬──────────┘  └────────────┬─────────────┘  │
│             └──────────┬───────────────┘                 │
│                        ▼                                 │
│               ranked_gaps[]                              │
│               → final report                             │
└─────────────────────────────────────────────────────────┘
```

---

## Per-Stage Contracts

### Stage 1: Data Collection

**Input:**
```python
class PipelineInput:
    query: str               # e.g. "project management tools"
    platforms: list[str]     # e.g. ["reddit", "g2", "producthunt"]
    max_results: int         # default 10_000
    date_range_days: int     # default 365
```

**Output:**
```python
class RawDocument:
    id: str                  # deterministic hash of source + url
    text: str                # cleaned body text
    source: str              # "reddit" | "g2" | "producthunt" | "app_store" | ...
    url: str
    author: str | None
    timestamp: datetime
    metadata: dict           # upvotes, star_rating, subreddit, app_id, etc.

class CompetitorRecord:
    name: str
    domain: str | None
    source: str              # where discovered
    category: str
    features_raw: list[str]  # scraped feature bullet points
```

**Dependencies:** `exa-py`, `requests` (Serper), `apify-client`, `google-play-scraper`
**API calls:** Exa search, Serper search, Apify actor runs
**Libraries:** `exa-py`, `apify-client`, `google-play-scraper`, `beautifulsoup4`

---

### Stage 2: Preprocessing & Embedding

**Input:** `list[RawDocument]`

**Output:**
```python
class ProcessedDocument:
    id: str
    text_clean: str
    language: str            # ISO 639-1
    embedding: list[float]   # 384-dim (MiniLM) or 768-dim (BGE)
    is_duplicate: bool
    token_count: int

# Duplicates filtered out; only unique docs passed downstream
```

**Dependencies:** None external (all local compute)
**API calls:** None (or OpenAI embeddings API as fallback)
**Libraries:** `sentence-transformers`, `datasketch` (MinHash), `langdetect`, `bleach`/`markdownify`

---

### Stage 3: Topic Clustering

**Input:** `list[ProcessedDocument]` (deduplicated, with embeddings)

**Output:**
```python
class TopicCluster:
    topic_id: int
    label: str               # human-readable topic name
    keywords: list[str]      # top-10 representative terms
    document_ids: list[str]
    document_count: int
    parent_topic_id: int | None   # for hierarchical view
    representative_docs: list[str] # 5 most central doc IDs
```

**Dependencies:** Stage 2 embeddings
**API calls:** None (all local)
**Libraries:** `bertopic`, `umap-learn`, `hdbscan`, `scikit-learn`

---

### Stage 4: Fast Classification

**Input:** `list[ProcessedDocument]`, `list[TopicCluster]`

**Output:**
```python
class ClassifiedDocument:
    id: str
    topic_id: int
    sentiment_score: float        # -1.0 to 1.0 (VADER compound)
    sentiment_label: str          # "positive" | "negative" | "neutral"
    category: str                 # "pain_point" | "feature_request" | "praise" | "question" | "bug_report"
    category_confidence: float    # 0.0 to 1.0
```

**Dependencies:** Stage 2 (docs), Stage 3 (topic assignments)
**API calls:** None (all local)
**Libraries:** `vaderSentiment`, `transformers` (pipeline zero-shot)

---

### Stage 5: LLM Extraction

**Input:** `list[TopicCluster]`, `list[ClassifiedDocument]`

**Output:**
```python
class ClusterInsight:
    topic_id: int
    pain_points: list[PainPoint]
    feature_requests: list[FeatureRequest]
    avg_sentiment: float
    avg_urgency: float            # 1-5 scale
    products_mentioned: list[str]
    sample_quotes: list[str]

class PainPoint:
    description: str
    urgency: int                  # 1-5
    frequency_in_sample: int

class FeatureRequest:
    description: str
    specificity: str              # "vague" | "specific" | "detailed"
    existing_workarounds: list[str]
```

**Dependencies:** Stage 3 (clusters), Stage 4 (classified docs for sampling strategy)
**API calls:** OpenAI Batch API (GPT-5-nano)
**Libraries:** `dspy`, `openai`, `pydantic`

---

### Stage 6: Gap Detection & Scoring

**Input:** `list[ClusterInsight]`, `list[CompetitorRecord]`, embeddings from Stage 2

**Output:**
```python
class MarketGap:
    gap_id: str
    title: str
    description: str
    gap_score: float              # 0.0 to 1.0 (composite)
    component_scores: GapScoreBreakdown
    evidence: list[str]           # sample quotes / doc IDs
    related_needs_cluster: int    # topic_id
    competitor_coverage: dict     # {competitor_name: bool}
    trend_direction: str          # "rising" | "stable" | "declining"

class GapScoreBreakdown:
    unaddressedness: float        # 0-1
    frequency: float              # 0-1
    sentiment_intensity: float    # 0-1
    competitive_whitespace: float # 0-1
    market_size_proxy: float      # 0-1
    trend_slope: float            # 0-1
```

**Dependencies:** All prior stages; Qdrant running
**API calls:** Qdrant vector queries (local or cloud)
**Libraries:** `qdrant-client`, `numpy`

---

## Scoring Formula

```
gap_score = 0.30 * unaddressedness
          + 0.25 * frequency
          + 0.15 * sentiment_intensity
          + 0.15 * competitive_whitespace
          + 0.10 * market_size_proxy
          + 0.05 * trend_slope
```

### Component Definitions

| Component (weight) | Calculation | Range |
|---|---|---|
| **Unaddressedness** (0.30) | `1 - max_cosine_similarity(need_embedding, all_feature_embeddings)` | 0-1 |
| **Frequency** (0.25) | `normalize(log(mention_count + 1))` across all needs | 0-1 |
| **Sentiment Intensity** (0.15) | `abs(avg_vader_compound)` for the cluster, higher = more emotional | 0-1 |
| **Competitive Whitespace** (0.15) | `1 - (competitors_addressing / total_competitors)` | 0-1 |
| **Market Size Proxy** (0.10) | `normalize(community_size + search_volume_estimate)` | 0-1 |
| **Trend Slope** (0.05) | Normalized slope of mention frequency over time (positive = rising) | 0-1 |

**Normalization:** Min-max scaling within each pipeline run. `normalize(x) = (x - min) / (max - min)`

---

## API Reference Table

| API | Cost | SDK | Returns | Rate Limits |
|---|---|---|---|---|
| **Exa** | $5/1K searches | `exa-py` | Semantically relevant URLs + extracted text/summaries | Not published; ~60 req/min observed |
| **Serper.dev** | $0.30-1.00/1K | REST (`requests`) | Google SERP JSON (titles, snippets, URLs) | 100 req/sec |
| **Apify** | $2/1K results | `apify-client` | Structured scraped data (posts, reviews, listings) | Per-actor; typically unlimited with compute budget |
| **Google Play Scraper** | Free | `google-play-scraper` | 65+ fields per app: ratings, reviews, descriptions, categories | No key needed; self-rate-limit to ~10 req/sec |
| **Product Hunt** | Free | GraphQL (`gql`) | Product launches, votes, descriptions, topics | 500 req/day (OAuth) |
| **OpenAI (GPT-5-nano Batch)** | $0.075/M input, $0.30/M output tokens | `openai` | Structured JSON per schema (Structured Outputs) | Batch: 90K tokens/min enqueued |
| **OpenAI Embeddings** | $0.02/M tokens | `openai` | 1536-dim vectors (`text-embedding-3-small`) | 3,500 req/min |
| **Qdrant Cloud** | Free (1GB), then $0.045/hr | `qdrant-client` | Vector search results, recommendation results, payloads | Self-hosted: unlimited |
| **Brave Search** | $5/1K | REST | Independent-index results + Discussions endpoint | 15 req/sec (free), 30 req/sec (paid) |
| **Tavily** | $0.008/credit | `tavily-python` | LLM-structured search results JSON | 1,000 req/min |

---

## Decision Log

### Qdrant over ChromaDB in production

| Factor | Qdrant | ChromaDB |
|---|---|---|
| **Dissimilarity search** | Native Recommendation API with negative examples; Discovery API for "far from" queries | Not supported; must implement in app layer |
| **Performance** | 326 QPS, ~45K inserts/sec (Rust) | ~50 QPS (Python/SQLite) |
| **Payload filtering** | Rich filtering with no metadata size limits | Basic `where` filtering |
| **Scaling** | Horizontal sharding, cloud-managed option | Single-node only |
| **Gap detection fit** | Purpose-built: query "like these needs, NOT like these features" | Requires manual distance computation for each need vs all features |

**Decision:** ChromaDB for prototype validation (5-line setup, zero infra). Migrate to Qdrant when the approach is proven, because dissimilarity search is the core operation and building it manually in the app layer is fragile and slow at scale.

---

### Hybrid NLP over pure-LLM

| Factor | Hybrid (chosen) | Pure LLM | Pure Traditional |
|---|---|---|---|
| **Cost per 10K posts** | $0.50-1.00 | ~$7.50 | $0 |
| **Latency** | Minutes | Hours | Seconds |
| **Quality** | Excellent (LLM on representative samples) | Best (but diminishing returns) | Misses nuance |
| **Determinism** | High (embedding + clustering is deterministic) | Low (LLM outputs vary) | High |
| **Scalability** | Linear with local compute | Linear with API cost | Linear with local compute |

**Decision:** Traditional NLP handles volume (sentiment, classification, clustering). LLMs handle depth (extracting structured insights from 50-100 samples per cluster). This gets 90%+ of pure-LLM quality at ~7% of the cost. The key insight: most posts in a topic cluster say similar things, so analyzing all of them with an LLM is redundant.

---

### BERTopic over LDA

| Factor | BERTopic | LDA |
|---|---|---|
| **Topic coherence (C_v)** | 0.76 | 0.38 |
| **Reddit-scale validation** | Tested on 352K+ posts | Degrades on short/noisy text |
| **Contextual understanding** | Uses transformer embeddings | Bag-of-words only |
| **Number of topics** | Auto-discovered via HDBSCAN density | Must be specified in advance |
| **Hierarchical topics** | Built-in `hierarchical_topics()` | Requires separate modeling |
| **Outlier handling** | HDBSCAN assigns noise points explicitly | Forces every doc into a topic |
| **Reusable embeddings** | Shares embeddings with dedup + gap detection | Separate representations |

**Decision:** BERTopic nearly doubles coherence, auto-discovers topic count, handles noisy social media text, and reuses the same embeddings computed in Stage 2. LDA's bag-of-words approach loses semantic relationships critical for gap detection downstream.
