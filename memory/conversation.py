import json
import threading
import datetime
import os
from pathlib import Path
from tools.summarizer import summarize_conversation

lock = threading.Lock()

SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# Generate a session file for today
SESSION_FILE = SESSIONS_DIR / f"{datetime.datetime.now().strftime('%Y-%m-%d')}.json"

MAX_HISTORY = 4
SUMMARY_TRIGGER = 8

conversation_summary = ""
active_task_summary = ""

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
    text = text.lower()
    if any(w in text for w in ["code", "bug", "python", "script", "api"]): return "programming"
    if any(w in text for w in ["schedule", "meeting", "task", "time"]): return "productivity"
    if any(w in text for w in ["weather", "temperature", "rain", "sun"]): return "weather"
    if any(w in text for w in ["news", "update", "latest"]): return "news"
    return "general"

def _update_active_task_background():
    global active_task_summary
    
    with lock:
        history = load_session()
        recent_msgs = [m["content"] for m in history[-3:]]
        
    if len(recent_msgs) < 2: return
    
    text = "\n".join(recent_msgs)
    prompt = f"""
Analyze the following recent conversation snippet. If the user is currently focused on a specific task, topic, or concept, summarize it in ONE very short phrase (e.g., 'Balancing chemical equations' or 'Debugging a python script'). If it is just casual chat or the task just finished, return 'None'. Do not output anything else.
Snippet:
{text}
"""
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.1,
            max_tokens=30
        )
        result = chat_completion.choices[0].message.content.strip()
        
        with lock:
            if result.lower() != 'none':
                active_task_summary = result
            else:
                active_task_summary = ""
    except Exception as e:
        print("[ACTIVE TASK TRACKER ERROR]", e)

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
    
    # Run active task tracker in background
    threading.Thread(target=_update_active_task_background, daemon=True).start()
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
        
    # Run active task tracker in background
    threading.Thread(target=_update_active_task_background, daemon=True).start()
    trim_history()

def get_history():
    with lock:
        history = load_session()
        recent = [{"role": m["role"], "content": m["content"]} for m in history[-MAX_HISTORY:]]

    sys_msgs = []
    if conversation_summary:
        sys_msgs.append({"role": "system", "content": f"Conversation summary: {conversation_summary}"})
    if active_task_summary:
        sys_msgs.append({"role": "system", "content": f"User's current active task/topic: {active_task_summary}"})
        
    return sys_msgs + recent

def get_recent_topics(count=3):
    with lock:
        history = load_session()
        topics = [m.get("topic", "general") for m in history[-count:]]
        return list(set(t for t in topics if t != "general"))

def get_recent_messages(count=2):
    with lock:
        history = load_session()
        return [m["content"] for m in history[-count:]]

def _trim_background():
    global conversation_summary
    
    with lock:
        history = load_session()
        if len(history) <= SUMMARY_TRIGGER:
            return
        to_summarize = history[:-MAX_HISTORY]
        n_to_remove = len(to_summarize)
        
    summarize_input = [{"role": m["role"], "content": m["content"]} for m in to_summarize]
    
    if conversation_summary:
        summarize_input.insert(0, {"role": "system", "content": f"Previous context: {conversation_summary}"})
        
    new_summary_data = summarize_conversation(summarize_input)
    
    with lock:
        current_history = load_session()
        
        if len(current_history) >= n_to_remove:
            new_history = current_history[n_to_remove:]
            save_session(new_history)
            
        if isinstance(new_summary_data, dict) and new_summary_data.get("summary"):
            conversation_summary = new_summary_data["summary"]
            
            from memory.manager import remember
            for fact in new_summary_data.get("important_facts", []):
                tags = new_summary_data.get("topic_tags", ["general"])
                remember("historical_context", fact, f"Context tags: {', '.join(tags)}")

def trim_history():
    threading.Thread(target=_trim_background, daemon=True).start()