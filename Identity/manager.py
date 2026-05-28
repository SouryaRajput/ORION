import json
import os

IDENTITY_FILE = "Identity/profile.json"

DEFAULT_PROFILE = {
    "name": None,
    "language_preference": "English",
    "learning_style": "step_by_step",
    "tone_preference": "casual",
    "hardware_interest": True
}

def load_identity():
    if not os.path.exists(IDENTITY_FILE):
        save_identity(DEFAULT_PROFILE)
        return DEFAULT_PROFILE

    # If file exists but is empty or broken → reset safely
    try:
        with open(IDENTITY_FILE, "r") as f:
            data = json.load(f)

            # Extra safety: ensure it's a dict
            if not isinstance(data, dict):
                raise ValueError("Invalid identity format")

            return data

    except Exception:
        # File exists but is corrupted or empty
        save_identity(DEFAULT_PROFILE)
        return DEFAULT_PROFILE


def save_identity(profile):
    os.makedirs("Identity", exist_ok=True)
    with open(IDENTITY_FILE, "w") as f:
        json.dump(profile, f, indent=2)