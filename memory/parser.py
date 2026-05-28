def parse_memory(text):
    text = text.lower()

    if "remember my name is" in text:
        value = text.split("remember my name is",1)[1].strip()
        return ("profile", "name", value)

    if "remember my birthday is" in text:
        value = text.split("remember my birthday is",1)[1].strip()
        return ("profile", "birthday", value)

    if "remember i like" in text:
        value = text.split("remember i like",1)[1].strip()
        return ("preferences", "likes", value)

    if "remember that" in text:
        value = text.split("remember that",1)[1].strip()
        return ("notes", "general", value)

    return None
