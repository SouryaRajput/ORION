def handle(text, ai_reply):
    prompt = f"""
You are a senior software engineer.
Explain bugs clearly.
Show fixed code.
Explain why it failed.

Problem:
{text}
"""
    return ai_reply(prompt)
