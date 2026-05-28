def is_confirmation(text):
    confirmation = [
        "yes",
        "yeah", 
        "sure", 
        "ok",
        "k",
        "okay",
        "sure",
        "remember it",
        "remember that",
        "do it",
        "go for it"
    ]
    return any(word in text.lower() for word in confirmation)