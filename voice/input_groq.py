import os
import tempfile
import soundfile as sf
from groq import Groq

from dotenv import load_dotenv
from Core.ai import groq_client as client

SAMPLE_RATE = 16000

def transcribe_audio(audio):
    """
    Transcribes audio using Groq's Whisper API (whisper-large-v3).
    Insanely fast: ~50-100ms latency.
    """
    try:
        import io
        wav_io = io.BytesIO()
        sf.write(wav_io, audio, SAMPLE_RATE, format='wav')
        wav_io.seek(0)
        
        # Add a dummy name attribute so the API recognizes it as a file
        wav_io.name = "audio.wav"
            
        transcription = client.audio.transcriptions.create(
            file=("audio.wav", wav_io),
            model="whisper-large-v3",
            response_format="text",
            language="en"
        )
            
        text = transcription.strip()
        
        if not text:
            return None
            
        # Whisper Hallucination Filter
        import re
        # Remove punctuation, spaces, and make lowercase to normalize
        clean_text = re.sub(r'[^a-z0-9]', '', text.lower())
        
        # Common whisper-large-v3 hallucinations during pure noise/silence
        hallucinations = {
            "thankyou", "imsorry", "thanksforwatching", "thankyouforwatching", 
            "subscribe", "bye", "you", "thisisalloverthecountry", 
            "thisisalloverthetable", "thankyouverymuch", "iam", "am"
        }
        
        if clean_text in hallucinations:
            return None
            
        return text
        
    except Exception as e:
        print("[GROQ STT ERROR]", e)
        return None

