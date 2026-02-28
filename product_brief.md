# Latent Signals — Product Brief

**Status:** Active — v1 validated
**Last updated:** February 26, 2026

---

## What This Is

Latent Signals is a B2B competitive intelligence tool that detects underserved market opportunities by analyzing community sentiment from forums and review sites, mapping those signals against competitor feature coverage, and scoring gaps by a composite metric. It targets startups operating in fast-moving markets where historical data is scarce and conventional market research fails.

The core output is a scored, evidence-backed report that reduces market validation research from weeks of manual work to under 24 hours.

---

## Why This Exists

Startups making product-market fit and pivot decisions currently have no tool that combines community sentiment analysis with competitor feature mapping and systematic gap scoring. The options available each solve a fragment of the problem:

Enterprise CI platforms (Crayon, Klue, Kompyte) focus on sales enablement for established companies. Trend tools (Exploding Topics, Glimpse) detect demand inflection points but not supply-side gaps. Review aggregators (G2, Capterra) extract sentiment but don't map it to market opportunities. Feature comparison tools (GapsFinder, Compint) analyze product feature sets but ignore the voice of the user.

No existing tool answers the three questions a startup needs answered simultaneously: "What do people need that nobody provides?", "Who else is failing to address this?", and "Is demand for this growing?"

---

## Who It Serves

B2B startups that need to identify market gaps quickly in fluid environments before hard data exists. These are teams making investment-grade decisions about where to build, what to prioritize, and whether to pivot — in domains where structured market data doesn't yet exist or is too stale to be useful.

These customers have dedicated budgets for competitive intelligence and market research. They are not individual consumers casually exploring ideas. A B2C model was evaluated and rejected: consumer willingness to pay for market research tools is low, leading to high churn. B2B clients, by contrast, treat this as operational tooling with recurring need.

---

## Positioning

**Latent Signals operates in the space before hard data exists.**

The tool is explicitly designed for markets where trend lines haven't formed, where conventional analytics tools return insufficient data, and where the strongest signals are emotional — frustrations, workarounds, unmet needs expressed in community discussions rather than captured in structured databases.

This positioning boundary is also a scoping constraint: Latent Signals deprioritizes mature markets with abundant structured data. If Google Trends, Statista, or industry reports already provide clear demand signals for a given market, Latent Signals is not the right tool. Its value is highest precisely where those sources fail.

The core differentiator is acting on real-time emotional signals from the market. The unit of analysis is not search volume or feature checklists — it is the emotional intensity and frequency of unmet needs as expressed by actual users in unstructured community discussions.

---

## What It Produces

A Latent Signals report delivers a ranked index of 5-10 underserved market opportunities, each scored by a composite metric weighting six factors: unaddressedness (30%), mention frequency (25%), sentiment intensity (15%), competitive coverage gaps (15%), market size signals (10%), and trend direction (5%).

Each opportunity in the report includes an evidence package:

- Clustered user quotes from forums and review sites demonstrating the unmet need
- A competitive whitespace map showing which existing solutions fail to address the need and which partially address it
- Conversation trend data (forum mention frequency over a 90-day window) indicating whether the need is growing, stable, or declining

The report provides enough evidentiary depth to directly inform a go/no-go investment decision. It replaces weeks of manual market validation research — reading forums, mapping competitors, triangulating demand signals — with a pipeline that produces equivalent output in under 24 hours.

---

## Two Jobs to Be Done

Latent Signals serves two distinct use cases for startups:

**Job 1 — Discovery:** "I'm entering a market. What underserved problems exist?" The user defines a market category or domain. The tool scrapes community discussions, extracts and clusters unmet needs, maps them against competitor coverage, scores the gaps, and delivers a ranked opportunity index. This is the primary use case and the one implemented in v1.

**Job 2 — Expansion:** "I have an existing product. Where should I expand?" The user inputs their own product. The tool analyzes their users' sentiment alongside the broader market, identifies needs their product and competitors both fail to address, and surfaces expansion opportunities ranked by gap score. This is the higher-retention use case — it gives paying customers a reason to return monthly as the market evolves. Deferred to v2.

---

## V1 Scope

V1 is a working prototype that takes a market category as input and produces a scored gap report as output.

**V1 includes:**

- Single user flow: input-based discovery (user defines a market/domain, tool finds gaps)
- Data ingestion: Exa (semantic search) + Serper.dev (keyword search) + Apify (bulk Reddit scraping)
- NLP pipeline: BERTopic clustering + VADER sentiment + zero-shot classification + GPT-4o-mini batch extraction on sampled clusters
- Vector storage: ChromaDB (embedded, zero infrastructure)
- Gap detection: cosine similarity threshold logic in application layer
- Scoring: full composite gap_score formula implemented
- Output: static report (Markdown or PDF), not an interactive dashboard
- Orchestration: sequential Python script

**V1 explicitly defers:**

- Job 2 (existing product analysis / expansion opportunities)
- Qdrant migration and native Discovery API for dissimilarity search
- Prefect or any workflow orchestration
- Web UI or interactive dashboard
- SparkToro audience mapping integration
- Trend validation via Glimpse or Exploding Topics API (v1 uses forum mention frequency as trend proxy)
- Multi-tenant SaaS infrastructure and billing
- User authentication or access control

V1 is feature-complete and validated. The pipeline produces directionally correct, useful output — it retroactively identified the market gaps that Linear, Notion, and Plausible Analytics exploited, ranking the target signal in the top 3 in all cases. V1 answers the question: "Does this approach work at all?" The answer is yes.

---

## Key Design Constraints

These constraints are derived from strategic decisions and must be respected by the technical architecture:

**Emotional signal primacy.** Sentiment intensity is the core differentiator, not an afterthought. The scoring formula weights it at 15%, but the product positioning leads with emotional signals. If the pipeline ever reduces sentiment to a binary positive/negative classification, it has failed. Intensity, urgency, and frustration gradients must be preserved through the entire analysis chain.

**Recurring value, not one-shot reports.** The B2C model failed because of churn. The B2B model must deliver ongoing value — tracked gaps over time, alerts when new needs emerge or existing gaps close, trend evolution across reporting periods. V1 produces a snapshot. V2 must produce a time series. Design data storage and gap identity from v1 with this future in mind.

**Latency awareness.** V1 uses GPT-4o-mini's Batch API (asynchronous, not real-time). This is acceptable for a prototype producing reports. But if the tool evolves toward interactive use — a startup founder querying during a strategy session — the batch processing model breaks. The architecture should not create dependencies that prevent a future shift to synchronous inference (e.g., Groq or Cerebras for low-latency LLM calls).

**Cost ceiling.** Prototype cost must remain under $50/month. Production cost must remain under $500/month. The hybrid NLP pipeline (traditional NLP for heavy lifting, LLMs on sampled subsets only) exists specifically to meet this constraint. Any architectural change that pushes LLM calls to the full dataset rather than representative samples violates the cost model.

---

## Validation Results

The v1 pipeline has been validated through historical backtests. Five test cases were run across two rounds of fixes.

**Positive cases (3/3 PASS):**
- **Linear** (Sept 2018 - Aug 2019): Jira frustration gap detected at rank 2 (score 0.723). Linear launched Sept 2019 to address exactly this gap.
- **Notion** (Mar 2017 - Feb 2018): Evernote frustration gap detected at rank 3 (score 0.657). Notion v2.0 launched Mar 2018 to address this gap.
- **Plausible** (Jan 2018 - Dec 2018): Google Analytics privacy gap detected at ranks 1-2 (scores 0.776, 0.745). Plausible launched Jan 2019 to address this gap.

**Control cases (2 markets — real gaps surfaced):**
- **Email clients** (2018-2019): Pipeline surfaced genuine email frustration gaps that HEY, ProtonMail, and Tutanota subsequently addressed.
- **VS Code** (2019): Pipeline surfaced real setup/configuration friction (Python, C++, Java) that JetBrains already differentiates on.

**Known limitation:** The scoring formula treats all frustration equally regardless of opportunity magnitude. A gap that spawned a billion-dollar company (Linear vs Jira, 0.723) scores similarly to a gap fixable by an extension update (VS Code Python setup, 0.740). This limitation is deferred to v2 as the Opportunity Scale Classifier.

**Conclusion:** The pipeline reliably detects genuine market gaps from historical community data. The approach is validated. Total cost across all backtest runs: $0.21.

---

## What This Document Does Not Cover

- Technical architecture and stack decisions: see `03_architecture/technical_stack.md`
- Competitive landscape detail: see `01_strategy/competitive_landscape.md`
- Pricing model and go-to-market: see `06_business/` (not yet written)
- Decision rationale for key tradeoffs: see `04_decisions/decision_log.md`
