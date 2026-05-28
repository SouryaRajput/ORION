from memory.manager import load_memory
import re

MAX_MEMORY_LINES = 10


def build_memory_context(query=None):

    memory = load_memory()
    context = []

    if not memory:
        return ""

    # -----------------------------
    # If no query → return summary
    # -----------------------------
    if not query:

        for category, items in memory.items():

            if not isinstance(items, dict):
                continue

            for key, value in items.items():
                context.append(f"{key}: {value}")

                if len(context) >= MAX_MEMORY_LINES:
                    break

        return "\n".join(context)

    # -----------------------------
    # Query-based filtering
    # -----------------------------

    query = query.lower()

    # extract keywords
    keywords = re.findall(r"\w+", query)

    for category, items in memory.items():

        if not isinstance(items, dict):
            continue

        for key, value in items.items():

            text = f"{key} {value}".lower()

            if any(word in text for word in keywords):

                context.append(f"{key}: {value}")

                if len(context) >= MAX_MEMORY_LINES:
                    return "\n".join(context)

    return "\n".join(context)