"""Apify collector for bulk Reddit scraping."""

from __future__ import annotations

from datetime import datetime

from apify_client import ApifyClient

from latent_signals.config import Config
from latent_signals.models import RawDocument
from latent_signals.stage1_collection.base import Collector
from latent_signals.utils.cost_tracker import CostTracker
from latent_signals.utils.logging import get_logger

log = get_logger("collector.apify")

# Apify Reddit Scraper actor ID
REDDIT_SCRAPER_ACTOR = "trudax/reddit-scraper"


class ApifyCollector(Collector):
    """Collect Reddit posts and comments via Apify Reddit scraper."""

    def __init__(self, config: Config, cost_tracker: CostTracker) -> None:
        super().__init__(config, cost_tracker)
        self.cfg = config.collection.apify
        self.date_range = config.collection.date_range
        self.client = ApifyClient(token=config.apify_api_token)

    @property
    def source_name(self) -> str:
        return "apify"

    def estimate_cost(self) -> float:
        return self.cfg.max_items * 0.002  # ~$2/1k results

    def collect(self) -> list[RawDocument]:
        if not self.cfg.enabled or not self.cfg.subreddits:
            return []

        docs: list[RawDocument] = []
        for subreddit in self.cfg.subreddits:
            results = self._scrape_subreddit(subreddit)
            docs.extend(results)
            log.info("apify.subreddit_complete", subreddit=subreddit, results=len(results))
            if len(docs) >= self.cfg.max_items:
                break

        docs = docs[: self.cfg.max_items]
        self.cost_tracker.add("apify", len(docs) * 0.002)
        log.info("apify.total", count=len(docs))
        return docs

    def _scrape_subreddit(self, subreddit: str) -> list[RawDocument]:
        """Scrape a single subreddit via Apify."""
        run_input = {
            "startUrls": [{"url": f"https://www.reddit.com/r/{subreddit}/"}],
            "maxItems": self.cfg.max_items // max(len(self.cfg.subreddits), 1),
            "sort": "hot",
            "includeComments": True,
        }

        run = self.client.actor(REDDIT_SCRAPER_ACTOR).call(run_input=run_input)
        dataset = self.client.dataset(run["defaultDatasetId"])

        docs: list[RawDocument] = []
        for item in dataset.iterate_items():
            doc = self._parse_item(item, subreddit)
            if doc:
                docs.append(doc)
        return docs

    def _parse_item(self, item: dict, subreddit: str) -> RawDocument | None:
        """Parse an Apify Reddit item into a RawDocument."""
        body = item.get("body") or item.get("selftext") or item.get("text") or ""
        title = item.get("title", "")
        if not body and not title:
            return None

        platform_id = item.get("id", "") or item.get("postId", "")
        created = item.get("createdAt") or item.get("created_utc")

        if isinstance(created, (int, float)):
            created_at = datetime.fromtimestamp(created)
        elif isinstance(created, str):
            try:
                created_at = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except ValueError:
                created_at = datetime.now()
        else:
            created_at = datetime.now()

        return RawDocument(
            id=f"apify_{platform_id}",
            source="reddit",
            platform_id=str(platform_id),
            title=title or None,
            body=f"{title}\n\n{body}".strip() if title else body,
            author=item.get("author") or item.get("username"),
            url=item.get("url") or item.get("permalink"),
            created_at=created_at,
            score=item.get("score") or item.get("upvotes"),
            subreddit=subreddit,
            metadata={"num_comments": item.get("numComments", 0)},
        )
