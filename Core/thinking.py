import datetime
from memory.behavior import get_profile
from memory.context import build_memory_context
from memory.conversation import get_history
from Core.context import is_followup, expand_followup

def think_before_reply(text):
    """
    The Thinking Layer.
    Runs before the LLM is called to assemble a rich context packet.
    """
    # 1. Behavior Profile
    profile = get_profile()
    
    # 2. Long-term memory context (filtered by relevance)
    relevant_memories = build_memory_context(text)
    
    # 3. Follow-up handling
    followup_detected = is_followup(text)
    processed_text = text
    if followup_detected:
        processed_text = expand_followup(text)
        
    # 4. Situational Awareness (Time & Date)
    now = datetime.datetime.now()
    time_context = f"Current Time: {now.strftime('%I:%M %p, %A, %B %d')}"
    
    # 5. Conversation History Summary
    # The history list already has the summary injected by get_history()
    history = get_history()
    
    context_packet = {
        "user_text": processed_text,
        "is_followup": followup_detected,
        "profile": profile,
        "memories": relevant_memories,
        "time_context": time_context,
        "history": history
    }
    
    return context_packet
