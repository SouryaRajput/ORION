import requests
import os

from dotenv import load_dotenv
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL_NAME = "google/gemini-2.5-flash"


import json

def summarize_conversation(messages):

    text = ""

    for m in messages:
        role = m["role"]
        content = m["content"]
        text += f"{role}: {content}\n"

    prompt = f"""
Summarize the following conversation briefly so an assistant can remember the important context.
You MUST output a valid JSON object matching this exact schema:
{{
  "topic_tags": ["list", "of", "topics", "discussed"],
  "important_facts": ["fact 1", "fact 2"],
  "summary": "The assistant helped the user with..."
}}

Conversation:
{text}
"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL_NAME,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }
    )

    try:
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        print("[SUMMARIZER ERROR]", e)
        return {"topic_tags": [], "important_facts": [], "summary": ""}