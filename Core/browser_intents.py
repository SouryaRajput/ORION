from Core.browser_control import google_search, youtube_search


def handle_browser_command(text: str):

    text = text.lower()

    # -----------------------
    # GOOGLE SEARCH
    # -----------------------

    if "search google for" in text:

        query = text.split("search google for", 1)[1].strip()

        if query:
            google_search(query)
            return f"Searching Google for {query}"

    # -----------------------
    # YOUTUBE
    # -----------------------

    if "youtube" in text or "play" in text:

        if "play" in text:
            query = text.split("play", 1)[1].strip()
        else:
            query = text.replace("youtube", "").strip()

        if query:
            youtube_search(query)
            return f"Playing {query} on YouTube"

    return None