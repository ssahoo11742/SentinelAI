"""
run_simple_pipeline.py - SIMPLIFIED, ROBUST pipeline

Changes from v2.0:
✅ Removed hard-coded categories
✅ Removed external forecast dependency (optional bonus, not required)
✅ Removed comment analysis dependency (flaky API)
✅ Removed topic modeling (unnecessary complexity)
✅ Direct question → article matching
✅ Universal signal extraction (works for ANY market)
✅ Relaxed filters (more opportunities)
"""
from .validation import filter_opportunities
import time
import argparse
from datetime import datetime
from typing import List, Dict
import time

# Record start time
start_time = time.time()
# Import modules
from .text_processing import collect_articles_from_newsapi
from .fetch import fetch_all_prediction_markets
from .matcher import (
    match_markets_to_topics,
    display_market_opportunities,
    export_market_opportunities
)
from .config import (
    NEWSAPI_KEY, FROM_DATE, TO_DATE,
    PREDICTION_TOPIC_GROUPS, MAX_ARTICLES,
    MAX_WORKERS_ARTICLES
)


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="AlphaHunt v3.0 - Domain-Agnostic Market Scanner")
    parser.add_argument("--platforms", nargs='+', default=['manifold', 'polymarket'],
                       help="Platforms to analyze")
    parser.add_argument("--min-liquidity", type=float, default=100,
                       help="Minimum market liquidity/volume in USD")
    parser.add_argument("--max-hours", type=int, default=2160,
                       help="Maximum hours until close (2160 = 90 days)")
    args = parser.parse_args()
    
    start_time = time.time()
    
    print(f"\n{'='*100}")
    print(f"🔥 ALPHAHUNT v3.0: DOMAIN-AGNOSTIC MARKET SCANNER 🔥")
    print(f"{'='*100}")
    print(f"📅 Date range: {FROM_DATE} to {TO_DATE}")
    print(f"🏪 Platforms: {', '.join(args.platforms)}")
    print(f"💰 Min activity: ${args.min_liquidity}")
    print(f"⏰ Max time to close: {args.max_hours} hours")
    print(f"\n🆕 v3.0 Improvements:")
    print(f"   ✓ Domain-agnostic (no hard-coded categories)")
    print(f"   ✓ Universal signal extraction (works for ANY question)")
    print(f"   ✓ Time-decay weighting (recent news matters more)")
    print(f"   ✓ Relaxed filters (more opportunities)")
    print(f"   ✓ Simplified pipeline (fewer dependencies)")
    print(f"{'='*100}\n")
    
    # Step 1: Fetch markets
    print("📊 Step 1: Fetching prediction markets...")
    markets = fetch_all_prediction_markets(
        platforms=args.platforms,
        min_liquidity=args.min_liquidity,
        max_hours_until_close=args.max_hours
    )
    
    if len(markets) < 5:
        print(f"\n❌ Not enough markets found ({len(markets)}). Try:")
        print(f"   • Lowering --min-liquidity (current: ${args.min_liquidity})")
        print(f"   • Increasing --max-hours (current: {args.max_hours})")
        exit()
    
    print(f"✅ Found {len(markets)} tradeable markets\n")
    
    # Step 2: Collect news
    print("📰 Step 2: Collecting news articles...")
    all_articles = []
    
    # Use broader queries for domain-agnostic approach
    broad_queries = [
        "breaking news",
        "latest developments", 
        "trending topics",
        "current events",
        "news today"
    ] + PREDICTION_TOPIC_GROUPS[:5]
    
    for query in broad_queries:
        print(f"  🔍 Query: {query}...")
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
            print(f"  ⚠️ Query failed: {e}")
            continue
    
    print(f"\n✅ Collected {len(all_articles)} articles\n")
    
    if len(all_articles) < 50:
        print(f"❌ Not enough articles ({len(all_articles)}). Try:")
        print(f"   • Expanding date range in config.py")
        print(f"   • Checking NEWSAPI_KEY")
        exit()
    
    # Step 3: Match and analyze
    print("🔍 Step 3: Analyzing markets with domain-agnostic signals...")
    print("This uses:")
    print("  • Question → Article semantic matching")
    print("  • Universal probability extraction (works for any domain)")
    print("  • Time-weighted sentiment (recent articles matter more)")
    print("  • Zero-shot classification (no category knowledge needed)\n")
    
    # Simple dict for compatibility (no actual topic model)
    topic_model = None
    
    topic_markets = match_markets_to_topics(
        articles=all_articles,
        topic_model=topic_model,
        markets=markets,
        top_n=30
    )
    
    if not topic_markets:
        print("\n❌ No opportunities found. Possible reasons:")
        print("  • Market prices are efficient")
        print("  • News doesn't contain strong signals")
        print("  • Articles not relevant to markets")
        exit()
    
    # Step 4: Display
    display_market_opportunities(topic_markets, topic_model)
    
    # Step 5: Export
    export_market_opportunities(topic_markets, topic_model)
    
    # Summary
    end_time = time.time()
    elapsed = end_time - start_time
    
    total_opportunities = sum(len(m) for m in topic_markets.values())
    strong = sum(
        1 for markets in topic_markets.values()
        for m in markets if m['confidence'] > 0.5
    )
    
    print(f"\n{'='*100}")
    print(f"📊 FINAL SUMMARY")
    print(f"{'='*100}")
    print(f"⏱️  Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"📰 Articles: {len(all_articles)}")
    print(f"🎯 Markets scanned: {len(markets)}")
    print(f"🔍 Opportunities: {total_opportunities}")
    print(f"⭐ Strong signals (>50% conf): {strong}")
    print(f"{'='*100}\n")
    
    if total_opportunities > 0:
        print("💡 What to do next:")
        print("1. Review alphahunt_v3_opportunities_*.csv")
        print("2. Focus on high-confidence opportunities (>50%)")
        print("3. Check 'Num_Prob_Mentions' - more mentions = stronger signal")
        print("4. Verify with external sources before trading")
        print("5. Use Kelly fractions for position sizing")
    
    print("\n⚠️  Educational purposes only. Trade at your own risk!")
    end_time = time.time()

    # Calculate elapsed time
    elapsed_time = end_time - start_time
    print(f"Script ran in {elapsed_time:.4f} seconds")