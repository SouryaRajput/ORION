from memory.manager import load_memory
import re
import math
import time

MAX_MEMORY_LINES = 5
SCORE_THRESHOLD = 0.05

def tf(word, doc):
    words = doc.split()
    if not words: return 0
    return words.count(word) / len(words)

def build_memory_context(query=None):
    memory = load_memory()
    if not memory:
        return ""

    docs = []
    for cat, items in memory.items():
        if not isinstance(items, dict): continue
        for key, entry in items.items():
            val = entry["value"] if isinstance(entry, dict) else entry
            ts = entry["timestamp"] if isinstance(entry, dict) else 0
            imp = entry["importance"] if isinstance(entry, dict) else 1.0
            
            doc_text = f"{cat} {key} {val}".lower()
            docs.append({
                "text": doc_text,
                "raw": f"{key}: {val}",
                "ts": ts,
                "importance": imp
            })

    # If no query → return top recent important memories
    if not query:
        docs.sort(key=lambda x: x["ts"] * x["importance"], reverse=True)
        return "\n".join([d["raw"] for d in docs[:MAX_MEMORY_LINES]])

    # -----------------------------
    # TF-IDF Semantic Scoring
    # -----------------------------
    query_words = set(re.findall(r"\w+", query.lower()))
    
    # Filter out stop words from query for better targeting
    stop_words = {"what", "how", "is", "the", "a", "an", "do", "you", "my", "i", "can"}
    query_words = {w for w in query_words if w not in stop_words}
    
    if not query_words:
        # Fallback to recency if query is just stop words
        docs.sort(key=lambda x: x["ts"] * x["importance"], reverse=True)
        return "\n".join([d["raw"] for d in docs[:MAX_MEMORY_LINES]])

    # Calculate IDF
    idf = {}
    N = len(docs)
    for word in query_words:
        df = sum(1 for d in docs if word in d["text"])
        idf[word] = math.log((N + 1) / (df + 1)) + 1

    scored = []
    now = time.time()
    
    for d in docs:
        tf_idf_score = sum(tf(w, d["text"]) * idf[w] for w in query_words)
        
        # Exact keyword match bonus
        if any(w in d["text"] for w in query_words):
            tf_idf_score += 0.5
            
        # Recency multiplier (decay over ~30 days)
        days_old = max(0, (now - d["ts"]) / 86400)
        recency_mult = max(0.5, 1.2 - (days_old * 0.02))
        
        final_score = tf_idf_score * recency_mult * d["importance"]
        
        if final_score >= SCORE_THRESHOLD:
            scored.append((final_score, d["raw"]))
            
    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    
    context = [s[1] for s in scored[:MAX_MEMORY_LINES]]
    return "\n".join(context)