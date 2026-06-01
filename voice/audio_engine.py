import pyaudio
import struct
import pvporcupine
import webrtcvad
import numpy as np
import os
from dotenv import load_dotenv
import time
import math

import voice.state as state
from Core.state_machine import sm, AgentState

load_dotenv()

ACCESS_KEY = os.getenv("PICOVOICE_KEY")

# -----------------------
# CONFIG
# -----------------------

from Core.config import config

vad = webrtcvad.Vad(config.voice.vad_aggressiveness)

porcupine = pvporcupine.create(
    access_key=ACCESS_KEY,
    keywords=config.system.wake_words
)

# 🔥 IMPORTANT FIX → match Porcupine frame size
FRAME_SIZE = porcupine.frame_length  # usually 512

pa = pyaudio.PyAudio()

stream = pa.open(
    rate=config.voice.rate,
    channels=config.voice.channels,
    format=pyaudio.paInt16,
    input=True,
    frames_per_buffer=FRAME_SIZE
)

# -----------------------
# MAIN AUDIO LOOP
# -----------------------

def listen():

    last_wake_time = 0

    audio_buffer = []
    silence_frames = 0
    speech_started = False

    # 🔥 NEW: small rolling buffer (pre-roll)
    pre_buffer = []

    while True:

        pcm = stream.read(FRAME_SIZE, exception_on_overflow=False)
        pcm_unpacked = struct.unpack_from("h" * FRAME_SIZE, pcm)

        # -----------------------
        # 1. ULTRA-STRICT MUTE (DEAF WHILE SPEAKING)
        # -----------------------
        # If JARVIS is speaking, or just finished speaking, or the mic is manually muted:
        # Completely drop the audio frame. Do not check wake words, do not transcribe.
        if sm.mic_muted or sm.current == AgentState.SPEAKING or (time.time() - getattr(state, "LAST_SPOKEN_TIME", 0) < 1.0):
            audio_buffer = []
            pre_buffer = []
            speech_started = False
            silence_frames = 0
            continue

        # -----------------------
        # 2. WAKE DETECTION
        # -----------------------
        result = porcupine.process(pcm_unpacked)

        if result >= 0:
            if time.time() - last_wake_time < 2:
                continue

            last_wake_time = time.time()
            print("🔥 Wake detected")
            
            # WARM UP LLM CONNECTION (Parallel preemptive TLS handshake)
            def _warm_llm():
                try:
                    from Core.ai import groq_client
                    if groq_client:
                        groq_client.models.list()
                except:
                    pass
            import threading
            threading.Thread(target=_warm_llm, daemon=True).start()

            state.WAKE_TRIGGERED = True
            state.INTERRUPT = True
            state.CURRENT_STREAM_ID += 1

            audio_buffer = []
            pre_buffer = pre_buffer[-2:] if len(pre_buffer) > 2 else pre_buffer.copy()
            silence_frames = 0
            speech_started = False
            continue

        # -----------------------
        # 3. AUTO-SLEEP TIMEOUT
        # -----------------------
        if sm.current == AgentState.LISTENING and not speech_started:
            now = time.time()
            if sm.waiting_for_followup:
                if now - sm.followup_start_time > config.voice.auto_sleep_followup_timeout:
                    print("💤 Follow-up timeout. Going to sleep.")
                    sm.transition(AgentState.SLEEPING)
                    return None, None
            else:
                if now - sm.last_engaged_time > config.voice.auto_sleep_idle_timeout:
                    print("💤 Idle timeout. Going to sleep.")
                    sm.transition(AgentState.SLEEPING)
                    return None, None

        # If we are sleeping and no wake word was triggered, drop audio
        if sm.current == AgentState.SLEEPING and not state.WAKE_TRIGGERED:
            continue

        # -----------------------
        # 4. PRE-BUFFER (last ~0.5 sec)
        # -----------------------
        pre_buffer.append(pcm)
        if len(pre_buffer) > 8:  # ~0.5 sec
            pre_buffer.pop(0)

        # -----------------------
        # 5. VAD & VOLUME DETECTION
        # -----------------------
        vad_frame = pcm[:480 * 2]

        try:
            is_speech = vad.is_speech(vad_frame, config.voice.rate)
            
            # Strict RMS volume check to reject fan noise / static hallucinations
            if is_speech:
                sum_squares = sum(s*s for s in pcm_unpacked)
                rms = math.sqrt(sum_squares / len(pcm_unpacked))
                if rms < config.voice.volume_threshold_rms:  # Very strict noise floor threshold
                    is_speech = False
                    
        except:
            continue

        if is_speech:

            if not speech_started:
                speech_started = True
                # 🔥 include pre-roll at speech start
                audio_buffer.extend(pre_buffer)
                listen.last_partial_time = time.time()
                listen.partial_in_progress = False

            silence_frames = 0
            audio_buffer.append(pcm)

        else:

            if speech_started:
                silence_frames += 1
                audio_buffer.append(pcm)

        # -----------------------
        # PARTIAL STT STREAMING
        # -----------------------
        if speech_started and (time.time() - getattr(listen, "last_partial_time", 0)) > 0.6:
            if len(audio_buffer) * FRAME_SIZE / config.voice.rate > 0.6:
                if not getattr(listen, "partial_in_progress", False):
                    listen.last_partial_time = time.time()
                    listen.partial_in_progress = True
                    
                    audio_data_partial = b"".join(list(audio_buffer))
                    
                    def _do_partial(audio_bytes):
                        try:
                            import numpy as np
                            audio_np_p = (
                                np.frombuffer(audio_bytes, dtype=np.int16)
                                .astype(np.float32) / 32768.0
                            )
                            from voice.input_groq import transcribe_audio
                            text = transcribe_audio(audio_np_p)
                            if text and speech_started: # Only send if still speaking
                                from voice.pipeline import _send_to_ui
                                _send_to_ui("user_partial", text)
                                print(f"\r\033[90m[Partial] {text}\033[0m", end="", flush=True)
                        except Exception as e:
                            pass
                        finally:
                            listen.partial_in_progress = False

                    import threading
                    threading.Thread(target=_do_partial, args=(audio_data_partial,), daemon=True).start()

        # -----------------------
        # EARLY SPECULATIVE STT
        # -----------------------
        if speech_started and silence_frames == 20: # ~640ms silence, high probability speech is over
            import concurrent.futures
            if not hasattr(listen, "stt_executor"):
                listen.stt_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

            def _early_stt():
                try:
                    audio_data_early = b"".join(list(audio_buffer))
                    audio_np_early = (
                        np.frombuffer(audio_data_early, dtype=np.int16)
                        .astype(np.float32) / 32768.0
                    )
                    from voice.input_groq import transcribe_audio
                    return transcribe_audio(audio_np_early)
                except Exception:
                    return None
            
            listen.early_future = listen.stt_executor.submit(_early_stt)

        # -----------------------
        # END OF SPEECH
        # -----------------------

        # Wait for ~1.28 seconds of silence (40 frames * 32ms) to avoid cutting off user mid-sentence
        if speech_started and silence_frames > 40:
            
            # 🔥 Ignore ultra-short blips (e.g. typing, breathing) < 0.5s
            if len(audio_buffer) < (config.voice.rate * 0.5) / FRAME_SIZE:
                speech_started = False
                silence_frames = 0
                audio_buffer = []
                continue

            audio_data = b"".join(audio_buffer)

            audio_np = (
                np.frombuffer(audio_data, dtype=np.int16)
                .astype(np.float32) / 32768.0
            )

            # Await early STT to finish if it's still running
            early_txt = None
            if getattr(listen, "early_future", None):
                try:
                    early_txt = listen.early_future.result(timeout=1.0)
                except Exception:
                    pass
            listen.early_future = None

            from Core.latency import tracker
            tracker.mark_end_of_speech()
            return audio_np, early_txt

        # -----------------------
        # SAFETY TIMEOUT (~4 sec)
        # -----------------------

        if speech_started and len(audio_buffer) > (config.voice.rate * 8) / FRAME_SIZE:

            audio_data = b"".join(audio_buffer)

            audio_np = (
                np.frombuffer(audio_data, dtype=np.int16)
                .astype(np.float32) / 32768.0
            )

            from Core.latency import tracker
            tracker.mark_end_of_speech()
            return audio_np, None