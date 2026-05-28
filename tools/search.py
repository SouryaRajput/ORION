from ddgs import DDGS


def search(query):

    try:
        with DDGS() as ddgs:

            keywords = [w for w in query.lower().split() if len(w) > 3]

            filtered = []
            fallback = []

            for r in ddgs.news(query, max_results=10):

                title = r.get("title", "")
                source = r.get("source", "")

                formatted = f"{title} — {source}"

                fallback.append(formatted)

                title_lower = title.lower()

                if any(k in title_lower for k in keywords):
                    filtered.append(formatted)

            # Prefer filtered results
            if filtered:
                return "\n".join(filtered[:5])

            # fallback to general results
            if fallback:
                return "\n".join(fallback[:5])

            return "No recent news found."

    except Exception as e:

        print("Search error:", e)
        return "News service temporarily unavailable."