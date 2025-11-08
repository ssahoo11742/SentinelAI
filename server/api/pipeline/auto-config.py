"""
Auto-configure the pipeline based on available market data
Detects optimal filter settings
"""
from fetch import fetch_polymarket_markets, fetch_manifold_markets
import statistics

print("🔧 Auto-Configuring Prediction Market Pipeline")
print("="*80)

# Test both platforms
poly_markets = []
manifold_markets = []

print("\n📊 Testing Polymarket...")
try:
    poly_markets = fetch_polymarket_markets(limit=50)
    print(f"  ✓ {len(poly_markets)} markets available")
except Exception as e:
    print(f"  ✗ Failed: {e}")

print("\n📊 Testing Manifold...")
try:
    manifold_markets = fetch_manifold_markets(limit=50)
    print(f"  ✓ {len(manifold_markets)} markets available")
except Exception as e:
    print(f"  ✗ Failed: {e}")

# Analyze what we got
all_markets = poly_markets + manifold_markets

if not all_markets:
    print("\n❌ No markets available from any platform!")
    print("Check your internet connection and API endpoints.")
    exit(1)

print(f"\n📈 Analyzing {len(all_markets)} total markets...")

# Extract stats
liquidities = [m['liquidity'] for m in all_markets if m['liquidity'] > 0]
volumes = [m['volume'] for m in all_markets if m['volume'] > 0]
hours = [m['hours_until_close'] for m in all_markets if m['hours_until_close'] > 0]

print("\n" + "="*80)
print("MARKET STATISTICS")
print("="*80)

if liquidities:
    print(f"\n💰 Liquidity:")
    print(f"  Min:     ${min(liquidities):>10,.0f}")
    print(f"  10th %:  ${sorted(liquidities)[len(liquidities)//10]:>10,.0f}")
    print(f"  Median:  ${statistics.median(liquidities):>10,.0f}")
    print(f"  90th %:  ${sorted(liquidities)[len(liquidities)*9//10]:>10,.0f}")
    print(f"  Max:     ${max(liquidities):>10,.0f}")

if volumes:
    print(f"\n📊 Volume:")
    print(f"  Min:     ${min(volumes):>10,.0f}")
    print(f"  Median:  ${statistics.median(volumes):>10,.0f}")
    print(f"  Max:     ${max(volumes):>10,.0f}")

if hours:
    print(f"\n⏰ Time Until Close:")
    print(f"  Min:     {min(hours):>10.1f} hours ({min(hours)/24:.1f} days)")
    print(f"  Median:  {statistics.median(hours):>10.1f} hours ({statistics.median(hours)/24:.1f} days)")
    print(f"  Max:     {max(hours):>10.1f} hours ({max(hours)/24:.1f} days)")

# Generate recommendations
print("\n" + "="*80)
print("RECOMMENDED SETTINGS")
print("="*80)

if poly_markets and manifold_markets:
    print("\n🎯 BALANCED (both platforms):")
    liq_10th = sorted(liquidities)[len(liquidities)//10]
    hours_90th = sorted(hours)[len(hours)*9//10]
    print(f"  python run_prediction_pipeline.py \\")
    print(f"    --min-liquidity {max(10, liq_10th):.0f} \\")
    print(f"    --max-hours {min(720, int(hours_90th))}")

if poly_markets:
    poly_liq = [m['liquidity'] for m in poly_markets if m['liquidity'] > 0]
    if poly_liq:
        poly_10th = sorted(poly_liq)[len(poly_liq)//10]
        print(f"\n💎 POLYMARKET ONLY (real money):")
        print(f"  python run_prediction_pipeline.py \\")
        print(f"    --platforms polymarket \\")
        print(f"    --min-liquidity {max(500, poly_10th):.0f} \\")
        print(f"    --max-hours 168")

if manifold_markets:
    manifold_liq = [m['liquidity'] for m in manifold_markets if m['liquidity'] > 0]
    if manifold_liq:
        manifold_10th = sorted(manifold_liq)[max(1, len(manifold_liq)//10)]
        print(f"\n🎮 MANIFOLD ONLY (play money, more markets):")
        print(f"  python run_prediction_pipeline.py \\")
        print(f"    --platforms manifold \\")
        print(f"    --min-liquidity {max(5, manifold_10th):.0f} \\")
        print(f"    --max-hours 720")

# Show market count projections
print("\n" + "="*80)
print("EXPECTED MARKET COUNTS")
print("="*80)

for threshold in [10, 50, 100, 500, 1000]:
    count = sum(1 for m in all_markets if m['liquidity'] >= threshold)
    if count > 0:
        print(f"  min_liquidity ${threshold:>4}: {count:>3} markets")

print("\n" + "="*80)
print("💡 TIP: Start with the 'BALANCED' settings above!")
print("="*80)