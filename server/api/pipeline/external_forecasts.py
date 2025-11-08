"""
external_forecasts.py - Scrape authoritative probability forecasts for macro markets
Provides real anchors for GDP, recession, inflation, Fed policy questions
"""
import requests
import re
from typing import Optional, Dict, List
from datetime import datetime
import time
from bs4 import BeautifulSoup

# ============================================================================
# ATLANTA FED GDPNOW
# ============================================================================

def get_gdpnow_forecast() -> Optional[Dict]:
    """
    Scrape Atlanta Fed GDPNow - the gold standard for real-time GDP tracking
    Returns: {'gdp_forecast': float, 'date': str, 'quarter': str}
    """
    try:
        url = "https://www.atlantafed.org/cqer/research/gdpnow"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the latest forecast number
        # Typically appears as "Latest forecast: X.X percent — Month DD, YYYY"
        text = soup.get_text()
        
        # Pattern: "Latest forecast: X.X percent"
        match = re.search(r'Latest forecast[:\s]+([+-]?\d+\.?\d*)\s*percent', text, re.IGNORECASE)
        if match:
            gdp_forecast = float(match.group(1))
            
            # Try to extract date
            date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', text)
            date_str = date_match.group(0) if date_match else datetime.now().strftime("%B %d, %Y")
            
            # Extract quarter
            quarter_match = re.search(r'(Q[1-4])\s+\d{4}', text)
            quarter = quarter_match.group(0) if quarter_match else "Current Quarter"
            
            return {
                'gdp_forecast': gdp_forecast,
                'date': date_str,
                'quarter': quarter,
                'source': 'Atlanta Fed GDPNow'
            }
        
        return None
        
    except Exception as e:
        print(f"  ⚠️ GDPNow scraping failed: {e}")
        return None


# ============================================================================
# FIVETHIRTYEIGHT ECONOMIC MODELS
# ============================================================================

def get_fivethirtyeight_recession_prob() -> Optional[Dict]:
    """
    Get recession probability from FiveThirtyEight models
    Note: As of 2024, they may not have active recession model - fallback to manual scraping
    """
    try:
        # Try their data repository first
        url = "https://projects.fivethirtyeight.com/checking-our-work/economy/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # Look for recession-related probability
        text = response.text.lower()
        
        # Pattern matching for recession probability
        match = re.search(r'recession.*?(\d{1,2}\.?\d*)%', text)
        if match:
            prob = float(match.group(1)) / 100
            return {
                'recession_probability': prob,
                'source': 'FiveThirtyEight',
                'date': datetime.now().strftime("%Y-%m-%d")
            }
        
        return None
        
    except Exception as e:
        print(f"  ⚠️ FiveThirtyEight scraping failed: {e}")
        return None


# ============================================================================
# BLOOMBERG CONSENSUS FORECASTS
# ============================================================================

def get_bloomberg_consensus() -> Optional[Dict]:
    """
    Bloomberg requires authentication, so we'll use publicly available summaries
    This is a placeholder - in production you'd use Bloomberg Terminal API
    """
    # For this hackathon, we'll return None and focus on free sources
    # In production: use Bloomberg API with authentication
    return None


# ============================================================================
# FRED (Federal Reserve Economic Data)
# ============================================================================

def get_fred_indicator(series_id: str) -> Optional[Dict]:
    """
    Get latest value from FRED economic indicators
    Free API, just needs a key (you'd get from: https://fred.stlouisfed.org/docs/api/api_key.html)
    
    Useful series:
    - UNRATE: Unemployment rate
    - CPIAUCSL: CPI
    - DFF: Federal Funds Rate
    - T10Y2Y: 10Y-2Y Treasury Spread (recession indicator)
    """
    # For demo purposes - would need API key in production
    # api_key = "YOUR_FRED_API_KEY"
    # url = f"https://api.stlouisfed.org/fred/series/observations"
    # params = {'series_id': series_id, 'api_key': api_key, 'file_type': 'json'}
    return None


# ============================================================================
# POLYMARKET CONSENSUS (Cross-platform arbitrage)
# ============================================================================

def get_polymarket_price_for_question(question: str) -> Optional[float]:
    """
    If the SAME question exists on Polymarket (higher liquidity), use it as anchor
    """
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {'limit': 100, 'closed': 'false'}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        markets = response.json()
        
        # Fuzzy match on question text
        question_lower = question.lower()
        question_words = set(question_lower.split())
        
        best_match = None
        best_score = 0
        
        for market in markets:
            market_q = market.get('question', '').lower()
            market_words = set(market_q.split())
            
            # Jaccard similarity
            intersection = question_words & market_words
            union = question_words | market_words
            
            if len(union) > 0:
                score = len(intersection) / len(union)
                
                if score > best_score and score > 0.6:  # 60% match threshold
                    best_score = score
                    best_match = market
        
        if best_match:
            prices = best_match.get('outcomePrices', [0.5, 0.5])
            if isinstance(prices, str):
                return float(prices)
            return float(prices[0]) if prices else None
        
        return None
        
    except Exception as e:
        print(f"  ⚠️ Polymarket cross-reference failed: {e}")
        return None


# ============================================================================
# SMART FORECAST MATCHING
# ============================================================================

def get_external_forecast(market: Dict) -> Optional[Dict]:
    """
    Match market questions to external forecasts
    Returns: {'probability': float, 'source': str, 'confidence': float}
    """
    question = market['question'].lower()
    category = market.get('category', '')
    
    # GDP-related markets
    if 'gdp' in question and ('growth' in question or 'quarter' in question or 'q1' in question or 'q2' in question or 'q3' in question or 'q4' in question):
        gdpnow = get_gdpnow_forecast()
        if gdpnow:
            gdp_forecast = gdpnow['gdp_forecast']
            
            # Convert GDP forecast to probability based on question
            # Example: "Will GDP growth exceed 2.5%?" -> compare forecast to threshold
            threshold_match = re.search(r'(\d+\.?\d*)\s*%', question)
            if threshold_match:
                threshold = float(threshold_match.group(1))
                
                # Determine direction: "exceed", "above" vs "below", "under"
                if any(word in question for word in ['exceed', 'above', 'over', 'more than', 'greater']):
                    # Higher is YES
                    if gdp_forecast > threshold:
                        prob = 0.65 + min((gdp_forecast - threshold) * 0.1, 0.25)
                    else:
                        prob = 0.35 - min((threshold - gdp_forecast) * 0.1, 0.25)
                elif any(word in question for word in ['below', 'under', 'less than', 'lower']):
                    # Lower is YES
                    if gdp_forecast < threshold:
                        prob = 0.65 + min((threshold - gdp_forecast) * 0.1, 0.25)
                    else:
                        prob = 0.35 - min((gdp_forecast - threshold) * 0.1, 0.25)
                else:
                    # Neutral comparison
                    prob = 0.5 + (gdp_forecast - threshold) * 0.05
                
                prob = max(0.1, min(0.9, prob))
                
                return {
                    'probability': prob,
                    'source': f"Atlanta Fed GDPNow ({gdp_forecast}%)",
                    'confidence': 0.85,  # High confidence in GDPNow
                    'raw_value': gdp_forecast
                }
    
    # Recession-related markets
    if 'recession' in question:
        recession_prob = get_fivethirtyeight_recession_prob()
        if recession_prob:
            prob = recession_prob['recession_probability']
            
            # Adjust based on timeframe in question
            if '2025' in question or 'next year' in question:
                # Use as-is
                pass
            elif 'this year' in question or '2024' in question:
                # Increase probability for near-term
                prob = min(0.9, prob * 1.2)
            
            return {
                'probability': prob,
                'source': 'FiveThirtyEight Recession Model',
                'confidence': 0.75,
                'raw_value': prob
            }
    
    # Cross-platform price check (Polymarket as anchor for Manifold)
    if market['platform'] == 'manifold' and market['liquidity'] < 5000:
        poly_price = get_polymarket_price_for_question(market['question'])
        if poly_price:
            return {
                'probability': poly_price,
                'source': 'Polymarket (higher liquidity)',
                'confidence': 0.80,
                'raw_value': poly_price
            }
    
    return None


# ============================================================================
# BATCH FORECAST FETCHING
# ============================================================================

def enrich_markets_with_forecasts(markets: List[Dict]) -> List[Dict]:
    """
    Batch process markets and add external forecasts where available
    """
    print("\n🔍 Fetching external forecasts...")
    
    # Cache forecasts to avoid repeated API calls
    gdpnow_cache = None
    recession_cache = None
    
    enriched_count = 0
    
    for market in markets:
        forecast = get_external_forecast(market)
        
        if forecast:
            market['external_forecast'] = forecast
            enriched_count += 1
            print(f"  ✓ {market['platform']}: {market['question'][:60]}... -> {forecast['source']}")
    
    print(f"\n✅ Enriched {enriched_count}/{len(markets)} markets with external forecasts")
    
    return markets