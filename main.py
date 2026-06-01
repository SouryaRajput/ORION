import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from voice.service import run_voice_service
if __name__ == "__main__":
    run_voice_service()