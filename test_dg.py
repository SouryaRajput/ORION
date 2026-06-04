import os, requests, time
from dotenv import load_dotenv
load_dotenv()
dg_key = os.getenv("DEEPGRAM_API_KEY")
start = time.time()
res = requests.post(
    "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true",
    headers={"Authorization": f"Token {dg_key}", "Content-Type": "audio/wav"},
    data=b"dummy_wav_data_not_real_audio_but_tests_auth"
)
print(time.time() - start, res.json())
