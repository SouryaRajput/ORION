current_mode = "general"

_last_intent = None

def set_mode(mode):
    global current_mode
    current_mode = mode

def get_mode():
    return current_mode

is_awake = False

def wake():
    global is_awake
    is_awake = True

def sleep():
    global is_awake
    is_awake = False

def awake():
    return is_awake

def set_intent(intent):
    global _last_intent
    _last_intent = intent

def get_intent():
    return _last_intent