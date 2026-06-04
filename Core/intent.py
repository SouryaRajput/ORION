import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def classify_intent(text):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"intent": "general"}
        
    client = Groq(api_key=api_key)
        
    system_prompt = """
You are an intent classification engine.
Categorize the user's speech into one of the following intents:
1. "screen_action": The user wants you to perform a physical action on the screen (e.g. click a button, type text, press a key).
2. "screen_query": The user wants you to look at the screen and read, summarize, or describe it.
3. "system_control": The user wants you to open an application, launch a workspace, or control the OS.
4. "study_mode": STRICTLY use this if the user explicitly asks you to "simulate", "animate", or open the "study simulator" for a concept. Do NOT use this for general academic questions or if they just ask "explain X" - those should go to "general".
5. "web_search": The user is asking about current events, news, live weather, real-time facts, or explicitly asking you to search the web or check the internet. Example: "what is the global news", "what's the weather in Tokyo", "who won the game yesterday".
6. "dynamic_action": The user wants you to PERFORM a real-world technical task that requires executing commands, making API calls, changing system/cloud settings, managing servers, or doing something actionable beyond just answering a question. Examples: "add my IP to MongoDB Atlas", "restart my server", "deploy my app", "check my disk space", "update my DNS records".
7. "agentic_task": Execution of specific, step-by-step physical actions on the web or system (e.g., navigating, clicking, copying data, interacting with UIs). Examples: "Go to render, copy my URL and paste it on Vercel", "Login to Github and star the repo".
8. "scheduled_task": Tasks involving scheduling, monitoring, recurring actions, or time-based triggers. Examples: "Monitor Bitcoin price", "Every morning at 10 AM summarize AI news", "Remind me to check email at 5 PM".
9. "deep_research": Deep planning, comparisons, budgeting, or generating detailed research reports on any topic. Triggered when the user asks to "plan", "compare", "research", "budget", or "find the cheapest" options. Examples: "Plan a trip to Switzerland under 3 lakh rupees", "Compare iPhone 15 and 16 features", "Deep research the history of Rome".
10. "general": General conversation, answering academic questions, explaining concepts normally, or anything else.

IMPORTANT: 
- For live info/news, classify as "web_search". 
- For specific technical actions, classify as "dynamic_action". 
- For physical web navigation, execution, and UI interactions, classify as "agentic_task".
- For deep planning, generating reports, budgeting, or thorough research, classify as "deep_research".
- For any time-based monitoring or recurring jobs, classify as "scheduled_task".
- If they just want information or conversation, use "general".

Output ONLY valid JSON:
{
  "intent": "<intent_name>",
  "target": "<target object/app/text if applicable. If study_mode, the specific topic to teach. If dynamic_action, the full task description.>",
  "action_type": "<if screen_action: 'click', 'type', or 'press'. Otherwise empty string>"
}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        import re
        content = re.sub(r'```json|```', '', content).strip()
        return json.loads(content)
    except Exception as e:
        print("[INTENT CLASSIFIER ERROR]", e)
        return {"intent": "general"}
