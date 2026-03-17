"""
NVIDIA NIM LLM Client — async wrapper with structured JSON output.
Supports any OpenAI-compatible API (NVIDIA NIM, OpenAI, etc.)
"""
import json
import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Retry config
MAX_RETRIES = 2
TIMEOUT_SECONDS = 30


async def chat_completion(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 2048,
    response_format: Optional[dict] = None,
) -> str:
    """
    Send chat completion request to NVIDIA NIM.
    Returns the assistant's message content as string.
    """
    if not settings.NVIDIA_NIM_API_KEY:
        raise RuntimeError(
            "NVIDIA_NIM_API_KEY not set. "
            "Add it to .env or .env.local."
        )

    # Log prompt for traceability
    user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
    logger.info(f"[PIPELINE] LLM request → model={settings.NVIDIA_NIM_MODEL}, prompt_len={len(user_msg)}")

    url = f"{settings.NVIDIA_NIM_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.NVIDIA_NIM_API_KEY}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": settings.NVIDIA_NIM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format

    last_error = None
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                logger.info(f"[PIPELINE] LLM response → len={len(content)}, preview='{content[:200]}'")
                return content
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    f"NIM API error (attempt {attempt+1}): {e.response.status_code} {e.response.text[:200]}"
                )
                if e.response.status_code == 429:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                logger.warning(f"NIM connection error (attempt {attempt+1}): {e}")
                if attempt < MAX_RETRIES:
                    import asyncio
                    await asyncio.sleep(1)
                    continue

    raise RuntimeError(f"NIM API failed after {MAX_RETRIES + 1} attempts: {last_error}")


async def chat_json(
    messages: list[dict],
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> Dict[str, Any]:
    """
    Send chat completion and parse response as JSON.
    Adds explicit JSON instruction to system prompt.
    """
    raw = await chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Strip markdown code fences if present
    content = raw.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON: {e}\nRaw: {raw[:500]}")
        raise ValueError(f"LLM returned invalid JSON: {e}")
