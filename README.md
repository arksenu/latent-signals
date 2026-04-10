# Latent Signals

A competitive intelligence tool that detects underserved market opportunities by analyzing community sentiment from Reddit and Hacker News, mapping signals against competitor feature coverage, and scoring gaps with a composite metric. Give it a description of your market — it returns a ranked, evidence-backed report of where demand exists but supply doesn't.

## How It Works

The pipeline runs in 7 stages, from a plain-text market description to a scored gap report:

```
User Description
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 0: Input Construction                             │
│   Exa semantic search → source discovery → competitor   │
│   extraction → anchor generation → pipeline config      │
├─────────────────────────────────────────────────────────┤
│ Stage 1: Data Collection                                │
│   Arctic Shift (Reddit) + HN Algolia API                │
├─────────────────────────────────────────────────────────┤
│ Stage 2: Preprocessing                                  │
│   HTML cleanup, language detection, MinHash dedup        │
├─────────────────────────────────────────────────────────┤
│ Stage 3: Embedding                                      │
│   sentence-transformers (all-MiniLM-L6-v2, 384d)        │
├─────────────────────────────────────────────────────────┤
│ Stage 4: Topic Clustering                               │
│   BERTopic + UMAP + HDBSCAN                             │
├─────────────────────────────────────────────────────────┤
│ Stage 5: Classification & Extraction                    │
│   VADER sentiment + zero-shot (bart-large-mnli)         │
│   + GPT-4o-mini Batch API on sampled clusters           │
├─────────────────────────────────────────────────────────┤
│ Stage 6: Gap Scoring                                    │
│   ChromaDB cosine similarity + composite gap_score      │
└─────────────────────────────────────────────────────────┘
  │
  ▼
Ranked Gap Report (Markdown)
```

Traditional NLP handles bulk processing (VADER at ~100k texts/sec, MinHash dedup, zero-shot classification). LLMs are only used on sampled subsets (50-100 posts per cluster) for nuanced extraction. This keeps per-run LLM costs under $1.

## Scoring Formula

Each gap is scored on six weighted components:

| Weight | Component | Signal |
|--------|-----------|--------|
| 30% | Unaddressedness | Cosine distance from nearest competitor feature |
| 25% | Frequency | Log-normalized mention count |
| 15% | Pain intensity | Average VADER sentiment intensity |
| 15% | Competitive whitespace | Fraction of competitors not covering this need |
| 10% | Market size proxy | Normalized community size signal |
| 5% | Trend direction | Mention frequency slope over time |

An additive dissatisfaction boost adjusts unaddressedness for complaints about existing products (which embed near the feature they're complaining about), and a coverage gap floor prevents undiscovered needs from being penalized.

## Validation

The pipeline was validated via historical backtesting — run it on data from before a known product launched, check if it would have detected the gap.

| Test Case | Known Gap | Result |
|-----------|-----------|--------|
| **Linear** (2018-2019) | Jira workflow frustration | Rank 2, score 0.723 |
| **Notion** (2017-2018) | Evernote frustration | Rank 3, score 0.657 |
| **Plausible** (2018) | Google Analytics privacy gap | Ranks 1-2, scores 0.776/0.745 |
| Email (2018-2019) | Privacy/UX frustration | Detected — later addressed by HEY, ProtonMail |
| VS Code (2019) | Setup/config friction | Detected — Python, C++, Java pain points |

Success criteria was 2/3 positive cases in top 3. Achieved 3/3. The two control cases (email, VS Code) were intended as negatives but surfaced genuine gaps that were later addressed by real products.

## Usage

```bash
# Full pipeline: describe your market, get a gap report
python run_query.py "We're building a lightweight issue tracker for small dev teams. \
  Our main competitor is Jira."

# With date range (for backtesting)
python run_query.py "Privacy-focused web analytics competing with Google Analytics" \
  --date-start 2018-01-01 --date-end 2018-12-31

# Discovery only (Stage 0 — see what sources and competitors it finds)
python run_query.py "your market description" --discovery-only

# Rerun later stages on existing data
python run_query.py "your market description" --run-id <previous-run-id> --stages 4,5,6
```

Requires `EXA_API_KEY` and `OPENAI_API_KEY` in `.env`.

## Tech Stack

**Data collection:** Exa API, Arctic Shift, HN Algolia, Serper.dev, Apify
**NLP:** sentence-transformers, BERTopic, UMAP, HDBSCAN, VADER, bart-large-mnli, KeyBERT, spaCy
**LLM:** GPT-4o-mini Batch API via DSPy
**Storage:** ChromaDB (embedded)
**Language:** Python 3.11+, managed with uv

## Project Status

The engine (stages 1-6) is validated and working. Stage 0 (automated input construction) is built — a user can go from a plain-text description to a full gap report. The project was originally explored as a startup but is not being pursued commercially.

## Documentation

Detailed docs are in `latent-signals/`:
- [`01_strategy/`](latent-signals/01_strategy/) — Product brief, positioning, competitive landscape
- [`02_requirements/`](latent-signals/02_requirements/) — Scoring formula spec, design constraints
- [`03_architecture/`](latent-signals/03_architecture/) — Technical stack, data pipeline design
- [`04_decisions/`](latent-signals/04_decisions/) — Decision log with rationale for all major choices
- [`05_validation/`](latent-signals/05_validation/) — Backtest plan, results, and analysis
