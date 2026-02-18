"""Serper.dev collector for keyword search."""

from __future__ import annotations

from datetime import datetime

import httpx

from latent_signals.config import Config
from latent_signals.models import RawDocument
from latent_signals.stage1_collection.base import Collector
from latent_signals.utils.cost_tracker import CostTracker
from latent_signals.utils.logging import get_logger

log = get_logger("collector.serper")

SERPER_URL = "https://google.serper.dev/search"


class SerperCollector(Collector):
    """Collect documents via Serper.dev keyword search."""

    def __init__(self, config: Config, cost_tracker: CostTracker) -> None:
        super().__init__(config, cost_tracker)
        self.cfg = config.collection.serper
        self.market = config.pipeline.market_category
        self.api_key = config.serper_api_key
        self.date_range = config.collection.date_range

    @property
    def source_name(self) -> str:
        return "serper"

    def estimate_cost(self) -> float:
        num_queries = len(self.cfg.queries) or 2
        return num_queries * 0.001  # ~$1/1k queries

    def collect(self) -> list[RawDocument]:
        if not self.cfg.enabled:
            return []

        queries = self.cfg.queries or [
            f"{self.market} frustrating site:reddit.com",
            f"hate {self.market} tool site:reddit.com",
        ]
        queries = [q.replace("{market_category}", self.market) for q in queries]

        docs: list[RawDocument] = []
        for query in queries:
            results = self._search(query)
            docs.extend(results)
            log.info("serper.query_complete", query=query, results=len(results))

        self.cost_tracker.add("serper", len(queries) * 0.001)

        # Deduplicate by URL
        seen: set[str] = set()
        unique: list[RawDocument] = []
        for doc in docs:
            key = doc.url or doc.id
            if key not in seen:
                seen.add(key)
                unique.append(doc)

        log.info("serper.total", count=len(unique))
        return unique

    def _search(self, query: str) -> list[RawDocument]:
        """Run a single Serper search query."""
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": self.cfg.max_results_per_query}

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(SERPER_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        docs: list[RawDocument] = []
        for item in data.get("organic", []):
            snippet = item.get("snippet", "")
            title = item.get("title", "")
            if not snippet:
                continue

            docs.append(
                RawDocument(
                    id=f"serper_{hash(item.get('link', ''))}",
                    source="web",
                    platform_id=item.get("link", ""),
                    title=title,
                    body=snippet,
                    url=item.get("link"),
                    created_at=datetime.now(),
                    metadata={"query": query, "position": item.get("position")},
                )
            )
        return docs
