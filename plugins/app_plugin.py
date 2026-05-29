import webbrowser
from typing import Optional, Dict, Any
from plugins.base import FastCommandPlugin

class AppLauncherPlugin(FastCommandPlugin):
    def handle(self, text: str) -> Optional[Dict[str, Any]]:
        # Only treat as a fast command if it's short (e.g., "open chrome"). 
        # Longer commands (e.g., "open chrome and search for...") should go to the AI router.
        if (text.startswith("open ") or text.startswith("launch ")) and len(text.split()) <= 4:
            app = text.replace("open ", "").replace("launch ", "").strip()
            if app == "google":
                webbrowser.open("https://google.com")
                return {"action": "reply", "reply": "Opening Google."}
            else:
                from Core.system_control import open_app
                success = open_app(app)
                if success:
                    return {"action": "reply", "reply": f"Opening {app}."}
                else:
                    return {"action": "reply", "reply": f"I couldn't find {app}."}
        return None
