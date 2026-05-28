from Features.Study_Tools.revision_planner import generate_revision_plan

def handle(text, ai_reply):

    if "revision plan" in text:
        topic = text.replace("revision plan", "").strip()
        return generate_revision_plan(topic)

    prompt = f"""
You are a strict but friendly teacher.
Explain step by step.
Ask me 1 question at the end to test me.
If topic is hard, use examples.

Topic:
{text}
"""
    return ai_reply(prompt)

