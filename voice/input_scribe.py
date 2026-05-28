import tempfile
import os
import soundfile as sf

from elevenlabs.client import ElevenLabs
from voice.key_manager import get_key, rotate_key


SAMPLE_RATE = 16000


def transcribe_audio(audio):

    temp_path = None

    try:

        # -----------------------
        # Save audio to temp file
        # -----------------------

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            sf.write(temp_path, audio, SAMPLE_RATE)

        retries = 0
        MAX_RETRIES = 4

        while retries < MAX_RETRIES:

            try:

                api_key = get_key()
                #print(f"[STT] Using key {api_key[:10]}...")

                client = ElevenLabs(api_key=api_key)

                with open(temp_path, "rb") as audio_file:

                    transcript = client.speech_to_text.convert(
                        file=audio_file,
                        model_id="scribe_v2",
                        language_code="en"
                    )

                    if not transcript or not hasattr(transcript, "text"):
                        print("[STT WARNING] Empty Transcript Reply")
                        return None

                    text = transcript.text.strip()

                if not text:
                    return None

                return text


            except Exception as e:

                error = str(e).lower()

                # ElevenLabs sometimes returns None response
                if "nonetype" in error:
                    print("[STT RETRY] Invalid API response")
                    retries += 1
                    continue

                if any(err in error for err in ["quota", "limit", "payment", "unauthorized", "invalid", "unauthenticated", "unusual"]):
                    #print("[STT] Error encountered (Quota/Auth) → rotating key")
                    rotate_key()
                    retries += 1
                    continue

                print("[STT ERROR]", e)
                retries += 1


        print("[STT] All ElevenLabs keys exhausted.")
        return None


    finally:

        # -----------------------
        # Cleanup temp file
        # -----------------------

        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass