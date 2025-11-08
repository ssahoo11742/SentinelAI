"""
question_retriever.py  –  replaces BERTopic with question-centric retrieval
"""
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import torch

_device = "cuda:0" if torch.cuda.is_available() else "cpu"
_encoder = None                     # lazy load


def _get_encoder():
    global _encoder
    if _encoder is None:
        _encoder = SentenceTransformer("all-MiniLM-L6-v2", device=_device)
    return _encoder


def retrieve_topk_for_question(articles: List[Dict],
                               question: str,
                               k: int = 30) -> List[Dict]:
    """
    Return the k articles most semantically similar to the market question.
    Adds a key 'q_score' (cosine similarity) to each returned article.
    """
    enc = _get_encoder()

    # embed question once
    q_emb = enc.encode(question, normalize_embeddings=True, convert_to_numpy=True)

    # build article texts  (title + first 400 tokens of body)
    texts = [
        (a.get("title", "") + " " + a.get("fulltext", "")[:400]).strip()
        for a in articles
    ]
    if not texts:
        return []

    # embed articles
    a_emb = enc.encode(texts, normalize_embeddings=True, convert_to_numpy=True)

    # cosine similarity
    scores = a_emb @ q_emb
    top_idx = np.argsort(scores)[::-1][:k]

    out = []
    for i in top_idx:
        articles[i]["q_score"] = float(scores[i])
        out.append(articles[i])
    return out