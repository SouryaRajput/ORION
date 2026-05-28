import json
import time
import os
import requests
from tools.registry import run_tool
from tools.task_manager import advance_step
from Core.screen_capture import capture_screen
from Core.vision import encode_image
from Core.action_engine import click_text, type_text, press_key
import voice.state as state

MODEL_NAME = "google/gemini-2.5-flash"

def perform_agent_step(step_description):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "Failed: Missing API Key"

    print(f"[AGENT] Starting step: {step_description}")
    
    for attempt in range(4): # Max 4 micro-actions per step
        if getattr(state, "STOP_AGENT", False):
            print("[AGENT] Aborted by user.")
            return "Aborted"

        # Give UI a moment to settle
        time.sleep(1.5)

        image_path = capture_screen()
        base64_image = encode_image(image_path)
        
        system_prompt = """
You are an autonomous computer agent executing a task. 
Goal: {step}
Look at the screen. Decide the EXACT next action to take.
Output ONLY valid JSON in one of these formats:
{{"action": "click", "target": "exact text of button or link visible on screen"}}
{{"action": "type", "text": "text to type"}}
{{"action": "press", "key": "enter or escape or tab"}}
{{"action": "done", "reason": "step completed"}}
{{"action": "fail", "reason": "cannot complete step"}}
"""
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": system_prompt.format(step=step_description)
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "response_format": { "type": "json_object" }
        }
        
        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            content = data['choices'][0]['message']['content'].strip()
            action_data = json.loads(content)
            
            action = action_data.get("action")
            
            print(f"[AGENT] Action decided: {action_data}")
            
            if action == "click":
                target = action_data.get("target", "")
                if click_text(target, image_path):
                    print(f"-> Clicked '{target}'")
                else:
                    print(f"-> Failed to click '{target}'")
            elif action == "type":
                text = action_data.get("text", "")
                type_text(text)
                print(f"-> Typed '{text}'")
            elif action == "press":
                key = action_data.get("key", "enter")
                press_key(key)
                print(f"-> Pressed '{key}'")
            elif action == "done":
                return "Completed"
            elif action == "fail":
                return "Failed: " + action_data.get("reason", "Unknown reason")
                
        except Exception as e:
            print("[AGENT ERROR]", e)
            return "Failed to evaluate screen"
            
    return "Failed: Max attempts reached"

def execute_plan(steps):
    # Reset STOP_AGENT at the start of a new plan
    state.STOP_AGENT = False

    results = []

    for step in steps:
        if getattr(state, "STOP_AGENT", False):
            results.append("Execution aborted by user.")
            break

        if "search" in step.lower():
            query = step.replace("search for", "").strip()
            result = run_tool("search", query)
            results.append(result)
        else:
            # Execute visually
            status = perform_agent_step(step)
            results.append(f"Step '{step}': {status}")

        advance_step()

    return "\n".join(results)