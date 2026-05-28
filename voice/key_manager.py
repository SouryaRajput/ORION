import os
from dotenv import load_dotenv

load_dotenv()

# -----------------------
# LOAD ALL KEYS
# -----------------------

KEYS = []
VOICES = []

for i in range(1, 5):
    k = os.getenv(f"ELEVEN_API_KEY_{i}", "").strip()
    v = os.getenv(f"ELEVEN_VOICE_ID_{i}", "").strip()
    if k and v:
        KEYS.append((k, v))

current_index = 0


def get_key():
    if not KEYS:
        return ""
    return KEYS[current_index][0]


def get_voice():
    if not KEYS:
        return ""
    return KEYS[current_index][1]


def rotate_key():
    """Rotate to the next available ElevenLabs API key."""
    global current_index
    if not KEYS:
        return
    
    old_index = current_index
    current_index = (current_index + 1) % len(KEYS)
    
    if current_index == old_index:
        print("[KEY MANAGER] Only 1 key available. Cannot rotate.")
    else:
        print(f"[KEY MANAGER] Rotated: Key {old_index + 1} → Key {current_index + 1}")