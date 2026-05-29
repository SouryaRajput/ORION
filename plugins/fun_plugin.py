import random
from typing import Optional, Dict, Any
from plugins.base import FastCommandPlugin

class FunPlugin(FastCommandPlugin):
    def handle(self, text: str) -> Optional[Dict[str, Any]]:
        if text in ["flip a coin", "coin flip"]:
            result = random.choice(["Heads", "Tails"])
            return {"action": "reply", "reply": f"It's {result}."}
            
        if text.startswith("roll a ") and text.endswith(" dice"):
            return {"action": "reply", "reply": f"You rolled a {random.randint(1, 6)}."}
            
        if text in ["roll a dice", "roll dice"]:
            return {"action": "reply", "reply": f"You rolled a {random.randint(1, 6)}."}

        return None
