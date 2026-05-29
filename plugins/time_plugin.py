import datetime
from typing import Optional, Dict, Any
from plugins.base import FastCommandPlugin

class TimeDatePlugin(FastCommandPlugin):
    def handle(self, text: str) -> Optional[Dict[str, Any]]:
        if "time is it" in text or text == "time":
            now = datetime.datetime.now().strftime("%I:%M %p")
            return {"action": "reply", "reply": f"The time is {now}."}

        if "date is it" in text or text == "date" or text == "what is today":
            today = datetime.datetime.now().strftime("%A, %B %d")
            return {"action": "reply", "reply": f"Today is {today}."}

        return None
