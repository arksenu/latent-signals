"""Arctic Shift collector for historical Reddit data (backtest use)."""
from __future__ import annotations

from datetime import datetime

import httpx

from latent_signals.config import Config
from latent_signals.models import RawDocument
from latent_signals.stage1_collection.base import Collector
from latent_signals.utils.cost_tracker import CostTracker
from latent_signals.utils.logging import get_logger

log = get_logger("collector.arctic_shift")

ARCTIC_SHIFT_API = "https://arctic-shift.photon-reddit.com/api/posts/search"
ARCTIC_SHIFT_COMMENTS_API = "https://arctic-shift.photon-reddit.com/api/comments/search"


class ArcticShiftCollector(Collector):
    """Collect historical Reddit posts and comments via Arctic Shift API."""

    def __init__(self, config: Config, cost_tracker: CostTracker) -> None:
        super().__init__(config, cost_tracker)
        self.cfg = config.collection.arctic_shift
        self.date_range = config.collection.date_range
        self.market = config.pipeline.market_category

    @property
    def source_name(self) -> str:
        return "arctic_shift"

    def estimate_cost(self) -> float:
        return 0.0  # Free API

    def collect(self) -> list[RawDocument]:
        if not self.cfg.enabled:
            return []

        # Distribute max_items evenly across subreddits so no single
        # subreddit monopolises the corpus (the prior version let
        # r/projectmanagement fill the entire quota).
        n_subs = len(self.cfg.subreddits)
        per_sub = self.cfg.max_items // max(n_subs, 1)

        docs: list[RawDocument] = []
        for subreddit in self.cfg.subreddits:
            posts = self._fetch_posts(subreddit, max_items=per_sub)
            comments = self._fetch_comments(subreddit, max_items=per_sub)
            sub_docs = (posts + comments)[:per_sub]
            docs.extend(sub_docs)
            log.info(
                "subreddit.collected",
                subreddit=subreddit,
                posts=len(posts),
                comments=len(comments),
                kept=len(sub_docs),
            )

        docs = docs[: self.cfg.max_items]
        log.info("arctic_shift.total", count=len(docs))
        return docs

    def _fetch_posts(self, subreddit: str, max_items: int | None = None) -> list[RawDocument]:
        """Fetch posts from a subreddit within the date range."""
        params = {
            "subreddit": subreddit,
            "after": self.date_range["start"],
            "before": self.date_range["end"],
            "limit": 100,
        }
        return self._paginate(ARCTIC_SHIFT_API, params, "post", subreddit, max_items=max_items)

    def _fetch_comments(self, subreddit: str, max_items: int | None = None) -> list[RawDocument]:
        """Fetch comments from a subreddit within the date range."""
        params = {
            "subreddit": subreddit,
            "after": self.date_range["start"],
            "before": self.date_range["end"],
            "limit": 100,
        }
        return self._paginate(ARCTIC_SHIFT_COMMENTS_API, params, "comment", subreddit, max_items=max_items)

    def _paginate(
        self, base_url: str, params: dict, doc_type: str, subreddit: str,
        max_items: int | None = None,
    ) -> list[RawDocument]:
        """Paginate through Arctic Shift API results."""
        cap = max_items or self.cfg.max_items
        docs: list[RawDocument] = []
        with httpx.Client(timeout=60.0) as client:
            while True:
                resp = client.get(base_url, params=params)
                resp.raise_for_status()
                data = resp.json().get("data", [])
                if not data:
                    break

                for item in data:
                    doc = self._parse_item(item, doc_type, subreddit)
                    if doc:
                        docs.append(doc)

                if len(data) < params.get("limit", 100):
                    break

                # Use the last item's created_utc for pagination
                last_created = data[-1].get("created_utc")
                if last_created:
                    params["before"] = str(last_created)
                else:
                    break

                if len(docs) >= cap:
                    break

        return docs

    def _parse_item(
        self, item: dict, doc_type: str, subreddit: str
    ) -> RawDocument | None:
        """Parse an Arctic Shift API item into a RawDocument."""
        body = item.get("body") or item.get("selftext") or ""
        title = item.get("title", "")
        if not body and not title:
            return None

        platform_id = item.get("id", "")
        created_utc = item.get("created_utc", 0)

        return RawDocument(
            id=f"arctic_{platform_id}",
            source="reddit",
            platform_id=platform_id,
            title=title if doc_type == "post" else None,
            body=f"{title}\n\n{body}".strip() if title and doc_type == "post" else body,
            author=item.get("author"),
            url=item.get("permalink", ""),
            created_at=datetime.fromtimestamp(created_utc) if created_utc else datetime.now(),
            score=item.get("score"),
            subreddit=subreddit,
            metadata={"type": doc_type, "num_comments": item.get("num_comments", 0)},
        )
