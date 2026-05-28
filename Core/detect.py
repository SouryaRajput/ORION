def detect_mode(text):
    text = text.lower()

    if any(w in text for w in ["explain", "derive", "solve", "what is", "define"]):
        return "study"
    if any(w in text for w in ["error", "bug", "code", "function"]):
        return "code"
    if any(w in text for w in ["edit", "video", "clip"]):
        return "edit"
    if any(w in text for w in ["sad", "feel", "life"]):
        return "life"
    if any(w in text for w in ["joke", "fun", "roast"]):
        return "fun"

    return "general"

def is_memory_command(text):
    triggers = ["remember that", "remember this", "remember my", "remember i"]
    return any(t in text.lower() for t in triggers)

def is_memory_query(text):
    triggers = [
        "what do you remember", 
        "what do you know about me", 
        "show my memory",
        "my memory",
        "your memory"
    ]
    return any(t in text.lower() for t in triggers)

def is_forget_command(text):
    return text.lower().startswith("forget ")

def is_memory_audit(text):
    return "is that still correct" in text.lower()