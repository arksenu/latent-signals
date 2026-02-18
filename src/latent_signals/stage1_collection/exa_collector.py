"""Exa API collector for semantic search."""

from __future__ import annotations

from datetime import datetime

from exa_py import Exa

from latent_signals.config import Config
from latent_signals.models import RawDocument
from latent_signals.stage1_collection.base import Collector
from latent_signals.utils.cost_tracker import CostTracker
from latent_signals.utils.logging import get_logger

log = get_logger("collector.exa")


class ExaCollector(Collector):
    """Collect documents via Exa semantic search API."""

    def __init__(self, config: Config, cost_tracker: CostTracker) -> None:
        super().__init__(config, cost_tracker)
        self.cfg = config.collection.exa
        self.date_range = config.collection.date_range
        self.market = config.pipeline.market_category
        self.client = Exa(api_key=config.exa_api_key)

    @property
    def source_name(self) -> str:
        return "exa"

    def estimate_cost(self) -> float:
        num_queries = len(self.cfg.queries) or 3
        return num_queries * self.cfg.max_results_per_query * 0.005  # ~$5/1k

    def collect(self) -> list[RawDocument]:
        if not self.cfg.enabled:
            return []

        queries = self.cfg.queries or [
            f"people frustrated with {self.market} tools",
            f"looking for alternative to {self.market}",
            f"{self.market} software complaints",
        ]
        queries = [q.replace("{market_category}", self.market) for q in queries]

        docs: list[RawDocument] = []
        for query in queries:
            results = self._search(query)
            docs.extend(results)
            log.info("exa.query_complete", query=query, results=len(results))

        # Track cost
        self.cost_tracker.add("exa", len(docs) * 0.005)

        # Deduplicate by URL
        seen: set[str] = set()
        unique: list[RawDocument] = []
        for doc in docs:
            key = doc.url or doc.id
            if key not in seen:
                seen.add(key)
                unique.append(doc)

        log.info("exa.total", count=len(unique))
        return unique

    def _search(self, query: str) -> list[RawDocument]:
        """Run a single Exa semantic search query."""
        response = self.client.search_and_contents(
            query=query,
            num_results=self.cfg.max_results_per_query,
            include_domains=self.cfg.domains if self.cfg.domains else None,
            start_published_date=self.date_range["start"],
            end_published_date=self.date_range["end"],
            text=True,
        )

        docs: list[RawDocument] = []
        for result in response.results:
            text = result.text or ""
            if not text:
                continue
            docs.append(
                RawDocument(
                    id=f"exa_{result.id}",
                    source="web",
                    platform_id=result.id,
                    title=result.title,
                    body=text,
                    url=result.url,
                    created_at=datetime.fromisoformat(result.published_date)
                    if result.published_date
                    else datetime.now(),
                    metadata={"query": query},
                )
            )
        return docs
