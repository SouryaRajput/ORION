import requests
import json
from dotenv import load_dotenv
import os
from Core.policy import get_system_prompt
from memory.conversation import add_user_message, add_assistant_message
from Core.thinking import think_before_reply
import re

from Identity.manager import load_identity

from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("⚠️ WARNING: GROQ_API_KEY is not set in .env")

import httpx
# Use Groq client for absolute lowest latency with ultra-long keepalive
http_client = httpx.Client(limits=httpx.Limits(keepalive_expiry=3600.0, max_keepalive_connections=10))
groq_client = Groq(api_key=GROQ_API_KEY, http_client=http_client) if GROQ_API_KEY else None
MODEL_NAME = "llama-3.1-8b-instant"

# --------------------------------------------------
# STREAMING RESPONSE (voice + web)
# --------------------------------------------------

def ai_reply_stream(text, is_urgent=False, mood="neutral"):

    # Run the Thinking Layer
    context_packet = think_before_reply(text)
    
    system_prompt = get_system_prompt()
    system_prompt += f"""\n
SITUATIONAL AWARENESS:
{context_packet['time_context']}
USER URGENCY: {'HIGH (Speak fast, use no filler words, be direct)' if is_urgent else 'NORMAL'}
USER MOOD: {mood.upper()}

USER PROFILE:
{context_packet['profile']}

RELEVANT MEMORIES:
{context_packet['memories']}

CRITICAL VOICE RULES (HYPER-REALISTIC ACTING):
- You are speaking out loud to a human. This is a VOICE conversation.
- ACT HUMAN. Do not sound like a perfectly polished AI.
- Use filler words naturally ("Well...", "Uh...", "Like", "You know,").
- Use em-dashes (—) frequently to show self-correction or shifting thoughts.
- Use lots of commas (,) to force yourself to take natural breathing pauses.
- Use exclamation marks (!) for excitement or high energy.
- Use ellipses (...) for trailing off or thinking.
- Keep responses to 1-3 sentences MAX. Be extremely concise.
- NEVER use markdown, bullet points, numbered lists, or headers.
- If the topic is complex, give the key insight casually and offer to elaborate.
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages += context_packet['history']

    messages.append({
        "role": "user",
        "content": context_packet['user_text']
    })

    if not groq_client:
        yield "Groq API key missing."
        return

    try:
        stream = groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.4,
            max_tokens=150,
            stream=True
        )
    except Exception as e:
        print("[GROQ API ERROR]", e)
        yield "Sorry, I am having trouble connecting to Groq right now."
        return

    full_reply = ""

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            full_reply += delta
            yield delta

    # store conversation after stream finishes
    add_user_message(text)
    add_assistant_message(full_reply)


# --------------------------------------------------
# THINK + REPLY (tool routing)
# --------------------------------------------------

def ai_think_and_reply(text, tool_result=None):

    # Run the Thinking Layer
    context_packet = think_before_reply(text)

    system_prompt = f"""
You are ORION, a personal AI voice assistant.

SITUATIONAL AWARENESS:
{context_packet['time_context']}

USER PROFILE:
{context_packet['profile']}

RELEVANT MEMORIES:
{context_packet['memories']}

You have access to tools.

Available tool:
search(query) → returns recent web articles including title, summary and source.

CRITICAL VOICE RULES (HYPER-REALISTIC ACTING):
- You are SPEAKING OUT LOUD. Act perfectly human.
- Use filler words naturally ("Um...", "Actually—", "Well,").
- Use em-dashes and commas to force breathing pauses.
- Maximum 2 sentences. Be direct and casual.
- NEVER use markdown, bullet points, or lists.
- NEVER structure your answer. Just talk like a friend.
- If you need a tool, return JSON silently.

TOOL FORMAT:
If a tool is needed, return ONLY this JSON:
{{{{
 "intent": "tool",
 "tool": "search",
 "input": "query here"
}}}}

Otherwise return ONLY this JSON:
{{{{
 "intent": "general",
 "reply": "your short spoken response"
}}}}
"""

    messages = [{"role": "system", "content": system_prompt}]

    if tool_result:
        messages.append({
            "role": "system",
            "content": "Summarize the following search results naturally."
        })

        messages.append({
            "role": "assistant",
            "content": f"Search results:\n{tool_result}"
        })

    messages += context_packet['history']

    messages.append({
        "role": "user",
        "content": context_packet['user_text']
    })

    if not groq_client:
        return {"intent": "general", "reply": "Groq API key missing."}

    try:
        response = groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.4
        )
        content = response.choices[0].message.content.strip()
    except Exception as e:
        print("[GROQ API ERROR]", e)
        return {
            "intent": "general",
            "reply": "Sorry, I am having trouble connecting to my brain servers."
        }

    # second pass after tool
    if tool_result:

        add_user_message(text)
        add_assistant_message(content)

        return {
            "intent": "general",
            "reply": content
        }

    # detect JSON tool instructions
    json_match = re.search(r"\{.*?\}", content, re.DOTALL)

    if not json_match:

        add_user_message(text)
        add_assistant_message(content)

        return {
            "intent": "general",
            "reply": content
        }

    try:
        result = json.loads(json_match.group())
    except Exception:

        add_user_message(text)
        add_assistant_message(content)

        return {
            "intent": "general",
            "reply": content
        }

    intent = result.get("intent", "general")
    reply = result.get("reply", "")
    tool = result.get("tool")
    tool_input = result.get("input")

    valid_intents = ["study", "code", "fun", "life", "general", "tool"]
    if intent not in valid_intents:
        intent = "general"

    add_user_message(text)

    if reply:
        add_assistant_message(reply)

    return {
        "intent": intent,
        "reply": reply,
        "tool": tool,
        "input": tool_input
    }