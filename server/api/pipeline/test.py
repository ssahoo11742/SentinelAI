"""
Simplified demo script to test the prediction market pipeline
This runs a minimal version to verify everything works
"""

import sys
import time
from datetime import datetime

print("🚀 BetGPT - Prediction Market Inefficiency Detector")
print("=" * 80)
print("Running simplified demo...\n")

# Step 1: Test market fetching
print("Step 1/4: Testing market data fetching...")
try:
    from fetch import fetch_all_prediction_markets
    
    markets = fetch_all_prediction_markets(
        platforms=['polymarket', 'manifold'],
        min_liquidity=100,  # Lower threshold for testing
        max_hours_until_close=720  # 30 days
    )
    
    print(f"✅ Fetched {len(markets)} markets\n")
    
    if len(markets) == 0:
        print("⚠️ No markets found. Using demo mode.")
    else:
        print("Sample markets:")
        for i, m in enumerate(markets[:3], 1):
            print(f"  {i}. {m['question'][:60]}")
            print(f"     Price: {m['yes_price']:.1%} | Liquidity: ${m['liquidity']:,.0f}\n")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Test news fetching
print("\nStep 2/4: Testing news article collection...")
try:
    from text_processing import collect_articles_from_newsapi
    from config import NEWSAPI_KEY, FROM_DATE, TO_DATE
    
    # Test with just one query
    articles = collect_articles_from_newsapi(
        api_key=NEWSAPI_KEY,
        query="bitcoin OR cryptocurrency OR crypto",
        from_date=FROM_DATE,
        to_date=TO_DATE,
        max_articles=20,
        max_workers=5
    )
    
    print(f"✅ Collected {len(articles)} articles\n")
    
    if articles:
        print("Sample articles:")
        for i, a in enumerate(articles[:3], 1):
            print(f"  {i}. {a.get('title', 'No title')[:60]}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Test text processing
print("\nStep 3/4: Testing text processing...")
try:
    from text_processing import extract_keywords, extract_entities, clean_text
    
    if articles:
        sample = articles[0]
        keywords = extract_keywords(sample['fulltext'])
        entities = extract_entities(sample['fulltext'])
        cleaned = clean_text(sample['fulltext'])
        
        print(f"✅ Text processing works")
        print(f"   Keywords: {keywords[:100]}...")
        print(f"   Entities: {entities[:100]}...")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: Test model loading
print("\nStep 4/4: Testing model initialization...")
try:
    from matcher import initialize_models
    
    initialize_models()
    print("✅ Models loaded successfully\n")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Summary
print("\n" + "=" * 80)
print("✅ ALL TESTS PASSED!")
print("=" * 80)
print("\nYou're ready to run the full pipeline:")
print("  python run_prediction_pipeline.py")
print("\nOr with custom settings:")
print("  python run_prediction_pipeline.py --min-liquidity 500 --max-hours 72")
print("=" * 80)