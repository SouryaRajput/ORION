import json
import datetime
from pathlib import Path

PROFILE_FILE = Path(__file__).parent / "profile.json"

default_profile = {
    "short_interactions": 0,
    "long_interactions": 0,
    "technical_queries": 0,
    "casual_queries": 0,
    "morning_usage": 0,
    "evening_usage": 0,
    "late_night_usage": 0,
    "topics": {}
}

def load_profile():
    if not PROFILE_FILE.exists():
        return default_profile.copy()
    try:
        with open(PROFILE_FILE, "r") as f:
            data = json.load(f)
            # Ensure all default keys exist
            for k, v in default_profile.items():
                if k not in data:
                    data[k] = v
            return data
    except:
        return default_profile.copy()

def save_profile(data):
    with open(PROFILE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def observe(text):
    data = load_profile()
    
    text = text.lower()
    words = len(text.split())

    # Length preference
    if words <= 5:
        data["short_interactions"] += 1
    else:
        data["long_interactions"] += 1

    # Tone/Style
    tech_keywords = ["code", "api", "model", "system", "bug", "error", "script", "python", "git"]
    if any(k in text for k in tech_keywords):
        data["technical_queries"] += 1
    else:
        data["casual_queries"] += 1

    # Time of day tracking
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        data["morning_usage"] += 1
    elif 17 <= hour < 22:
        data["evening_usage"] += 1
    elif hour >= 22 or hour < 5:
        data["late_night_usage"] += 1

    # Basic topic extraction
    topics = {
        "programming": ["code", "python", "javascript", "bug", "function", "api", "compile", "script"],
        "productivity": ["schedule", "calendar", "reminder", "todo", "task", "meeting"],
        "casual_chat": ["hello", "how are you", "joke", "fun", "bored", "what's up"]
    }
    for topic, keywords in topics.items():
        if any(k in text for k in keywords):
            data["topics"][topic] = data["topics"].get(topic, 0) + 1

    save_profile(data)

def get_profile():
    data = load_profile()
    
    traits = []
    
    # Interaction style
    total_interactions = data["short_interactions"] + data["long_interactions"]
    if total_interactions > 10:
        if data["short_interactions"] > data["long_interactions"] * 2:
            traits.append("The user prefers quick, direct interactions.")
        elif data["long_interactions"] > data["short_interactions"] * 2:
            traits.append("The user likes detailed, longer conversations.")

    # Technical vs Casual
    total_tone = data["technical_queries"] + data["casual_queries"]
    if total_tone > 10:
        if data["technical_queries"] > data["casual_queries"]:
            traits.append("The user frequently asks highly technical questions (engineering, coding).")
        
    # Usage habits
    max_usage = max(data["morning_usage"], data["evening_usage"], data["late_night_usage"])
    if max_usage > 5:
        if max_usage == data["morning_usage"]:
            traits.append("The user is often active in the mornings.")
        elif max_usage == data["late_night_usage"]:
            traits.append("The user is a night owl, often working late.")

    # Interests
    if data["topics"]:
        top_topic = max(data["topics"].items(), key=lambda x: x[1])[0]
        if data["topics"][top_topic] > 3:
            traits.append(f"The user has a strong interest in {top_topic.replace('_', ' ')}.")

    if not traits:
        return "I am still learning about the user's preferences."
        
    return " ".join(traits)