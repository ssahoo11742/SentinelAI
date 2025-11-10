"""
Configuration for Prediction Market Analysis Pipeline
"""
import nltk
from nltk.corpus import stopwords
import spacy
from datetime import datetime, timedelta

nltk.download('stopwords', quiet=True)
STOPWORDS = set(stopwords.words('english'))

# API Configuration
NEWSAPI_KEY = '0c6458185614471e85f31fd67f473e69' # Hidden for security
TO_DATE = datetime.now().date()
FROM_DATE = TO_DATE - timedelta(days=5)  # Shorter window for more relevant news

FROM_DATE = FROM_DATE.strftime('%Y-%m-%d')
TO_DATE = TO_DATE.strftime('%Y-%m-%d')

# HTTP Headers
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Text Processing Settings
BOILERPLATE_TERMS = {
    'email', 'digest', 'homepage', 'feed', 'newsletter', 'subscribe', 'subscription',
    'menu', 'navigation', 'sidebar', 'footer', 'header', 'cookie', 'privacy',
    'policy', 'terms', 'service', 'copyright', 'reserved', 'rights', 'contact',
    'facebook', 'twitter', 'instagram', 'linkedin', 'youtube', 'social', 'share',
    'comment', 'comments', 'reply', 'login', 'signup', 'register', 'search',
    'advertisement', 'sponsored', 'promo', 'promotion'
}

STOPWORDS.update(BOILERPLATE_TERMS)

nlp = spacy.load("en_core_web_sm")
nlp.max_length = 100000

# Analysis Settings
MIN_ARTICLE_LENGTH = 400
MAX_ARTICLE_LENGTH = 100000
MAX_TEXT_LENGTH = 50000
MIN_ARTICLES_FOR_ANALYSIS = 5
MAX_ARTICLES = 400

# Topic Modeling Settings
MIN_TOPIC_SIZE = 5  # Require more articles per topic for significance
TOP_N_MARKETS = 20
SIMILARITY_THRESHOLD = 0.15  # Higher threshold for better matches

# Multithreading
MAX_WORKERS_ARTICLES = 15
MAX_WORKERS_MARKETS = 10

# Inefficiency Detection Thresholds
MIN_CONFIDENCE_GAP = 0.15  # Minimum gap between market odds and news
MIN_SENTIMENT_CONFIDENCE = 0.5  # Minimum confidence in sentiment
MIN_LIQUIDITY = 1000  # Minimum liquidity in USD
MAX_MARKET_AGE_HOURS = 720  # 30 days

# Search Queries - Focused on verifiable events
PREDICTION_TOPIC_GROUPS = [
    # Politics & Elections - specific and verifiable
    "election results OR polling data OR primary results OR congressional race",
    "presidential race OR candidate polling OR swing state OR electoral college",
    
    # Sports - verifiable outcomes
    "nfl playoff predictions OR super bowl odds OR championship game",
    "nba finals OR world series OR stanley cup OR tournament bracket",
    
    # Crypto & Finance - measurable events
    "bitcoin price prediction OR ethereum forecast OR crypto regulation",
    "federal reserve decision OR interest rate cut OR inflation report",
    
    # Technology - specific product launches
    "ai model release OR gpt launch OR tech product announcement",
    "earnings report OR ipo filing OR merger announcement",
    
    # Economics - measurable indicators
    "gdp growth OR unemployment rate OR jobs report OR economic forecast",
    "recession indicators OR market crash OR bull market OR bear market",
    
    # Weather - verifiable events
    "hurricane forecast OR winter storm prediction OR temperature record",
    "drought conditions OR flood warning OR climate pattern"
]

# Market-Specific NLP Entities to Extract
MARKET_ENTITY_TYPES = {
    'PERSON',      # For elections, entertainment
    'ORG',         # For business, sports teams
    'GPE',         # For geography-based events
    'DATE',        # For time-sensitive events
    'EVENT',       # For named events
    'MONEY',       # For financial markets
    'PERCENT',     # For polling, odds
    'CARDINAL'     # For scores, numbers
}

# Legacy variables (for compatibility)
GENERIC_NOUNS = {
    "business", "company", "market", "economy", "government", 
    "state", "people", "industry"
}

COMMON_WORD_BLACKLIST = set([
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    'am', 'an', 'as', 'at', 'be', 'by', 'do', 'go', 'he', 'hi', 'if',
    'in', 'is', 'it', 'me', 'my', 'no', 'of', 'on', 'or', 'so', 'to',
    'up', 'us', 'we', 'all', 'and', 'are', 'but', 'can', 'for', 'had',
    'has', 'her', 'him', 'his', 'how', 'its', 'let', 'may', 'new', 'not',
    'now', 'old', 'one', 'our', 'out', 'own', 'run', 'saw', 'say', 'see',
    'set', 'she', 'sit', 'six', 'ten', 'the', 'too', 'top', 'two', 'use',
    'was', 'way', 'who', 'why', 'win', 'yes', 'yet', 'you'
])

TOP_N_COMPANIES = TOP_N_MARKETS  # Alias for compatibility
TOPIC_GROUPS = PREDICTION_TOPIC_GROUPS  # Alias for compatibility