import json
from pathlib import Path

MEMORY_FILE = Path(__file__).parent / "store.json"

# Pending update confirmation memory
pending_memory = None


def load_memory():
    if not MEMORY_FILE.exists():
        return {}

    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


def remember(category, key, value):

    memory = load_memory()

    if category not in memory:
        memory[category] = {}

    existing = memory[category].get(key)

    # Ask confirmation before overwriting
    if existing and existing != value:
        global pending_memory
        pending_memory = (category, key, value)

        return f"I already have '{existing}' saved for {key}. Do you want to update it?"

    memory[category][key] = value
    save_memory(memory)

    return "Memory saved."


def recall(category, key):

    memory = load_memory()

    return memory.get(category, {}).get(key)


def all_memory():

    return load_memory()


def formatted_memory():

    memory = load_memory()
    lines = []

    for category, items in memory.items():

        if not items:
            continue

        lines.append(f"{category.capitalize()}:")

        for key, value in items.items():
            lines.append(f" - {key}: {value}")

    return "\n".join(lines) if lines else "I don't remember anything yet, sir."


def delete_memory(key, category):

    memory = load_memory()

    if category in memory and key in memory[category]:

        del memory[category][key]

        # remove empty category
        if not memory[category]:
            del memory[category]

        save_memory(memory)

        return True

    return False

def relevant_memory(query):

    memory = load_memory()

    relevant = {}

    query = query.lower()

    for category, items in memory.items():

        for key, value in items.items():

            text = f"{key} {value}".lower()

            if any(word in text for word in query.split()):

                if category not in relevant:
                    relevant[category] = {}

                relevant[category][key] = value

    return relevant