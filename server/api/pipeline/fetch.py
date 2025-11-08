"""
fetch_v2.py - Fetch prediction markets WITHOUT hard-coded category filtering
Accept ALL markets, let the signal extraction decide if they're good
"""
import requests
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import time
import re

# ============================================================================
# POLYMARKET (No filtering)
# ============================================================================

def fetch_polymarket_markets(limit: int = 100) -> List[Dict]:
    """Fetch ALL active Polymarket markets"""
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {
            'closed': 'false',
            'limit': limit,
            '_order': 'volume',
            '_sort': 'DESC'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        markets = response.json()
        
        processed_markets = []
        for market in markets:
            try:
                # Calculate time until close
                end_date_str = market.get('endDate', market.get('end_date_iso', ''))
                if not end_date_str:
                    continue
                
                # Parse timezone-aware
                if end_date_str.endswith('Z'):
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                elif '+' in end_date_str or end_date_str.count('-') > 2:
                    end_date = datetime.fromisoformat(end_date_str)
                else:
                    end_date = datetime.fromisoformat(end_date_str).replace(tzinfo=timezone.utc)
                
                now = datetime.now(timezone.utc)
                hours_until_close = (end_date - now).total_seconds() / 3600
                
                if hours_until_close < 0:
                    continue
                
                question = market.get('question', market.get('title', ''))
                description = market.get('description', '')
                
                # Get prices
                outcome_prices = market.get('outcomePrices', ['0.5', '0.5'])
                if isinstance(outcome_prices, str):
                    outcome_prices = [outcome_prices, str(1 - float(outcome_prices))]
                
                yes_price = float(outcome_prices[0]) if outcome_prices else 0.5
                
                processed_markets.append({
                    'platform': 'polymarket',
                    'market_id': market.get('id', market.get('condition_id', '')),
                    'question': question,
                    'description': description[:500],
                    'yes_price': yes_price,
                    'no_price': 1 - yes_price,
                    'volume': float(market.get('volume', market.get('volume24hr', 0))),
                    'liquidity': float(market.get('liquidity', market.get('liquidityNum', 0))),
                    'end_date': end_date.isoformat(),
                    'hours_until_close': hours_until_close,
                    'url': f"https://polymarket.com/event/{market.get('slug', market.get('question', '').lower().replace(' ', '-'))}"
                })
            except Exception as e:
                continue
        
        return processed_markets
    
    except Exception as e:
        print(f"❌ Error fetching Polymarket data: {e}")
        return []


# ============================================================================
# MANIFOLD (No filtering)
# ============================================================================

def fetch_manifold_markets(limit: int = 100) -> List[Dict]:
    """Fetch ALL active Manifold markets"""
    try:
        url = "https://api.manifold.markets/v0/search-markets"
        params = {
            'limit': limit,
            'filter': 'open',
            'sort': 'liquidity',
            'contractType': 'BINARY'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        markets = response.json()
        
        processed_markets = []
        for market in markets:
            try:
                if market.get('isResolved') or market.get('closeTime', 0) < time.time() * 1000:
                    continue
                
                # Calculate time until close
                close_time_ms = market.get('closeTime', 0)
                if close_time_ms == 0:
                    continue
                
                close_time = datetime.fromtimestamp(close_time_ms / 1000, tz=timezone.utc)
                now = datetime.now(timezone.utc)
                hours_until_close = (close_time - now).total_seconds() / 3600
                
                if hours_until_close < 0:
                    continue
                
                question = market.get('question', '')
                description = market.get('description', '')
                
                # Get current probability
                probability = market.get('probability', 0.5)
                if probability is None:
                    probability = 0.5
                
                # Manifold liquidity
                liquidity = 0
                if market.get('liquidity'):
                    liquidity = float(market['liquidity'])
                elif market.get('totalLiquidity'):
                    liquidity = float(market['totalLiquidity'])
                elif market.get('pool'):
                    pool = market['pool']
                    if isinstance(pool, dict):
                        liquidity = sum(float(v) for v in pool.values())
                    else:
                        liquidity = float(pool)
                
                # Volume
                volume = float(market.get('volume', 0))
                if volume == 0:
                    volume = float(market.get('volume24Hours', 0))
                
                processed_markets.append({
                    'platform': 'manifold',
                    'market_id': market.get('id'),
                    'question': question,
                    'description': description[:500],
                    'yes_price': probability,
                    'no_price': 1 - probability,
                    'volume': volume,
                    'liquidity': liquidity,
                    'end_date': close_time.isoformat(),
                    'hours_until_close': hours_until_close,
                    'url': market.get('url')
                })
            except Exception as e:
                continue
        
        return processed_markets
    
    except Exception as e:
        print(f"❌ Error fetching Manifold data: {e}")
        return []


# ============================================================================
# AGGREGATION (Minimal filtering)
# ============================================================================

def fetch_all_prediction_markets(
    platforms: List[str] = ['polymarket', 'manifold'],
    min_liquidity: float = 100,  # Lowered from 1000
    max_hours_until_close: int = 2160,  # Increased to 90 days
    categories: Optional[List[str]] = None  # Ignored
) -> List[Dict]:
    """
    Fetch ALL markets with minimal filtering
    Let the signal extraction decide what's good
    """
    all_markets = []
    
    if 'polymarket' in platforms:
        print("📊 Fetching Polymarket markets...")
        try:
            markets = fetch_polymarket_markets(limit=100)
            all_markets.extend(markets)
            print(f"  ✓ Fetched {len(markets)} Polymarket markets")
        except Exception as e:
            print(f"  ⚠️ Polymarket failed: {e}")
    
    if 'manifold' in platforms:
        print("📊 Fetching Manifold markets...")
        try:
            markets = fetch_manifold_markets(limit=100)
            all_markets.extend(markets)
            print(f"  ✓ Fetched {len(markets)} Manifold markets")
        except Exception as e:
            print(f"  ⚠️ Manifold failed: {e}")
    
    if not all_markets:
        print("\n⚠️ No markets fetched from any platform!")
        return []
    
    # ONLY filter by basic criteria
    filtered_markets = []
    for market in all_markets:
        # Must have SOME liquidity or volume
        has_activity = (market['liquidity'] >= min_liquidity) or (market['volume'] >= min_liquidity)
        
        # Must be open
        in_time_range = 0 < market['hours_until_close'] <= max_hours_until_close
        
        # Must have question text
        has_question = len(market['question']) > 10
        
        if has_activity and in_time_range and has_question:
            filtered_markets.append(market)
    
    print(f"\n✅ Found {len(filtered_markets)} tradeable markets")
    print(f"   Filters: min_activity=${min_liquidity}, max_hours={max_hours_until_close}")
    
    return filtered_markets


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_market_quality_score(market: Dict) -> float:
    """Simple quality score based on liquidity + volume"""
    score = 0.0
    
    # Liquidity
    if market['liquidity'] > 10000:
        score += 0.4
    elif market['liquidity'] > 5000:
        score += 0.3
    elif market['liquidity'] > 1000:
        score += 0.2
    elif market['liquidity'] > 100:
        score += 0.1
    
    # Volume
    if market['volume'] > 50000:
        score += 0.4
    elif market['volume'] > 10000:
        score += 0.3
    elif market['volume'] > 1000:
        score += 0.2
    elif market['volume'] > 100:
        score += 0.1
    
    # Time horizon (prefer near-term for quick resolution)
    hours = market['hours_until_close']
    if 24 <= hours <= 720:
        score += 0.2
    elif 720 < hours <= 2160:
        score += 0.1
    
    return min(1.0, score)