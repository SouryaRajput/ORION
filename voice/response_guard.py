import re


BANNED_PATTERNS = [
    r"completed step:.*",
    r"step\s*\d+:.*",
    r"next step:.*",
    r"task completed.*",
    r"here'?s the plan.*",
    r"\[.*?\]",
    r"\(.*?\)"
]


def clean_response(text):

    if not text:
        return text

    cleaned = text

    for pattern in BANNED_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned