from memory.conversation import get_recent_topics, get_recent_messages

FOLLOWUP_WORDS = {
    "he",
    "she",
    "they",
    "it",
    "them",
    "him",
    "her",
    "that",
    "this",
    "those",
    "these",
    "what about",
    "and",
    "also",
    "why",
    "how",
    "when"
}

def is_followup(text):
    text = text.lower()

    # 1. Pronoun / Question prefix check
    for word in FOLLOWUP_WORDS:
        if text.startswith(word) or text.endswith(word):
            return True

    # 2. Topic continuation check
    # If the user mentions a topic they were just talking about, it's a follow-up.
    recent_topics = get_recent_topics(count=3)
    if recent_topics:
        from memory.conversation import extract_topic
        current_topic = extract_topic(text)
        if current_topic in recent_topics and current_topic != "general":
            return True

    return False


def expand_followup(text):
    """
    Expands a short follow-up query by injecting recent conversation context.
    Instead of just the previous question, it provides the last full exchange.
    """
    recent_messages = get_recent_messages(count=2)
    
    if not recent_messages:
        return text

    context = " | ".join(recent_messages)
    return f"[Context: {context}]\nFollow-up question: {text}"