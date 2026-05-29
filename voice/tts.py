import hashlib
from pathlib import Path
import subprocess
import asyncio
import os
import time
import queue
import threading

import voice.state as state
from Core.state_machine import sm, AgentState
from dotenv import load_dotenv
import io

load_dotenv()

# -----------------------
# TTS ENGINE TOGGLE
# Set in .env: TTS_ENGINE=elevenlabs, edge, or kokoro
# -----------------------

TTS_ENGINE = os.getenv("TTS_ENGINE", "kokoro").strip().lower()
print(f"🔊 TTS Engine: {TTS_ENGINE.upper()}")


# -----------------------
# GLOBAL AUDIO QUEUE
# Items are (byte_stream_queue, pause_ms, cache_file, format_flag)
# format_flag can be 'mp3' or 'f32le'
# -----------------------

audio_queue = queue.Queue()
active_tts_tasks = 0
tts_lock = threading.Lock()

CACHE_DIR = Path("voice/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Edge TTS voice
EDGE_VOICE = "en-US-AriaNeural"

# Kokoro Pipeline (lazy loaded)
_kokoro_pipeline = None

# -----------------------
# AUDIO PLAYER (INSTANT STREAMING PLAYBACK)
# -----------------------

def audio_player():

    while True:

        item = audio_queue.get()

        if item is None:
            break

        byte_stream, pause_ms, cache_file, format_flag = item

        # Check interrupt before playing
        if sm.interrupt_flag:
            audio_queue.task_done()
            continue

        try:
            # Configure ffplay based on format
            if format_flag == "f32le":
                ffplay_cmd = ["ffplay", "-f", "f32le", "-ar", "24000", "-ac", "1", "-nodisp", "-autoexit", "-i", "pipe:0"]
            else:
                ffplay_cmd = ["ffplay", "-nodisp", "-autoexit", "-i", "pipe:0"]

            process = subprocess.Popen(
                ffplay_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            while True:
                if sm.interrupt_flag:
                    break
                chunk = byte_stream.get()
                if chunk is None:  # EOF
                    break
                try:
                    process.stdin.write(chunk)
                    process.stdin.flush()
                    
                    from Core.latency import tracker
                    tracker.end_tracking_and_report()
                except BrokenPipeError:
                    break

            process.stdin.close()

            while process.poll() is None:
                if sm.interrupt_flag:
                    process.terminate()
                    with audio_queue.mutex:
                        audio_queue.queue.clear()
                    break
                time.sleep(0.01)

            # Natural pause between chunks (breathing room)
            if not sm.interrupt_flag and pause_ms > 0:
                pause_end = time.time() + (pause_ms / 1000.0)
                while time.time() < pause_end:
                    if sm.interrupt_flag:
                        break
                    time.sleep(0.01)

        except Exception as e:
            print("[AUDIO ERROR]", e)

        audio_queue.task_done()

        if audio_queue.empty():
            with tts_lock:
                tasks_active = active_tts_tasks > 0

            if not tasks_active and not sm.pipeline_active:
                if sm.current == AgentState.SPEAKING:
                    if getattr(sm, "handoff_to_sleep", False):
                        sm.transition(AgentState.SLEEPING)
                        sm.handoff_to_sleep = False
                    else:
                        sm.transition(AgentState.LISTENING)
            
            # Always update LAST_SPOKEN_TIME so the 1.0s room echo buffer applies
            state.LAST_SPOKEN_TIME = time.time()

# 🚀 START PLAYER THREAD
threading.Thread(target=audio_player, daemon=True).start()


# ============================================================
# ENGINE 1: EDGE TTS (FREE, STREAMING)
# ============================================================

async def _edge_tts_stream(text, byte_stream, cache_file):
    """Uses Microsoft Edge neural TTS. Streams MP3 chunks in real-time."""
    import edge_tts

    full_audio = b""
    communicate = edge_tts.Communicate(text, EDGE_VOICE, rate="+5%", pitch="+0Hz")

    async for chunk_data in communicate.stream():
        if sm.interrupt_flag:
            break
        if chunk_data["type"] == "audio":
            audio_bytes = chunk_data["data"]
            byte_stream.put(audio_bytes)
            full_audio += audio_bytes

    byte_stream.put(None)  # EOF

    if not sm.interrupt_flag and full_audio:
        try:
            with open(cache_file, "wb") as f:
                f.write(full_audio)
        except Exception:
            pass


def _run_edge_tts(text, byte_stream, cache_file):
    """Run the async edge-tts in a new event loop (thread-safe)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_edge_tts_stream(text, byte_stream, cache_file))
    finally:
        loop.close()


# ============================================================
# ENGINE 2: ELEVENLABS (PREMIUM, STREAMING + EMOTION)
# ============================================================

def _run_elevenlabs_tts(text, byte_stream, cache_file):
    """Uses ElevenLabs API with key rotation and emotion detection."""
    from elevenlabs.client import ElevenLabs
    from voice.key_manager import get_key, get_voice, rotate_key
    from voice.emotion import get_voice_settings

    voice_settings = get_voice_settings(text)

    retries = 0
    MAX_RETRIES = 4

    while retries < MAX_RETRIES:
        try:
            api_key = get_key()
            voice_id = get_voice()

            if not api_key or not voice_id:
                print("[TTS] No ElevenLabs keys configured. Falling back to Edge TTS.")
                _run_edge_tts(text, byte_stream, cache_file)
                return

            client = ElevenLabs(api_key=api_key)

            audio_stream = client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_turbo_v2",
                voice_settings=voice_settings,
                output_format="mp3_44100_128"
            )

            full_audio = b""
            for chunk in audio_stream:
                if sm.interrupt_flag:
                    break
                byte_stream.put(chunk)
                full_audio += chunk

            byte_stream.put(None)  # EOF

            if not sm.interrupt_flag and full_audio:
                try:
                    with open(cache_file, "wb") as f:
                        f.write(full_audio)
                except Exception:
                    pass

            return

        except Exception as e:
            error = str(e).lower()

            if any(err in error for err in ["quota", "limit", "payment", "unauthorized", "invalid", "unauthenticated", "unusual"]):
                print(f"[TTS] Key blocked. Rotating...")
                old_key = api_key
                rotate_key()

                # If rotation gave us the same key back, fall back to Edge
                if get_key() == old_key:
                    print("[TTS] All ElevenLabs keys exhausted. Falling back to Edge TTS.")
                    _run_edge_tts(text, byte_stream, cache_file)
                    return

                retries += 1
                continue

            print("[TTS ERROR]", e)
            print("[TTS] Falling back to Edge TTS.")
            _run_edge_tts(text, byte_stream, cache_file)
            return

    print("[TTS] Max retries hit. Falling back to Edge TTS.")
    _run_edge_tts(text, byte_stream, cache_file)


# ============================================================
# ENGINE 3: KOKORO LOCAL TTS (OPEN-WEIGHTS, HIGH QUALITY)
# ============================================================

def _run_kokoro_tts(text, byte_stream, cache_file):
    """Runs the Kokoro TTS model using a4f_local (OpenAI API format)."""
    try:
        from a4f_local import A4F
    except ImportError:
        print("[TTS ERROR] a4f_local not found. Please run: pip install a4f-local")
        print("[TTS] Falling back to Edge TTS.")
        _run_edge_tts(text, byte_stream, cache_file)
        return

    try:
        client = A4F()
        
        # a4f_local returns raw audio bytes (mp3 format)
        audio_bytes = client.audio.speech.create(
            model="tts-1",
            input=text,
            voice="nova"
        )
        
        if audio_bytes:
            byte_stream.put(audio_bytes)
            
        byte_stream.put(None) # EOF
        
        if not sm.interrupt_flag and audio_bytes:
            try:
                with open(cache_file, "wb") as f:
                    f.write(audio_bytes)
            except Exception:
                pass
                
    except Exception as e:
        print("[KOKORO TTS ERROR]", e)
        print("[TTS] Falling back to Edge TTS.")
        _run_edge_tts(text, byte_stream, cache_file)


# ============================================================
# MAIN TTS FUNCTION (NON-BLOCKING)
# ============================================================

def speak_audio(text, pause_ms=0):

    if not text.strip():
        return

    stream_id = state.CURRENT_STREAM_ID

    # Mark as speaking
    state.MIC_MUTED = True
    state.INTERRUPT_LISTENING = True
    state.SPEAKING = True

    global active_tts_tasks
    with tts_lock:
        active_tts_tasks += 1

    def tts_worker():
        global active_tts_tasks
        try:

            # -----------------------
            # CACHE CHECK
            # -----------------------

            engine_tag = TTS_ENGINE
            key_hash = hashlib.md5(f"{text}_{engine_tag}".encode()).hexdigest()
            format_flag = "mp3"
            
            cache_file = CACHE_DIR / f"{key_hash}.{format_flag}"

            if cache_file.exists():
                if stream_id != state.CURRENT_STREAM_ID:
                    return

                with open(cache_file, "rb") as f:
                    data = f.read()

                byte_stream = queue.Queue()
                audio_queue.put((byte_stream, pause_ms, cache_file, format_flag))

                chunk_size = 4096
                for i in range(0, len(data), chunk_size):
                    byte_stream.put(data[i:i+chunk_size])
                byte_stream.put(None)
                return

            # -----------------------
            # GENERATE AUDIO
            # -----------------------

            byte_stream = queue.Queue()
            audio_queue.put((byte_stream, pause_ms, cache_file, format_flag))

            if TTS_ENGINE == "elevenlabs":
                _run_elevenlabs_tts(text, byte_stream, cache_file)
            elif TTS_ENGINE == "kokoro":
                _run_kokoro_tts(text, byte_stream, cache_file)
            else:
                _run_edge_tts(text, byte_stream, cache_file)

        except Exception as e:
            print("[TTS WORKER ERROR]", e)

        finally:
            with tts_lock:
                active_tts_tasks -= 1

            if active_tts_tasks == 0 and audio_queue.empty() and not sm.pipeline_active:
                if sm.current == AgentState.SPEAKING:
                    if getattr(sm, "handoff_to_sleep", False):
                        sm.transition(AgentState.SLEEPING)
                        sm.handoff_to_sleep = False
                    else:
                        sm.transition(AgentState.LISTENING)
            
            # Always update LAST_SPOKEN_TIME so the 1.0s room echo buffer applies
            state.LAST_SPOKEN_TIME = time.time()

    # 🚀 RUN TTS IN PARALLEL
    threading.Thread(target=tts_worker, daemon=True).start()
