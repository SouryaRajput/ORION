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
            # Configure ffplay based on format with ultra-low latency flags
            if format_flag == "f32le":
                ffplay_cmd = ["ffplay", "-fflags", "nobuffer", "-flags", "low_delay", "-f", "f32le", "-ar", "24000", "-ac", "1", "-nodisp", "-autoexit", "-i", "pipe:0"]
            elif format_flag == "mp3":
                ffplay_cmd = ["ffplay", "-fflags", "nobuffer", "-flags", "low_delay", "-f", "mp3", "-nodisp", "-autoexit", "-i", "pipe:0"]
            else:
                ffplay_cmd = ["ffplay", "-fflags", "nobuffer", "-flags", "low_delay", "-nodisp", "-autoexit", "-i", "pipe:0"]

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
# ENGINE 3: ELEVENLABS (EMOTIVE, FAST TURBO)
# ============================================================

import requests
import threading
import time
import random

elevenlabs_session = requests.Session()
elevenlabs_semaphore = threading.Semaphore(4)

def _run_elevenlabs_tts(text, byte_stream, cache_file):
    """Uses ElevenLabs turbo-v2.5 for fast and highly emotional TTS."""
    keys = [os.getenv(f"ELEVEN_API_KEY_{i}") for i in range(1, 5)]
    voice_ids = [os.getenv(f"ELEVEN_VOICE_ID_{i}") for i in range(1, 5)]
    
    valid = [(k, v) for k, v in zip(keys, voice_ids) if k and v]
    if not valid:
        print("[TTS] No ElevenLabs keys configured.")
        byte_stream.put(None)
        return
        
    api_key, voice_id = random.choice(valid)
    
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream?optimize_streaming_latency=4"
        
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "output_format": "mp3_44100_128"
        }
        
        with elevenlabs_semaphore:
            response = elevenlabs_session.post(url, headers=headers, json=payload, stream=True)
            if response.status_code == 429:
                time.sleep(0.5)
                response = elevenlabs_session.post(url, headers=headers, json=payload, stream=True)
            response.raise_for_status()
            
            full_audio = b""
            for chunk in response.iter_content(chunk_size=4096):
                if sm.interrupt_flag:
                    break
                if chunk:
                    byte_stream.put(chunk)
                    full_audio += chunk
                    
            byte_stream.put(None)
            
            if not sm.interrupt_flag and full_audio:
                try:
                    with open(cache_file, "wb") as f:
                        f.write(full_audio)
                except Exception:
                    pass
                    
    except Exception as e:
        print(f"[ELEVENLABS TTS ERROR] {e}")
        byte_stream.put(None)


# ============================================================
# ENGINE 4: DEEPGRAM (ULTRA-LOW LATENCY, STREAMING)
# ============================================================

import requests
import threading
import time

deepgram_session = requests.Session()
deepgram_semaphore = threading.Semaphore(4)

def _run_deepgram_tts(text, byte_stream, cache_file):
    """Uses Deepgram Aura TTS. Extremely fast streaming with high quality."""
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    if not DEEPGRAM_API_KEY:
        print("[TTS] No Deepgram key configured.")
        byte_stream.put(None)
        return
        
    try:
        url = f"https://api.deepgram.com/v1/speak?model=aura-asteria-en"
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json"
        }
        
        with deepgram_semaphore:
            # Use persistent session to eliminate TLS handshake latency on subsequent TTS calls
            response = deepgram_session.post(url, headers=headers, json={"text": text}, stream=True)
            
            # Simple retry mechanism for 429 rate limits
            if response.status_code == 429:
                time.sleep(0.5)
                response = deepgram_session.post(url, headers=headers, json={"text": text}, stream=True)
                
            response.raise_for_status()
            
            full_audio = b""
            for chunk in response.iter_content(chunk_size=4096):
                if sm.interrupt_flag:
                    break
                if chunk:
                    byte_stream.put(chunk)
                    full_audio += chunk
                    
            byte_stream.put(None) # EOF
            
            if not sm.interrupt_flag and full_audio:
                try:
                    with open(cache_file, "wb") as f:
                        f.write(full_audio)
                except Exception:
                    pass
                
    except Exception as e:
        print(f"[DEEPGRAM TTS ERROR] {e}")
        byte_stream.put(None)

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

            if TTS_ENGINE == "deepgram":
                engine_tag = "deepgram_mp3"
            else:
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
            else:
                _run_deepgram_tts(text, byte_stream, cache_file)

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
