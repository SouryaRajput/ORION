from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class FastCommandPlugin(ABC):
    """
    Base class for fast command plugins.
    Fast commands intercept user speech before it reaches the LLM.
    """
    @abstractmethod
    def handle(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Process the text. 
        Return a dict with {"action": "...", "reply": "..."} if handled.
        Return None if the text does not match this plugin.
        """
        pass
