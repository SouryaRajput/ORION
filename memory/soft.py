import json
import time
from pathlib import Path

ROUTINE_FILE = Path(__file__).parent / "routines.json"

default_routines = {}

def load_routines():
    if not ROUTINE_FILE.exists():
        return default_routines.copy()
    try:
        with open(ROUTINE_FILE, "r") as f:
            return json.load(f)
    except:
        return default_routines.copy()

def save_routines(data):
    with open(ROUTINE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def observe(text, current_mode, hour):
    text = text.lower()
    data = load_routines()
    now = time.time()
    
    dirty = False

    def track(routine_key):
        nonlocal dirty
        if routine_key not in data:
            data[routine_key] = {"count": 0, "last_seen": 0, "last_suggested": 0}
        data[routine_key]["count"] += 1
        data[routine_key]["last_seen"] = now
        dirty = True

    # Detect late night studying habit
    if current_mode == "study" and hour >= 22:
        track("late_night_study")
        
    # Detect study playlist habit
    if "playlist" in text and "study" in text:
        track("study_playlist")
        
    # Detect detailed explanation preference
    if len(text.split()) > 20:
        track("like_detailed_explanations")

    if dirty:
        save_routines(data)

def get_routine_confidence(routine_data):
    now = time.time()
    count = routine_data.get("count", 0)
    last_seen = routine_data.get("last_seen", 0)
    
    # Decay count over time (lose 1 count every 2 days)
    days_old = max(0, (now - last_seen) / 86400)
    decayed_count = max(0, count - int(days_old / 2))
    
    # Confidence scales linearly up to 1.0 at 10 occurrences
    confidence = min(1.0, decayed_count / 10.0)
    return confidence

def suggest_memory():
    data = load_routines()
    now = time.time()
    
    best_routine = None
    highest_conf = 0
    
    for r_key, r_data in data.items():
        conf = get_routine_confidence(r_data)
        
        # Don't suggest if we suggested it in the last 2 days (172800 seconds)
        last_suggested = r_data.get("last_suggested", 0)
        if now - last_suggested < 172800:
            continue
            
        # Strict high-confidence threshold
        if conf >= 0.85 and conf > highest_conf:
            highest_conf = conf
            best_routine = r_key
            
    if best_routine:
        data[best_routine]["last_suggested"] = now
        save_routines(data)
        
        if best_routine == "late_night_study":
            return "I noticed it's late and you're studying. Would you like me to suggest a focus playlist or dim the screen?"
        if best_routine == "study_playlist":
            return "You usually play your study playlist when working. Should I queue it up?"
        if best_routine == "like_detailed_explanations":
            return "I noticed you prefer deep, detailed explanations. Should I enable 'deep-dive' mode for future answers?"
            
    return None