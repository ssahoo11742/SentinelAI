"""
run_simple_pipeline.py - Domain-Agnostic Market Scanner

Refactored to provide a callable main() for FastAPI integration.
"""

import os
import time
from typing import List, Dict

# Local imports
from .fetch import fetch_all_prediction_markets
from .text_processing import collect_articles_from_newsapi
from .matcher import match_markets_to_topics, display_market_opportunities, export_market_opportunities
from .config import NEWSAPI_KEY, FROM_DATE, TO_DATE, PREDICTION_TOPIC_GROUPS, MAX_ARTICLES, MAX_WORKERS_ARTICLES

def main(
    platforms: List[str] = ['manifold', 'polymarket'],
    min_liquidity: float = 100,
    max_hours: int = 2160,
    output_dir: str = None
):
    """
    Runs the AlphaHunt v3.0 pipeline.
    Can be called from FastAPI or standalone.
    """
    start_time = time.time()

    print(f"\n{'='*80}")
    print(f"🔥 ALPHAHUNT v3.0: DOMAIN-AGNOSTIC MARKET SCANNER 🔥")
    print(f"{'='*80}")
    print(f"Platforms: {', '.join(platforms)} | Min liquidity: ${min_liquidity} | Max hours: {max_hours}")
    print(f"{'='*80}\n")

    # Ensure output directory exists
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Step 1: Fetch markets
    print("📊 Step 1: Fetching prediction markets...")
    markets = fetch_all_prediction_markets(
        platforms=platforms,
        min_liquidity=min_liquidity,
        max_hours_until_close=max_hours
    )
    if len(markets) < 5:
        raise RuntimeError(f"Not enough markets found ({len(markets)})")

    print(f"✅ Found {len(markets)} tradeable markets\n")

    # Step 2: Collect news
    print("📰 Step 2: Collecting news articles...")
    all_articles = []
    broad_queries = ["breaking news", "latest developments", "trending topics", "current events", "news today"] + PREDICTION_TOPIC_GROUPS[:5]
    for query in broad_queries:
        try:
            articles = collect_articles_from_newsapi(
                api_key=NEWSAPI_KEY,
                query=query,
                from_date=FROM_DATE,
                to_date=TO_DATE,
                max_articles=MAX_ARTICLES // len(broad_queries),
                max_workers=MAX_WORKERS_ARTICLES
            )
            all_articles.extend(articles)
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Query failed for '{query}': {e}")
            continue

    print(f"\n✅ Collected {len(all_articles)} articles\n")

    if len(all_articles) < 50:
        raise RuntimeError(f"Not enough articles collected ({len(all_articles)})")

    # Step 3: Match and analyze
    print("🔍 Step 3: Analyzing markets with domain-agnostic signals...")
    topic_markets = match_markets_to_topics(
        articles=all_articles,
        topic_model=None,
        markets=markets,
        top_n=30
    )

    if not topic_markets:
        raise RuntimeError("No opportunities found in this batch")

    # Step 4: Display + Export
    display_market_opportunities(topic_markets, topic_model=None)
    export_market_opportunities(topic_markets, topic_model=None, output_dir=output_dir)

    # Step 5: Summary
    elapsed = time.time() - start_time
    total_opportunities = sum(len(m) for m in topic_markets.values())
    strong_signals = sum(
        1 for markets in topic_markets.values() 
        for m in markets if m.get('confidence', 0) > 0.5
    )

    print(f"\n{'='*80}")
    print(f"📊 FINAL SUMMARY")
    print(f"Time elapsed: {elapsed:.1f}s | Articles: {len(all_articles)} | Markets scanned: {len(markets)}")
    print(f"Opportunities: {total_opportunities} | Strong signals (>50% conf): {strong_signals}")
    print(f"{'='*80}\n")
    print("⚠️ Educational purposes only. Trade at your own risk!")


# CLI support
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AlphaHunt v3.0 - Domain-Agnostic Market Scanner")
    parser.add_argument("--platforms", nargs='+', default=['manifold', 'polymarket'])
    parser.add_argument("--min-liquidity", type=float, default=100)
    parser.add_argument("--max-hours", type=int, default=2160)
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    main(
        platforms=args.platforms,
        min_liquidity=args.min_liquidity,
        max_hours=args.max_hours,
        output_dir=args.output_dir
    )
