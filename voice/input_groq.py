import os
import tempfile
import soundfile as sf
from groq import Groq

from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY)

SAMPLE_RATE = 16000

def transcribe_audio(audio):
    """
    Transcribes audio using Groq's Whisper API (whisper-large-v3).
    Insanely fast: ~50-100ms latency.
    """
    temp_path = None
    try:
        # Save audio to a temporary wav file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            sf.write(temp_path, audio, SAMPLE_RATE)
            
        with open(temp_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
              file=(temp_path, file.read()),
              model="whisper-large-v3-turbo",
              response_format="text",
              language="en"
            )
            
        text = transcription.strip()
        if not text:
            return None
            
        return text
        
    except Exception as e:
        print("[GROQ STT ERROR]", e)
        return None
        
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
