# Latent Signals: Historical Backtest Plan v2

**Status:** Final
**Last updated:** February 16, 2026

---

This document specifies the historical backtest plan for validating the engine Latent Signals pipeline. The objective is to prove that the pipeline can retroactively identify validated market gaps by analyzing public community sentiment from the 6-12 month period preceding a successful product launch. This backtest is the definitive milestone for the engine; its success is a prerequisite for any v2 development.

## 1. Test Case Selection

Four test cases are selected: three positive cases where a known market gap was successfully exploited, and one negative control where no major disruption occurred during the test window.

The criteria for positive case selection were, in order of importance: the verifiable existence of strong, public, pre-launch community frustration with incumbents; the clarity and specificity of the market gap; and the confirmed availability of historical data through archives.

The chosen products -- **Linear**, **Notion**, and **Plausible Analytics** -- represent ideal scenarios where significant, vocal frustration was demonstrably present in public forums before a new solution emerged to directly address it.

The negative control -- **Email Clients (2018-2019)** -- represents a stable market where no major disruptive product launched during the test window. HEY launched in June 2020, well after the observation period ends. The pipeline should not produce any high-scoring gaps for this case.

### Positive Cases

| Product | Market Entered | Gap Filled | Approx. Launch | Rationale for Selection |
| :--- | :--- | :--- | :--- | :--- |
| **Linear** | Project Management | Addressed the pervasive frustration with the slowness, complexity, and developer-hostile user experience of Jira. | Sept 2019 | **Excellent Signal.** Pre-launch sentiment was strong and specific. A Hacker News thread from August 2019, "Ask HN: Looking for an Alternative to Jira," gathered 78 comments detailing user pain points. [1] This provides a concentrated, high-signal dataset to test the pipeline's core hypothesis. |
| **Notion** | All-in-One Workspace | Filled the gap for a flexible, unified workspace, disrupting the fragmented and rigid experience of using separate tools like Evernote and Confluence. | Mar 2018 | **Excellent Signal.** The primary catalyst was Evernote's deeply unpopular June 2016 price hike and introduction of a two-device limit for its free plan. [3] This event triggered years of sustained, public complaints about bugs, slowness, and high cost, creating a clear and persistent market demand for a superior alternative long before Notion's v2.0 launch. |
| **Plausible Analytics** | Web Analytics | Provided a simple, lightweight, and privacy-centric alternative to the perceived complexity and data privacy issues of Google Analytics. | Jan 2019 | **Strong Signal.** The EU's General Data Protection Regulation (GDPR), which became enforceable in May 2018, was a structural market shift that created immediate and widespread demand for privacy-first tooling. [5] This provides a test case driven by a specific external event, allowing us to measure the pipeline's ability to detect sentiment shifts tied to regulatory changes. |

### Negative Control

| Market | Observation Window | Rationale |
| :--- | :--- | :--- |
| **Email Clients** | Jan 2018 - Dec 2019 | No major disruptive email product launched in this window. HEY (Basecamp) launched June 2020, well after the observation period ends. Gmail, Outlook, and Spark dominated without significant challenger activity. If the pipeline produces a high-scoring gap (top 3, above the calibrated threshold), it indicates a false positive problem. Subreddits: `r/email`, `r/gmail`, `r/productivity`, `r/software`. |

---

## 2. Data Requirements Per Test Case

Data will be collected using the technical stack defined in `Building a Market Gap Finder.md`. The primary data sources are Reddit archives (via **Arctic Shift**) and the Hacker News Algolia API.

**Critical distinction:** The competitor feature set and the user complaint corpus are separate collections with fundamentally different content. The competitor feature set describes what incumbents actually offered -- their real product capabilities. The user complaint corpus contains the pain points expressed in community discussions. The gap emerges when user needs have low cosine similarity to any actual product feature, meaning the incumbent's offering does not address what users want. Encoding complaints as both the "need" and the "feature" vectors collapses the comparison and defeats the detection logic.

### Step 0: Data Availability Audit

Before executing any pipeline code, verify that sufficient historical data exists for each test case. For every subreddit and date range below, pull monthly post and comment counts from Arctic Shift dumps. Each test case requires a minimum of 5,000 total posts/comments across all listed subreddits for the specified date range. If a test case falls below this threshold, substitute alternative subreddits or extend the date range before proceeding. Do not run the pipeline on insufficient data.

### Data Specifications

| Test Case | Data Sources | Data Date Range | Expected Data Volume |
| :--- | :--- | :--- | :--- |
| **Linear** | `r/projectmanagement`, `r/agile`, `r/devops`, `r/programming`, Hacker News | Sept 2018 - Aug 2019 | 10,000 - 20,000 posts/comments |
| **Notion** | `r/evernote`, `r/productivity`, `r/confluence`, `r/selfhosted`, Hacker News | Mar 2017 - Feb 2018 | 15,000 - 25,000 posts/comments |
| **Plausible** | `r/analytics`, `r/webdev`, `r/privacy`, `r/degoogle`, `r/gdpr`, Hacker News | Jan 2018 - Dec 2018 | 20,000 - 30,000 posts/comments |
| **Email (control)** | `r/email`, `r/gmail`, `r/productivity`, `r/software`, Hacker News | Jan 2018 - Dec 2019 | 10,000 - 20,000 posts/comments |

### Competitor Feature Sets (Actual Product Capabilities)

These vectors represent what incumbents actually provided, not user complaints about them. Each feature is embedded as a standalone description of a real product capability.

**Linear test case -- Jira features (circa 2019):**
- Customizable Scrum and Kanban board workflows
- Configurable issue types, fields, and workflow states
- Enterprise permission schemes and role-based access control
- Marketplace plugin and add-on ecosystem
- Advanced JQL query language for issue search
- Sprint planning, backlog grooming, and velocity tracking
- Integration with Bitbucket, GitHub, and CI/CD pipelines
- Cross-project epics and portfolio-level tracking

**Notion test case -- Evernote features (circa 2017):**
- Rich text note editor with formatting and attachments
- Optical character recognition for scanned documents
- Web clipper browser extension
- Cross-device sync (limited to 2 devices on free plan)
- Notebook and tag organization system
- Shared notebooks for team collaboration
- Offline access to saved notes
- Premium search across PDFs and Office documents

**Plausible test case -- Google Analytics features (circa 2018):**
- Pageview and session tracking with JavaScript snippet
- Real-time visitor dashboard
- Audience demographic and interest profiling
- Acquisition channel and campaign attribution
- Behavior flow and site content reports
- Conversion goals and e-commerce tracking
- Custom dimensions, segments, and calculated metrics
- Integration with Google Ads, Search Console, and Tag Manager

**Email control case -- Gmail features (circa 2018):**
- Threaded conversation view
- Labels, filters, and automated sorting rules
- 15 GB free storage shared with Google Drive
- Smart Compose and Smart Reply suggestions
- Priority Inbox and importance markers
- Full-text search with advanced operators
- Native integration with Google Calendar and Meet
- Spam and phishing detection

---

## 3. Success Criteria

### Threshold Calibration

The gap score threshold is not set in advance. The Linear test case serves as the calibration run. After executing the full pipeline on the Linear dataset, examine the complete distribution of gap scores across all detected opportunities. Set the success threshold at the 90th percentile of that distribution. This percentile threshold then applies unchanged to Notion, Plausible, and the Email control case.

This avoids the problem of setting an arbitrary absolute threshold (e.g., 0.75) before knowing what the scoring formula actually produces on real data.

### Positive Case Criteria

- **Rank:** The historically-validated market gap must appear within the **top 3** ranked opportunities in the final report.
- **Gap Score:** The identified gap must score at or above the calibrated threshold (90th percentile from the Linear calibration run).
- **Content Match:** Evaluation is based on the content of the representative documents within the identified cluster, not on the auto-generated topic label. If the cluster's representative posts describe the known pain point (e.g., posts complaining about Jira's speed, bloat, and developer-hostile UX), the detection is valid regardless of whether BERTopic labels it "Jira performance" or "project management frustration" or something generic. A human reviewer examines the top 20 representative documents per flagged cluster to make this judgment.
- **Pass Threshold:** At least two of the three positive test cases must produce a valid detection (top 3 rank, above threshold, content match confirmed) for the engine backtest to pass.

### Negative Control Criteria

- The Email control case must **not** produce any opportunity in the top 3 that scores above the calibrated threshold. If it does, this indicates an unacceptable false positive rate, and the scoring formula or upstream pipeline requires recalibration before retesting.

---

## 4. Failure Analysis Framework

In the event of a failed backtest, a sequential diagnostic will be executed to isolate the point of failure. Each step must be passed before proceeding to the next.

| Step | Diagnostic Target | Test Procedure |
| :--- | :--- | :--- |
| **0** | **Data Availability** | Verify that the raw dataset meets the minimum volume threshold (5,000 posts/comments). If not, the test case cannot be evaluated. Expand subreddit list or date range and re-collect. |
| **1** | **Data Quality & Ingestion** | Manually review a random sample of 200 posts from the raw scraped data. Verify that the content is relevant and that scraping artifacts are minimal. Run keyword searches for domain-specific terms (e.g., "slow", "buggy", "hate", "frustrating" for Linear; "privacy", "GDPR", "cookie" for Plausible). A low hit count suggests the initial data pull was flawed or too broad. |
| **2** | **Clustering & Topic Modeling** | Analyze the BERTopic output. Visualize the topic clusters and review the top 10 most frequent topics. If the dominant topics are generic (e.g., "general discussion," "questions"), the model is failing to capture specific pain points. Re-run the clustering with a more powerful embedding model (`BAAI/bge-base-en-v1.5`) and experiment with BERTopic's `KeyBERTInspired` representation to improve topic coherence. |
| **3** | **Scoring Weights & Formula** | Create a synthetic "perfect gap" document (e.g., a fabricated Reddit post: "I despise how slow and bloated Jira is. I would immediately pay for a faster, simpler alternative."). Process this single document through the scoring pipeline. It must receive an `unaddressedness` score > 0.9 and a `sentiment_intensity` score > 0.8. If not, the scoring logic or normalization is broken. |
| **4** | **Gap Detection Logic** | For a known gap cluster, extract the embeddings of the 5 most representative documents. Query the competitor feature embedding collection with these vectors. The returned `max_similarity` score for each should be low (< 0.5), confirming that the user complaints are semantically distant from the actual product features offered by the incumbent. If the similarity is high, it indicates either the embedding model cannot differentiate user pain language from product capability descriptions, or the competitor feature set is incorrectly defined. Review the competitor feature vectors and verify they describe actual capabilities, not user complaints. |
| **5** | **Negative Control Check** | If positive cases pass but the negative control also produces high-scoring "gaps," the issue is likely in normalization or the scoring formula's treatment of generic complaints. Examine the top-scoring clusters from the Email control case. If they reflect real but minor frustrations (e.g., "Gmail's interface is cluttered"), tighten the `unaddressedness` weight or raise the frequency threshold to filter low-signal noise. |

---

## 5. Execution Plan

The backtest will be run via a sequential Python script (`run_pipeline.py`). All four test cases use identical embedding models, hyperparameters, and scoring weights. The only inputs that vary per case are the dataset, the competitor feature set, and the subreddit/date configuration. This ensures the backtest validates one pipeline, not four different configurations.

### Phase 1: Data Availability Audit

For each test case, query Arctic Shift monthly dumps and the Hacker News Algolia API. Record post/comment counts per subreddit per month. Confirm each test case meets the 5,000-post minimum. Document any substitutions or date range adjustments.

### Phase 2: Data Collection

Use Apify and its Reddit scraper actor to pull historical data based on the defined subreddits and date ranges. For Hacker News, use the official Algolia API with pagination (respect rate limits; budget for delays in runtime estimates).

Note: Verify the Apify actor ID and CLI syntax against current Apify documentation before execution. The examples below are illustrative; exact actor IDs and parameter formats may differ.

**Example (Linear):**
```bash
apify call <reddit-scraper-actor-id> --input='{"subreddits": ["projectmanagement", "agile", "devops", "programming"], "postsFrom": "2018-09-01", "postsTo": "2019-08-31", "maxItems": 10000}'
```

### Phase 3: Pipeline Execution

Execute `run_pipeline.py` for each test case, providing the path to the collected data and the corresponding competitor feature set as arguments.

The script orchestrates the full pipeline: embedding, clustering, sentiment analysis, scoring, and ranking.

Run the **Linear** case first. Use its output to calibrate the gap score threshold (90th percentile). Then run Notion, Plausible, and Email with the calibrated threshold locked.

Expected runtime: 2-4 hours per test case (excluding Hacker News API pagination delays).

### Phase 4: Result Evaluation & Reporting

The script generates a Markdown report (`report_[test_case].md`) with the ranked list of market gaps, including the full gap score distribution.

For each positive case, a human reviewer examines the top 20 representative documents in the top-3 clusters to confirm content match against the known gap.

For the negative control, verify that no cluster in the top 3 exceeds the calibrated threshold.

A final summary report synthesizes the results of all four cases and issues a definitive pass/fail judgment on the engine pipeline.

---

## References

[1] "Ask HN: Looking for an Alternative to Jira." Hacker News, August 27, 2019. https://news.ycombinator.com/item?id=20807328

[2] "Linear: Designing for the Developers." Sequoia Capital, January 5, 2023. https://sequoiacap.com/article/linear-spotlight/

[3] "Evernote users vent anger after it cuts free tier and raises prices." The Guardian, June 30, 2016. https://www.theguardian.com/technology/2016/jun/30/evernote-users-vent-anger-after-it-cuts-free-tier-and-raises-prices

[4] "Notion 2.0." Product Hunt, March 2018. https://www.producthunt.com/products/notion

[5] "Plausible Analytics." Indie Hackers, January 24, 2019. https://www.indiehackers.com/product/plausible-insights

[6] "Thousands of Reddit Users Are Trying to Delete Google From Their Lives..." Business Insider, March 23, 2019. https://www.businessinsider.com/profile-reddit-de-google-community-2019-3