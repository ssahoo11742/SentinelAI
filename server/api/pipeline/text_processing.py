import requests
from bs4 import BeautifulSoup

import re

from newsapi import NewsApiClient
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import HEADERS




def fetch_article_body(url):
    """Fetch full article content"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        
        for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 
                                       'aside', 'form', 'button', 'iframe']):
            element.decompose()
        
        for element in soup.find_all(class_=re.compile(r'(nav|menu|sidebar|footer|header|cookie|newsletter|subscribe|comment|social|share)', re.I)):
            element.decompose()
        
        for element in soup.find_all(id=re.compile(r'(nav|menu|sidebar|footer|header|cookie|newsletter|subscribe|comment|social|share)', re.I)):
            element.decompose()
        
        article_content = None
        article_selectors = [
            'article', '[class*="article"]', '[class*="content"]',
            '[class*="post"]', '[id*="article"]', '[id*="content"]', 'main'
        ]
        
        for selector in article_selectors:
            article_content = soup.select_one(selector)
            if article_content:
                paragraphs = article_content.find_all("p")
                break
        
        if not article_content:
            paragraphs = soup.find_all("p")
        
        text_parts = []
        for p in paragraphs:
            p_text = p.get_text(strip=True)
            if len(p_text) > 40:
                text_parts.append(p_text)
        
        text = " ".join(text_parts)
        if len(text) > 50000:
            text = text[:50000]
        if len(text) > 100000:
            return None
            
        return text if len(text) > 300 else None
        
    except:
        return None

def collect_articles_from_newsapi(api_key, query, from_date, to_date, max_articles=100, max_workers=15):
    """Collect articles from NewsAPI"""
    newsapi = NewsApiClient(api_key=api_key)
    print(f"🔍 Fetching articles from NewsAPI for: {query}")
    
    try:
        response = newsapi.get_everything(
            q=query, from_param=from_date, to=to_date,
            language='en', sort_by='relevancy',
            page_size=min(max_articles, 100)
        )
        
        articles_data = response.get('articles', [])
        print(f"  📰 Found {len(articles_data)} articles")
        
        enhanced_articles = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_article = {
                executor.submit(fetch_article_body, article.get('url')): article
                for article in articles_data
            }
            
            completed = 0
            for future in as_completed(future_to_article):
                completed += 1
                article = future_to_article[future]
                
                try:
                    full_text = future.result()
                    if full_text and len(full_text) > 300:
                        enhanced_articles.append({
                            'title': article.get('title', 'No title'),
                            'link': article.get('url'),
                            'snippet': article.get('description', ''),
                            'date': article.get('publishedAt', ''),
                            'fulltext': full_text
                        })
                        print(f"  [{completed}/{len(articles_data)}] ✅")
                    else:
                        print(f"  [{completed}/{len(articles_data)}] ⚠️ Skipped")
                except:
                    print(f"  [{completed}/{len(articles_data)}] ❌")
        
        print(f"  ✅ Fetched {len(enhanced_articles)} articles")
        return enhanced_articles
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return []
