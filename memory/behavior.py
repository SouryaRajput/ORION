import json
import datetime
import threading
import time
from pathlib import Path

PROFILE_FILE = Path(__file__).parent / "profile.json"

default_profile = {
    "short_interactions": {"count": 0, "last_observed": 0},
    "long_interactions": {"count": 0, "last_observed": 0},
    "technical_queries": {"count": 0, "last_observed": 0},
    "casual_queries": {"count": 0, "last_observed": 0},
    "morning_usage": {"count": 0, "last_observed": 0},
    "evening_usage": {"count": 0, "last_observed": 0},
    "late_night_usage": {"count": 0, "last_observed": 0},
    "topics": {}
}

_cached_profile = None
_profile_lock = threading.Lock()

def load_profile():
    global _cached_profile
    if _cached_profile is not None:
        return _cached_profile

    if not PROFILE_FILE.exists():
        _cached_profile = default_profile.copy()
        return _cached_profile

    try:
        with open(PROFILE_FILE, "r") as f:
            data = json.load(f)
            # Handle legacy migration format if necessary
            for k, v in default_profile.items():
                if k not in data:
                    data[k] = v
                # migrate integer to dict
                elif isinstance(data[k], int):
                    data[k] = {"count": data[k], "last_observed": time.time()}

            if "topics" in data:
                for t_key, t_val in data["topics"].items():
                    if isinstance(t_val, int):
                        data["topics"][t_key] = {"count": t_val, "last_observed": time.time()}

            _cached_profile = data
            return _cached_profile
    except Exception as e:
        print("[PROFILE LOAD ERROR]", e)
        _cached_profile = default_profile.copy()
        return _cached_profile

def save_profile():
    global _cached_profile
    if not _cached_profile: return
    try:
        with open(PROFILE_FILE, "w") as f:
            json.dump(_cached_profile, f, indent=2)
    except Exception as e:
        print("[PROFILE SAVE ERROR]", e)

def _observe_background(text):
    global _cached_profile
    with _profile_lock:
        data = load_profile()
        now = time.time()
        
        text = text.lower()
        words = len(text.split())

        # Helper to increment
        def inc(key):
            data[key]["count"] += 1
            data[key]["last_observed"] = now

        # Length preference
        if words <= 5:
            inc("short_interactions")
        else:
            inc("long_interactions")

        # Tone/Style
        tech_keywords = ["code", "api", "model", "system", "bug", "error", "script", "python", "git"]
        if any(k in text for k in tech_keywords):
            inc("technical_queries")
        else:
            inc("casual_queries")

        # Time of day tracking
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            inc("morning_usage")
        elif 17 <= hour < 22:
            inc("evening_usage")
        elif hour >= 22 or hour < 5:
            inc("late_night_usage")

        # Basic topic extraction
        topics = {
            "programming": ["code", "python", "javascript", "bug", "function", "api", "compile", "script"],
            "productivity": ["schedule", "calendar", "reminder", "todo", "task", "meeting"],
            "casual_chat": ["hello", "how are you", "joke", "fun", "bored", "what's up"]
        }
        for topic, keywords in topics.items():
            if any(k in text for k in keywords):
                if topic not in data["topics"]:
                    data["topics"][topic] = {"count": 0, "last_observed": now}
                data["topics"][topic]["count"] += 1
                data["topics"][topic]["last_observed"] = now

        save_profile()

def observe(text):
    # Dispatch to background thread so it doesn't block
    threading.Thread(target=_observe_background, args=(text,), daemon=True).start()

def get_profile():
    with _profile_lock:
        data = load_profile()
        
    traits = []
    now = time.time()
    
    # Decay function: subtract 1 count for every 7 days (604800 seconds) since last observed
    def get_decayed_count(entry):
        if not entry: return 0
        count = entry["count"]
        last_observed = entry["last_observed"]
        days_passed = (now - last_observed) / 86400
        decayed = max(0, count - int(days_passed / 7))
        return decayed

    short = get_decayed_count(data["short_interactions"])
    long = get_decayed_count(data["long_interactions"])
    tech = get_decayed_count(data["technical_queries"])
    casual = get_decayed_count(data["casual_queries"])
    morning = get_decayed_count(data["morning_usage"])
    evening = get_decayed_count(data["evening_usage"])
    night = get_decayed_count(data["late_night_usage"])
    
    # Interaction style
    total_interactions = short + long
    if total_interactions > 10:
        if short > long * 2:
            traits.append("The user prefers quick, direct interactions.")
        elif long > short * 2:
            traits.append("The user likes detailed, longer conversations.")

    # Technical vs Casual
    total_tone = tech + casual
    if total_tone > 10:
        if tech > casual:
            traits.append("The user frequently asks highly technical questions (engineering, coding).")
        
    # Usage habits
    max_usage = max(morning, evening, night)
    if max_usage > 5:
        if max_usage == morning:
            traits.append("The user is often active in the mornings.")
        elif max_usage == night:
            traits.append("The user is a night owl, often working late.")

    # Interests
    if data["topics"]:
        decayed_topics = {t: get_decayed_count(v) for t, v in data["topics"].items()}
        if decayed_topics:
            top_topic = max(decayed_topics.items(), key=lambda x: x[1])[0]
            if decayed_topics[top_topic] > 3:
                traits.append(f"The user has a strong interest in {top_topic.replace('_', ' ')}.")

    if not traits:
        return "I am still learning about the user's preferences."
        
    return " ".join(traits)