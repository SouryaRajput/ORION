import time
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def scrape_url(url, timeout=3):
    """Fetches and extracts clean text from a URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.extract()
            
        text = soup.get_text(separator=' ')
        # Collapse whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Limit to first ~3000 chars to save context window and speed up reading
        return text[:3000]
    except Exception as e:
        print(f"[SCRAPE ERROR] Failed to fetch {url}: {e}")
        return ""

def search_and_scrape(query, num_results=2):
    """Uses DuckDuckGo to search the web and scrapes the top results."""
    print(f"🔎 Searching the web for: {query}")
    results = []
    try:
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=num_results))
            
        for r in search_results:
            url = r.get("href")
            title = r.get("title")
            snippet = r.get("body")
            print(f"🌐 Reading: {title} ({url})")
            
            page_text = scrape_url(url)
            
            # Combine snippet and page text
            content = f"Title: {title}\nSnippet: {snippet}\nContent:\n{page_text}"
            results.append(content)
            
        return "\n\n---\n\n".join(results)
    except Exception as e:
        print(f"[SEARCH ERROR] {e}")
        return "Could not perform search."

def web_search_stream(query):
    """Performs web search and yields a streaming LLM response summarizing the results."""
    if not groq_client:
        yield "I cannot search the web because my API key is missing."
        return

    yield "Let me check the web for that... "

    # 1. Gather data
    scraped_context = search_and_scrape(query)

    # 2. Build Prompt
    system_prompt = """
You are ORION, a highly advanced AI assistant. You have just performed a real-time web search to answer the user's query.
Below is the raw, scraped data from the top search results.
Read it quickly, extract ONLY the most relevant and accurate information to answer the user's question, and summarize it naturally.

CRITICAL RULES:
- Do NOT read out the URLs or article titles unless specifically asked.
- Do NOT use markdown, bullet points, or lists. This is for a VOICE interface.
- Be concise. Give the answer directly without unnecessary jargon.
- Speak conversationally, using filler words ("Well...", "It looks like...", "So,") and natural pauses (use commas).
- Keep your answer to 2-4 sentences max.
"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"User's Query: {query}\n\nSearch Results Data:\n{scraped_context}"}
    ]

    # 3. Stream output
    try:
        stream = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            max_tokens=200,
            stream=True
        )
        
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token
    except Exception as e:
        print(f"[STREAM ERROR] {e}")
        yield "Sorry, I had trouble summarizing the search results."
