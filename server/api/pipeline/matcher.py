"""
matcher_v3.py - Robust, domain-agnostic market matcher
NOW WITH SANITY CHECKS AND PROPER VALIDATION
"""
from .question_retriever import retrieve_topk_for_question
from .manifold_bias import calibrated_prob
from .universal_signals import extract_all_signals, calculate_time_weights
from .validation import (
    passes_sanity_checks,
    filter_opportunities,
    recalibrate_confidence
)
import numpy as np
from typing import List, Dict, Optional
from transformers import pipeline
import torch
from .debug import diagnose_filtering_cascade

# Global classifier
_classifier = None

def _get_classifier():
    global _classifier
    if _classifier is None:
        print("📥 Loading zero-shot classifier...")
        device = 0 if torch.cuda.is_available() else -1
        _classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=device
        )
        print(f"  ✓ Loaded")
    return _classifier


# ============================================================================
# ALPHA CALCULATION (Updated)
# ============================================================================

def calculate_alpha_score(
    market: Dict,
    signal_data: Dict,
    articles: List[Dict],
    kelly_cap_base: float = 0.25
) -> Dict:
    """
    CUSTOM TUNED: Your data has good signals, be less aggressive with filtering
    """
    market_price = market['yes_price']
    model_estimate = signal_data['final_estimate']
    
    # Recalibrate confidence
    confidence = recalibrate_confidence(signal_data, market, articles)
    
    # Calculate edge
    edge = abs(model_estimate - market_price)
    
    # Get market info
    hours = market.get('hours_until_close', 720)
    num_prob_mentions = signal_data.get('num_prob_mentions', 0)
    
    # === MORE LENIENT FILTERS ===
    
    # Filter 1: Minimum confidence (LOWERED based on your data)
    if hours > 8760:  # >1 year
        min_conf = 0.35  # Was 0.38, you have good signals
    elif hours > 2160:  # >3 months
        min_conf = 0.30  # Was 0.32
    else:
        min_conf = 0.25  # Keep this
    
    if confidence < min_conf:
        return {
            'alpha_score': 0.0,
            'recommendation': f"⚪ SKIP - Low Confidence ({confidence:.1%} < {min_conf:.1%})",
            'confidence': confidence,
            'edge': edge,
            'kelly_fraction': 0.0
        }
    
    # Filter 2: Minimum edge (LOWERED)
    if hours > 8760:  # >1 year
        min_edge = 0.08  # Was 0.10
    elif hours > 2160:  # >3 months
        min_edge = 0.07  # Was 0.08
    else:
        min_edge = 0.06
    
    if edge < min_edge:
        return {
            'alpha_score': 0.0,
            'recommendation': "⚪ HOLD - Efficient Market",
            'confidence': confidence,
            'edge': edge,
            'kelly_fraction': 0.0
        }
    
    # Filter 3: Probability requirement (VERY LENIENT - you have good probs)
    # Only require for truly massive edges
    if num_prob_mentions < 2 and edge > 0.30:  # Was 2/0.22, now 2/0.30
        return {
            'alpha_score': 0.0,
            'recommendation': f"⚪ SKIP - Massive edge ({edge:.1%}) needs 2+ prob mentions",
            'confidence': confidence,
            'edge': edge,
            'kelly_fraction': 0.0
        }
    
    # === ALPHA COMPONENTS ===
    
    # 1. Edge size (45%)
    edge_score = min(1.0, edge / 0.25)
    
    # 2. Confidence (35%)
    conf_score = confidence
    
    # 3. Signal strength (10%) - MORE GENEROUS
    if num_prob_mentions >= 20:
        signal_strength = 1.0
    elif num_prob_mentions >= 15:
        signal_strength = 0.95
    elif num_prob_mentions >= 10:
        signal_strength = 0.85
    elif num_prob_mentions >= 5:
        signal_strength = 0.70
    elif num_prob_mentions >= 3:
        signal_strength = 0.55
    elif num_prob_mentions >= 1:
        signal_strength = 0.40
    else:
        signal_strength = 0.25  # Sentiment-only
    
    # 4. Time urgency (10%)
    if hours < 48:
        time_score = 1.0
    elif hours < 168:
        time_score = 0.85
    elif hours < 720:
        time_score = 0.70
    elif hours < 2160:
        time_score = 0.58
    elif hours < 8760:
        time_score = 0.48
    else:
        time_score = 0.38  # Less harsh on long-term
    
    # Weighted alpha
    alpha_score = (
        edge_score * 0.45 +
        conf_score * 0.35 +
        signal_strength * 0.10 +
        time_score * 0.10
    )
    
    # === RECOMMENDATION (Based on your data patterns) ===
    
    # Strong buy: Large edge with good signal
    if edge > 0.15 and confidence > 0.50 and num_prob_mentions >= 10:
        if model_estimate > market_price:
            rec = f"🟢 STRONG BUY YES (Edge: {edge:.1%}, {num_prob_mentions} mentions)"
        else:
            rec = f"🔴 STRONG BUY NO (Edge: {edge:.1%}, {num_prob_mentions} mentions)"
    
    # Good buy: Decent edge + confidence
    elif edge > 0.12 and confidence > 0.40:
        if model_estimate > market_price:
            rec = f"🟢 BUY YES (Edge: {edge:.1%})"
        else:
            rec = f"🔴 BUY NO (Edge: {edge:.1%})"
    
    # Moderate: Smaller edge but passing filters
    elif edge > 0.08:
        rec = f"⚠️ MODERATE (Edge: {edge:.1%})"
    
    # Weak: Very small edge
    else:
        rec = f"⚪ WEAK (Edge: {edge:.1%})"
        alpha_score *= 0.5
    
    # === KELLY FRACTION ===
    
    # === KELLY FRACTION ===

    has_forecast = market.get('external_forecast') is not None

    # Liquidity adjustment: map liquidity -> multiplier in [0.6, 1.5]
    liquidity = float(market.get('liquidity') or 0.0)
    # Base multiplier: 0.6 when liquidity=0, ~1.0 at liquidity=5000, saturates at 1.5 for very high liquidity
    liq_mult = 0.6 + (1.0 - 0.6) * min(1.0, liquidity / 5000.0)
    liq_mult = min(1.5, liq_mult)

    kelly_cap = kelly_cap_base * (1.3 if has_forecast else 1.0) * liq_mult

    
    if 0.01 < market_price < 0.99:
        if model_estimate > market_price:
            kelly = (edge * confidence) / market_price
        else:
            kelly = (edge * confidence) / (1 - market_price)
        
        kelly = min(kelly_cap, max(0.0, kelly))
    else:
        kelly = 0.0
    
    return {
        'alpha_score': alpha_score,
        'recommendation': rec,
        'confidence': confidence,
        'edge': edge,
        'kelly_fraction': kelly,
        'model_estimate': model_estimate,
        'market_price': market_price,
        'signal_data': signal_data,
        'has_forecast': has_forecast,
        'num_prob_mentions': num_prob_mentions
    }
# ============================================================================
# MAIN MATCHING (Updated with Validation)
# ============================================================================

def match_markets_to_topics(
    articles: List[Dict],
    topic_model,
    markets: List[Dict],
    top_n: int = 50  # Increased from 30 to 50
) -> Dict[int, List[Dict]]:
    """
    Market matching with SANITY CHECKS and VALIDATION
    """

    classifier = _get_classifier()
    
    opportunities = []
    if False:  # Set to False to disable diagnostics
        diagnose_filtering_cascade(markets, articles, classifier)
        return {}  # Exit early after diagnostics
    print(f"\n🔍 Analyzing {len(markets)} markets...")
    
    for idx, market in enumerate(markets):
        question = market['question']
        
        # 1. Get relevant articles (increased from 40 to 50)
        relevant = retrieve_topk_for_question(articles, question, k=50)
        
        if len(relevant) < 3:  # Lowered from 5 to 3
            continue
        
        # 2. Calibrate Manifold prices
        if market['platform'] == 'manifold':
            market['yes_price'] = calibrated_prob(market['yes_price'])
        
        # 3. Extract signals
        signal_data = extract_all_signals(relevant, question, classifier, market.get("hoirs_until_close"), market=market)
        
        # 4. Calculate alpha (with recalibrated confidence)
        alpha_result = calculate_alpha_score(market, signal_data, relevant)
        
        # 5. Filter by minimum alpha (lowered from 0.20 to 0.15)
        if alpha_result['alpha_score'] < 0.15:
            continue
        
        # 6. RUN SANITY CHECKS (NEW!)
        passes, reason = passes_sanity_checks(market, signal_data, classifier, verbose=False)
        
        if not passes:
            # Optionally log rejection
            # print(f"  ❌ Rejected: {question[:50]}... - {reason}")
            continue
        
        opportunities.append({
            'market_id': idx,
            'market': market,
            'alpha_score': alpha_result['alpha_score'],
            'recommendation': alpha_result['recommendation'],
            'confidence': alpha_result['confidence'],
            'edge': alpha_result['edge'],
            'kelly_fraction': alpha_result['kelly_fraction'],
            'model_estimate': alpha_result['model_estimate'],
            'market_price': alpha_result['market_price'],
            'signal_data': signal_data,
            'article_count': len(relevant),
            'has_forecast': alpha_result['has_forecast']
        })
        
        if len(opportunities) % 5 == 0 and len(opportunities) > 0:
            print(f"  ✓ Found {len(opportunities)} opportunities so far...")
    
    print(f"\n✅ Total opportunities found (before final filter): {len(opportunities)}")
    
    # 7. FINAL BATCH FILTERING (NEW!)
    opportunities = filter_opportunities(opportunities, classifier, verbose=True)
    
    # Sort by alpha score
    opportunities.sort(key=lambda x: x['alpha_score'], reverse=True)
    
    # Take top N
    top_opportunities = opportunities[:top_n]
    
    # Convert to old format
    result = {}
    for opp in top_opportunities:
        market_id = opp['market_id']
        result[market_id] = [opp]
    
    return result


# ============================================================================
# DISPLAY (Updated with Better Stats)
# ============================================================================

def display_market_opportunities(topic_markets: Dict, topic_model) -> None:
    """Enhanced display with sanity indicators"""
    print("\n" + "="*140)
    print("=== 🔥 ALPHAHUNT v3.1: VALIDATED MARKET SCANNER 🔥 ===")
    print("="*140 + "\n")

    flat = [(tid, m) for tid, markets in topic_markets.items() for m in markets]
    flat.sort(key=lambda x: x[1]["alpha_score"], reverse=True)

    if not flat:
        print("  No validated alpha opportunities found")
        return

    print(f"{'#':<4} {'Platform':<10} {'Alpha':<7} {'Conf':<6} {'Edge':<7} {'Kelly':<7} {'Rec':<40} {'Question'}")
    print("-" * 140)

    for rank, (tid, match) in enumerate(flat[:30], 1):
        mkt = match["market"]
        
        print(f"{rank:<4} "
              f"{mkt['platform']:<10} "
              f"{match['alpha_score']:.3f}   "
              f"{match['confidence']:.1%}  "
              f"{match['edge']:.1%}   "
              f"{match['kelly_fraction']:.2%}   "
              f"{match['recommendation']:<40} "
              f"{mkt['question'][:50]}")
    
    # Summary stats
    print("\n" + "="*140)
    print("=== SIGNAL QUALITY (Post-Validation) ===")
    print("="*140)
    
    # Confidence distribution
    high_conf = sum(1 for _, m in flat if m['confidence'] > 0.60)
    med_conf = sum(1 for _, m in flat if 0.40 <= m['confidence'] <= 0.60)
    low_conf = sum(1 for _, m in flat if m['confidence'] < 0.40)
    
    print(f"\n📊 Confidence Distribution:")
    print(f"   High (>60%): {high_conf}")
    print(f"   Medium (40-60%): {med_conf}")
    print(f"   Low (<40%): {low_conf}")
    
    # Edge distribution
    large_edge = sum(1 for _, m in flat if m['edge'] > 0.20)
    med_edge = sum(1 for _, m in flat if 0.15 <= m['edge'] <= 0.20)
    small_edge = sum(1 for _, m in flat if m['edge'] < 0.15)
    
    print(f"\n📈 Edge Distribution:")
    print(f"   Large (>20%): {large_edge}")
    print(f"   Medium (15-20%): {med_edge}")
    print(f"   Small (<15%): {small_edge}")
    
    # Directional
    buy_yes = sum(1 for _, m in flat if '🟢' in m['recommendation'])
    buy_no = sum(1 for _, m in flat if '🔴' in m['recommendation'])
    weak = sum(1 for _, m in flat if '⚠️' in m['recommendation'])
    
    print(f"\n📈 Directional Breakdown:")
    print(f"   🟢 BUY YES: {buy_yes}")
    print(f"   🔴 BUY NO: {buy_no}")
    print(f"   ⚠️ MODERATE: {weak}")
    
    # Signal composition for top 5
    print(f"\n🔍 Top 5 Signal Breakdown:")
    for rank, (tid, match) in enumerate(flat[:5], 1):
        print(f"\n{rank}. {match['market']['question'][:60]}...")
        sd = match['signal_data']
        print(f"   Model: {match['model_estimate']:.1%} vs Market: {match['market_price']:.1%}")
        
        if sd.get('probability_estimate'):
            print(f"   → Probability extraction: {sd['probability_estimate']:.1%} ({sd['num_prob_mentions']} mentions)")
        
        print(f"   → Sentiment: {sd['sentiment_estimate']:.1%} (conf: {sd['sentiment_confidence']:.2f})")
        print(f"   → Recalibrated confidence: {match['confidence']:.1%}")


def export_market_opportunities(topic_markets: Dict, topic_model, output_dir: str = None):
    """Export opportunities"""
    import csv
    from datetime import datetime
    import os

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"alphahunt_v3.1_validated_{timestamp}.csv"

    # Ensure output directory exists and build full path
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
    else:
        filepath = filename

    print(f"\n📊 Exporting to {filepath}...")

    flat = [(tid, m) for tid, markets in topic_markets.items() for m in markets]
    flat.sort(key=lambda x: x[1]["alpha_score"], reverse=True)

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Rank', 'Platform', 'Market_Question', 'Market_URL',
            'Market_Price', 'Model_Estimate', 'Edge', 'Alpha_Score',
            'Confidence', 'Kelly_Fraction', 'Recommendation',
            'Num_Prob_Mentions', 'Num_Articles', 'Hours_Until_Close',
            'Validated'
        ])

        for rank, (tid, match) in enumerate(flat, 1):
            market = match['market']
            sd = match['signal_data']

            writer.writerow([
                rank,
                market['platform'],
                market['question'],
                market['url'],
                f"{match['market_price']:.3f}",
                f"{match['model_estimate']:.3f}",
                f"{match['edge']:.3f}",
                f"{match['alpha_score']:.3f}",
                f"{match['confidence']:.3f}",
                f"{match['kelly_fraction']:.4f}",
                match['recommendation'],
                sd['num_prob_mentions'],
                sd['num_articles'],
                f"{market.get('hours_until_close', 0):.1f}",
                'YES'  # All exported opportunities passed validation
            ])

    print(f"✅ Exported {len(flat)} validated opportunities to {filepath}")
