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
                    print(f"Orion: Opening {app}.")
                    return {"action": "reply", "reply": f"Opening {app}."}
                else:
                    # Web search fallback for websites/web-apps (e.g. "open render")
                    try:
                        import requests, re, urllib.parse
                        query = urllib.parse.quote(app)
                        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                        res = requests.get(f"https://www.google.com/search?btnI=1&q={query}", headers=headers, timeout=3)
                        
                        # Google "I'm Feeling Lucky" returns a Redirect Notice page
                        match = re.search(r'<a href="([^"]+)">', res.text)
                        if match:
                            url = match.group(1)
                            if url.startswith("http"):
                                webbrowser.open(url)
                                print(f"Orion: I couldn't find a local app for {app}, but I opened it on the web.")
                                return {"action": "reply", "reply": f"I couldn't find a local app for {app}, but I opened it on the web."}
                    except Exception:
                        pass
                    
                    print(f"Orion: I couldn't find {app}.")
                    return {"action": "reply", "reply": f"I couldn't find {app}."}
        return None
