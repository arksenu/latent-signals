# Latent Signals

## What This Is

Latent Signals is a B2B competitive intelligence tool that detects underserved market opportunities by analyzing community sentiment from forums and review sites, mapping signals against competitor feature coverage, and scoring gaps by a composite metric. Target: startups in fast-moving markets where historical data is scarce.

Core output: a scored, evidence-backed gap report that replaces weeks of manual market validation.

## Project Structure

```
latent-signals/
  01_strategy/          # Product brief, positioning, competitive landscape, meeting notes
  02_requirements/      # User flows, design constraints, scoring function spec
  03_architecture/      # Technical stack, data pipeline, infrastructure
  04_decisions/         # Decision log (active decisions documented here)
  05_validation/        # Historical backtest plan and results
  06_business/          # Pricing model, GTM plan
```

Key reference docs:
- `product_brief.md` (root) — canonical product spec, V1 scope, design constraints
- `Building_a_Market_Gap_Finder.md` (root) — full technical stack research
- `latent-signals/05_validation/results/historical_backtest_plan.md` — backtest spec (final)
- `latent-signals/04_decisions/decision_log.md` — all architectural decisions

## V1 Scope (What We're Building)

Sequential Python script that takes a market category as input and produces a scored gap report.

### V1 Pipeline (6 stages)
1. **Data Collection** — Exa (semantic search) + Serper.dev (keyword search) + Apify (bulk Reddit scraping)
2. **Preprocessing** — HTML cleanup, language detection, MinHash dedup, length filtering
3. **Embedding** — `all-MiniLM-L6-v2` (384d) or `BAAI/bge-base-en-v1.5` (768d), computed once and reused
4. **Topic Clustering** — BERTopic with UMAP + HDBSCAN, KeyBERTInspired representation
5. **Classification & Extraction** — VADER sentiment + zero-shot (`facebook/bart-large-mnli`) + GPT-4o-mini Batch API on sampled clusters (50-100 posts per cluster) with Structured Outputs
6. **Gap Detection & Scoring** — ChromaDB for vector storage, cosine similarity threshold logic, composite gap_score

### V1 Output
Static Markdown/PDF report with ranked gap opportunities (5-10), each with evidence package.

### V1 Explicitly Defers
- Job 2 (expansion analysis for existing products)
- Qdrant migration / native dissimilarity search
- Prefect orchestration
- Web UI / dashboard
- SparkToro, Glimpse, Exploding Topics integrations
- Multi-tenant SaaS, auth, billing

## Tech Stack (V1)

| Layer | Tool | Notes |
|-------|------|-------|
| Semantic search | Exa API (`exa-py`) | $5/1k searches |
| Keyword search | Serper.dev | $0.30-1.00/1k queries, REST only |
| Bulk scraping | Apify (`apify-client`) | $2/1k results, Reddit + review sites |
| Embeddings | sentence-transformers (local) | `all-MiniLM-L6-v2` or `bge-base-en-v1.5` |
| Topic modeling | BERTopic + UMAP + HDBSCAN | KeyBERTInspired for labels |
| Sentiment | VADER (vaderSentiment) | ~100k texts/sec |
| Classification | HF zero-shot (`bart-large-mnli`) | Pain point / feature request / praise / question / bug |
| LLM extraction | GPT-4o-mini Batch API | Structured Outputs with Pydantic schemas |
| LLM framework | DSPy | Typed signatures, self-improving prompts |
| Keyphrase extraction | KeyBERT + KeyphraseVectorizers | POS pattern-based extraction |
| NER | spaCy `en_core_web_trf` | Product names, companies |
| Vector store | ChromaDB (embedded) | Zero infrastructure, migrate to Qdrant later |
| Language | Python 3.11+ | Sequential script orchestration |

## Hard Constraints

1. **Cost ceiling**: Prototype < $50/month, production < $500/month
2. **Emotional signal fidelity**: Sentiment must preserve intensity/urgency gradients, never reduce to binary pos/neg
3. **Hybrid NLP only**: LLMs on sampled subsets (50-100 per cluster), traditional NLP for bulk processing
4. **Data separation**: Competitor feature vectors describe actual capabilities. User complaint vectors describe pain points. These are separate collections — never collapse them
5. **Future-proof for time series**: Design data storage and gap identity so V2 can track gaps over time
6. **No batch-only lock-in**: Architecture must not prevent future shift to synchronous inference

## Gap Scoring Formula

```
gap_score = 0.30 * (1 - max_similarity)           # unaddressedness
          + 0.25 * normalize(log(mention_count+1)) # frequency
          + 0.15 * avg_sentiment_intensity          # pain intensity
          + 0.15 * (1 - competitor_coverage_ratio)  # competitive whitespace
          + 0.10 * normalize(market_size_proxy)     # market size
          + 0.05 * trend_slope_normalized           # trend direction
```

## Validation Strategy

Historical backtest with 4 test cases (3 positive, 1 negative control):
- **Linear** (Sept 2018 - Aug 2019): Should detect Jira frustration gap
- **Notion** (Mar 2017 - Feb 2018): Should detect Evernote frustration gap
- **Plausible** (Jan 2018 - Dec 2018): Should detect GA privacy gap
- **Email Control** (Jan 2018 - Dec 2019): Should NOT produce high-scoring gaps

Success: 2/3 positive cases detected in top 3 + negative control produces no false positives.

See `latent-signals/05_validation/results/historical_backtest_plan.md` for full spec.

## Active Decisions (from decision log)

- B2B model only (B2C rejected due to churn)
- Sentiment analysis as primary methodology (combined with white space mapping via vectors)
- Hybrid NLP pipeline (not pure-LLM or pure-traditional)
- Custom LLM on inference hardware deferred to post-prototype

## Development Workflow

- Use `uv` for Python dependency management
- Keep the pipeline as a sequential script (`run_pipeline.py`) — no orchestration framework in V1
- All pipeline stages should be independently runnable for debugging
- Store intermediate outputs (embeddings, clusters, scores) for inspection
- Write tests against the backtest plan's failure analysis framework

## Subagents

Custom agents are defined in `.claude/agents/` for specialized tasks:
- `api-researcher` — research current API docs, SDKs, pricing, and integration patterns
- `nlp-engineer` — build and debug the NLP pipeline (BERTopic, embeddings, classification)
- `data-pipeline` — build data collection and preprocessing stages
- `scoring-engine` — implement gap detection, scoring formula, and report generation
- `dev-logger` - run automatically each time AFTER you finish responding.