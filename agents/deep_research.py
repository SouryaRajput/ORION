"""
ORION Deep Research Mode Engine
Performs multi-query background web scraping and long-form synthesis.
"""

import os
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from groq import Groq
from duckduckgo_search import DDGS
from Core.web_searcher import scrape_url
import re
import markdown
from xhtml2pdf import pisa

def _generate_queries(goal: str, num_queries=3):
    """Use a fast LLM to generate diverse search queries, or ask a clarifying question."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return [goal]
        
    client = Groq(api_key=api_key)
    prompt = f"""You are a research planning assistant. The user wants to accomplish this: "{goal}".
If this goal is missing critical context required to actually start researching (like missing a budget for a trip, missing dates, or being wildly too broad), output EXACTLY ONE conversational clarifying question starting with "QUESTION: ".
Otherwise, if you have enough context to start, generate {num_queries} distinct web search queries to gather comprehensive data. Return them as a valid JSON list of strings. Example: ["query 1", "query 2"]"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        content = response.choices[0].message.content.strip()
        
        if content.startswith("QUESTION:"):
            return content
            
        if content.startswith("```json"): content = content[7:]
        if content.endswith("```"): content = content[:-3]
        queries = json.loads(content.strip())
        return queries[:num_queries]
    except Exception as e:
        print(f"[DEEP RESEARCH] Query generation failed: {e}")
        return [goal]

def _fetch_links(queries: list, links_per_query=3) -> list:
    """Fetch search result links for multiple queries."""
    all_links = []
    try:
        with DDGS() as ddgs:
            for q in queries:
                results = list(ddgs.text(q, max_results=links_per_query))
                for r in results:
                    url = r.get("href")
                    if url and url not in [link["url"] for link in all_links]:
                        all_links.append({"url": url, "title": r.get("title", ""), "query": q})
    except Exception as e:
        print(f"[DEEP RESEARCH] Search failed: {e}")
    return all_links

def execute_deep_research(goal: str, speak_fn=None) -> str:
    """Executes the deep research pipeline."""
    start_time = time.time()
    from agents.background import BackgroundManager
    
    # 1. Generate Queries or Ask Question
    current_goal = goal
    while True:
        print(f"[DEEP RESEARCH] Analyzing goal for queries or questions...")
        if speak_fn: speak_fn("Analyzing your request to see if I need more details...")
        
        queries_or_question = _generate_queries(current_goal)
        
        if isinstance(queries_or_question, str) and queries_or_question.startswith("QUESTION:"):
            question_text = queries_or_question.replace("QUESTION:", "").strip()
            # Pause and ask the user
            answer = BackgroundManager.request_input(question_text)
            current_goal += f"\n[User added context]: {answer}"
            if speak_fn: speak_fn("Got it. Let me incorporate that and start searching.")
        else:
            queries = queries_or_question
            break
            
    print(f"[DEEP RESEARCH] Final Queries: {queries}")
    
    # 2. Get Links
    links = _fetch_links(queries)
    print(f"[DEEP RESEARCH] Found {len(links)} unique sources to scrape.")
    if speak_fn: speak_fn(f"Found {len(links)} sources. Reading them now...")
    
    # 3. Parallel Scrape
    scraped_data = []
    
    # We redefine scrape_url slightly to get more context
    def safe_scrape(item):
        text = scrape_url(item["url"], timeout=5)
        # We take up to 8000 chars per page to get real depth
        return f"--- SOURCE (Query: {item['query']}) ---\nTitle: {item['title']}\nURL: {item['url']}\nContent: {text[:8000]}\n"
        
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(safe_scrape, link): link for link in links}
        for i, future in enumerate(as_completed(futures)):
            try:
                res = future.result()
                if len(res) > 200: # Ensure it actually got text
                    scraped_data.append(res)
            except Exception as e:
                pass
                
    full_context = "\n\n".join(scraped_data)
    print(f"[DEEP RESEARCH] Scraped {len(scraped_data)} successful pages. Context size: {len(full_context)} chars.")
    if speak_fn: speak_fn("Finished reading. Synthesizing the final report...")
    
    # 4. Heavy Synthesis
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "I couldn't complete the deep research because the OpenRouter API key is missing."
        
    system_prompt = """You are ORION's Deep Research Engine. 
You have been provided with scraped text from dozens of sources about a specific topic.

YOUR TASK is to synthesize this information into a highly detailed, comprehensive research report.
You MUST format your response in beautiful Markdown. 
You have COMPLETE FREEDOM to decide how many sections the report needs and what the headers should be based purely on the user's topic. Structure it logically.

CRITICAL RULES:
- Use bolding, bullet points, and subheaders where appropriate to make the report highly readable.
- There is NO length limit. Go as deep as the topic warrants. Be extremely thorough.
- At the VERY END of your report, you MUST add a block exactly like this:
[SPEECH_SUMMARY]
A highly conversational, engaging 150-word spoken summary of your findings. This is what ORION will speak out loud to the user. Speak conversationally! Use filler words ("So...", "Well...", "Interestingly,"), em-dashes, and pauses.
[/SPEECH_SUMMARY]
"""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "google/gemini-2.5-flash",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"User's Topic: {goal}\n\nScraped Data:\n{full_context[:80000]}"}
                ],
                "temperature": 0.4,
                "max_tokens": 4000,
            },
            timeout=40
        )
        response.raise_for_status()
        final_text = response.json()["choices"][0]["message"]["content"].strip()
        
        # 5. Extract Summary and Main Report
        summary = "I've generated the deep research report and saved it to your Desktop."
        report_md = final_text
        
        match = re.search(r'\[SPEECH_SUMMARY\](.*?)\[/SPEECH_SUMMARY\]', final_text, re.DOTALL)
        if match:
            summary = match.group(1).strip()
            report_md = re.sub(r'\[SPEECH_SUMMARY\].*?\[/SPEECH_SUMMARY\]', '', final_text, flags=re.DOTALL).strip()
            
        # 6. Generate PDF
        try:
            html = markdown.markdown(report_md, extensions=['tables', 'fenced_code'])
            styled_html = f"""
            <html>
            <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333; margin: 40px; }}
                h1 {{ color: #1a1a1a; font-size: 24px; border-bottom: 2px solid #eaeaea; padding-bottom: 10px; margin-top: 30px; }}
                h2 {{ color: #2c3e50; font-size: 20px; margin-top: 25px; }}
                h3 {{ color: #34495e; font-size: 16px; }}
                p {{ margin-bottom: 15px; }}
                ul, ol {{ margin-bottom: 15px; }}
                li {{ margin-bottom: 5px; }}
                code {{ background-color: #f8f9fa; padding: 2px 4px; border-radius: 4px; font-family: monospace; }}
            </style>
            </head>
            <body>
            <h1>Deep Research: {goal}</h1>
            {html}
            </body>
            </html>
            """
            
            safe_goal = re.sub(r'[^a-zA-Z0-9_\- ]', '', goal).strip().replace(' ', '_')[:30]
            desktop_path = os.path.expanduser(f"~/Desktop/Deep_Research_{safe_goal}.pdf")
            
            with open(desktop_path, "wb") as pdf_file:
                pisa.CreatePDF(styled_html, dest=pdf_file)
                
            print(f"[DEEP RESEARCH] PDF saved to {desktop_path}")
            summary = f"{summary} I've also saved the full detailed report to your Desktop."
        except Exception as pdf_err:
            print(f"[DEEP RESEARCH PDF ERROR] {pdf_err}")
            
        elapsed = time.time() - start_time
        print(f"[DEEP RESEARCH] Finished in {elapsed:.1f}s.")
        return summary
    except Exception as e:
        print(f"[DEEP RESEARCH ERROR] {e}")
        return "I ran into an error while trying to synthesize the deep research report."
