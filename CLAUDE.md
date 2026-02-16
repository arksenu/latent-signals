# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GapFinder is a Python CLI tool that identifies market gaps by analyzing community sentiment and competitor features. It takes a product niche as input and outputs ranked market opportunities.

## Key Documentation

- `SPEC.md` — Technical specification with architecture diagram, per-stage contracts (typed input/output schemas), scoring formula, API reference, and decision log
- `INITIAL_PROMPT.md` — Scoped MVP prompt with project structure and constraints
- `research.md` — Full research backing all technical decisions

## Architecture

Six-stage sequential pipeline: **Collect → Preprocess → Cluster → Classify → Extract → Score**

Each stage is a pure function: typed Pydantic models in, typed Pydantic models out. No raw dicts cross stage boundaries. Stages live in `gapfinder/stages/` as separate modules.

The core insight is asymmetric vector comparison: user needs that are maximally *distant* from all product features in embedding space represent gaps. Qdrant's native dissimilarity search handles this; ChromaDB is used for prototyping.

### Scoring Formula (memorize this)

```
gap_score = 0.30 * (1 - max_similarity)       # unaddressedness
          + 0.25 * normalize(log(mention+1))   # frequency
          + 0.15 * avg_sentiment_intensity     # pain level
          + 0.15 * (1 - coverage_ratio)        # competitive whitespace
          + 0.10 * normalize(market_size)      # market proxy
          + 0.05 * trend_slope                 # momentum
```

## Planned Tech Stack

- **CLI:** Typer
- **Models:** Pydantic v2 (strict mode)
- **Config:** pydantic-settings (env vars: `EXA_API_KEY`, `SERPER_API_KEY`, `OPENAI_API_KEY`)
- **Embeddings:** sentence-transformers `all-MiniLM-L6-v2` (384-dim)
- **Topics:** BERTopic (UMAP + HDBSCAN + KeyBERTInspired)
- **Sentiment:** VADER (fast) + zero-shot `bart-large-mnli` (classification)
- **LLM extraction:** OpenAI GPT-5-nano Batch API with Structured Outputs, orchestrated via DSPy
- **Vector store:** ChromaDB (prototype) behind abstract interface → Qdrant (production)
- **Logging:** structlog
- **Python:** 3.11+

## MVP Scope

Stages 1-4 + Stage 6 with simplified scorer. No Stage 5 (LLM extraction). ChromaDB only. Reddit as only community source. Manual competitor features via JSON file.

## Design Constraints

- Vector store access must be behind an abstract interface (ChromaDB ↔ Qdrant swap)
- Each stage independently testable with fixture data
- Hybrid NLP approach: traditional NLP for volume, LLMs surgically on sampled representatives only
