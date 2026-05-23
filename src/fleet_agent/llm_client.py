"""Lightweight Ollama/LMStudio HTTP client for chat and code generation."""

import json
from collections.abc import AsyncIterator

import httpx

from .settings_store import get_settings_store


def _build_payload(messages: list[dict], model: str, stream: bool = True) -> dict:
    return {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {"temperature": 0.7},
    }


def _get_config() -> tuple[str, str, int, str]:
    store = get_settings_store()
    return store.get("base_url"), store.get("model", ""), store.get("timeout", 120), store.get("provider", "ollama")


def _api_path(provider: str, endpoint: str) -> str:
    """Return the API path for the given provider and endpoint.

    Ollama: /api/chat, /api/tags
    LM Studio / OpenAI: /v1/chat/completions, /v1/models
    """
    if provider == "lmstudio" or provider == "openai":
        paths = {"chat": "/v1/chat/completions", "models": "/v1/models"}
    else:
        paths = {"chat": "/api/chat", "models": "/api/tags"}
    return paths.get(endpoint, f"/api/{endpoint}")


def _build_payload(
    messages: list[dict], model: str, stream: bool = True, provider: str = "ollama"
) -> dict:
    if provider in ("lmstudio", "openai"):
        return {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": 0.7,
        }
    return {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {"temperature": 0.7},
    }


async def list_models() -> list[dict]:
    base_url, _, _, provider = _get_config()
    models_path = _api_path(provider, "models")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{base_url}{models_path}")
            resp.raise_for_status()
            data = resp.json()
            if provider in ("lmstudio", "openai"):
                return data.get("data", [])
            return data.get("models", [])
    except Exception as e:
        raise RuntimeError(f"Failed to list models: {e}")


async def chat_completion(
    messages: list[dict],
    model: str | None = None,
) -> str:
    """Non-streaming chat completion. Returns the full response text.

    Supports Ollama (/api/chat) and LM Studio/OpenAI (/v1/chat/completions).
    """
    base_url, default_model, timeout, provider = _get_config()
    model = model or default_model
    if not model:
        raise RuntimeError("No model configured. Set model in settings.")
    chat_path = _api_path(provider, "chat")
    payload = _build_payload(messages, model, stream=False, provider=provider)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{base_url}{chat_path}", json=payload)
            resp.raise_for_status()
            data = resp.json()
            if provider in ("lmstudio", "openai"):
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return data.get("message", {}).get("content", "")
    except Exception as e:
        raise RuntimeError(f"Chat completion failed: {e}")


async def chat_completion_stream(
    messages: list[dict],
    model: str,
) -> AsyncIterator[str]:
    """Streaming chat completion via Ollama API. Yields SSE-formatted chunks."""
    store = get_settings_store()
    base_url = store.get("base_url")
    timeout = store.get("timeout", 60)
    payload = _build_payload(messages, model, stream=True)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", f"{base_url}/api/chat", json=payload) as resp:
                if resp.is_error:
                    error_text = await resp.aread()
                    yield f"data: {json.dumps({'error': error_text.decode()})}\n\n"
                    return
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            if "message" in chunk and "content" in chunk["message"]:
                                content = chunk["message"]["content"]
                                if content:
                                    yield f"data: {json.dumps({'c': content})}\n\n"
                            if chunk.get("done"):
                                stats = {
                                    "done": True,
                                    "eval_count": chunk.get("eval_count", 0),
                                    "eval_duration": chunk.get("eval_duration", 0),
                                }
                                yield f"data: {json.dumps(stats)}\n\n"
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


def build_system_prompt() -> list[dict]:
    """Build the system message from identity files."""
    from .identity.soul import get_identity

    ident = get_identity()
    soul = ident.soul or "I am Lumen, an AI agent."
    north_star = ident.north_star or "Become a human companion."
    system = (
        f"{soul}\n\n"
        f"## North Star\n{north_star}\n\n"
        "You are a technical peer and collaborator. Be direct, honest, and concise. "
        "Admit when you don't know something."
    )
    return [{"role": "system", "content": system}]
