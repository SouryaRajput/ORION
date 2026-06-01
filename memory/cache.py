import json
import os
import threading
import time
from pathlib import Path

CACHE_FILE = Path("memory/semantic_cache.json")

# Lazy loading of sentence transformer model
_model = None
_model_lock = threading.Lock()

def get_model():
    global _model
    if _model is False:
        return None
    if _model is not None:
        return _model

    with _model_lock:
        if _model is False:
            return None
        if _model is not None:
            return _model

        try:
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            if os.getenv("SEMANTIC_CACHE_ALLOW_DOWNLOAD", "0") != "1":
                os.environ["HF_HUB_OFFLINE"] = "1"
            from sentence_transformers import SentenceTransformer
            print("[CACHE] Loading semantic cache model (all-MiniLM-L6-v2)...")
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            print("[CACHE] Semantic cache model loaded and ready.")
        except Exception as e:
            print(f"[CACHE] Semantic cache disabled: {e}")
            _model = False
            return None
    return _model

def preload_model():
    """Optionally warm the semantic model without slowing normal voice startup."""
    if os.getenv("SEMANTIC_CACHE_PRELOAD", "0") != "1":
        return
    threading.Thread(target=get_model, daemon=True, name="preload-cache-model").start()

def load_cache():
    if not CACHE_FILE.exists():
        return []

    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)  # Avoid indent to save space with embeddings

def get_cached_answer(question, semantic=True):
    # Skip ultra-short contextual phrases
    if len(question.split()) < 4:
        return None

    # Skip real-time, temporal, or dynamic queries
    dynamic_keywords = {
        "weather", "news", "today", "tonight", "tomorrow", "yesterday", 
        "now", "current", "currently", "latest", "score", "time", "date",
        "price", "stocks", "market", "live"
    }
    
    import re
    words = set(re.findall(r'\b\w+\b', question.lower()))
    if words.intersection(dynamic_keywords):
        print(f"[CACHE] Bypassing cache for dynamic query: '{question}'")
        return None

    cache = load_cache()
    if not cache:
        return None

    normalized_question = question.lower()
    for record in cache:
        if record["question"] == normalized_question:
            print("[CACHE HIT] Exact question match found.")
            return record["answer"]

    # Embedding inference is too expensive for the voice audio-start path.
    if not semantic:
        return None

    model = get_model()
    if not model:
        return None

    query_embedding = model.encode(normalized_question, convert_to_tensor=True)
    
    from sentence_transformers import util
    best_match = None
    highest_score = 0.0

    for record in cache:
        score = util.cos_sim(query_embedding, record['embedding']).item()
        if score > highest_score:
            highest_score = score
            best_match = record['answer']

    if highest_score > 0.92:
        print(f"[CACHE HIT] Semantic match found (Score: {highest_score:.2f})")
        return best_match

    return None

def store_answer(question, answer):
    if len(question.split()) < 4:
        return

    dynamic_keywords = {
        "weather", "news", "today", "tonight", "tomorrow", "yesterday", 
        "now", "current", "currently", "latest", "score", "time", "date",
        "price", "stocks", "market", "live"
    }
    
    import re
    words = set(re.findall(r'\b\w+\b', question.lower()))
    if words.intersection(dynamic_keywords):
        return

    model = get_model()
    if not model:
        return

    cache = load_cache()
    embedding = model.encode(question.lower()).tolist()

    # Update if exact question already exists
    for record in cache:
        if record['question'] == question.lower():
            record['answer'] = answer
            record['embedding'] = embedding
            save_cache(cache)
            return

    # Otherwise append new
    cache.append({
        "question": question.lower(),
        "answer": answer,
        "embedding": embedding
    })
    
    # Prune old cache to keep it fast
    if len(cache) > 1000:
        cache = cache[-1000:]

    save_cache(cache)
