"""
universal_signals.py - Domain-agnostic signal extraction
FIXED VERSION: More conservative, fewer false positives
"""
import re
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timezone
from collections import Counter


# ============================================================================
# ENTITY EXTRACTION
# ============================================================================

def extract_key_entities(text: str) -> List[str]:
    """Extract key entities from question for validation"""
    stop_words = {'will', 'the', 'be', 'in', 'by', 'on', 'at', 'to', 'a', 'an', 
                  'is', 'are', 'was', 'were', 'have', 'has', 'had', 'before', 'after'}
    
    words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b|\b[a-z]{4,}\b', text)
    entities = [w for w in words if w.lower() not in stop_words]
    
    return list(set(entities))[:10]


def is_comparative_question(question: str) -> bool:
    """Detect if question is comparing two entities"""
    comparative_words = ['vs', 'versus', 'flip', 'overtake', 'beat', 'surpass', 
                        'outperform', 'better than', 'more than']
    return any(word in question.lower() for word in comparative_words)


# ============================================================================
# IMPROVED PROBABILITY EXTRACTION
# ============================================================================

def extract_all_probabilities(text: str, question: str = "", context_window: int = 200) -> List[Tuple[float, str, float]]:
    """
    Extract probabilities with STRICT validation
    Only returns probabilities actually relevant to the question
    """
    results = []
    
    # Extract entities for validation
    question_entities = extract_key_entities(question) if question else []
    is_comparative = is_comparative_question(question)
    
    # Pattern 1: Explicit percentages
    percent_patterns = [
        (r'(\d+(?:\.\d+)?)\s*%', 1.0),
        (r'(\d+(?:\.\d+)?)\s*percent', 1.0),
    ]
    
    for pattern, confidence in percent_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                prob = float(match.group(1)) / 100
                if not (0.01 <= prob <= 0.99):
                    continue
                
                start = max(0, match.start() - context_window)
                end = min(len(text), match.end() + context_window)
                context = text[start:end]
                context_lower = context.lower()
                
                # STRICT VALIDATION
                if question_entities:
                    entity_matches = sum(1 for ent in question_entities if ent.lower() in context_lower)
                    
                    # Comparative questions need BOTH entities
                    required_matches = len(question_entities) if is_comparative else max(1, len(question_entities) // 2)
                    
                    if entity_matches < required_matches:
                        continue
                    
                    # Boost confidence for multiple entity matches
                    if entity_matches >= len(question_entities):
                        confidence *= 1.5
                    elif entity_matches >= required_matches:
                        confidence *= 1.2
                
                # Boost for probability keywords
                if any(kw in context_lower for kw in ['chance', 'probability', 'odds', 'forecast', 'estimate', 'poll', 'predict']):
                    confidence *= 1.3
                
                # Penalize if near year dates (often GDP %, not probabilities)
                if re.search(r'20\d{2}', context):
                    confidence *= 0.6
                
                # Penalize if near financial terms (price changes, not probabilities)
                if any(term in context_lower for term in ['revenue', 'profit', 'sales', 'growth rate', 'increase by']):
                    confidence *= 0.5
                
                results.append((prob, context, min(1.0, confidence)))
            except:
                continue
    
    # Pattern 2: Fractions
    fraction_patterns = [
        r'(\d+)\s*in\s*(\d+)',
        r'(\d+)\s*out\s*of\s*(\d+)',
        r'(\d+)\s*to\s*(\d+)',
    ]
    
    for pattern in fraction_patterns:
        for match in re.finditer(pattern, text):
            try:
                num1 = float(match.group(1))
                num2 = float(match.group(2))
                
                prob1 = num1 / (num1 + num2)
                prob2 = num1 / num2 if num2 != 0 else None
                
                for prob in [prob1, prob2]:
                    if prob and 0.01 <= prob <= 0.99:
                        start = max(0, match.start() - context_window)
                        end = min(len(text), match.end() + context_window)
                        context = text[start:end]
                        context_lower = context.lower()
                        
                        conf = 0.6
                        
                        if question_entities:
                            entity_matches = sum(1 for ent in question_entities if ent.lower() in context_lower)
                            required_matches = len(question_entities) if is_comparative else 1
                            
                            if entity_matches < required_matches:
                                continue
                            if entity_matches >= required_matches:
                                conf *= 1.2
                        
                        results.append((prob, context, conf))
            except:
                continue
    
    # Pattern 3: Qualitative (LOWER weights)
    qualitative_map = {
        r'\b(certain|definitely|surely)\b': (0.95, 0.35),
        r'\b(very likely|highly likely|probable)\b': (0.75, 0.45),
        r'\b(likely|expected|probably)\b': (0.65, 0.40),
        r'\b(possible|maybe|perhaps|could)\b': (0.50, 0.25),
        r'\b(unlikely|doubtful)\b': (0.35, 0.40),
        r'\b(very unlikely|highly unlikely)\b': (0.25, 0.45),
        r'\b(impossible|definitely not)\b': (0.05, 0.35),
    }
    
    for pattern, (prob, conf) in qualitative_map.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, match.start() - context_window)
            end = min(len(text), match.end() + context_window)
            context = text[start:end]
            context_lower = context.lower()
            
            if question_entities:
                entity_matches = sum(1 for ent in question_entities if ent.lower() in context_lower)
                if entity_matches < 1:
                    continue
            
            results.append((prob, context, conf))
    
    return results


def calculate_relevance_score(context: str, question: str) -> float:
    """Relevance score with stricter thresholds"""
    question_words = set(re.findall(r'\b\w{4,}\b', question.lower()))
    context_words = set(re.findall(r'\b\w{4,}\b', context.lower()))
    
    if not question_words:
        return 0.0
    
    overlap = len(question_words & context_words)
    jaccard = overlap / len(question_words | context_words) if question_words | context_words else 0
    
    # Stricter boost requirements
    boost = 1.0
    if overlap >= 2:
        boost = 1.5
    elif overlap >= 1:
        boost = 1.2
    
    return min(1.0, jaccard * boost)



def aggregate_probabilities(
    probs: List[Tuple[float, str, float, Dict]], 
    question: str,
    time_weights: Optional[np.ndarray] = None,
    articles: Optional[List[Dict]] = None
) -> Optional[float]:
    """
    Aggregate with stricter relevance filtering but now with source credibility and time weights.
    probs: list of tuples (prob, context, confidence, article_meta)
    """
    if not probs:
        return None

    weighted_probs = []
    weights = []

    for idx, (prob, context, confidence, article_meta) in enumerate(probs):
        relevance = calculate_relevance_score(context, question)

        # keep more possibilities but still require minimal relevance
        if relevance < 0.05:   # relaxed from 0.15 to 0.05 for coverage
            continue

        # source credibility
        try:
            src_cred = _get_source_credibility(article_meta)
        except:
            src_cred = _SOURCE_CREDIBILITY['__default__']

        weight = confidence * relevance * src_cred

        if time_weights is not None and idx < len(time_weights):
            weight *= time_weights[idx]

        weighted_probs.append(prob)
        weights.append(weight)

    if not weighted_probs:
        return None

    arr = np.array(weighted_probs)
    weights_arr = np.array(weights)

    # Remove extreme outliers robustly
    if len(arr) > 4:
        mean = np.average(arr, weights=weights_arr)
        std = np.sqrt(np.average((arr - mean)**2, weights=weights_arr))
        mask = np.abs(arr - mean) <= 2.5 * std
        arr = arr[mask]
        weights_arr = weights_arr[mask]

    if len(arr) == 0:
        return None

    # normalize
    weights_arr = weights_arr / (weights_arr.sum() + 1e-12)

    return float(np.average(arr, weights=weights_arr))

# ============================================================================
# TIME DECAY
# ============================================================================

def calculate_time_weights(articles: List[Dict], market_hours: Optional[float] = None, tau: Optional[float] = None) -> np.ndarray:
    """
    Exponential time decay: w = exp(-age / tau)
    Adaptive tau: if market is near-term, use smaller tau (fast decay) so recent articles matter more;
    if market is long-term, use larger tau (slower decay).
    """
    now = datetime.now(timezone.utc)
    ages = []

    # adaptive tau heuristic
    if tau is None:
        if market_hours is None:
            tau = 36.0
        else:
            # map hours -> tau (hours/10 clipped), then limit to reasonable bounds
            derived = max(12.0, min(96.0, float(market_hours) / 10.0))
            # bias a bit toward recency
            tau = derived * 0.9

    for article in articles:
        published_at = article.get('publishedAt')
        if not published_at:
            ages.append(48.0)
            continue

        try:
            if isinstance(published_at, str):
                pub_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            else:
                pub_time = published_at

            age_hours = (now - pub_time).total_seconds() / 3600
            ages.append(max(0.1, age_hours))
        except:
            ages.append(48.0)

    ages = np.array(ages)
    # avoid division by zero
    if tau <= 0:
        tau = 36.0

    weights = np.exp(-ages / tau)

    # if all zeros (shouldn't happen), return uniform
    if weights.sum() == 0:
        weights = np.ones_like(weights)

    return weights / weights.sum()


# credibility mapping for common sources (extend as needed)
_SOURCE_CREDIBILITY = {
    # high credibility
    "new york times": 0.95,
    "the new york times": 0.95,
    "washington post": 0.92,
    "bbc": 0.90,
    "reuters": 0.93,
    "ap": 0.92,
    "associated press": 0.92,
    # medium credibility
    "cnn": 0.75,
    "bloomberg": 0.85,
    "fortune": 0.78,
    "the guardian": 0.80,
    # lower credibility (social, blogs)
    "twitter": 0.40,
    "x": 0.40,
    "reddit": 0.35,
    "medium": 0.45,
    # default
    "__default__": 0.65
}

def _get_source_credibility(article: Dict) -> float:
    """
    Determine a credibility multiplier from article['source']['name'].
    Returns value in (0.3..1.0) - higher means more trusted.
    """
    src = None
    if isinstance(article.get('source'), dict):
        src = article['source'].get('name', '')
    else:
        src = article.get('source', '') or article.get('source_name', '')
    if not src:
        return _SOURCE_CREDIBILITY['__default__']
    key = src.strip().lower()
    # exact match then substring fallback
    if key in _SOURCE_CREDIBILITY:
        return _SOURCE_CREDIBILITY[key]
    for k, v in _SOURCE_CREDIBILITY.items():
        if k in key and k != '__default__':
            return v
    return _SOURCE_CREDIBILITY['__default__']



# ============================================================================
# SENTIMENT
# ============================================================================

def calculate_universal_sentiment(
    articles: List[Dict],
    question: str,
    classifier_model,
    max_articles: int = 15
) -> Tuple[float, float]:
    """Zero-shot sentiment classification"""
    time_weights = calculate_time_weights(articles)
    
    article_scores = []
    for idx, article in enumerate(articles[:300]):
        title = article.get('title', '')
        text = article.get('fulltext', '')[:500]
        combined = f"{title} {text}".lower()
        
        question_words = set(re.findall(r'\b\w{4,}\b', question.lower()))
        text_words = set(re.findall(r'\b\w{4,}\b', combined))
        
        overlap = len(question_words & text_words)
        relevance = overlap / len(question_words) if question_words else 0
        
        score = relevance * time_weights[idx]
        article_scores.append((idx, score, article))
    
    article_scores.sort(key=lambda x: x[1], reverse=True)
    top_articles = [a[2] for a in article_scores[:max_articles] if a[1] > 0.01]
    
    if len(top_articles) < 3:
        return 0.5, 0.1
    
    hypotheses = [
        f"YES: {question}",
        f"NO: {question}"
    ]
    
    sentiments = []
    confidences = []
    article_weights = []
    
    for article in top_articles:
        text = article.get('fulltext', '')[:1000]
        
        if len(text) < 100:
            continue
        
        try:
            result = classifier_model(
                text,
                candidate_labels=hypotheses,
                multi_label=False
            )
            
            yes_idx = result['labels'].index(hypotheses[0])
            prob_yes = result['scores'][yes_idx]
            
            sentiments.append(prob_yes)
            confidences.append(abs(prob_yes - 0.5) * 2)
            
            orig_idx = next(i for i, (j, _, a) in enumerate(article_scores) if a == article)
            article_weights.append(time_weights[orig_idx])
            
        except:
            continue
    
    if not sentiments:
        return 0.5, 0.1
    
    combined_weights = np.array(confidences) * np.array(article_weights)
    
    if combined_weights.sum() > 0:
        combined_weights = combined_weights / combined_weights.sum()
        sentiment = float(np.average(sentiments, weights=combined_weights))
    else:
        sentiment = float(np.mean(sentiments))
    
    avg_confidence = float(np.mean(confidences))
    
    return sentiment, avg_confidence


# ============================================================================
# MAIN SIGNAL EXTRACTION (FIXED)
# ============================================================================

def extract_all_signals(
    articles: List[Dict],
    question: str,
    classifier_model,
    market_hours: Optional[float] = None,
    market=None,
) -> Dict:
    """
    Extract signals with improved recency, source credibility, and a simple ensemble.
    Returns final_estimate plus provenance.
    """
    # 1. Time weights (adaptive)
    time_weights = calculate_time_weights(articles, market_hours=market_hours)

    # 2. Extract probabilities from articles (include article metadata for credibility)
    all_probs = []
    for idx, article in enumerate(articles[:150]):  # increased pool
        text = article.get('fulltext', '')[:5000]
        probs = extract_all_probabilities(text, question=question)
        for prob, context, conf in probs:
            all_probs.append((prob, context, conf, article))

    # 3. Aggregate probability mentions (source & time-weighted)
    prob_estimate = aggregate_probabilities(all_probs, question, time_weights=time_weights, articles=articles)

    # 4. Sentiment estimate (as before, but allow classifier to use more articles)
    sentiment, sentiment_conf = calculate_universal_sentiment(
        articles, question, classifier_model, max_articles=40
    )

    # 5. Build an ensemble: weights adapt to signal quality
    signals = []
    weights = []
    sources = []
    overall_confidence = 0.0

    num_prob_mentions = len(all_probs)

    # If we have explicit probability mentions, give them priority
    if prob_estimate is not None:
        signals.append(prob_estimate)
        # weight driven by number of prob mentions (log-scale) and average confidence
        prob_weight = 0.60 + min(0.25, np.log1p(num_prob_mentions) / 10.0)
        weights.append(prob_weight)
        sources.append(f"Probability Extraction ({num_prob_mentions} mentions)")

        # sentiment as secondary signal (weighted by sentiment_conf)
        if sentiment_conf > 0.20:
            signals.append(sentiment)
            weights.append(0.25 * sentiment_conf)
            sources.append(f"Sentiment (conf: {sentiment_conf:.2f})")

        overall_confidence = float(np.clip(np.mean([min(1.0, num_prob_mentions / 25.0), sentiment_conf, min(1.0, len(articles) / 40.0)]), 0.0, 1.0))

    else:
        # No explicit probabilities — use sentiment but allow it to move estimate
        dampening = 0.40  # you've already used 0.40; keep that but combine with source hint
        dampened_sentiment = 0.5 + (sentiment - 0.5) * dampening
        signals.append(dampened_sentiment)
        weights.append(1.0)
        sources.append(f"Sentiment Only (dampened, conf: {sentiment_conf:.2f})")
        overall_confidence = float(np.clip(min(0.35, sentiment_conf * 0.6), 0.0, 1.0))

    # Optional: incorporate external forecast if present in some article / market
    # (caller can later include market['external_forecast'] into signal_data)
    # normalize weights
    weights = np.array(weights, dtype=float)
    if weights.sum() == 0:
        weights = np.ones_like(weights)
    weights = weights / weights.sum()

    final_estimate = float(np.average(signals, weights=weights))
    # incorporate optional market-level external forecast if available
    ext = market.get('external_forecast') if isinstance(market, dict) else None
    if ext is not None:
        try:
            ext_val = float(ext)
            # blend: weight external forecast proportional to its declared confidence (if available)
            ext_weight = 0.15
            final_estimate = float((final_estimate * (1 - ext_weight)) + (ext_val * ext_weight))
        except:
            pass

    return {
        'final_estimate': final_estimate,
        'probability_estimate': prob_estimate,
        'sentiment_estimate': sentiment,
        'sentiment_confidence': sentiment_conf,
        'confidence': overall_confidence,
        'num_prob_mentions': num_prob_mentions,
        'num_articles': len(articles),
        'signal_sources': list(zip(sources, signals, weights))
    }