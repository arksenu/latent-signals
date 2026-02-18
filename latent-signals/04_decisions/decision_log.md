# Decision Log

Running log of key architectural and strategic decisions. Each entry records context, the decision made, alternatives considered, and current status.

---

## 2026-02-15 — B2B model over B2C

**Context**: Initial exploration considered both B2C (individual founders/indie hackers) and B2B (startup teams with budgets) as target markets.

**Decision**: B2B only. B2C was rejected.

**Rationale**: Consumer willingness to pay for market research tools is low, leading to high churn. B2B clients have dedicated competitive intelligence budgets and treat this as operational tooling with recurring need. The B2B model also supports higher price points that justify the pipeline's compute costs.

**Alternatives rejected**: B2C freemium, B2C with usage-based pricing. Both rejected due to churn dynamics and insufficient revenue per user to cover API costs.

**Status**: Active.

---

## 2026-02-15 — Sentiment analysis as primary methodology

**Context**: Four market research methodologies were evaluated for the core analytical approach: Trend Analysis, White Space Mapping, Conjoint Analysis, and Sentiment Analysis.

**Decision**: Sentiment analysis is the primary methodology.

**Rationale**: The target users (startups in fast-moving markets) operate in environments where historical data is scarce and structured datasets don't exist. Trend Analysis requires historical data to detect patterns. White Space Mapping requires structured feature datasets. Conjoint Analysis requires survey infrastructure and has the highest barrier to entry. Sentiment analysis detects unmet emotional needs from unstructured community discussions before they become visible trends — matching the "before hard data exists" positioning.

**Nuance**: The technical implementation actually combines sentiment analysis with computational white space mapping (finding sparse regions in embedding space). The meeting summary created a false binary between the two methodologies. The actual architecture uses sentiment analysis for signal extraction and white space mapping techniques (via vector similarity) for gap detection. These are complementary, not competing.

**Alternatives rejected**: Trend Analysis (misses emerging markets), White Space Mapping alone (requires structured data we don't have), Conjoint Analysis (too high a barrier for startup context).

**Status**: Active.

---

## 2026-02-15 — Hybrid NLP pipeline over pure-LLM or pure-traditional

**Context**: The NLP pipeline design needed to balance extraction quality against cost. Three approaches were evaluated.

**Decision**: Hybrid pipeline — traditional NLP for heavy lifting, LLMs surgically on sampled subsets only.

**Rationale**: Processing 10,000+ posts through GPT-4o costs ~$7.50 per run and takes hours. Pure traditional NLP (TF-IDF, VADER) is free but misses contextual nuance. The hybrid approach uses BERTopic for clustering, VADER for fast sentiment, zero-shot classification for categorization, and GPT-4o-mini Batch API only on 50-100 representative posts per cluster. Total LLM cost: ~$0.50 per 10,000 posts. This meets the $50/month prototype cost ceiling.

**Alternatives rejected**: Full LLM processing (10-15x more expensive, violates cost ceiling), pure traditional NLP (insufficient extraction quality for nuanced pain points and feature requests).

**Status**: Active.

---

## 2026-02-15 — Deferred custom LLM on inference hardware to post-prototype

**Context**: The initial strategy session proposed deploying smaller, fine-tuned LLMs on fast inference chips (Groq, Cerebras) for denoising at low latency.

**Decision**: Defer this to post-prototype. V1 uses GPT-4o-mini Batch API.

**Rationale**: Custom LLM deployment on inference hardware is premature before validating that the pipeline produces useful output at all. The hybrid NLP approach achieves the same cost goals without requiring model fine-tuning or infrastructure management. Groq/Cerebras become relevant only if the tool evolves toward real-time interactive use (a startup founder querying during a strategy session), which is not a v1 requirement.

**Future trigger**: If v2 requires synchronous inference under 2 seconds for interactive queries, revisit Groq/Cerebras deployment. The architecture should not create dependencies that prevent this shift.

**Alternatives rejected**: Immediate Groq deployment (over-investment at prototype stage), local model hosting (operational overhead not justified for MVP).

**Status**: Active. Revisit when interactive use case is prioritized.
