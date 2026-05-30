from Core.state import get_mode, set_mode
from Core.ai import ai_think_and_reply, ai_reply_stream
from Core.context import is_followup, expand_followup
from Core.system_control import open_app

from agents import study, code, life, fun

import voice.state as state

from Core.detect import (
    is_memory_command,
    is_memory_query,
    is_forget_command,
    is_memory_audit,
)

from memory.conversation import add_user_message, add_assistant_message
from memory.manager import remember, formatted_memory, delete_memory
from memory.parser import parse_memory
import memory.soft as soft
from memory.forget import parse_forget
from memory.confirm import is_confirmation
from memory.cache import get_cached_answer, store_answer
from memory.behavior import get_profile
from memory.predictor import predict

from tools.registry import run_tool
from tools.planner import create_plan
from tools.executor import execute_plan
from tools.task_manager import start_task, get_current_task
from tools.response_style import detect_response_style
from plugins.plugin_manager import check_fast_command

import datetime


MAX_TOOL_STEPS = 3


# -----------------------
# THINK FUNCTION
# -----------------------

def think(text):

    text = text.lower()
    words = text.split()

    if any(x in text for x in ["open", "launch"]):
        return "system"

    if any(x in text for x in ["screen", "see", "read"]):
        return "vision"

    # 🔥 smarter short detection
    if len(words) <= 2 and text in ["yes", "no", "ok", "hmm"]:
        return "short"

    if "?" in text:
        return "question"

    return "general"


# -----------------------
# MAIN DELEGATE FUNCTION
# -----------------------

def delegate(text: str, stream=False, is_urgent=False, mood="neutral"):

    text = text.strip().lower()

    # -------------------
    # 1. PREDICTION (FASTEST)
    # -------------------

    prediction = predict(text)

    if prediction == "system" and text.startswith("open "):
        app = text.replace("open ", "").strip()
        success = open_app(app)
        return f"Opening {app}" if success else f"I couldn't find {app}"

    # -------------------
    # 2. THINK (FAST)
    # -------------------

    decision = think(text)

    if decision == "short":
        return "Yes?"

    # -------------------
    # 3. CONTEXT PREDICTION
    # -------------------

    if len(text.split()) < 4 and state.LAST_INTENT:

        if state.LAST_INTENT == "system":
            if text.startswith("chrome"):
                return open_app("chrome")

    # -------------------
    # 4. SYSTEM COMMANDS
    # -------------------

    if text.startswith("open "):
        app = text.replace("open ", "").strip()
        success = open_app(app)
        return f"Opening {app}" if success else f"I couldn't find {app}"

    # -------------------
    # 5. BEHAVIOR + MEMORY LEARNING
    # -------------------

    soft.observe(
        text,
        get_mode(),
        datetime.datetime.now().hour
    )

    suggestion = soft.suggest_memory()
    if suggestion:
        return suggestion

    # -------------------
    # 6. FAST COMMANDS
    # -------------------

    fast = check_fast_command(text)
    if fast:
        return fast

    # -------------------
    # 7. CACHE
    # -------------------

    cached = get_cached_answer(text)
    if cached:
        return cached

    # -------------------
    # 8. CONTEXT EXPANSION
    # -------------------

    if is_followup(text):
        text = expand_followup(text)

    state.LAST_USER_QUESTION = text

    # -------------------
    # 9. STREAM MODE (CONTROLLED)
    # -------------------

    if stream and decision not in ["system", "short"]:
        return ai_reply_stream(text, is_urgent=is_urgent, mood=mood)

    # -------------------
    # 10. PLANNING
    # -------------------

    plan = create_plan(text)

    if plan.get("type") == "plan":

        steps = plan.get("steps", [])

        if steps:
            start_task(text, steps)
            return execute_plan(steps)

    # -------------------
    # 11. CONTINUE TASK
    # -------------------

    task = get_current_task()

    if text in ["continue", "resume", "next"]:

        if task:
            steps = task["steps"][task["current_step"]:]
            return execute_plan(steps)

        return "There is no active task to continue"

    # -------------------
    # 12. AI THINKING
    # -------------------

    result = ai_think_and_reply(text)

    intent = result.get("intent", "general")
    reply = result.get("reply", "")

    set_mode(intent)

    # ✅ FIXED POSITION
    state.LAST_INTENT = intent

    # -------------------
    # 13. TOOL LOOP
    # -------------------

    for _ in range(MAX_TOOL_STEPS):

        if intent != "tool":
            break

        tool_name = result.get("tool")
        tool_input = result.get("input")

        if not tool_name:
            return "I couldn't determine which tool to use."

        tool_result = run_tool(tool_name, tool_input)

        if not tool_result:
            return "I couldn't retrieve the information."

        result = ai_think_and_reply(text, tool_result=tool_result)

        intent = result.get("intent", "general")
        reply = result.get("reply", "")

    # -------------------
    # 14. MEMORY COMMANDS
    # -------------------

    if is_memory_command(text):

        memory_data = parse_memory(text)
        remember(memory_data)

        reply = "Alright. I'll remember that."
        add_assistant_message(reply)
        return reply

    if is_memory_query(text):

        reply = formatted_memory()
        add_assistant_message(reply)
        return reply

    if is_forget_command(text):

        key = parse_forget(text)
        delete_memory(key)

        reply = "Done. I've forgotten that."
        add_assistant_message(reply)
        return reply

    if is_memory_audit(text):

        suggestion = soft.suggest_memory()
        if suggestion:
            return suggestion

    if is_confirmation(text) and soft.pending_memory:

        remember(soft.pending_memory)
        soft.pending_memory = None

        reply = "Got it. I've saved that."
        add_assistant_message(reply)
        return reply

    if soft.pending_memory:

        category, key, value = soft.pending_memory

        remember(category, key, value)
        soft.pending_memory = None

        reply = "Got it. I'll remember that."
        add_assistant_message(reply)
        return reply

    # -------------------
    # 15. AGENT ROUTING
    # -------------------

    if intent == "study":
        reply = study.handle(text)

    elif intent == "code":
        reply = code.handle(text)

    elif intent == "life":
        reply = life.handle(text)

    elif intent == "fun":
        reply = fun.handle(text)

    # -------------------
    # 16. RESPONSE STYLE (ADAPTIVE)
    # -------------------

    style = detect_response_style(text)
    profile = get_profile()

    if "prefers short responses" in profile:
        reply = reply.split(".")[0] + "."

    elif style == "short":
        reply = reply.split(".")[0] + "."

    elif style == "medium":
        sentences = reply.split(".")
        reply = ".".join(sentences[:3]) + "."

    # -------------------
    # 17. SAVE CONVERSATION
    # -------------------

    add_user_message(text)

    if reply:
        add_assistant_message(reply)

    if reply and len(reply) < 300:
        store_answer(text, reply)

    return reply