import time
import datetime
import re
import queue
import threading
import types

from Core.core import delegate
from Core.state import wake, sleep
from Core.system_control import open_app
from Core.workspaces import launch_workspace
from Core.browser_intents import handle_browser_command
from Core.screen_capture import capture_screen
from Core.vision import extract_text, analyze_screen_with_llm
from Core.action_engine import click_text, type_text, press_key
from Core.agent_executor import execute_action

from voice.tts import speak_audio
import voice.state as state
from voice.response_guard import clean_response
from voice.acknowledgements import get_ack
from voice.chunker import chunk_for_speech

from memory.behavior import observe
from Core.events import bus
from Core.state_machine import sm, AgentState

speech_queue = queue.Queue()


def _send_to_ui(role: str, text: str):
    """Push transcript line to the Desktop UI (fire-and-forget)."""
    try:
        from desktop.ipc import get_engine_sender
        get_engine_sender().send("transcript", role=role, text=text)
    except Exception:
        pass

def clean_for_speech(text):
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    text = re.sub(r'\*', '', text)
    text = re.sub(r'[#_`]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def limit_response(text, max_words=50):
    words = text.split()
    if len(words) <= max_words:
        return text
    truncated = " ".join(words[:max_words])
    last_period = truncated.rfind(".")
    if last_period > len(truncated) // 2:
        return truncated[:last_period + 1]
    return truncated + "."

def voice_allowed():
    hour = datetime.datetime.now().hour
    return not (0 <= hour <= 6)

def speech_worker():
    while True:
        text = speech_queue.get()
        if text is None: break
        
        if sm.interrupt_flag:
            with speech_queue.mutex:
                speech_queue.queue.clear()
            speech_queue.task_done()
            continue

        sm.transition(AgentState.SPEAKING)
        speak_audio(text)
        
        # Audio finished playing
        state.LAST_SPOKEN_TIME = time.time()
            
        speech_queue.task_done()

threading.Thread(target=speech_worker, daemon=True).start()

def speak_stream(stream, is_urgent=False):
    buffer = ""
    full_reply = ""
    first_token = True
    for chunk in stream:
        if sm.interrupt_flag: break
        
        if first_token:
            from Core.latency import tracker
            tracker.mark_checkpoint("LLM (Time To First Token)")
            first_token = False
            
        full_reply += chunk
        buffer += chunk
        
        sm.transition(AgentState.SPEAKING)

        while re.search(r'[.!?]\s+|,\s+|—\s*|\.\.\.\s*', buffer):
            match = re.search(r'[.!?]\s+|,\s+|—\s*|\.\.\.\s*', buffer)
            punctuation = match.group().strip()
            sentence = buffer[:match.end()].strip()
            buffer = buffer[match.end():]
            cleaned = clean_for_speech(clean_response(sentence))
            
            if cleaned:
                # Dynamic breath timing based on punctuation
                pause = 0
                if '...' in punctuation or '—' in punctuation:
                    pause = 500
                elif '?' in punctuation or '!' in punctuation:
                    pause = 400
                elif '.' in punctuation:
                    pause = 350
                elif ',' in punctuation:
                    pause = 150
                    
                # Modify speed based on urgency
                if is_urgent:
                    pause = int(pause * 0.3)
                    
                if sm.interrupt_flag: break
                speak_audio(cleaned, pause_ms=pause)

    if buffer.strip():
        cleaned = clean_for_speech(clean_response(buffer.strip()))
        if cleaned:
            if not sm.interrupt_flag:
                speak_audio(cleaned, pause_ms=0)

    state.LAST_SPOKEN_TIME = time.time()
    
    return full_reply

# -----------------------
# EVENT HANDLERS
# -----------------------

def handle_speech_recognized(text):
    if not text or len(text) < 3 or text in ["hmm", "ok", "huh", "hmmm"]:
        sm.transition(AgentState.LISTENING)
        return

    observe(text)
    _send_to_ui("user", text)

    with speech_queue.mutex:
        speech_queue.queue.clear()

    now = time.time()
    if now - state.LAST_TEXT_TIME < state.MIN_TEXT_INTERVAL:
        sm.transition(AgentState.LISTENING)
        return
        
    state.LAST_TEXT_TIME = now
    sm.set_followup(False)
    
    # 1. Fast Paths
    from plugins.plugin_manager import check_fast_command
    fast_result = check_fast_command(text)
    
    from Core.latency import tracker
    tracker.mark_checkpoint("Local Fast Commands")
    
    if fast_result:
        action = fast_result.get("action")
        reply = fast_result.get("reply", "")
        if action == "stop":
            sm.trigger_interrupt()
            with speech_queue.mutex:
                speech_queue.queue.clear()
        
        if reply:
            speech_queue.put(reply)
        else:
            sm.transition(AgentState.LISTENING)
        return

    # 2. Intent Router (Keyword Heuristic to save 1000ms)
    # Only run the heavy LLM intent router if trigger words are present
    trigger_words = [
        "screen", "click", "type", "press", "read", "look", 
        "open", "launch", "close", "workspace", 
        "study", "simulate", "animate", "teach",
        "search", "news", "weather", 
        "server", "deploy", "dns", "database", "check"
    ]
    
    needs_router = any(word in text.lower() for word in trigger_words)
    
    if needs_router:
        from Core.intent import classify_intent
        intent_data = classify_intent(text)
        tracker.mark_checkpoint("Intent Router (LLM)")
    else:
        intent_data = {"intent": "general", "target": "", "action_type": ""}
        tracker.mark_checkpoint("Intent Router (Skipped)")
        
    intent = intent_data.get("intent", "general")
    target = intent_data.get("target", "")
    action_type = intent_data.get("action_type", "")

    # Emit classified intent event for further processing
    bus.emit("INTENT_CLASSIFIED", {
        "text": text,
        "intent": intent,
        "target": target,
        "action_type": action_type
    })

def handle_intent(data):
    text = data["text"]
    intent = data["intent"]
    target = data["target"]
    action_type = data["action_type"]

    if intent == "screen_action":
        if action_type == "click":
            speech_queue.put(f"Clicking {target}")
            if click_text(target, capture_screen()):
                speech_queue.put("Done.")
            else:
                speech_queue.put(f"I couldn't find {target} on the screen.")
        elif action_type == "type":
            if type_text(target): speech_queue.put("Typed.")
            else: speech_queue.put("Failed to type.")
        elif action_type == "press":
            key_map = {"enter": "enter", "space": "space", "escape": "esc", "tab": "tab"}
            mapped = key_map.get(target.lower(), target)
            if press_key(mapped): speech_queue.put(f"Pressed {target}.")
            else: speech_queue.put("Failed to press key.")
        return

    elif intent == "screen_query":
        speech_queue.put("Checking your screen.")
        summary = analyze_screen_with_llm(capture_screen())
        speech_queue.put(summary if summary else "I couldn't understand the screen clearly.")
        return

    elif intent == "system_control":
        browser_result = handle_browser_command(text)
        if browser_result:
            speech_queue.put(browser_result)
            return
            
        workspace = None
        if "study" in text: workspace = "study"
        elif "coding" in text: workspace = "coding"
        elif "entertainment" in text: workspace = "entertainment"
        
        if workspace and launch_workspace(workspace):
            speech_queue.put(f"Launched {workspace} workspace.")
            return
                
        if text.startswith("open "):
            app = text.replace("open ", "").strip()
            
            # Explicitly asking for a website
            search_query = app
            if "on web" in app or "website" in app:
                search_query = app.replace("on web", "").replace("website", "").strip()
                from duckduckgo_search import DDGS
                try:
                    with DDGS() as ddgs:
                        results = list(ddgs.text(search_query, max_results=1))
                        if results:
                            import webbrowser
                            webbrowser.open(results[0]["href"])
                            speech_queue.put(f"Opening {search_query} on the web.")
                            return
                except:
                    pass

            # Try local app first
            if open_app(app): 
                speech_queue.put(f"Opening {app}")
            else:
                # Dynamic fallback: Search web and open top result
                from duckduckgo_search import DDGS
                try:
                    with DDGS() as ddgs:
                        results = list(ddgs.text(search_query, max_results=1))
                        if results:
                            import webbrowser
                            webbrowser.open(results[0]["href"])
                            speech_queue.put(f"I couldn't find an app for {search_query}, but I opened the website for you.")
                        else:
                            speech_queue.put(f"I couldn't find {search_query} on your system or the web.")
                except Exception as e:
                    print(f"Web fallback error: {e}")
                    speech_queue.put(f"I couldn't find {app}")
            return

    elif intent == "study_mode":
        topic = target if target else text
        speech_queue.put(f"Sure, let me pull up the study simulator for {topic}.")
        
        # Send IPC message to the Study GUI process
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(topic.encode('utf-8'), ("127.0.0.1", 5005))
            sock.close()
        except Exception as e:
            print(f"Failed to send to study GUI: {e}")
            
        # Put ORION to sleep immediately after speaking this so he doesn't hear the GUI
        sm.handoff_to_sleep = True
        return

    elif intent == "web_search":
        sm.interrupt_flag = False
        sm.pipeline_active = True
        
        try:
            from Core.web_searcher import web_search_stream
            result = web_search_stream(text)
            
            raw_reply = speak_stream(result)
            reply = limit_response(clean_response(raw_reply)) if raw_reply else ""
        except Exception as e:
            print(f"[WEB SEARCH ERROR] {e}")
            reply = "Sorry, I had trouble searching the web."
            speech_queue.put(reply)
            speech_queue.join()
        finally:
            sm.pipeline_active = False

        if not reply.strip():
            sm.transition(AgentState.LISTENING)

        print("Orion:", reply)
        _send_to_ui("bot", reply)
        return

    elif intent == "dynamic_action":
        task_description = target if target else text
        speech_queue.put("On it. Let me figure out how to do that.")

        # Run the dynamic agent in a background thread
        def _run_dynamic_action():
            try:
                sm.pipeline_active = True

                def _confirm():
                    """Voice-based confirmation for unsafe commands."""
                    # For now, auto-confirm. Future: use STT to listen for yes/no.
                    return True

                result = execute_action(
                    task_description,
                    confirm_fn=_confirm,
                    speak_fn=lambda msg: speech_queue.put(msg),
                )
                speech_queue.put(result)
            except Exception as e:
                print(f"[DYNAMIC ACTION ERROR] {e}")
                speech_queue.put("Sorry, I ran into an error while trying to do that.")
            finally:
                sm.pipeline_active = False

        threading.Thread(target=_run_dynamic_action, daemon=True, name="dynamic-action").start()
        return

    # If it's a general intent, delegate to AI

    sm.interrupt_flag = False
    sm.pipeline_active = True
    
    # Fast 0ms semantic detection for dynamics
    is_urgent = any(word in text.lower() for word in ["quick", "fast", "urgent", "hurry", "now", "emergency", "speed"])
    mood = "angry" if any(word in text.lower() for word in ["hate", "stupid", "annoying", "idiot"]) else "neutral"
    
    try:
        result = delegate(text, stream=True, is_urgent=is_urgent, mood=mood)

        if isinstance(result, types.GeneratorType):
            raw_reply = speak_stream(result, is_urgent=is_urgent)
            reply = limit_response(clean_response(raw_reply)) if raw_reply else ""
        elif isinstance(result, dict):
            reply = clean_response(result.get("reply", ""))
            if reply: speech_queue.put(reply)
        else:
            reply = clean_response(str(result))
            if reply: speech_queue.put(reply)

        speech_queue.join()

        # Follow up detection
        if reply.strip().endswith("?"):
            sm.set_followup(True)

    finally:
        sm.pipeline_active = False

    # Only transition to LISTENING immediately if there is nothing to speak.
    # Otherwise, audio_player will transition to LISTENING when it finishes playback.
    if not reply.strip():
        sm.transition(AgentState.LISTENING)

    print("Orion:", reply)
    _send_to_ui("bot", reply)

# Register Handlers
bus.on("SPEECH_RECOGNIZED", handle_speech_recognized)
bus.on("INTENT_CLASSIFIED", handle_intent)