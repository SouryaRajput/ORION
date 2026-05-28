import requests
import json
import os

from dotenv import load_dotenv
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL_NAME = "google/gemini-2.5-flash"

def create_plan(user_input):

    system_prompt = """
You are a planning engine for an AI assistant.

Determine whether the user's request is simple or requires multiple steps.

Return JSON only.

If simple:
{
 "type": "simple"
}

If complex:
{
 "type": "plan",
 "steps": [
  "step 1",
  "step 2",
  "step 3"
 ]
}

Response should be concise, short, and straight to point but still with all important information.

You are STRICTLY PROHIBITED to use words like: "Completed step", "Step 1", "Next step", "Task completed"

Only produce the final summary answer to the user like a human answering to another human, no need for that kind of structure

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
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            "temperature": 0.2
        }
    )

    data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except:
        return {"type": "simple"}