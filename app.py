import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Core system imports
from Core.state import wake, sleep, awake, set_mode, get_mode
from Core.core import delegate

# Memory
from memory.manager import load_memory, delete_memory

# -------------------
# App Initialization
# -------------------

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# -------------------
# Data Models
# -------------------

class UserMessage(BaseModel):
    text: str

# -------------------
# UI Route
# -------------------

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    with open("static/index.html", "r") as f:
        return f.read()

# -------------------
# Memory Routes
# -------------------

@app.get("/memory")
def get_memory():
    return load_memory()

@app.post("/memory/forget")
def forget_memory(key: str):
    delete_memory(key)
    return {"status": "deleted"}

# -----------------
# Voice Route
# -----------------
@app.post("/voice")
def voice_input(msg: UserMessage):
    from voice.pipeline import process_text
    process_text(msg.text)
    return {"status": "ok"}

# -------------------
# Chat Route (MAIN)
# -------------------

@app.post("/chat")
def chat(msg: UserMessage):
    text = msg.text.strip()

    # Wake word
    if text.lower() == "orion":
        wake()
        set_mode("general")
        return {
            "reply": "Yes, Sir?",
            "mode": get_mode()
        }

    # Manual sleep
    if text.lower() == "sleep":
        sleep()
        return {
            "reply": "Sleeping... (Say 'orion' to wake me up)",
            "mode": get_mode()
        }

    # If asleep
    if not awake():
        return {
            "reply": "Sleeping...",
            "mode": get_mode()
        }
    

    # Main AI delegation
    reply = delegate(text)

    return {
        "reply": reply,
        "mode": get_mode()
    }