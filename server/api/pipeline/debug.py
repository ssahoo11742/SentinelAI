"""
diagnostic_debug.py - Debug why you're getting 0 opportunities

Add this BEFORE the filter in matcher_v3.py to see what's happening
"""
from typing import List, Dict
import numpy as np
def diagnose_filtering_cascade(
    markets: List[Dict],
    articles: List[Dict],
    classifier
) -> None:
    """
    Show exactly where opportunities are being filtered out
    """
    print("\n" + "="*80)
    print("🔍 DIAGNOSTIC: Filtering Cascade Analysis")
    print("="*80)
    
    from question_retriever import retrieve_topk_for_question
    from manifold_bias import calibrated_prob
    from universal_signals import extract_all_signals
    from validation import passes_sanity_checks, recalibrate_confidence
    
    stats = {
        'total_markets': len(markets),
        'insufficient_articles': 0,
        'low_alpha': 0,
        'failed_sanity': 0,
        'passed_all': 0
    }
    
    sanity_failures = {}
    alpha_distribution = []
    prob_mention_distribution = []
    
    print(f"\n📊 Analyzing {len(markets)} markets...\n")
    
    for idx, market in enumerate(markets[:20]):  # Sample first 20
        question = market['question']
        
        # Step 1: Article retrieval
        relevant = retrieve_topk_for_question(articles, question, k=50)
        
        if len(relevant) < 3:
            stats['insufficient_articles'] += 1
            continue
        
        # Step 2: Calibrate
        if market['platform'] == 'manifold':
            market['yes_price'] = calibrated_prob(market['yes_price'])
        
        # Step 3: Extract signals
        signal_data = extract_all_signals(relevant, question, classifier)
        
        num_probs = signal_data['num_prob_mentions']
        prob_mention_distribution.append(num_probs)
        
        # Step 4: Calculate alpha (simplified)
        market_price = market['yes_price']
        model_estimate = signal_data['final_estimate']
        edge = abs(model_estimate - market_price)
        
        confidence = recalibrate_confidence(signal_data, market, relevant)
        
        # Simple alpha calculation
        alpha_score = edge * confidence * 2.0  # Simplified
        alpha_distribution.append(alpha_score)
        
        # Check minimum alpha
        if alpha_score < 0.15:
            stats['low_alpha'] += 1
            print(f"  ❌ Alpha too low ({alpha_score:.3f}): {question[:50]}...")
            print(f"     Edge: {edge:.1%}, Conf: {confidence:.1%}, Probs: {num_probs}")
            continue
        
        # Step 5: Sanity checks
        passes, reason = passes_sanity_checks(market, signal_data, classifier, verbose=False)
        
        if not passes:
            stats['failed_sanity'] += 1
            sanity_failures[reason] = sanity_failures.get(reason, 0) + 1
            print(f"  ⚠️ Failed sanity: {question[:50]}...")
            print(f"     Reason: {reason}")
            print(f"     Edge: {edge:.1%}, Conf: {confidence:.1%}, Probs: {num_probs}")
            continue
        
        # Passed everything!
        stats['passed_all'] += 1
        print(f"  ✅ PASSED: {question[:50]}...")
        print(f"     Edge: {edge:.1%}, Conf: {confidence:.1%}, Probs: {num_probs}, Alpha: {alpha_score:.3f}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 DIAGNOSTIC SUMMARY")
    print("="*80)
    
    print(f"\n🎯 Filtering Cascade:")
    print(f"  Total markets analyzed: {stats['total_markets']}")
    print(f"  ❌ Insufficient articles (<3): {stats['insufficient_articles']}")
    print(f"  ❌ Low alpha score (<0.15): {stats['low_alpha']}")
    print(f"  ❌ Failed sanity checks: {stats['failed_sanity']}")
    print(f"  ✅ Passed all filters: {stats['passed_all']}")
    
    if sanity_failures:
        print(f"\n🚫 Top Sanity Check Failures:")
        for reason, count in sorted(sanity_failures.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   • {reason}: {count}")
    
    if prob_mention_distribution:
        print(f"\n📈 Probability Mention Distribution:")
        print(f"   Mean: {np.mean(prob_mention_distribution):.1f}")
        print(f"   Median: {np.median(prob_mention_distribution):.1f}")
        print(f"   Max: {np.max(prob_mention_distribution):.0f}")
        print(f"   Markets with 0 mentions: {sum(1 for x in prob_mention_distribution if x == 0)}")
        print(f"   Markets with 5+ mentions: {sum(1 for x in prob_mention_distribution if x >= 5)}")
    
    if alpha_distribution:
        print(f"\n📊 Alpha Score Distribution:")
        print(f"   Mean: {np.mean(alpha_distribution):.3f}")
        print(f"   Median: {np.median(alpha_distribution):.3f}")
        print(f"   Max: {np.max(alpha_distribution):.3f}")
        print(f"   Above 0.15 threshold: {sum(1 for x in alpha_distribution if x >= 0.15)}")
    
    print("\n" + "="*80)
    print("💡 RECOMMENDATIONS")
    print("="*80)
    
    # Recommendations based on stats
    if stats['insufficient_articles'] > stats['total_markets'] * 0.3:
        print("\n⚠️ HIGH ARTICLE FILTERING (>30% markets)")
        print("   • Try: Increase k in retrieve_topk_for_question (50 → 100)")
        print("   • Try: Collect more diverse news sources")
    
    if stats['low_alpha'] > stats['total_markets'] * 0.5:
        print("\n⚠️ MANY LOW ALPHA SCORES (>50% markets)")
        if np.mean(prob_mention_distribution) < 2:
            print("   • Root cause: Very few probability mentions in articles")
            print("   • Try: Expand date range (more articles)")
            print("   • Try: Lower min_edge threshold (but carefully)")
        else:
            print("   • Root cause: Low confidence scores")
            print("   • Try: Adjust recalibrate_confidence() weights")
    
    if stats['failed_sanity'] > stats['passed_all'] * 2:
        print("\n⚠️ SANITY CHECKS TOO STRICT")
        print("   • Top failure reasons shown above")
        print("   • Consider relaxing specific checks that dominate")
    
    if stats['passed_all'] == 0:
        print("\n❌ ZERO OPPORTUNITIES - SYSTEM TOO CONSERVATIVE")
        print("   • Option 1: Gradually relax filters (see recommendations above)")
        print("   • Option 2: Check if articles match market domains")
        print("   • Option 3: Verify probability extraction is working")


# HOW TO USE:
# In matcher_v3.py, in match_markets_to_topics(), ADD this BEFORE the main loop:
#
# if True:  # Set to False to disable diagnostics
#     diagnose_filtering_cascade(markets, articles, classifier)
#     return {}  # Exit early after diagnostics