import json
import time
from pathlib import Path

MEMORY_FILE = Path(__file__).parent / "store.json"

# Pending update confirmation memory
pending_memory = None


def load_memory():
    if not MEMORY_FILE.exists():
        return {}

    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
            # Migration for older plain-string values
            for cat, items in data.items():
                if isinstance(items, dict):
                    for k, v in items.items():
                        if isinstance(v, str):
                            data[cat][k] = {
                                "value": v,
                                "timestamp": time.time(),
                                "importance": 1.0
                            }
            return data
    except:
        return {}


def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


def remember(category, key, value, importance=1.0):

    memory = load_memory()

    if category not in memory:
        memory[category] = {}

    existing = memory[category].get(key)
    existing_val = existing["value"] if isinstance(existing, dict) else existing

    # Ask confirmation before overwriting
    if existing_val and existing_val != value:
        global pending_memory
        pending_memory = (category, key, value)

        return f"I already have '{existing_val}' saved for {key}. Do you want to update it?"

    memory[category][key] = {
        "value": value,
        "timestamp": time.time(),
        "importance": importance
    }
    save_memory(memory)

    return "Memory saved."


def recall(category, key):

    memory = load_memory()
    entry = memory.get(category, {}).get(key)
    if entry and isinstance(entry, dict):
        return entry.get("value")
    return entry


def all_memory():

    return load_memory()


def formatted_memory():

    memory = load_memory()
    lines = []

    for category, items in memory.items():

        if not items:
            continue

        lines.append(f"{category.capitalize()}:")

        for key, entry in items.items():
            val = entry["value"] if isinstance(entry, dict) else entry
            lines.append(f" - {key}: {val}")

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