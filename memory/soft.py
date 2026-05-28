from collections import defaultdict

pending_memory = None

soft_memory = defaultdict(int)


def observe(text, current_mode, hour):

    text = text.lower()

    # Detect late night studying habit
    if current_mode == "study" and hour >= 22:
        soft_memory["late_night_study"] += 1

    # Detect preference for detailed explanations
    if len(text.split()) > 20:
        soft_memory["like_detailed_explanations"] += 1


def suggest_memory():

    global pending_memory

    # Late night study detection
    if soft_memory["late_night_study"] >= 3:

        pending_memory = ("habits", "study_time", "late_night")

        # prevent repeated suggestion
        soft_memory["late_night_study"] = 0

        return "You often study late at night. Should I remember this?"


    # Detailed explanation preference
    if soft_memory["like_detailed_explanations"] >= 3:

        pending_memory = ("preferences", "explanation_style", "detailed")

        # prevent repeated suggestion
        soft_memory["like_detailed_explanations"] = 0

        return "You seem to prefer detailed explanations. Should I remember that?"


    return None