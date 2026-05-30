import time
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

t0 = time.time()
stream = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "Hello, how are you? " * 10}],
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        t1 = time.time()
        print(f"TTFT 1st request: {(t1-t0)*1000:.1f} ms")
        break

t0 = time.time()
stream = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "Hello again, how are you? " * 10}],
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        t1 = time.time()
        print(f"TTFT 2nd request (reusing connection): {(t1-t0)*1000:.1f} ms")
        break
