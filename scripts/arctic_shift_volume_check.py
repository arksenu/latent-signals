"""
Check Arctic Shift post counts for discovered subreddits in 2018-09 to 2019-08.
Uses limit=100 to estimate volume.
"""

import httpx

API = "https://arctic-shift.photon-reddit.com/api/posts/search"
COMMENTS_API = "https://arctic-shift.photon-reddit.com/api/comments/search"

DATE_START = "2018-01-01"
DATE_END = "2018-12-31"

SUBREDDITS = [
    # Current config
    "analytics",
    "webdev",
    "privacy",
    "degoogle",
    "gdpr",
    # Exa-discovered
    "googleanalytics",
    "opensource",
    "selfhosted",
    "wordpress",
    "bigseo",
    "webflow",
]


def count_items(subreddit: str) -> dict:
    """Fetch up to 100 posts and 100 comments to estimate volume."""
    with httpx.Client(timeout=60.0) as client:
        post_resp = client.get(API, params={
            "subreddit": subreddit,
            "after": DATE_START,
            "before": DATE_END,
            "limit": 100,
        })
        post_data = post_resp.json()
        posts = post_data.get("data", [])

        comment_resp = client.get(COMMENTS_API, params={
            "subreddit": subreddit,
            "after": DATE_START,
            "before": DATE_END,
            "limit": 100,
        })
        comment_data = comment_resp.json()
        comments = comment_data.get("data", [])

    return {
        "posts": len(posts),
        "comments": len(comments),
        "posts_capped": len(posts) == 100,
        "comments_capped": len(comments) == 100,
    }


def main():
    print(f"Arctic Shift volume check: {DATE_START} to {DATE_END}")
    print(f"{'Subreddit':<25} {'Posts':>8} {'Comments':>10} {'Note'}")
    print("-" * 65)

    for sub in SUBREDDITS:
        try:
            c = count_items(sub)
            post_str = f"{c['posts']}+" if c['posts_capped'] else str(c['posts'])
            comm_str = f"{c['comments']}+" if c['comments_capped'] else str(c['comments'])
            total = c['posts'] + c['comments']
            note = ""
            if total == 0:
                note = "NO DATA"
            elif total < 50:
                note = "very low"
            elif c['posts_capped'] or c['comments_capped']:
                note = "GOOD (has more)"
            else:
                note = f"total ~{total}"
            print(f"r/{sub:<23} {post_str:>8} {comm_str:>10} {note}")
        except Exception as e:
            print(f"r/{sub:<23} ERROR: {e}")


if __name__ == "__main__":
    main()
