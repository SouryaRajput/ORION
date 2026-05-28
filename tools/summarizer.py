import requests
import os

from dotenv import load_dotenv
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL_NAME = "google/gemini-2.5-flash"


def summarize_conversation(messages):

    text = ""

    for m in messages:
        role = m["role"]
        content = m["content"]
        text += f"{role}: {content}\n"

    prompt = f"""
Summarize the following conversation briefly so an assistant can remember the important context.

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
            "temperature": 0.2
        }
    )

    try:
        return response.json()["choices"][0]["message"]["content"]
    except:
        return ""