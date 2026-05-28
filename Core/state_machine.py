from enum import Enum, auto
import time


class AgentState(Enum):
    SLEEPING = auto()    # Idle, waiting for wake word
    LISTENING = auto()   # Wake word triggered, actively capturing query audio
    PROCESSING = auto()  # Transcribing or waiting for LLM response
    SPEAKING = auto()    # Playing TTS audio


def _notify_ui(state_name: str):
    """Push state change to the Desktop UI over IPC (non-blocking, fire-and-forget)."""
    try:
        from desktop.ipc import get_engine_sender
        get_engine_sender().send("state", state=state_name)
    except Exception:
        pass  # UI might not be running


class StateMachine:
    def __init__(self):
        self._state = AgentState.SLEEPING
        self.last_state_change = time.time()
        self.last_engaged_time = 0
        
        # Sub-states
        self.waiting_for_followup = False
        self.followup_start_time = 0
        
        # Modifier flags (independent of primary state)
        self.interrupt_flag = False
        self.mic_muted = False
        self.pipeline_active = False
        self.handoff_to_sleep = False
        
    @property
    def current(self):
        return self._state
        
    def transition(self, new_state: AgentState):
        if self._state == new_state:
            return False
            
        print(f"🚦 STATE CHANGE: {self._state.name} -> {new_state.name}")
        self._state = new_state
        self.last_state_change = time.time()
        
        # Notify Desktop UI
        _notify_ui(new_state.name.lower())
        
        if new_state == AgentState.LISTENING:
            if self._state != AgentState.PROCESSING:
                self.last_engaged_time = time.time()
            self.interrupt_flag = False
            
        if new_state == AgentState.SLEEPING:
            self.waiting_for_followup = False
            self.interrupt_flag = False
            
        return True
        
    def set_followup(self, active=True):
        self.waiting_for_followup = active
        if active:
            self.followup_start_time = time.time()
            
    def trigger_interrupt(self):
        self.interrupt_flag = True

# Global singleton
sm = StateMachine()
