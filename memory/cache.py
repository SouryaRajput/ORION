import json
from pathlib import Path

CACHE_FILE = Path("memory/response_cache.json")

def load_cache():

    if not CACHE_FILE.exists():
        return {}

    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_cache(cache):

    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def get_cached_answer(question):

    cache = load_cache()

    return cache.get(question.lower())


def store_answer(question, answer):

    cache = load_cache()

    cache[question.lower()] = answer

    save_cache(cache)