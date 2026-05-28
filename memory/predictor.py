prediction_map = {
    "open": "system",
    "launch": "system",
    "what": "question",
    "how": "question",
    "explain": "question",
    "screen": "vision"
}


def predict(text):

    words = text.lower().split()

    if not words:
        return None

    first = words[0]

    return prediction_map.get(first)