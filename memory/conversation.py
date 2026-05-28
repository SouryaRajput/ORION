from tools.summarizer import summarize_conversation
import threading
import json
from pathlib import Path
import datetime

lock = threading.Lock()

SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# Generate a session file for today
SESSION_FILE = SESSIONS_DIR / f"{datetime.datetime.now().strftime('%Y-%m-%d')}.json"

MAX_HISTORY = 10
SUMMARY_TRIGGER = 15

conversation_summary = ""

def load_session():
    if not SESSION_FILE.exists():
        return []
    try:
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_session(history):
    with open(SESSION_FILE, "w") as f:
        json.dump(history, f, indent=2)

def extract_topic(text):
    # Lightweight topic extraction
    text = text.lower()
    if any(w in text for w in ["code", "bug", "python", "script", "api"]): return "programming"
    if any(w in text for w in ["schedule", "meeting", "task", "time"]): return "productivity"
    if any(w in text for w in ["weather", "temperature", "rain", "sun"]): return "weather"
    if any(w in text for w in ["news", "update", "latest"]): return "news"
    return "general"

def add_user_message(text):
    with lock:
        history = load_session()
        topic = extract_topic(text)
        history.append({
            "role": "user",
            "content": text,
            "topic": topic
        })
        save_session(history)
    trim_history()

def add_assistant_message(text):
    with lock:
        history = load_session()
        topic = "general"
        if history and history[-1]["role"] == "user":
            topic = history[-1].get("topic", "general")
            
        history.append({
            "role": "assistant",
            "content": text,
            "topic": topic
        })
        save_session(history)
    trim_history()

def get_history():
    with lock:
        history = load_session()
        # We only pass the content to the LLM (strip out the topic metadata)
        recent = [{"role": m["role"], "content": m["content"]} for m in history[-MAX_HISTORY:]]

    if conversation_summary:
        return [{"role": "system", "content": f"Conversation summary: {conversation_summary}"}] + recent
    return recent

def get_recent_topics(count=3):
    """Returns the unique topics from the last few messages for follow-up detection."""
    with lock:
        history = load_session()
        topics = [m.get("topic", "general") for m in history[-count:]]
        return list(set(t for t in topics if t != "general"))

def get_recent_messages(count=2):
    """Returns the exact content of recent messages for context expansion."""
    with lock:
        history = load_session()
        return [m["content"] for m in history[-count:]]

def trim_history():
    global conversation_summary
    
    with lock:
        history = load_session()
        
        if len(history) > SUMMARY_TRIGGER:
            # We want to summarize the OLD messages, keeping the newest MAX_HISTORY
            to_summarize = history[:-MAX_HISTORY]
            
            # Use the summarizer tool
            summarize_input = [{"role": m["role"], "content": m["content"]} for m in to_summarize]
            
            # Combine previous summary with new summary context
            if conversation_summary:
                summarize_input.insert(0, {"role": "system", "content": f"Previous summary: {conversation_summary}"})
                
            new_summary = summarize_conversation(summarize_input)
            
            if new_summary:
                conversation_summary = new_summary
                
            # Keep only the max history
            save_session(history[-MAX_HISTORY:])