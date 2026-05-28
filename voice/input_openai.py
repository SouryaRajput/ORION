import sounddevice as sd
import soundfile as sf
import numpy as np
import requests
import base64
import io
import os

from dotenv import load_dotenv
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
SAMPLE_RATE = 16000
DURATION = 4  # seconds


def record_audio():
    print("🎤 Listening...")
    recording = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16"
    )
    sd.wait()
    return recording


def audio_to_base64(audio_array):
    buffer = io.BytesIO()
    sf.write(buffer, audio_array, SAMPLE_RATE, format="WAV")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def transcribe_audio():
    audio = record_audio()
    audio_base64 = audio_to_base64(audio)

    payload = {
        "model": "openai/gpt-audio-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Transcribe this audio clearly. Only return the transcription."
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_base64,
                            "format": "wav"
                        }
                    }
                ]
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )

    data = response.json()

    try:
        return data["choices"][0]["message"]["content"].strip()
    except:
        print("STT error:", data)
        return None