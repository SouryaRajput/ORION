import os
import json
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # {"param_name": "description"}
    function: Callable
    is_safe: bool = True
    category: str = "general"


class ToolRegistry:
    _tools: dict = {}
    _lock = threading.Lock()

    @classmethod
    def register(cls, tool: Tool):
        with cls._lock:
            cls._tools[tool.name] = tool

    @classmethod
    def get(cls, name: str) -> Optional[Tool]:
        return cls._tools.get(name)

    @classmethod
    def execute(cls, name: str, *, allow_unsafe: bool = False, **kwargs) -> Any:
        tool = cls._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found. Available: {list(cls._tools.keys())}"
        if not tool.is_safe and not allow_unsafe:
            return f"Error: Tool '{name}' requires explicit user confirmation."
        try:
            return tool.function(**kwargs)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

    @classmethod
    def get_tool_descriptions(cls) -> str:
        lines = []
        for name, tool in cls._tools.items():
            params = ", ".join(f"{k}: {v}" for k, v in tool.parameters.items())
            safety = "" if tool.is_safe else " [REQUIRES CONFIRMATION]"
            lines.append(f"- {name}({params}){safety}: {tool.description}")
        return "\n".join(lines)

    @classmethod
    def list_tools(cls) -> list:
        return list(cls._tools.keys())


# =============================================================
# TOOL WRAPPER FUNCTIONS
# =============================================================

def _web_search(query: str) -> str:
    """Search the web and return scraped results."""
    from Core.web_searcher import search_and_scrape
    return search_and_scrape(query, num_results=3)


def _web_scrape(url: str) -> str:
    """Scrape text content from a specific URL."""
    from Core.web_searcher import scrape_url
    return scrape_url(url, timeout=5)


def _shell_execute(command: str) -> str:
    """Execute a shell command and return output."""
    from Core.agent_executor import execute_command, is_command_safe
    if not is_command_safe(command):
        return f"Error: Command '{command}' is not in the safe list. Skipping."
    result = execute_command(command, timeout=30)
    if result["success"]:
        return result["output"][:3000] if result["output"] else "Command executed successfully (no output)."
    return f"Command failed: {result.get('error', 'Unknown error')}"


def _open_app(name: str) -> str:
    """Open a macOS application by name."""
    from Core.system_control import open_app
    success = open_app(name)
    return f"Opened {name}" if success else f"Could not find application: {name}"


def _open_url(url: str) -> str:
    """Open a URL in the default web browser."""
    import webbrowser
    webbrowser.open(url)
    return f"Opened {url} in browser."


def _screen_capture() -> str:
    """Take a screenshot of the current screen. Returns the file path."""
    from Core.screen_capture import capture_screen
    path = capture_screen()
    return f"Screenshot saved to: {path}"


def _screen_read() -> str:
    """Read all visible text on the screen using OCR."""
    from Core.screen_capture import capture_screen
    from Core.vision import extract_text
    path = capture_screen()
    return extract_text(path)


def _screen_analyze(prompt: str) -> str:
    """Analyze the current screen with an LLM vision model."""
    from Core.screen_capture import capture_screen
    from Core.vision import analyze_screen_with_llm
    path = capture_screen()
    return analyze_screen_with_llm(path, prompt=prompt)


def _click_target(target: str) -> str:
    """Click on a text element visible on the screen."""
    from Core.screen_capture import capture_screen
    from Core.action_engine import click_text
    path = capture_screen()
    success = click_text(target, path)
    return f"Clicked on '{target}'" if success else f"Could not find '{target}' on screen."


def _type_text(text: str) -> str:
    """Type text using the keyboard."""
    from Core.action_engine import type_text
    success = type_text(text)
    return "Typed successfully." if success else "Failed to type."


def _press_key(key: str) -> str:
    """Press a keyboard key (enter, tab, escape, space, etc)."""
    from Core.action_engine import press_key
    success = press_key(key)
    return f"Pressed {key}." if success else f"Failed to press {key}."


def _remember(category: str, key: str, value: str) -> str:
    """Store information in long-term memory."""
    from memory.manager import remember
    remember(category, key, value)
    return f"Remembered: [{category}] {key} = {value}"


def _recall(query: str) -> str:
    """Search long-term memory for relevant information."""
    from memory.context import build_memory_context
    result = build_memory_context(query)
    return result if result else "No relevant memories found."


def _llm_analyze(prompt: str, data: str = "") -> str:
    """Ask an LLM to analyze, summarize, or reason about data."""
    from groq import Groq
    from dotenv import load_dotenv
    load_dotenv()
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    messages = [{"role": "user", "content": f"{prompt}\n\nData:\n{data}" if data else prompt}]
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"LLM analysis error: {e}"


def _speak_to_user(message: str) -> str:
    """Speak a message to the user via TTS."""
    from voice.tts import speak_audio
    speak_audio(message)
    return f"Spoke to user: {message}"


_browser_instance = None
_browser_lock = threading.Lock()


def _get_browser():
    """Lazy-initialize a persistent Playwright browser."""
    global _browser_instance
    with _browser_lock:
        if _browser_instance is None:
            try:
                from playwright.sync_api import sync_playwright
                pw = sync_playwright().start()
                _browser_instance = pw.chromium.launch(headless=True)
            except Exception as e:
                print(f"[BROWSER] Failed to launch: {e}")
                return None
        return _browser_instance


def _browser_read_page(url: str) -> str:
    """Navigate to a URL and extract the full text content of the page."""
    browser = _get_browser()
    if not browser:
        # Fallback to requests-based scraping
        from Core.web_searcher import scrape_url
        return scrape_url(url)
    try:
        page = browser.new_page()
        page.goto(url, timeout=15000, wait_until="domcontentloaded")
        content = page.inner_text("body")[:5000]
        page.close()
        return content
    except Exception as e:
        return f"Browser error: {e}"


def _browser_navigate(url: str, action: str = "click", selector: str = "") -> str:
    """Navigate to a URL and perform an action (click/fill/screenshot)."""
    browser = _get_browser()
    if not browser:
        return "Browser not available. Playwright may not be installed."
    try:
        page = browser.new_page()
        page.goto(url, timeout=15000, wait_until="domcontentloaded")
        result = ""
        if action == "click" and selector:
            page.click(selector, timeout=5000)
            page.wait_for_timeout(1000)
            result = f"Clicked '{selector}'. Page title: {page.title()}"
        elif action == "fill" and selector:
            parts = selector.split("|", 1)
            if len(parts) == 2:
                page.fill(parts[0], parts[1], timeout=5000)
                result = f"Filled '{parts[0]}' with '{parts[1]}'."
            else:
                result = "Fill requires 'selector|value' format."
        elif action == "screenshot":
            path = "/tmp/orion_browser_screenshot.png"
            page.screenshot(path=path)
            result = f"Screenshot saved to {path}"
        elif action == "read":
            result = page.inner_text("body")[:5000]
        else:
            result = f"Page loaded: {page.title()}. Content: {page.inner_text('body')[:2000]}"
        page.close()
        return result
    except Exception as e:
        return f"Browser action error: {e}"


def _browser_screenshot(url: str) -> str:
    """Take a screenshot of a webpage."""
    return _browser_navigate(url, action="screenshot")


# =============================================================
# REGISTER ALL TOOLS
# =============================================================

def register_all_tools():
    """Register all available tools. Called once at startup."""
    tools = [
        Tool("web_search", "Search the web using DuckDuckGo and return scraped results from top pages.",
             {"query": "The search query string"}, _web_search, category="research"),

        Tool("web_scrape", "Scrape and extract text content from a specific URL.",
             {"url": "The full URL to scrape"}, _web_scrape, category="research"),

        Tool("browser_read_page", "Open a URL in a real browser and extract the full text content. Better than web_scrape for JavaScript-heavy sites.",
             {"url": "The URL to read"}, _browser_read_page, category="browser"),

        Tool("browser_navigate", "Navigate to a URL and perform an action: 'click' (selector), 'fill' (selector|value), 'screenshot', or 'read'.",
             {"url": "The URL to navigate to", "action": "click/fill/screenshot/read", "selector": "CSS selector or text (for click/fill)"}, _browser_navigate, is_safe=False, category="browser"),

        Tool("browser_screenshot", "Take a screenshot of a webpage.",
             {"url": "The URL to screenshot"}, _browser_screenshot, category="browser"),

        Tool("shell_execute", "Execute a safe shell command on macOS and return the output.",
             {"command": "The shell command to run"}, _shell_execute, is_safe=False, category="system"),

        Tool("open_app", "Open a macOS application by name.",
             {"name": "The application name (e.g. 'Chrome', 'Terminal')"}, _open_app, is_safe=False, category="system"),

        Tool("open_url", "Open a URL in the default web browser.",
             {"url": "The URL to open"}, _open_url, is_safe=False, category="system"),

        Tool("screen_capture", "Take a screenshot of the current screen.",
             {}, _screen_capture, category="vision"),

        Tool("screen_read", "Read all visible text on the screen using OCR.",
             {}, _screen_read, category="vision"),

        Tool("screen_analyze", "Analyze the current screen with a vision LLM. Use for understanding UI elements, layouts, or visual content.",
             {"prompt": "What to look for or analyze on the screen"}, _screen_analyze, category="vision"),

        Tool("click_target", "Click on a text element visible on the screen.",
             {"target": "The text to click on"}, _click_target, is_safe=False, category="interaction"),

        Tool("type_text", "Type text using the keyboard at the current cursor position.",
             {"text": "The text to type"}, _type_text, is_safe=False, category="interaction"),

        Tool("press_key", "Press a keyboard key (enter, tab, escape, space, etc).",
             {"key": "The key to press"}, _press_key, is_safe=False, category="interaction"),

        Tool("remember", "Store important information in long-term memory for future recall.",
             {"category": "Memory category (e.g. 'user_preferences', 'facts')", "key": "Short label", "value": "The information to remember"}, _remember, is_safe=False, category="memory"),

        Tool("recall", "Search long-term memory for information relevant to a query.",
             {"query": "What to search for in memory"}, _recall, category="memory"),

        Tool("llm_analyze", "Ask an LLM to analyze, compare, summarize, extract, or reason about text data. Use this for any data processing that requires intelligence.",
             {"prompt": "The analysis instruction", "data": "The data to analyze (optional)"}, _llm_analyze, category="reasoning"),

        Tool("speak_to_user", "Speak a message to the user via voice. Use sparingly for important updates.",
             {"message": "The message to speak"}, _speak_to_user, is_safe=False, category="communication"),
    ]

    for tool in tools:
        ToolRegistry.register(tool)

    print(f"[AGENT] Registered {len(tools)} tools: {ToolRegistry.list_tools()}")


# Auto-register on import
register_all_tools()
