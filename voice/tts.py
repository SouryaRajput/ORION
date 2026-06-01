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

import pyaudio
global_pa = pyaudio.PyAudio()


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
    raw_stream = None
    raw_stream_format = None

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
            # For MP3, fallback to ffplay
            if format_flag == "mp3":
                ffplay_cmd = ["ffplay", "-fflags", "nobuffer", "-flags", "low_delay", "-f", "mp3", "-nodisp", "-autoexit", "-i", "pipe:0"]
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

                try:
                    process.stdin.close()
                except Exception:
                    pass

                while process.poll() is None:
                    if sm.interrupt_flag:
                        process.terminate()
                        with audio_queue.mutex:
                            audio_queue.queue.clear()
                        break
                    time.sleep(0.01)
                    
            # For RAW PCM (ElevenLabs, Gemini, Cartesia), use PyAudio for flawless direct sub-ms playback
            else:
                # Format mappings
                if format_flag == "f32le":
                    pa_format = pyaudio.paFloat32
                    bytes_per_sample = 4
                else:
                    pa_format = pyaudio.paInt16
                    bytes_per_sample = 2
                    
                if raw_stream is None or raw_stream_format != pa_format:
                    if raw_stream is not None:
                        raw_stream.stop_stream()
                        raw_stream.close()
                    raw_stream = global_pa.open(format=pa_format,
                                                channels=1,
                                                rate=24000,
                                                output=True)
                    raw_stream_format = pa_format
                                 
                first_chunk = True
                audio_buffer = b""
                
                while True:
                    if sm.interrupt_flag:
                        with audio_queue.mutex:
                            audio_queue.queue.clear()
                        break
                    
                    chunk = byte_stream.get()
                    if chunk is None:
                        # Write any remaining aligned bytes
                        if len(audio_buffer) >= bytes_per_sample:
                            aligned_len = len(audio_buffer) - (len(audio_buffer) % bytes_per_sample)
                            if aligned_len > 0:
                                raw_stream.write(audio_buffer[:aligned_len],
                                                 exception_on_underflow=False)
                        break
                        
                    audio_buffer += chunk
                    
                    # Pre-buffer 4096 bytes (approx 85ms) before playing to eliminate network jitter underflows
                    if first_chunk and len(audio_buffer) < 4096:
                        continue
                    
                    # Write in thick chunks (>= 4096 bytes) aligned to the sample format 
                    # This prevents BOTH phase distortion and PortAudio interrupt starvation
                    aligned_len = len(audio_buffer) - (len(audio_buffer) % bytes_per_sample)
                    if aligned_len >= 4096:
                        raw_stream.write(audio_buffer[:aligned_len],
                                         exception_on_underflow=False)
                        audio_buffer = audio_buffer[aligned_len:]
                    
                    if first_chunk:
                        from Core.latency import tracker
                        tracker.end_tracking_and_report()
                        first_chunk = False
                        
                # Keep PortAudio open across speech chunks. Reopening the
                # device at punctuation boundaries can produce audible clicks.

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
# Use a semaphore of 1 for ElevenLabs to completely prevent 429 rate limits on free keys
elevenlabs_semaphore = threading.Semaphore(1)

_eleven_key_idx = 0
_eleven_key_lock = threading.Lock()

def _run_elevenlabs_tts(text, byte_stream, cache_file):
    """Uses ElevenLabs turbo-v2.5 for fast and highly emotional TTS."""
    global _eleven_key_idx
    
    keys = [os.getenv(f"ELEVEN_API_KEY_{i}") for i in range(1, 5)]
    voice_ids = [os.getenv(f"ELEVEN_VOICE_ID_{i}") for i in range(1, 5)]
    
    valid = [(k, v) for k, v in zip(keys, voice_ids) if k and v]
    if not valid:
        print("[TTS] No ElevenLabs keys configured.")
        byte_stream.put(None)
        return
        
    with _eleven_key_lock:
        api_key, voice_id = valid[_eleven_key_idx]
        _eleven_key_idx = (_eleven_key_idx + 1) % len(valid)
    
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream?optimize_streaming_latency=4"
        
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "output_format": "pcm_24000"
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
# ENGINE 5: GEMINI (NATIVE AUDIO, PARALLEL)
# ============================================================

import json
import base64

gemini_session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
gemini_session.mount('https://', adapter)
# Heavy parallelization allowed
gemini_semaphore = threading.Semaphore(10)

def _run_gemini_tts(text, byte_stream, cache_file):
    API_KEY = os.getenv("GEMINI_API_KEY")
    if not API_KEY:
        print("[TTS] No Gemini API Key configured.")
        byte_stream.put(None)
        return

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:streamGenerateContent?alt=sse&key={API_KEY}"
    
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": f"Speak exactly this text: '{text}'. Do not add any conversational text."}]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": "Puck"
                    }
                }
            }
        }
    }
    
    try:
        with gemini_semaphore:
            response = gemini_session.post(url, json=payload, stream=True)
            response.raise_for_status()
            
            full_audio = b""
            for line in response.iter_lines():
                if sm.interrupt_flag:
                    break
                if not line:
                    continue
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]
                    if data_str == "[DONE]" or data_str.strip() == "":
                        continue
                    try:
                        chunk_json = json.loads(data_str)
                        if "candidates" in chunk_json:
                            for cand in chunk_json["candidates"]:
                                if "content" in cand and "parts" in cand["content"]:
                                    for part in cand["content"]["parts"]:
                                        if "inlineData" in part:
                                            # Decode base64 PCM 24kHz
                                            audio_bytes = base64.b64decode(part["inlineData"]["data"])
                                            byte_stream.put(audio_bytes)
                                            full_audio += audio_bytes
                    except json.JSONDecodeError:
                        pass
                        
            byte_stream.put(None)
            
            if not sm.interrupt_flag and full_audio:
                try:
                    with open(cache_file, "wb") as f:
                        f.write(full_audio)
                except Exception:
                    pass
    except Exception as e:
        print(f"[GEMINI TTS ERROR] {e}")
        byte_stream.put(None)


# ============================================================
# ENGINE 6: CARTESIA (ULTRA-LOW LATENCY WEBSOCKET)
# ============================================================

import websocket
import uuid

cartesia_ws = None
cartesia_ws_lock = threading.Lock()
cartesia_send_lock = threading.Lock()
cartesia_streams_lock = threading.Lock()
cartesia_synthesis_semaphore = threading.Semaphore(1)
cartesia_streams = {} # context_id -> queue.Queue()

def _close_cartesia_streams():
    with cartesia_streams_lock:
        streams = list(cartesia_streams.values())
        cartesia_streams.clear()

    for stream_queue in streams:
        stream_queue.put(None)

def cartesia_ws_listener():
    global cartesia_ws
    ws = None
    while True:
        if cartesia_ws is None:
            time.sleep(0.1)
            continue
        try:
            ws = cartesia_ws
            msg = ws.recv()
            if not msg:
                continue
            resp = json.loads(msg)
            ctx = resp.get("context_id")
            if not ctx:
                continue

            with cartesia_streams_lock:
                q = cartesia_streams.get(ctx)
            if q is None:
                continue

            if resp.get("type") == "chunk":
                audio_bytes = base64.b64decode(resp["data"])
                from Core.latency import tracker
                tracker.mark_checkpoint_once("First TTS Audio Chunk")
                q.put(audio_bytes)
            elif resp.get("type") == "error":
                print(f"[CARTESIA TTS ERROR] {resp.get('message', 'Unknown error')}")
                q.put(None)
            elif resp.get("type") == "done":
                q.put(None)
        except Exception:
            with cartesia_ws_lock:
                if cartesia_ws is ws:
                    cartesia_ws = None
                    _close_cartesia_streams()
            time.sleep(0.5)

threading.Thread(target=cartesia_ws_listener, daemon=True).start()

def _ensure_cartesia_ws():
    global cartesia_ws
    with cartesia_ws_lock:
        if cartesia_ws is None or not cartesia_ws.connected:
            API_KEY = os.getenv("CARTESIA_API_KEY")
            if not API_KEY:
                return None
            ws_url = "wss://api.cartesia.ai/tts/websocket"
            try:
                cartesia_ws = websocket.create_connection(
                    ws_url,
                    header=[
                        f"Authorization: Bearer {API_KEY}",
                        "Cartesia-Version: 2026-03-01"
                    ],
                    timeout=10
                )
                # The socket stays open between utterances. A receive timeout
                # would tear it down during ordinary pauses in conversation.
                cartesia_ws.settimeout(None)
            except Exception:
                cartesia_ws = None
    return cartesia_ws

# Pre-warm connection in background
threading.Thread(target=_ensure_cartesia_ws, daemon=True).start()

def _run_cartesia_tts(text, byte_stream, cache_file):
    API_KEY = os.getenv("CARTESIA_API_KEY")
    if not API_KEY:
        print("[TTS] No Cartesia API Key configured.")
        byte_stream.put(None)
        return

    with cartesia_synthesis_semaphore:
        ws = _ensure_cartesia_ws()
        if not ws:
            byte_stream.put(None)
            return

        ctx_id = str(uuid.uuid4())
        local_q = queue.Queue()
        with cartesia_streams_lock:
            cartesia_streams[ctx_id] = local_q

        payload = {
            "model_id": "sonic-3.5",
            "transcript": text,
            "voice": {"mode": "id", "id": "db6b0ed5-d5d3-463d-ae85-518a07d3c2b4"}, # Skylar
            "output_format": {"container": "raw", "encoding": "pcm_s16le", "sample_rate": 24000},
            "language": "en",
            "context_id": ctx_id,
            "continue": False
        }

        try:
            with cartesia_send_lock:
                ws.send(json.dumps(payload))

            full_audio = b""
            while True:
                if sm.interrupt_flag:
                    with cartesia_send_lock:
                        ws.send(json.dumps({"context_id": ctx_id, "cancel": True}))
                    break

                chunk = local_q.get()
                if chunk is None:
                    break

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
            print(f"[CARTESIA TTS ERROR] {e}")
            byte_stream.put(None)
        finally:
            with cartesia_streams_lock:
                cartesia_streams.pop(ctx_id, None)


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
                format_flag = "mp3"
            elif TTS_ENGINE == "elevenlabs":
                engine_tag = "elevenlabs_pcm24"
                format_flag = "s16le_24000"
            elif TTS_ENGINE == "gemini":
                engine_tag = "gemini_pcm24"
                format_flag = "s16le_24000"
            elif TTS_ENGINE == "cartesia":
                engine_tag = "cartesia_sonic35_pcm24"
                format_flag = "s16le_24000"
            else:
                engine_tag = TTS_ENGINE
                format_flag = "mp3"
            key_hash = hashlib.md5(f"{text}_{engine_tag}".encode()).hexdigest()
            
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
            elif TTS_ENGINE == "gemini":
                _run_gemini_tts(text, byte_stream, cache_file)
            elif TTS_ENGINE == "cartesia":
                _run_cartesia_tts(text, byte_stream, cache_file)
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
