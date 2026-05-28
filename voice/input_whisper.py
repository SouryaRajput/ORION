from faster_whisper import WhisperModel
import tempfile
import soundfile as sf
import os
from dotenv import load_dotenv

load_dotenv()
# Load once globally
model = WhisperModel("large-v3", compute_type="int8")


def transcribe_audio(audio):

    temp_path = None

    try:
        # Save audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            sf.write(temp_path, audio, 16000)

        segments, info = model.transcribe(
            temp_path,
            beam_size=5,
            vad_filter=True
        )

        text = " ".join([seg.text for seg in segments]).strip()

        if not text or len(text.split()) < 2:
            return None

        print("[WHISPER]", text)

        return text

    except Exception as e:
        print("[WHISPER ERROR]", e)
        return None

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass