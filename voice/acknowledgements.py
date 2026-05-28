import random

ACKNOWLEDGEMENTS = [
    "Got it.",
    "Hmm.",
    "Let's see.",
    "One moment.",
    "Just a second.",
    "Okay."
]

def get_ack():
    return random.choice(ACKNOWLEDGEMENTS)