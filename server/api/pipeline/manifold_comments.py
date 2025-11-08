"""
manifold_comments.py - Fetch and analyze Manifold market comments
Comments often contain insider info, expert analysis, and sentiment shifts
"""
import requests
from typing import List, Dict, Optional
import re
from transformers import pipeline
import numpy as np

# Global classifier (lazy init)
_classifier = None


def _get_classifier():
    global _classifier
    if _classifier is None:
        print("📥 Loading zero-shot classifier for comments...")
        _classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=0 if __import__('torch').cuda.is_available() else -1
        )
        print("  ✓ Loaded")
    return _classifier


# ============================================================================
# MANIFOLD COMMENTS API
# ============================================================================

def fetch_manifold_comments(market_id: str, limit: int = 50) -> List[Dict]:
    """
    Fetch comments for a Manifold market using their REST API
    
    Returns list of comments with: {text, createdTime, userName, betAmount, betOutcome}
    """
    try:
        # Manifold v0 API endpoint for comments
        url = f"https://api.manifold.markets/v0/comments"
        params = {
            'contractId': market_id,
            'limit': limit
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        comments_data = response.json()
        
        comments = []
        for comment in comments_data:
            # Skip deleted or hidden comments
            if comment.get('hidden') or comment.get('deleted'):
                continue
            
            text = comment.get('text', '')
            if len(text) < 20:  # Skip very short comments
                continue
            
            # Extract betting context if available
            bet_info = comment.get('betId')
            bet_amount = comment.get('betAmount', 0)
            bet_outcome = comment.get('betOutcome', '')
            
            comments.append({
                'text': text,
                'created_time': comment.get('createdTime', 0),
                'user': comment.get('userName', 'Anonymous'),
                'bet_amount': bet_amount,
                'bet_outcome': bet_outcome,
                'has_bet': bet_info is not None
            })
        
        return comments
        
    except Exception as e:
        print(f"  ⚠️ Failed to fetch comments for {market_id}: {e}")
        return []


# ============================================================================
# COMMENT QUALITY FILTERING
# ============================================================================

def filter_quality_comments(comments: List[Dict], min_length: int = 50) -> List[Dict]:
    """
    Filter for substantive comments (not just "nice market!" or emojis)
    """
    quality_comments = []
    
    # Patterns indicating low-quality comments
    low_quality_patterns = [
        r'^(nice|good|great|cool|lol|lmao|based)\s*(market)?[\s!.]*$',
        r'^\s*[👍👎🔥💯😂❤️]+\s*$',
        r'^[@#]\w+\s*$'
    ]
    
    # Patterns indicating high-quality analysis
    high_quality_indicators = [
        r'\d+%',  # Probability estimates
        r'(because|since|given|considering|based on)',  # Reasoning
        r'(data|evidence|source|study|poll|forecast)',  # Evidence references
        r'(however|although|but|yet)',  # Nuanced thinking
        r'(likely|probably|unlikely|expect)',  # Predictions
        r'(model|analysis|estimate|calculate)',  # Analytical terms
    ]
    
    for comment in comments:
        text = comment['text'].strip().lower()
        
        # Skip if too short
        if len(text) < min_length:
            continue
        
        # Skip low-quality patterns
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in low_quality_patterns):
            continue
        
        # Boost score for high-quality indicators
        quality_score = sum(
            1 for pattern in high_quality_indicators 
            if re.search(pattern, text, re.IGNORECASE)
        )
        
        # Add quality score to comment
        comment['quality_score'] = quality_score
        
        # Keep if has any quality indicators or is long enough
        if quality_score > 0 or len(text) > 100:
            quality_comments.append(comment)
    
    # Sort by quality score
    quality_comments.sort(key=lambda x: x['quality_score'], reverse=True)
    
    return quality_comments


# ============================================================================
# COMMENT SENTIMENT ANALYSIS
# ============================================================================

def analyze_comment_sentiment(comments: List[Dict], market_question: str) -> Dict:
    """
    Use zero-shot classification to determine if comments support YES or NO
    Returns: {'sentiment': float, 'confidence': float, 'analyzed_count': int}
    """
    if not comments:
        return {'sentiment': 0.5, 'confidence': 0.0, 'analyzed_count': 0}
    
    classifier = _get_classifier()
    
    # Simplified hypotheses
    hypotheses = [
        f"This supports: {market_question}",
        f"This opposes: {market_question}"
    ]
    
    sentiment_scores = []
    confidence_scores = []
    
    # Analyze top comments
    for comment in comments[:20]:
        text = comment['text'][:800]  # Truncate for speed
        
        try:
            result = classifier(
                text,
                candidate_labels=hypotheses,
                multi_label=False
            )
            
            # Get probability for "supports" hypothesis
            supports_idx = result['labels'].index(hypotheses[0])
            prob_yes = result['scores'][supports_idx]
            
            # Weight by quality score
            weight = 1.0 + (comment.get('quality_score', 0) * 0.2)
            
            # Additional weight if user placed a bet
            if comment.get('has_bet') and comment.get('bet_amount', 0) > 0:
                weight *= 1.3
                
                # Strong signal if bet aligns with comment sentiment
                if comment.get('bet_outcome') == 'YES' and prob_yes > 0.6:
                    weight *= 1.2
                elif comment.get('bet_outcome') == 'NO' and prob_yes < 0.4:
                    weight *= 1.2
            
            sentiment_scores.append(prob_yes * weight)
            confidence_scores.append((abs(prob_yes - 0.5) * 2) * weight)
            
        except Exception as e:
            continue
    
    if not sentiment_scores:
        return {'sentiment': 0.5, 'confidence': 0.0, 'analyzed_count': 0}
    
    # Weighted average
    total_weight = sum(confidence_scores)
    if total_weight > 0:
        sentiment = sum(s for s in sentiment_scores) / total_weight
    else:
        sentiment = np.mean(sentiment_scores)
    
    avg_confidence = np.mean(confidence_scores)
    
    return {
        'sentiment': float(sentiment),
        'confidence': float(avg_confidence),
        'analyzed_count': len(sentiment_scores),
        'total_comments': len(comments)
    }


# ============================================================================
# EXTRACT QUANTITATIVE PREDICTIONS FROM COMMENTS
# ============================================================================

def extract_comment_predictions(comments: List[Dict]) -> List[float]:
    """
    Extract explicit probability predictions from comments
    Examples: "I think 70% chance", "My model says 45%", "60-40 split"
    """
    predictions = []
    
    patterns = [
        r'(\d+)%\s*(?:chance|probability|likely)',
        r'(?:chance|probability|odds).*?(\d+)%',
        r'(\d+)-(\d+)\s*(?:split|ratio)',
        r'(?:model|estimate|forecast).*?(\d+)%',
    ]
    
    for comment in comments:
        text = comment['text']
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if len(match.groups()) == 1:
                        prob = float(match.group(1)) / 100
                    else:
                        # Handle X-Y split (e.g., "60-40")
                        yes_pct = float(match.group(1))
                        no_pct = float(match.group(2))
                        prob = yes_pct / (yes_pct + no_pct)
                    
                    if 0.05 <= prob <= 0.95:
                        # Weight by quality and bet amount
                        weight = 1.0 + comment.get('quality_score', 0) * 0.1
                        if comment.get('bet_amount', 0) > 100:
                            weight *= 1.5
                        
                        predictions.append(prob)
                except:
                    continue
    
    return predictions


# ============================================================================
# COMPREHENSIVE COMMENT ANALYSIS
# ============================================================================

def analyze_market_comments(market: Dict) -> Optional[Dict]:
    """
    Complete comment analysis pipeline
    Returns: {'sentiment', 'confidence', 'predictions', 'quality'}
    """
    if market['platform'] != 'manifold':
        return None
    
    market_id = market['market_id']
    question = market['question']
    
    # Fetch comments
    comments = fetch_manifold_comments(market_id, limit=50)
    
    if len(comments) < 3:
        return None
    
    # Filter for quality
    quality_comments = filter_quality_comments(comments, min_length=40)
    
    if len(quality_comments) < 2:
        return None
    
    # Sentiment analysis
    sentiment_result = analyze_comment_sentiment(quality_comments, question)
    
    # Extract explicit predictions
    predictions = extract_comment_predictions(quality_comments)
    
    # Calculate overall quality
    avg_quality = np.mean([c.get('quality_score', 0) for c in quality_comments])
    bet_count = sum(1 for c in quality_comments if c.get('has_bet'))
    
    return {
        'sentiment': sentiment_result['sentiment'],
        'confidence': sentiment_result['confidence'],
        'predictions': predictions,
        'avg_prediction': np.mean(predictions) if predictions else None,
        'quality_score': avg_quality,
        'comment_count': len(quality_comments),
        'bet_count': bet_count,
        'analyzed_count': sentiment_result['analyzed_count']
    }


# ============================================================================
# BATCH COMMENT ANALYSIS
# ============================================================================

def enrich_manifold_markets_with_comments(markets: List[Dict]) -> List[Dict]:
    """
    Batch analyze comments for Manifold markets
    """
    print("\n💬 Analyzing Manifold market comments...")
    
    manifold_markets = [m for m in markets if m['platform'] == 'manifold']
    
    if not manifold_markets:
        print("  No Manifold markets to analyze")
        return markets
    
    analyzed_count = 0
    
    for market in manifold_markets:
        comment_analysis = analyze_market_comments(market)
        
        if comment_analysis:
            market['comment_analysis'] = comment_analysis
            analyzed_count += 1
            
            if comment_analysis['comment_count'] > 5:
                print(f"  ✓ {market['question'][:50]}... -> {comment_analysis['comment_count']} quality comments, {comment_analysis['sentiment']:.2f} sentiment")
    
    print(f"\n✅ Analyzed comments for {analyzed_count}/{len(manifold_markets)} Manifold markets")
    
    return markets