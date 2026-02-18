"""Hacker News Algolia API collector."""

from __future__ import annotations

import time
from datetime import datetime

import httpx

from latent_signals.config import Config
from latent_signals.models import RawDocument
from latent_signals.stage1_collection.base import Collector
from latent_signals.utils.cost_tracker import CostTracker
from latent_signals.utils.logging import get_logger

log = get_logger("collector.hackernews")

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


class HackerNewsCollector(Collector):
    """Collect posts and comments from Hacker News via Algolia API."""

    def __init__(self, config: Config, cost_tracker: CostTracker) -> None:
        super().__init__(config, cost_tracker)
        self.cfg = config.collection.hackernews
        self.date_range = config.collection.date_range
        self.market = config.pipeline.market_category

    @property
    def source_name(self) -> str:
        return "hackernews"

    def estimate_cost(self) -> float:
        return 0.0  # Free API

    def collect(self) -> list[RawDocument]:
        if not self.cfg.enabled:
            return []

        queries = self.cfg.queries or [self.market]
        # Resolve template vars
        queries = [q.replace("{market_category}", self.market) for q in queries]

        docs: list[RawDocument] = []
        for query in queries:
            results = self._search(query)
            docs.extend(results)
            log.info("hn.query_complete", query=query, results=len(results))

        # Deduplicate by platform_id
        seen: set[str] = set()
        unique: list[RawDocument] = []
        for doc in docs:
            if doc.platform_id not in seen:
                seen.add(doc.platform_id)
                unique.append(doc)

        unique = unique[: self.cfg.max_items]
        log.info("hackernews.total", count=len(unique))
        return unique

    def _search(self, query: str) -> list[RawDocument]:
        """Search HN Algolia API with pagination."""
        start_ts = int(datetime.strptime(self.date_range["start"], "%Y-%m-%d").timestamp())
        end_ts = int(datetime.strptime(self.date_range["end"], "%Y-%m-%d").timestamp())

        docs: list[RawDocument] = []
        page = 0
        with httpx.Client(timeout=30.0) as client:
            while True:
                params = {
                    "query": query,
                    "tags": "(story,comment)",
                    "numericFilters": f"created_at_i>{start_ts},created_at_i<{end_ts}",
                    "hitsPerPage": 100,
                    "page": page,
                }
                resp = client.get(HN_SEARCH_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

                hits = data.get("hits", [])
                if not hits:
                    break

                for hit in hits:
                    doc = self._parse_hit(hit)
                    if doc:
                        docs.append(doc)

                page += 1
                if page >= data.get("nbPages", 0):
                    break
                if len(docs) >= self.cfg.max_items:
                    break

                time.sleep(0.2)  # Rate limiting

        return docs

    def _parse_hit(self, hit: dict) -> RawDocument | None:
        """Parse an Algolia hit into a RawDocument."""
        text = hit.get("comment_text") or hit.get("story_text") or ""
        title = hit.get("title", "")
        if not text and not title:
            return None

        object_id = hit.get("objectID", "")
        created_at_i = hit.get("created_at_i", 0)
        is_story = "_type" in hit and hit["_type"] == "story"

        return RawDocument(
            id=f"hn_{object_id}",
            source="hackernews",
            platform_id=object_id,
            title=title if is_story else None,
            body=f"{title}\n\n{text}".strip() if title and is_story else text,
            author=hit.get("author"),
            url=hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}",
            created_at=datetime.fromtimestamp(created_at_i) if created_at_i else datetime.now(),
            score=hit.get("points"),
            metadata={"num_comments": hit.get("num_comments", 0)},
        )
