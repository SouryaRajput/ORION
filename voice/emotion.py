# -----------------------
# EMOTION DETECTOR
# Maps text content to ElevenLabs VoiceSettings profiles
# for human-like tonal variation.
# -----------------------

from elevenlabs import VoiceSettings


# -----------------------
# EMOTION PROFILES
# -----------------------

PROFILES = {
    "warm": VoiceSettings(
        stability=0.40,
        similarity_boost=0.75,
        style=0.30,
        use_speaker_boost=True
    ),
    "excited": VoiceSettings(
        stability=0.30,
        similarity_boost=0.70,
        style=0.50,
        use_speaker_boost=True
    ),
    "serious": VoiceSettings(
        stability=0.60,
        similarity_boost=0.80,
        style=0.10,
        use_speaker_boost=True
    ),
    "calm": VoiceSettings(
        stability=0.55,
        similarity_boost=0.75,
        style=0.20,
        use_speaker_boost=True
    ),
    "neutral": VoiceSettings(
        stability=0.50,
        similarity_boost=0.75,
        style=0.0,
        use_speaker_boost=True
    ),
}


# -----------------------
# KEYWORD TRIGGERS
# -----------------------

WARM_WORDS = {
    "good morning", "good evening", "good night", "hello", "hi there",
    "hey", "welcome", "great job", "nice", "well done", "proud",
    "love", "thank", "appreciate", "glad", "happy", "awesome",
    "wonderful", "brilliant", "fantastic", "sure thing", "of course",
    "no problem", "you got it", "happy to help",
}

EXCITED_WORDS = {
    "wow", "amazing", "incredible", "guess what", "breaking",
    "just found", "discovered", "exciting", "huge", "perfect",
    "excellent", "milestone", "congrats", "celebration", "win",
    "success", "finally", "nailed it", "let's go",
}

SERIOUS_WORDS = {
    "error", "fail", "crash", "warning", "careful", "danger",
    "issue", "problem", "bug", "broken", "couldn't", "unable",
    "sorry", "unfortunately", "bad news", "critical", "urgent",
    "missing", "not found", "down", "offline",
}

CALM_WORDS = {
    "sleep", "relax", "calm", "breathe", "easy", "no rush",
    "take your time", "don't worry", "it's okay", "it's fine",
    "all good", "gentle", "quiet", "peace", "rest", "goodnight",
    "sleeping", "pause", "chill",
}


def detect_emotion(text: str) -> str:
    """
    Fast keyword scan to determine the emotional tone of text.
    Returns one of: 'warm', 'excited', 'serious', 'calm', 'neutral'.
    """
    text_lower = text.lower()

    # Check in priority order (serious > excited > warm > calm > neutral)
    for word in SERIOUS_WORDS:
        if word in text_lower:
            return "serious"

    for word in EXCITED_WORDS:
        if word in text_lower:
            return "excited"

    for word in WARM_WORDS:
        if word in text_lower:
            return "warm"

    for word in CALM_WORDS:
        if word in text_lower:
            return "calm"

    return "neutral"


def get_voice_settings(text: str) -> VoiceSettings:
    """
    Returns the appropriate ElevenLabs VoiceSettings for the given text.
    """
    emotion = detect_emotion(text)
    return PROFILES[emotion]