"""
AI Router — Handles all communication with the OpenRouter API.
Provides both streaming and non-streaming JSON generation.
"""

import os
import json
import requests
from typing import Optional, Generator
from dotenv import load_dotenv

import time
from study.utils.logger import get_logger

load_dotenv()
log = get_logger("ai_router")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

from Core.config import config

# Model tiers: fast for planning, smart for explanations
FAST_MODEL = config.ai.models.fast
SMART_MODEL = config.ai.models.smart

_session = requests.Session()


def _build_headers() -> dict:
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }


def generate_json(
    system_prompt: str,
    user_prompt: str,
    model: str = FAST_MODEL,
    max_tokens: int = 2000,
    temperature: float = 0.3,
    retries: int = 3,
) -> Optional[dict]:
    """
    Call the LLM and parse the response as JSON.
    The system prompt must instruct the model to output valid JSON.
    """
    log.info(f"Requesting JSON from {model} (max_tokens={max_tokens})")

    for attempt in range(retries):
        try:
            response = _session.post(
                API_URL,
                headers=_build_headers(),
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "response_format": {"type": "json_object"},
                },
                timeout=30,
            )
            
            if response.status_code == 429:
                log.warning(f"Rate limited (429). Retrying in {2 ** attempt}s...")
                time.sleep(2 ** attempt)
                continue
                
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Parse the JSON from the response
            parsed = json.loads(content)
            log.info("Successfully parsed JSON response.")
            return parsed

        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON from LLM: {e}")
            return None
        except Exception as e:
            log.error(f"API request failed on attempt {attempt+1}: {e}")
            if attempt == retries - 1:
                return None
            time.sleep(2 ** attempt)
            
    return None


def generate_text(
    system_prompt: str,
    user_prompt: str,
    model: str = SMART_MODEL,
    max_tokens: int = 500,
    temperature: float = 0.5,
    retries: int = 3,
) -> str:
    """Call the LLM and return plain text."""
    log.info(f"Requesting text from {model}")

    for attempt in range(retries):
        try:
            response = _session.post(
                API_URL,
                headers=_build_headers(),
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=25,
            )
            
            if response.status_code == 429:
                log.warning(f"Rate limited (429). Retrying in {2 ** attempt}s...")
                time.sleep(2 ** attempt)
                continue
                
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

        except Exception as e:
            log.error(f"Text generation failed on attempt {attempt+1}: {e}")
            if attempt == retries - 1:
                return "I'm sorry, I couldn't generate a response right now."
            time.sleep(2 ** attempt)
            
    return "I'm sorry, I couldn't generate a response right now."


def generate_stream(
    system_prompt: str,
    user_prompt: str,
    model: str = SMART_MODEL,
    max_tokens: int = 500,
    temperature: float = 0.5,
    retries: int = 3,
) -> Generator[str, None, None]:
    """Stream tokens from the LLM for real-time narration."""
    log.info(f"Starting stream from {model}")

    for attempt in range(retries):
        try:
            response = _session.post(
                API_URL,
                headers=_build_headers(),
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                },
                stream=True,
                timeout=25,
            )
            
            if response.status_code == 429:
                log.warning(f"Rate limited (429). Retrying in {2 ** attempt}s...")
                time.sleep(2 ** attempt)
                continue
                
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue
                text = line.decode("utf-8")
                if not text.startswith("data: "):
                    continue
                payload = text[6:]
                if payload.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield token
                except json.JSONDecodeError:
                    continue
                    
            return # Successfully streamed

        except Exception as e:
            log.error(f"Stream failed on attempt {attempt+1}: {e}")
            if attempt == retries - 1:
                yield "I'm having trouble connecting right now."
                return
            time.sleep(2 ** attempt)
