def detect_response_style(text):

    text = text.lower()

    # short factual queries
    short_keywords = [
        "what is",
        "who is",
        "define",
        "meaning of",
        "when did",
        "where is"
    ]

    # deeper explanations
    long_keywords = [
        "explain",
        "why",
        "how does",
        "how do",
        "in detail",
        "deeply"
    ]

    for k in long_keywords:
        if k in text:
            return "long"

    for k in short_keywords:
        if k in text:
            return "short"

    return "medium"