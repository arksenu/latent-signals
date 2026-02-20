"""
Check Arctic Shift post counts for discovered subreddits in 2018-09 to 2019-08.
Verifies which subreddits had sufficient volume during the backtest period.
"""

import httpx

API = "https://arctic-shift.photon-reddit.com/api/posts/search"
COMMENTS_API = "https://arctic-shift.photon-reddit.com/api/comments/search"

DATE_START = "2018-09-01"
DATE_END = "2019-08-31"

# Subreddits from Exa discovery (ranked by relevance)
SUBREDDITS = [
    # Currently in config
    "jira",
    "agile",
    "devops",
    "programming",
    "webdev",              # NOT surfaced by Exa
    "softwareengineering", # NOT surfaced by Exa
    # Discovered by Exa (not in config)
    "projectmanagement",
    "atlassian",
    "experienceddevs",
    "sysadmin",
    "cscareerquestions",
    "scrum",
    "softwaredevelopment",
    "productivity",
    "saas",
]


def count_items(subreddit: str) -> dict:
    """Get approximate post and comment counts for a subreddit in date range."""
    with httpx.Client(timeout=30.0) as client:
        # Posts count - fetch first page to see total
        post_resp = client.get(API, params={
            "subreddit": subreddit,
            "after": DATE_START,
            "before": DATE_END,
            "limit": 1,
        })
        post_data = post_resp.json()
        post_count = post_data.get("metadata", {}).get("total_results", len(post_data.get("data", [])))

        # Comments count
        comment_resp = client.get(COMMENTS_API, params={
            "subreddit": subreddit,
            "after": DATE_START,
            "before": DATE_END,
            "limit": 1,
        })
        comment_data = comment_resp.json()
        comment_count = comment_data.get("metadata", {}).get("total_results", len(comment_data.get("data", [])))

    return {"posts": post_count, "comments": comment_count, "total": post_count + comment_count}


def main():
    print(f"Arctic Shift volume check: {DATE_START} to {DATE_END}")
    print(f"{'Subreddit':<25} {'Posts':>8} {'Comments':>10} {'Total':>10} {'Status'}")
    print("-" * 75)

    for sub in SUBREDDITS:
        try:
            counts = count_items(sub)
            status = ""
            if counts["total"] == 0:
                status = "EMPTY - did not exist or no data"
            elif counts["total"] < 100:
                status = "LOW volume"
            elif counts["total"] < 1000:
                status = "moderate"
            else:
                status = "GOOD"
            print(f"r/{sub:<23} {counts['posts']:>8} {counts['comments']:>10} {counts['total']:>10} {status}")
        except Exception as e:
            print(f"r/{sub:<23} ERROR: {e}")


if __name__ == "__main__":
    main()
