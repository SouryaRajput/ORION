import psutil
from typing import Optional, Dict, Any
from plugins.base import FastCommandPlugin

class SystemStatusPlugin(FastCommandPlugin):
    def handle(self, text: str) -> Optional[Dict[str, Any]]:
        if "battery" in text and ("level" in text or "percentage" in text or "status" in text):
            try:
                battery = psutil.sensors_battery()
                if battery:
                    return {"action": "reply", "reply": f"Your battery is at {battery.percent} percent."}
            except:
                pass
                
        if text in ["system status", "how is your cpu", "cpu usage"]:
            try:
                cpu = psutil.cpu_percent(interval=0.1)
                return {"action": "reply", "reply": f"CPU usage is at {cpu} percent."}
            except:
                pass

        return None
