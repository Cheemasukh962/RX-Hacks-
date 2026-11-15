"""Thin OpenAI client (server-side only). Structured JSON output via json_schema.

Every caller must have a non-LLM fallback: if the key is missing or a call fails,
callers return seeded / template output and report mode "demo" (PLAN.md rule 10).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
log = logging.getLogger("rexo.llm")

API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")


def available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY")) and os.getenv("REXO_DISABLE_LLM", "").lower() not in ("1", "true")


def chat_json(system: str, user: str, schema: dict, name: str = "result",
              model: Optional[str] = None, timeout: float = 45.0) -> Optional[dict]:
    """Return parsed JSON matching `schema`, or None on any failure (caller falls back)."""
    if not available():
        return None
    body = {
        "model": model or DEFAULT_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": name, "strict": True, "schema": schema}},
    }
    effort = os.getenv("OPENAI_REASONING_EFFORT", "low")
    if effort:
        body["reasoning_effort"] = effort
    try:
        r = httpx.post(API_URL, json=body, timeout=timeout,
                       headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
        if r.status_code != 200:
            log.warning("OpenAI %s: %s", r.status_code, r.text[:300])
            return None
        msg = r.json()["choices"][0]["message"]
        if msg.get("refusal"):
            log.warning("OpenAI refusal: %s", msg["refusal"])
            return None
        return json.loads(msg["content"])
    except Exception as e:
        log.warning("OpenAI call failed: %s: %s", type(e).__name__, e)
        return None
