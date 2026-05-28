def handle(text, ai_reply):
    prompt = f"""
You are a calm personal life assistant.
Give practical advice.
Be clear and short.
Help me decide and plan.

Situation:
{text}
"""
    return ai_reply(prompt)
