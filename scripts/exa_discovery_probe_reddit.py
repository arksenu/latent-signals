"""
Exa Discovery Probe (Reddit-only): find which subreddits discuss PM frustration.
Also checks HN volume for the same queries.
"""

import json
import os
import re
from collections import Counter

from dotenv import load_dotenv
from exa_py import Exa

load_dotenv()

client = Exa(api_key=os.environ["EXA_API_KEY"])

QUERIES = [
    "people frustrated with project management tools",
    "looking for alternative to Jira",
    "Jira is too slow and complicated",
    "why developers hate Jira",
    "project management software complaints developers",
    "switching from Jira to something simpler",
    "Jira alternative for small team",
    "project tracking tool frustration",
]

NUM_RESULTS = 20


def extract_subreddits(url: str) -> str | None:
    m = re.search(r"reddit\.com/r/(\w+)", url)
    return m.group(1).lower() if m else None


def run_reddit_probe():
    print("=" * 60)
    print("REDDIT-ONLY PROBE")
    print("=" * 60)
    subreddit_counts = Counter()
    all_results = []

    for query in QUERIES:
        print(f"\n--- Query: {query} ---")
        try:
            response = client.search_and_contents(
                query=query,
                num_results=NUM_RESULTS,
                include_domains=["reddit.com"],
                text=True,
            )
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        for result in response.results:
            sub = extract_subreddits(result.url)
            if sub:
                subreddit_counts[sub] += 1
            title = (result.title or "")[:80]
            print(f"  r/{sub or '?'}: {title}")
            all_results.append({
                "query": query,
                "subreddit": sub,
                "title": result.title,
                "url": result.url,
                "snippet": (result.text or "")[:200].replace("\n", " "),
            })

    print("\n" + "=" * 60)
    print("SUBREDDIT FREQUENCY (Reddit-only probe):")
    print("=" * 60)
    for sub, count in subreddit_counts.most_common(30):
        print(f"  r/{sub}: {count}")

    return subreddit_counts, all_results


def run_hn_probe():
    print("\n" + "=" * 60)
    print("HACKER NEWS PROBE")
    print("=" * 60)
    all_results = []

    hn_queries = [
        "Jira frustration developers",
        "project management tool complaints",
        "Jira alternative",
        "why Jira is terrible",
    ]

    for query in hn_queries:
        print(f"\n--- Query: {query} ---")
        try:
            response = client.search_and_contents(
                query=query,
                num_results=10,
                include_domains=["news.ycombinator.com"],
                text=True,
            )
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        for result in response.results:
            title = (result.title or "")[:100]
            print(f"  {title}")
            print(f"    {result.url}")
            all_results.append({
                "query": query,
                "title": result.title,
                "url": result.url,
            })

    print(f"\nTotal HN results: {len(all_results)}")
    return all_results


def main():
    sub_counts, reddit_results = run_reddit_probe()
    hn_results = run_hn_probe()

    out_path = "data/discovery_probe_reddit_hn.json"
    with open(out_path, "w") as f:
        json.dump({
            "subreddit_counts": dict(sub_counts.most_common()),
            "reddit_results": reddit_results,
            "hn_results": hn_results,
        }, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
