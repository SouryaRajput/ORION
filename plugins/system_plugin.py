from typing import Optional, Dict, Any
from plugins.base import FastCommandPlugin
import voice.state as state

class SystemControlPlugin(FastCommandPlugin):
    def handle(self, text: str) -> Optional[Dict[str, Any]]:
        # STOP / CANCEL / DISMISS
        if text in ["stop", "cancel", "abort", "halt", "stop talking", "shut up"]:
            from Core.state_machine import sm
            sm.trigger_interrupt()
            state.STOP_AGENT = True
            return {"action": "stop", "reply": "Stopped."}
            
        if text in ["nevermind", "nothing", "no thanks", "forget it", "never mind"]:
            from Core.state_machine import sm, AgentState
            sm.trigger_interrupt()
            state.STOP_AGENT = True
            sm.transition(AgentState.SLEEPING)
            return {"action": "dismiss", "reply": ""}

        # SLEEP
        if text in ["sleep", "go to sleep", "pause"]:
            from Core.state import sleep
            sleep()
            return {"action": "sleep", "reply": "Sleeping... (Say 'orion' to wake me up)"}

        return None
