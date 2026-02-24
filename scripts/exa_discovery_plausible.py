"""
Exa Discovery Probe for Plausible backtest case.
Signal: Google Analytics privacy/GDPR frustration, complexity complaints.
Date range: 2018-01 to 2018-12.
"""

import json
import os
import re
from collections import Counter

from dotenv import load_dotenv
from exa_py import Exa

load_dotenv()

client = Exa(api_key=os.environ["EXA_API_KEY"])

QUERIES_GENERAL = [
    "Google Analytics privacy concerns GDPR",
    "Google Analytics alternative privacy",
    "frustrated with Google Analytics complexity",
    "GDPR compliant web analytics",
    "privacy friendly website analytics",
    "Google Analytics tracking too much data",
    "simple alternative to Google Analytics",
    "website analytics without cookies",
]

QUERIES_REDDIT = [
    "Google Analytics privacy concerns",
    "GDPR compliant analytics alternative",
    "frustrated with Google Analytics",
    "simple web analytics alternative",
    "privacy friendly analytics",
    "Google Analytics too complex",
    "website analytics without tracking users",
    "Google Analytics GDPR compliance problems",
]

QUERIES_HN = [
    "Google Analytics alternative",
    "Google Analytics privacy",
    "GDPR analytics",
    "simple web analytics",
]

NUM_RESULTS = 20


def extract_subreddits(url: str) -> str | None:
    m = re.search(r"reddit\.com/r/(\w+)", url)
    return m.group(1).lower() if m else None


def extract_domain(url: str) -> str:
    m = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1) if m else url


def run_general_probe():
    print("=" * 60)
    print("GENERAL PROBE (all domains)")
    print("=" * 60)
    domain_counts = Counter()
    subreddit_counts = Counter()

    for query in QUERIES_GENERAL:
        print(f"\n--- Query: {query} ---")
        try:
            response = client.search_and_contents(
                query=query, num_results=NUM_RESULTS, text=True,
            )
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        for result in response.results:
            domain = extract_domain(result.url)
            domain_counts[domain] += 1
            sub = extract_subreddits(result.url)
            if sub:
                subreddit_counts[sub] += 1
            print(f"  [{domain}] {(result.title or '')[:80]}")

    print(f"\nTOP DOMAINS:")
    for d, c in domain_counts.most_common(20):
        print(f"  {d}: {c}")
    print(f"\nSUBREDDITS (from general probe):")
    for s, c in subreddit_counts.most_common(20):
        print(f"  r/{s}: {c}")
    return domain_counts, subreddit_counts


def run_reddit_probe():
    print("\n" + "=" * 60)
    print("REDDIT-ONLY PROBE")
    print("=" * 60)
    subreddit_counts = Counter()
    results = []

    for query in QUERIES_REDDIT:
        print(f"\n--- Query: {query} ---")
        try:
            response = client.search_and_contents(
                query=query, num_results=NUM_RESULTS,
                include_domains=["reddit.com"], text=True,
            )
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        for result in response.results:
            sub = extract_subreddits(result.url)
            if sub:
                subreddit_counts[sub] += 1
            print(f"  r/{sub or '?'}: {(result.title or '')[:80]}")
            results.append({
                "query": query, "subreddit": sub,
                "title": result.title, "url": result.url,
            })

    print("\n" + "=" * 60)
    print("SUBREDDIT FREQUENCY (Reddit-only):")
    print("=" * 60)
    for s, c in subreddit_counts.most_common(30):
        print(f"  r/{s}: {c}")
    return subreddit_counts, results


def run_hn_probe():
    print("\n" + "=" * 60)
    print("HACKER NEWS PROBE")
    print("=" * 60)
    results = []

    for query in QUERIES_HN:
        print(f"\n--- Query: {query} ---")
        try:
            response = client.search_and_contents(
                query=query, num_results=10,
                include_domains=["news.ycombinator.com"], text=True,
            )
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        for result in response.results:
            print(f"  {(result.title or '')[:100]}")
            print(f"    {result.url}")
            results.append({
                "query": query, "title": result.title, "url": result.url,
            })

    print(f"\nTotal HN results: {len(results)}")
    return results


def main():
    domain_counts, gen_sub_counts = run_general_probe()
    reddit_sub_counts, reddit_results = run_reddit_probe()
    hn_results = run_hn_probe()

    # Merge subreddit counts
    merged = Counter()
    merged.update(gen_sub_counts)
    merged.update(reddit_sub_counts)

    print("\n" + "=" * 60)
    print("MERGED SUBREDDIT RANKING:")
    print("=" * 60)
    for s, c in merged.most_common(30):
        print(f"  r/{s}: {c}")

    out_path = "data/discovery_probe_plausible.json"
    os.makedirs("data", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({
            "domain_counts": dict(domain_counts.most_common()),
            "subreddit_counts_merged": dict(merged.most_common()),
            "reddit_results": reddit_results,
            "hn_results": hn_results,
        }, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
