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

RATE = 16000

vad = webrtcvad.Vad(3)  # Most aggressive mode to cut off instantly when speech stops

porcupine = pvporcupine.create(
    access_key=ACCESS_KEY,
    keywords=["jarvis"]
)

# 🔥 IMPORTANT FIX → match Porcupine frame size
FRAME_SIZE = porcupine.frame_length  # usually 512

pa = pyaudio.PyAudio()

stream = pa.open(
    rate=RATE,
    channels=1,
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
                if now - sm.followup_start_time > getattr(state, "FOLLOWUP_TIMEOUT", 10):
                    print("💤 Follow-up timeout. Going to sleep.")
                    sm.transition(AgentState.SLEEPING)
                    return None
            else:
                if now - sm.last_engaged_time > getattr(state, "ENGAGE_TIMEOUT", 10):
                    print("💤 Idle timeout. Going to sleep.")
                    sm.transition(AgentState.SLEEPING)
                    return None

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
            is_speech = vad.is_speech(vad_frame, RATE)
            
            # Strict RMS volume check to reject fan noise / static hallucinations
            if is_speech:
                sum_squares = sum(s*s for s in pcm_unpacked)
                rms = math.sqrt(sum_squares / len(pcm_unpacked))
                if rms < 400:  # Very strict noise floor threshold
                    is_speech = False
                    
        except:
            continue

        if is_speech:

            if not speech_started:
                speech_started = True
                # 🔥 include pre-roll at speech start
                audio_buffer.extend(pre_buffer)

            silence_frames = 0
            audio_buffer.append(pcm)

        else:

            if speech_started:
                silence_frames += 1
                audio_buffer.append(pcm)

        # -----------------------
        # END OF SPEECH
        # -----------------------

        if speech_started and silence_frames > 8:
            
            # 🔥 Ignore ultra-short blips (e.g. typing, breathing) < 0.5s
            if len(audio_buffer) < (RATE * 0.5) / FRAME_SIZE:
                speech_started = False
                silence_frames = 0
                audio_buffer = []
                continue

            audio_data = b"".join(audio_buffer)

            audio_np = (
                np.frombuffer(audio_data, dtype=np.int16)
                .astype(np.float32) / 32768.0
            )

            return audio_np

        # -----------------------
        # SAFETY TIMEOUT (~4 sec)
        # -----------------------

        if speech_started and len(audio_buffer) > (RATE * 8) / FRAME_SIZE:

            audio_data = b"".join(audio_buffer)

            audio_np = (
                np.frombuffer(audio_data, dtype=np.int16)
                .astype(np.float32) / 32768.0
            )

            return audio_np