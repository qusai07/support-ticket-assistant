"""Thin wrapper around Ollama.

Responsibilities:
1. Structured output: pass a Pydantic JSON schema to Ollama's `format` (constrained
   decoding), then validate. If validation still fails, retry once and feed the
   error back to the model.
2. Usage tracking: every call records model, tokens and latency into whichever
   `track_usage()` block is active. The pipeline uses this to persist llm_calls
   rows without the client knowing anything about the database.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TypeVar

import ollama
from pydantic import BaseModel, ValidationError

from app.config import get_settings

T = TypeVar("T", bound=BaseModel)
PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass
class LLMUsage:
    purpose: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


_usage: ContextVar[list[LLMUsage] | None] = ContextVar("llm_usage", default=None)


@contextmanager
def track_usage():
    calls: list[LLMUsage] = []
    token = _usage.set(calls)
    try:
        yield calls
    finally:
        _usage.reset(token)


def _record(purpose: str, model: str, resp, started: float) -> None:
    sink = _usage.get()
    if sink is not None:
        sink.append(LLMUsage(
            purpose=purpose, model=model,
            input_tokens=getattr(resp, "prompt_eval_count", 0) or 0,
            output_tokens=getattr(resp, "eval_count", 0) or 0,
            latency_ms=int((time.perf_counter() - started) * 1000),
        ))


@lru_cache
def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


@lru_cache
def _client() -> ollama.Client:
    # A hung model call must never block a ticket forever.
    return ollama.Client(host=get_settings().ollama_host, timeout=get_settings().llm_timeout_s)


def chat(messages: list[dict], *, model: str, purpose: str, tools: list | None = None,
         format: dict | None = None):
    """Raw chat call (used by the agent loop for tool calling)."""
    started = time.perf_counter()
    resp = _client().chat(
        model=model, messages=messages, tools=tools, format=format,
        # Ollama silently truncates prompts longer than num_ctx (dropping the start,
        # i.e. the system prompt). Set it explicitly.
        options={"temperature": get_settings().llm_temperature, "num_ctx": get_settings().llm_num_ctx},
    )
    _record(purpose, model, resp, started)
    return resp


def structured(messages: list[dict], schema: type[T], *, model: str, purpose: str,
               retries: int = 1) -> T:
    """Chat call whose answer must validate against `schema`."""
    msgs = list(messages)
    last_err: Exception | None = None
    for _ in range(retries + 1):
        resp = chat(msgs, model=model, purpose=purpose, format=schema.model_json_schema())
        content = resp.message.content or ""
        try:
            return schema.model_validate_json(content)
        except ValidationError as e:
            last_err = e
            msgs = msgs + [
                {"role": "assistant", "content": content},
                {"role": "user", "content": f"Your JSON was invalid: {e.errors()[:3]}. Return corrected JSON only."},
            ]
    raise ValueError(f"{purpose}: model output failed validation after retries: {last_err}")
