from Core.state_machine import sm, AgentState

# We will keep some legacy variables for now if they are simple values,
# but proxy the core architecture states to the state machine.

def __getattr__(name):
    if name == "INTERRUPT":
        return sm.interrupt_flag
    if name == "ENGAGED":
        return sm.current in [AgentState.LISTENING, AgentState.PROCESSING, AgentState.SPEAKING]
    if name == "PROCESSING":
        return sm.current == AgentState.PROCESSING
    if name == "SPEAKING":
        return sm.current == AgentState.SPEAKING
    if name == "LISTENING":
        return sm.current == AgentState.LISTENING
    if name == "WAITING_FOR_FOLLOWUP":
        return sm.waiting_for_followup
    if name == "FOLLOWUP_START":
        return sm.followup_start_time
    if name == "LAST_ENGAGED_TIME":
        return sm.last_engaged_time
    if name == "MIC_MUTED":
        return sm.mic_muted
    raise AttributeError(f"module 'voice.state' has no attribute '{name}'")

# It's actually safer to just define the getters/setters as a clean replacement,
# but Python module-level __getattr__ works. However, setting module properties is trickier.
# Instead of __getattr__ magic which can be fragile, let's just expose the state machine 
# directly and map the rest.

# To not break too many things at once, let's keep the file as a mix of old configs and proxy.
CURRENT_STREAM_ID = 0
LAST_TEXT_TIME = 0
MIN_TEXT_INTERVAL = 0.8
PENDING_CONTEXT = None
LAST_USER_QUESTION = None
LAST_SPOKEN_TIME = 0

FOLLOWUP_TIMEOUT = 10
INTERRUPT_LISTENING = False
WAKE_ACTIVE = True
WAKE_TRIGGERED = False
LAST_COMMANDS = []
ENGAGE_TIMEOUT = 10
LAST_INTENT = None
STOP_AGENT = False

YES_WORDS = {"yes", "yeah", "yep", "haan", "haanji", "yess", "of course", "sure", "please"}
NO_WORDS = {"no", "nah", "nope", "not now", "later"}

# Because many files do `state.ENGAGED = False`, we need to use a class module pattern if we want true proxying, 
# or we just update the few files that do it. Let's update the files instead.
# For now, I will keep dummy properties here that get overwritten, and just rely on the new state machine in the refactored files.
ENGAGED = False
PROCESSING = False
SPEAKING = False
INTERRUPT = False
WAITING_FOR_FOLLOWUP = False
FOLLOWUP_START = 0
LAST_ENGAGED_TIME = 0
MIC_MUTED = False