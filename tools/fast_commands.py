import datetime
import webbrowser
import voice.state as state

def check_fast_command(text):
    text = text.lower().strip()

    # -------------------------
    # STOP / CANCEL / DISMISS
    # -------------------------
    if text in ["stop", "cancel", "abort", "halt", "stop talking", "shut up"]:
        from Core.state_machine import sm, AgentState
        sm.trigger_interrupt()
        state.STOP_AGENT = True
        return {"action": "stop", "reply": "Stopped."}
        
    if text in ["nevermind", "nothing", "no thanks", "forget it", "never mind"]:
        from Core.state_machine import sm, AgentState
        sm.trigger_interrupt()
        state.STOP_AGENT = True
        sm.transition(AgentState.SLEEPING)
        return {"action": "dismiss", "reply": ""}

    # -------------------------
    # SLEEP
    # -------------------------
    if text in ["sleep", "go to sleep", "pause"]:
        from Core.state import sleep
        sleep()
        return {"action": "sleep", "reply": "Sleeping... (Say 'orion' to wake me up)"}

    # -------------------------
    # TIME
    # -------------------------
    if "time is it" in text or text == "time":
        now = datetime.datetime.now().strftime("%I:%M %p")
        return {"action": "reply", "reply": f"The time is {now}."}

    # -------------------------
    # DATE
    # -------------------------
    if "date is it" in text or text == "date" or text == "what is today":
        today = datetime.datetime.now().strftime("%A, %B %d")
        return {"action": "reply", "reply": f"Today is {today}."}

    # -------------------------
    # APP LAUNCHER
    # -------------------------
    # Only treat as a fast command if it's short (e.g., "open chrome"). 
    # Longer commands (e.g., "open chrome and search for...") should go to the AI router.
    if (text.startswith("open ") or text.startswith("launch ")) and len(text.split()) <= 4:
        app = text.replace("open ", "").replace("launch ", "").strip()
        if app == "google":
            webbrowser.open("https://google.com")
            return {"action": "reply", "reply": "Opening Google."}
        else:
            from Core.system_control import open_app
            success = open_app(app)
            if success:
                return {"action": "reply", "reply": f"Opening {app}."}
            else:
                return {"action": "reply", "reply": f"I couldn't find {app}."}

    # -------------------------
    # SIMPLE MATH
    # -------------------------
    if text.startswith("what is "):
        try:
            expression = text.replace("what is", "").strip()
            # Basic safe math evaluation
            result = eval(expression, {"__builtins__": None}, {})
            return {"action": "reply", "reply": f"The answer is {result}."}
        except:
            pass

    return None