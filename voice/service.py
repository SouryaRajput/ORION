import time
import voice.state as state
from voice.audio_engine import listen
from voice.input_groq import transcribe_audio
from Core.state_machine import sm, AgentState
from Core.events import bus
import voice.pipeline # Initialize event handlers
import Core.web_searcher # Preload heavy libraries to eliminate 1000ms import latency

from agents.scheduler import Scheduler
from agents.background import BackgroundManager

scheduler = Scheduler()


def _start_ui_listener():
    """Listen for commands from the Desktop UI (mute toggle, etc.)."""
    try:
        from desktop.ipc import JsonUDPListener, ENGINE_PORT

        def _handle(msg):
            if msg.get("type") == "mute":
                sm.mic_muted = msg.get("muted", False)
                print(f"🎙️ Mic {'MUTED' if sm.mic_muted else 'UNMUTED'} (from UI)")

        listener = JsonUDPListener(ENGINE_PORT, _handle)
        listener.start()
    except Exception:
        pass  # UI module not available


def run_voice_service():
    print("ORION voice system is online.")
    
    # Start Agentic Infrastructure
    from voice.tts import speak_audio
    BackgroundManager.set_notify_fn(speak_audio)
    scheduler.start()
    
    # Preload the semantic cache model to eliminate the 25s cold-start latency
    import memory.cache as cache
    cache.preload_model()
    
    sm.transition(AgentState.SLEEPING)
    _start_ui_listener()

    while True:
        # Check timeouts for followups or idle sleep
        now = time.time()
        
        if sm.current == AgentState.LISTENING:
            if sm.waiting_for_followup:
                if now - sm.followup_start_time > state.FOLLOWUP_TIMEOUT:
                    print("💤 Follow-up timeout. Going to sleep.")
                    sm.transition(AgentState.SLEEPING)
            else:
                if now - sm.last_engaged_time > state.ENGAGE_TIMEOUT:
                    print("💤 Idle timeout. Going to sleep.")
                    sm.transition(AgentState.SLEEPING)

        result = listen()
        audio, early_txt = result if result else (None, None)

        if audio is None and not state.WAKE_TRIGGERED:
            continue

        if state.WAKE_TRIGGERED:
            print("🔥 Wake confirmed")
            if sm.current == AgentState.SPEAKING:
                sm.trigger_interrupt()
            state.WAKE_TRIGGERED = False
            state.CURRENT_STREAM_ID += 1
            
            sm.transition(AgentState.PROCESSING)
            
            print("🎤 Capturing query...")
            text = early_txt if early_txt else transcribe_audio(audio)
            
            from Core.latency import tracker
            tracker.mark_checkpoint("STT Engine")

            if not text or (text.startswith("[") and text.endswith("]")) or len(text.split()) < 2:
                sm.transition(AgentState.LISTENING)
                continue

            print("\r" + " " * 150 + "\r", end="")
            print("You:", text.strip())
            bus.emit("SPEECH_RECOGNIZED", text.strip())
            continue

        # If we are not LISTENING (engaged), ignore audio
        if sm.current != AgentState.LISTENING:
            continue
            
        # Cooldown debounce to prevent echo triggers
        if time.time() - state.LAST_SPOKEN_TIME < 0.8:
            continue

        print("🧠 Processing...")
        sm.transition(AgentState.PROCESSING)

        text = early_txt if early_txt else transcribe_audio(audio)
        
        from Core.latency import tracker
        tracker.mark_checkpoint("STT Engine")

        if not text or (text.startswith("[") and text.endswith("]")) or len(text.split()) < 2:
            sm.transition(AgentState.LISTENING)
            continue

        print("\r" + " " * 150 + "\r", end="")
        print("You:", text.strip())
        bus.emit("SPEECH_RECOGNIZED", text.strip())