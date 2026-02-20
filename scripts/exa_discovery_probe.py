"""
Exa Discovery Probe: find which communities discuss project management frustration.

This is a one-time probe to generate defensible backtest config inputs
instead of hand-guessing subreddits and market anchors.
"""

import json
import os
import re
from collections import Counter

from dotenv import load_dotenv
from exa_py import Exa

load_dotenv()

client = Exa(api_key=os.environ["EXA_API_KEY"])

# Queries that simulate what a real user would ask the discovery layer
QUERIES = [
    "people frustrated with project management tools",
    "looking for alternative to Jira",
    "project management software complaints",
    "Jira is too slow and complicated",
    "best Jira alternatives for developers",
    "why developers hate Jira",
    "project management tool bloated",
]

NUM_RESULTS = 20  # per query


def extract_subreddits(url: str) -> str | None:
    """Extract subreddit name from a reddit URL."""
    m = re.search(r"reddit\.com/r/(\w+)", url)
    return m.group(1).lower() if m else None


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    m = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1) if m else url


def main():
    all_results = []
    subreddit_counts = Counter()
    domain_counts = Counter()

    for query in QUERIES:
        print(f"\n--- Query: {query} ---")
        try:
            response = client.search_and_contents(
                query=query,
                num_results=NUM_RESULTS,
                text=True,
            )
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        for result in response.results:
            url = result.url
            title = result.title or "(no title)"
            domain = extract_domain(url)
            domain_counts[domain] += 1

            subreddit = extract_subreddits(url)
            if subreddit:
                subreddit_counts[subreddit] += 1

            snippet = (result.text or "")[:200].replace("\n", " ")
            all_results.append({
                "query": query,
                "title": title,
                "url": url,
                "domain": domain,
                "subreddit": subreddit,
                "snippet": snippet,
            })
            print(f"  [{domain}] {title[:80]}")
            if subreddit:
                print(f"    -> r/{subreddit}")

    print("\n" + "=" * 60)
    print("SUBREDDIT FREQUENCY (from Exa results):")
    print("=" * 60)
    for sub, count in subreddit_counts.most_common(30):
        print(f"  r/{sub}: {count}")

    print(f"\nTOP DOMAINS:")
    for domain, count in domain_counts.most_common(20):
        print(f"  {domain}: {count}")

    print(f"\nTotal results: {len(all_results)}")
    print(f"Reddit results: {sum(1 for r in all_results if r['subreddit'])}")
    print(f"Unique subreddits: {len(subreddit_counts)}")

    # Save full results for inspection
    out_path = "data/discovery_probe_results.json"
    os.makedirs("data", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({
            "queries": QUERIES,
            "subreddit_counts": dict(subreddit_counts.most_common()),
            "domain_counts": dict(domain_counts.most_common()),
            "results": all_results,
        }, f, indent=2)
    print(f"\nFull results saved to {out_path}")


if __name__ == "__main__":
    main()
