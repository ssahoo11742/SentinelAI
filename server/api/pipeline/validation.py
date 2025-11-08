"""
validation_custom.py - CUSTOM TUNED for your specific data
Based on diagnostic output: 11 markets above alpha threshold, only 3 passed sanity

Key issues found:
1. Edge validation too strict for long-term markets (blocking JD Vance 2028)
2. Liquidity threshold too harsh (blocking Republicans House majority)
3. "Non-forecasting-grade" classifier too aggressive
"""
import re
import numpy as np
from typing import Dict, List, Tuple, Optional


# ============================================================================
# RELAXED MARKET CLASSIFICATION
# ============================================================================

def classify_market_realism(question: str, classifier) -> Tuple[str, float]:
    """Classify market type - MORE LENIENT"""
    categories = [
        "Serious forecasting market about politics, economics, sports, or technology",
        "Speculative or meme market about supernatural, impossible, or joke events",
        "Personal subjective question with no objective resolution"
    ]
    
    try:
        result = classifier(
            question,
            candidate_labels=categories,
            multi_label=False
        )
        return result['labels'][0], result['scores'][0]
    except:
        return categories[0], 0.5


def is_forecasting_grade_market(question: str, classifier) -> bool:
    """RELAXED: Only reject obvious garbage"""
    category, confidence = classify_market_realism(question, classifier)
    
    # Much higher threshold - only reject if VERY confident it's garbage
    if 'Speculative' in category and confidence > 0.80:  # Was 0.70
        return False
    
    if 'Personal' in category and confidence > 0.85:  # Was 0.75
        return False
    
    return True


# ============================================================================
# KEYWORD FILTERS (Same)
# ============================================================================

def has_supernatural_content(question: str) -> bool:
    supernatural_keywords = [
        'jesus', 'christ', 'god', 'messiah', 'rapture', 'second coming',
        'ufo', 'alien', 'extraterrestrial', 'interdimensional',
        'supernatural', 'paranormal', 'ghost', 'spirit',
        'miracle', 'divine', 'prophecy'
    ]
    
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in supernatural_keywords)


def is_meme_market(question: str) -> bool:
    meme_patterns = [
        r'gta\s*6',
        r'ww3',
        r'world war (3|three|iii)',
        r'zombie',
        r'simulation',
        r'matrix',
        r'time travel',
        r'before.*gta',
        r'versus.*gta'
    ]
    
    question_lower = question.lower()
    return any(re.search(pattern, question_lower) for pattern in meme_patterns)


def is_personal_market(question: str) -> bool:
    personal_patterns = [
        r'\bmy ex\b',  # "Will my ex..." - obvious personal
        r'\bi will\b',
        r'\bmy (diagnosis|health|relationship)\b',
    ]
    
    question_lower = question.lower()
    return any(re.search(pattern, question_lower) for pattern in personal_patterns)


# ============================================================================
# CUSTOM TUNED THRESHOLDS (Based on your data)
# ============================================================================

def get_time_adjusted_thresholds(hours_until_close: float) -> Dict[str, float]:
    """
    CUSTOM TUNED based on your diagnostic:
    - You have GOOD probability mentions (avg 19.8)
    - Edge validation is blocking good opportunities
    - Need to allow larger edges for long-term markets
    """
    if hours_until_close > 17520:  # >2 years (JD Vance 2028 case)
        return {
            'max_edge': 0.30,           # Was 0.18, now 0.30 to allow 26% edges
            'min_prob_mentions': 3,     # Was 5, you have good signals
            'min_confidence': 0.45,     # Keep this
        }
    elif hours_until_close > 8760:  # >1 year
        return {
            'max_edge': 0.35,           # Was 0.22, now 0.35
            'min_prob_mentions': 2,     # Was 3
            'min_confidence': 0.40,
        }
    elif hours_until_close > 2160:  # >3 months
        return {
            'max_edge': 0.38,           # Was 0.28, now 0.38
            'min_prob_mentions': 2,
            'min_confidence': 0.35,
        }
    elif hours_until_close > 168:  # >1 week
        return {
            'max_edge': 0.45,           # Was 0.35, now 0.45 to allow chatbot arena
            'min_prob_mentions': 1,
            'min_confidence': 0.30,
        }
    else:  # <1 week
        return {
            'max_edge': 0.50,           # Was 0.40
            'min_prob_mentions': 1,
            'min_confidence': 0.25,
        }


def is_edge_plausible(
    market_price: float,
    model_estimate: float,
    market: Dict
) -> Tuple[bool, str]:
    """
    RELAXED edge validation for your data
    Your diagnostic showed: edges up to 46% with good signals (36 prob mentions)
    """
    edge = abs(model_estimate - market_price)
    hours = market.get('hours_until_close', 720)
    num_prob_mentions = market.get('num_prob_mentions', 0)  # Add this context
    
    thresholds = get_time_adjusted_thresholds(hours)
    
    # Rule 1: Time-adjusted max edge (WITH EXCEPTIONS for strong signals)
    if edge > thresholds['max_edge']:
        # Exception: If you have MANY probability mentions, allow larger edge
        if num_prob_mentions >= 20:
            if edge > thresholds['max_edge'] * 1.5:  # Allow 50% more edge
                return False, f"Edge {edge:.1%} exceeds even relaxed max {thresholds['max_edge']*1.5:.1%}"
        else:
            return False, f"Edge {edge:.1%} exceeds max {thresholds['max_edge']:.1%} for {hours:.0f}h horizon"
    
    # Rule 2: Extreme base rate moves (VERY RELAXED)
    if market_price < 0.02 and model_estimate > 0.50:
        return False, "Implausible 48+ point move on <2% market"
    
    if market_price > 0.98 and model_estimate < 0.50:
        return False, "Implausible 48+ point move on >98% market"
    
    # Rule 3: High liquidity (MUCH MORE LENIENT - your data had $223k liquid market)
    liquidity = market.get('liquidity', 0)
    volume = market.get('volume', 0)
    max_activity = max(liquidity, volume)
    
    # Allow up to 35% edge even on $200k+ markets if signal is strong
    if max_activity > 200000 and edge > 0.35:
        if num_prob_mentions < 20:  # Only block if weak signal
            return False, f"Edge {edge:.1%} on very high liquidity (${max_activity:,.0f}) needs 20+ prob mentions"
    
    if max_activity > 50000 and edge > 0.45:
        return False, f"Edge {edge:.1%} too extreme even for liquid market (${max_activity:,.0f})"
    
    return True, ""


# ============================================================================
# CUSTOM SANITY CHECKS
# ============================================================================

def passes_sanity_checks(
    market: Dict,
    signal_data: Dict,
    classifier,
    verbose: bool = False
) -> Tuple[bool, str]:
    """
    CUSTOM TUNED for your data - only rejects obvious garbage
    """
    question = market['question']
    model_estimate = signal_data['final_estimate']
    market_price = market['yes_price']
    edge = abs(model_estimate - market_price)
    hours = market.get('hours_until_close', 720)
    num_prob_mentions = signal_data.get('num_prob_mentions', 0)
    confidence = signal_data.get('confidence', 0)
    
    # Add num_prob_mentions to market dict for is_edge_plausible
    market['num_prob_mentions'] = num_prob_mentions
    
    # Get thresholds
    thresholds = get_time_adjusted_thresholds(hours)
    
    # Check 1: Forecasting-grade (RELAXED)
    if not is_forecasting_grade_market(question, classifier):
        return False, "Non-forecasting-grade market"
    
    # Check 2: Personal markets (MORE SPECIFIC)
    if is_personal_market(question):
        return False, "Personal/subjective market"
    
    # Check 3: Meme markets
    if is_meme_market(question):
        return False, "Meme/joke market"
    
    # Check 4: Supernatural (ONLY for very large edges)
    if has_supernatural_content(question):
        if edge > 0.30:  # Was 0.20, much more lenient
            return False, "Supernatural content with very large edge"
    
    # Check 5: Edge plausibility (RELAXED)
    plausible, reason = is_edge_plausible(market_price, model_estimate, market)
    if not plausible:
        return False, reason
    
    # Check 6: Signal quality (ONLY for massive edges)
    if edge > 0.35:  # Only check if edge is truly massive
        if num_prob_mentions < 3:
            return False, f"Massive edge ({edge:.1%}) needs at least 3 prob mentions"
    
    # Check 7: Sentiment-only on long-term (MUCH MORE LENIENT)
    if num_prob_mentions == 0 and hours > 8760:  # Was 4320, now 1 year
        if edge > 0.20:  # Was 0.15
            return False, "Sentiment-only on >1yr market with large edge"
    
    # Check 8: Minimum confidence (ONLY for very large edges)
    if edge > 0.30:  # Was 0.20, much more lenient
        if confidence < 0.40:  # Was threshold-based
            return False, f"Confidence {confidence:.1%} too low for massive {edge:.1%} edge"
    
    if verbose:
        print(f"  ✓ Passed: {question[:60]}...")
    
    return True, "Passed all checks"


# ============================================================================
# BATCH FILTERING
# ============================================================================

def filter_opportunities(
    opportunities: List[Dict],
    classifier,
    verbose: bool = True
) -> List[Dict]:
    """Filter opportunities"""
    if verbose:
        print("\n🔍 Running custom-tuned sanity checks...")
    
    filtered = []
    rejection_reasons = {}
    
    for opp in opportunities:
        market = opp['market']
        signal_data = opp['signal_data']
        
        passes, reason = passes_sanity_checks(market, signal_data, classifier, verbose=False)
        
        if passes:
            filtered.append(opp)
        else:
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
    
    if verbose:
        print(f"\n✅ Filtered: {len(opportunities)} → {len(filtered)} opportunities")
        
        if rejection_reasons:
            print(f"\n❌ Rejection reasons:")
            for reason, count in sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"   • {reason}: {count}")
    
    return filtered


# ============================================================================
# CONFIDENCE RECALIBRATION (More generous for strong signals)
# ============================================================================

def recalibrate_confidence(
    signal_data: Dict,
    market: Dict,
    articles: List[Dict]
) -> float:
    """
    TUNED for your data - you have good probability mentions (avg 19.8)
    """
    factors = []
    
    # Factor 1: Probability mentions (YOUR DATA IS STRONG HERE)
    prob_count = signal_data.get('num_prob_mentions', 0)
    if prob_count >= 30:
        factors.append(0.95)
    elif prob_count >= 20:
        factors.append(0.90)     # You have many in this range
    elif prob_count >= 15:
        factors.append(0.85)
    elif prob_count >= 10:
        factors.append(0.75)
    elif prob_count >= 5:
        factors.append(0.65)
    elif prob_count >= 3:
        factors.append(0.55)
    elif prob_count >= 1:
        factors.append(0.45)
    else:
        factors.append(0.30)
    
    # Factor 2: Sentiment confidence
    sent_conf = signal_data.get('sentiment_confidence', 0.3)
    factors.append(sent_conf)
    
    # Factor 3: Article volume
    num_articles = len(articles)
    if num_articles >= 40:
        factors.append(0.85)
    elif num_articles >= 30:
        factors.append(0.75)
    elif num_articles >= 20:
        factors.append(0.65)
    elif num_articles >= 10:
        factors.append(0.55)
    else:
        factors.append(0.45)
    
    # Factor 4: Market liquidity (LESS HARSH)
    liquidity = market.get('liquidity', 0)
    volume = market.get('volume', 0)
    max_activity = max(liquidity, volume)
    
    if max_activity > 200000:
        factors.append(0.55)     # Was 0.50, slightly more generous
    elif max_activity > 50000:
        factors.append(0.65)
    elif max_activity > 10000:
        factors.append(0.75)
    else:
        factors.append(0.85)
    
    # Factor 5: Signal agreement
    prob_est = signal_data.get('probability_estimate')
    sent_est = signal_data.get('sentiment_estimate')
    
    if prob_est is not None and sent_est is not None:
        agreement = 1 - abs(prob_est - sent_est)
        factors.append(agreement)
    else:
        factors.append(0.50)
    
    # Factor 6: Time horizon (LESS HARSH)
    hours = market.get('hours_until_close', 720)
    if hours < 168:  # <1 week
        factors.append(0.85)
    elif hours < 720:  # <1 month
        factors.append(0.75)
    elif hours < 2160:  # <3 months
        factors.append(0.65)
    elif hours < 8760:  # <1 year
        factors.append(0.55)
    else:  # >1 year
        factors.append(0.48)     # Was 0.45, slightly more generous
    
    # Weights (emphasize probability mentions - your strength)
    weights = [0.30, 0.20, 0.15, 0.15, 0.10, 0.10]
    
    factors_array = np.array(factors)
    weights_array = np.array(weights)
    
    return float(np.average(factors_array, weights=weights_array))