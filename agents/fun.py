def handle(text, ai_reply):
    prompt = f"""
You are a friendly, funny companion.
Be playful.
Light roast allowed.
Keep things fun.

Message:
{text}
"""
    return ai_reply(prompt)
