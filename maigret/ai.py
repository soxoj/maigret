"""Maigret AI Analysis Module

Provides AI-powered analysis of search results using OpenAI-compatible APIs.
"""

import asyncio
import json
import os
import sys
import threading

import aiohttp


def load_ai_prompt() -> str:
    """Load the AI system prompt from the resources directory."""
    maigret_path = os.path.dirname(os.path.realpath(__file__))
    prompt_path = os.path.join(maigret_path, "resources", "ai_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def resolve_api_key(settings) -> str | None:
    """Resolve OpenAI API key from settings or environment variable.

    Priority: settings.openai_api_key > OPENAI_API_KEY env var.
    """
    key = getattr(settings, "openai_api_key", None)
    if key:
        return key
    return os.environ.get("OPENAI_API_KEY")


class _Spinner:
    """Simple animated spinner for terminal output."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, text=""):
        self.text = text
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            frame = self.FRAMES[i % len(self.FRAMES)]
            sys.stderr.write(f"\r{frame} {self.text}")
            sys.stderr.flush()
            i += 1
            self._stop.wait(0.08)

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join()
        sys.stderr.write("\r\033[2K")
        sys.stderr.flush()


async def print_streaming(text: str, delay: float = 0.04):
    """Print text word by word with a delay, simulating streaming LLM output."""
    words = text.split(" ")
    for i, word in enumerate(words):
        if i > 0:
            sys.stdout.write(" ")
        sys.stdout.write(word)
        sys.stdout.flush()
        await asyncio.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()


async def get_ai_analysis(
    api_key: str,
    markdown_report: str,
    model: str = "gpt-4o",
    api_base_url: str = "https://api.openai.com/v1",
) -> str:
    """Send the markdown report to an OpenAI-compatible API and return the analysis.

    Uses streaming to display tokens as they arrive.
    Raises on HTTP errors with descriptive messages.
    """
    system_prompt = load_ai_prompt()

    url = f"{api_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "stream": True,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": markdown_report},
        ],
    }

    spinner = _Spinner("Analysing the data with AI...")
    spinner.start()
    first_token = True
    full_response = []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 401:
                    raise RuntimeError("Invalid OpenAI API key (HTTP 401)")
                if resp.status == 429:
                    raise RuntimeError("OpenAI API rate limit exceeded (HTTP 429)")
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(
                        f"OpenAI API error (HTTP {resp.status}): {body[:500]}"
                    )

                async for line in resp.content:
                    decoded = line.decode("utf-8").strip()
                    if not decoded or not decoded.startswith("data: "):
                        continue

                    data_str = decoded[len("data: "):]
                    if data_str == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if not content:
                        continue

                    if first_token:
                        spinner.stop()
                        print()
                        first_token = False

                    sys.stdout.write(content)
                    sys.stdout.flush()
    except Exception:
        spinner.stop()
        raise

    if first_token:
        # No tokens received — stop spinner anyway
        spinner.stop()

    print()
    return "".join(full_response)
