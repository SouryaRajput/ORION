import os
import base64
import requests
import json
import soundfile as sf
import tempfile

from dotenv import load_dotenv
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
SAMPLE_RATE = 16000

def transcribe_audio(audio):
    """
    Transcribes audio using Gemini 2.5 Flash via OpenRouter.
    Gemini 1.5/2.5 Flash natively supports multimodal audio input.
    """
    temp_path = None
    try:
        # Save audio to a temporary wav file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            sf.write(temp_path, audio, SAMPLE_RATE)
            
        with open(temp_path, "rb") as f:
            audio_data = f.read()
            
        audio_b64 = base64.b64encode(audio_data).decode("utf-8")
        
        # Call OpenRouter with Gemini 2.5 Flash
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "google/gemini-2.5-flash",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please transcribe the following audio exactly as spoken. Do not add any extra commentary, translation, or description. Just the pure transcription."
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_b64,
                                "format": "wav"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.0
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        
        response.raise_for_status()
        data = response.json()
        
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        
        if not text:
            return None
            
        # Strip out weird model artifacts if it hallucinated markdown
        text = text.strip("`").strip('"').strip()
        
        return text
        
    except Exception as e:
        print("[GEMINI STT ERROR]", e)
        return None
        
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
