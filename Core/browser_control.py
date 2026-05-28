import webbrowser
import urllib.parse


def open_url(url: str):
    webbrowser.open(url)


def google_search(query: str):

    query = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={query}"

    webbrowser.open(url)


def youtube_search(query: str):

    query = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={query}"

    webbrowser.open(url)