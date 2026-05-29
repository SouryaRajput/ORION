import time
from Core.latency import tracker

print("Starting fake speech...")
time.sleep(1)

# End of speech
tracker.mark_end_of_speech()
time.sleep(0.5)

# STT completes
tracker.mark_checkpoint("STT Engine")
time.sleep(0.1)

# Intent router
tracker.mark_checkpoint("Intent Router (LLM)")
time.sleep(1.2)

# LLM first token
tracker.mark_checkpoint("LLM (Time To First Token)")
time.sleep(0.2)

# TTS Audio start
tracker.end_tracking_and_report()
