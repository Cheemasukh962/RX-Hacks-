"""Thin OpenAI client (server-side only). Structured JSON output via json_schema.

Every caller must have a non-LLM fallback: if the key is missing or a call fails,
callers return seeded / template output and report mode "demo" (PLAN.md rule 10).
"""
from __future__ import annotations

import json
import logging
import os
import re
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


def chat_json(system: str, user, schema: dict, name: str = "result",
              model: Optional[str] = None, timeout: float = 45.0,
              effort: Optional[str] = None) -> Optional[dict]:
    """Return parsed JSON matching `schema`, or None on any failure (caller falls back).

    `user` is a string, or a list of content parts (e.g. text + image_url) for vision calls.
    """
    if not available():
        return None
    body = {
        "model": model or DEFAULT_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": name, "strict": True, "schema": schema}},
    }
    effort = effort or os.getenv("OPENAI_REASONING_EFFORT", "low")
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


IMAGES_URL = "https://api.openai.com/v1/images/generations"
IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")


def generate_image(prompt: str, timeout: float = 150.0) -> Optional[str]:
    """Draw one square image; return base64 JPEG, or None on any failure (caller falls back)."""
    if not available():
        return None
    body = {"model": IMAGE_MODEL, "prompt": prompt, "size": "1024x1024",
            "quality": os.getenv("OPENAI_IMAGE_QUALITY", "medium"), "output_format": "jpeg", "n": 1}
    try:
        r = httpx.post(IMAGES_URL, json=body, timeout=timeout,
                       headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
        if r.status_code != 200:
            log.warning("OpenAI image %s: %s", r.status_code, r.text[:300])
            return None
        return r.json()["data"][0]["b64_json"]
    except Exception as e:
        log.warning("OpenAI image call failed: %s: %s", type(e).__name__, e)
        return None


RESPONSES_URL = "https://api.openai.com/v1/responses"
# Health sites the web fallback may cite (PRD_V2 F5).
TRUSTED_DOMAINS = ["medlineplus.gov", "nih.gov", "dailymed.nlm.nih.gov", "fda.gov", "cdc.gov",
                   "mayoclinic.org", "clevelandclinic.org", "nhs.uk"]
_MD_LINK = re.compile(r"\s*\(\[[^\]]*\]\([^)]*\)\)|\[([^\]]+)\]\((?:[^)]+)\)")


def _clean_url(url: str) -> str:
    return re.sub(r"[?&]utm_source=openai$", "", url).replace("?utm_source=openai&", "?")


def web_answer(question: str, instructions: str, timeout: float = 90.0) -> Optional[dict]:
    """Answer with the OpenAI Responses `web_search` tool, limited to TRUSTED_DOMAINS.

    Returns {"text", "sources": [{"title", "url"}]} or None. Only the question and a medicine name
    are sent, never patient identifiers.
    """
    if not available():
        return None
    body = {"model": DEFAULT_MODEL, "instructions": instructions, "input": question,
            "tools": [{"type": "web_search", "filters": {"allowed_domains": TRUSTED_DOMAINS}}]}
    try:
        r = httpx.post(RESPONSES_URL, json=body, timeout=timeout,
                       headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
        if r.status_code != 200:
            log.warning("OpenAI web search %s: %s", r.status_code, r.text[:300])
            return None
        text, sources, seen = [], [], set()
        for item in r.json().get("output", []):
            if item.get("type") != "message":
                continue
            for part in item.get("content", []):
                text.append(part.get("text", ""))
                for a in part.get("annotations", []):
                    if a.get("type") == "url_citation":
                        url = _clean_url(a.get("url", ""))
                        if url and url not in seen:
                            seen.add(url)
                            sources.append({"title": a.get("title") or url, "url": url})
        clean = _MD_LINK.sub(lambda m: m.group(1) or "", "\n".join(text)).strip()
        return {"text": clean, "sources": sources} if clean else None
    except Exception as e:
        log.warning("OpenAI web search failed: %s: %s", type(e).__name__, e)
        return None
