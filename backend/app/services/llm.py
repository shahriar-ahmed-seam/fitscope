"""DeepSeek chat client: JSON-mode helper, disk-free caching, usage accounting."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import httpx

from .. import db
from ..config import settings
from .textkit import sha

log = logging.getLogger("fitscope.llm")


class LLMUnavailable(RuntimeError):
    """Raised when the model cannot be reached or returns unusable output."""


def configured() -> bool:
    return bool(settings.deepseek_api_key.strip())


def _extract_json(content: str) -> Any:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    # Fall back to the outermost JSON object/array in the response.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = content.find(opener)
        end = content.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise LLMUnavailable("model did not return valid JSON")


async def chat_json(
    system: str,
    user: str,
    operation: str,
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> Any:
    """Call DeepSeek in JSON mode and return parsed output.

    Identical prompts are served from provider_cache, which keeps a public demo
    cheap and makes repeat analyses of the same resume/JD pair instant.
    """
    if not configured():
        raise LLMUnavailable("DEEPSEEK_API_KEY is not configured")

    max_tokens = max_tokens or settings.llm_max_output_tokens
    key = "llm:" + sha(settings.deepseek_model, operation, system, user, str(temperature))
    cached = await db.cache_get(key)
    if cached is not None:
        log.info("llm cache hit operation=%s", operation)
        return cached

    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }

    started = time.perf_counter()
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                resp = await client.post(
                    f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
                    json=payload,
                    headers=headers,
                )
            if resp.status_code >= 500 or resp.status_code in (408, 429):
                raise httpx.HTTPStatusError(
                    f"upstream {resp.status_code}", request=resp.request, response=resp
                )
            resp.raise_for_status()
            body = resp.json()
            break
        except Exception as exc:
            last_error = exc
            if attempt == 2:
                raise LLMUnavailable(f"DeepSeek call failed: {exc}") from exc
            log.warning("llm retry %s operation=%s: %s", attempt + 1, operation, exc)
    else:  # pragma: no cover - loop always breaks or raises
        raise LLMUnavailable(str(last_error))

    latency_ms = int((time.perf_counter() - started) * 1000)
    usage = body.get("usage") or {}
    await db.log_usage(
        "deepseek",
        body.get("model", settings.deepseek_model),
        operation,
        {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "cached_tokens": usage.get("prompt_cache_hit_tokens", 0),
        },
        latency_ms,
    )

    content = (body.get("choices") or [{}])[0].get("message", {}).get("content", "")
    parsed = _extract_json(content)
    await db.cache_put(key, "deepseek", parsed)
    return parsed
