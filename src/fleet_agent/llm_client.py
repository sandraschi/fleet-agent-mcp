"""Lightweight Ollama/LMStudio HTTP client for chat and code generation."""

import json
from collections.abc import AsyncIterator

import httpx

from .settings_store import get_settings_store

_PROVIDER_CHAIN: list[tuple[str, str]] = [
    ("ollama", "http://127.0.0.1:11434"),
    ("lmstudio", "http://127.0.0.1:1234"),
]


def _get_provider_chain(preferred: str) -> list[tuple[str, str]]:
    """Return ordered list of (provider, base_url) to try, preferred first."""
    return sorted(_PROVIDER_CHAIN, key=lambda p: (0 if p[0] == preferred else 1))


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


async def list_models() -> list[dict]:
    _, _, _, provider = _get_config()
    providers_to_try = _get_provider_chain(provider)
    last_error = ""
    for prov_name, prov_url in providers_to_try:
        try:
            models_path = _api_path(prov_name, "models")
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{prov_url}{models_path}")
                resp.raise_for_status()
                data = resp.json()
                raw_models: list[dict] = []
                if prov_name in ("lmstudio", "openai"):
                    raw_models = data.get("data", [])
                else:
                    raw_models = data.get("models", [])
                return [
                    {
                        "name": m.get("name") or m.get("id", "unknown"),
                        "size": m.get("size", m.get("size_bytes", 0)),
                    }
                    for m in raw_models
                ]
        except Exception as e:
            last_error = f"{prov_url}: {e}"
            continue
    raise RuntimeError(
        f"Failed to list models. Tried: {', '.join(u for _, u in providers_to_try)}. "
        f"Last error: {last_error}"
    )


async def chat_completion(
    messages: list[dict],
    model: str | None = None,
) -> str:
    """Non-streaming chat completion. Returns the full response text.

    Supports Ollama (/api/chat) and LM Studio/OpenAI (/v1/chat/completions).
    Tries Ollama first, then falls back to LM Studio.
    """
    _, default_model, timeout, provider = _get_config()
    model = model or default_model
    if not model:
        raise RuntimeError("No model configured. Set model in settings.")
    providers_to_try = _get_provider_chain(provider)
    last_error = ""
    for prov_name, prov_url in providers_to_try:
        try:
            chat_path = _api_path(prov_name, "chat")
            payload = _build_payload(messages, model, stream=False, provider=prov_name)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{prov_url}{chat_path}", json=payload)
                resp.raise_for_status()
                data = resp.json()
                if prov_name in ("lmstudio", "openai"):
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return data.get("message", {}).get("content", "")
        except Exception as e:
            last_error = f"{prov_url}: {e}"
            continue
    raise RuntimeError(
        f"Chat completion failed: all providers unreachable. "
        f"Tried: {', '.join(u for _, u in providers_to_try)}. "
        f"Last error: {last_error}"
    )


async def chat_completion_stream(
    messages: list[dict],
    model: str,
) -> AsyncIterator[str]:
    """Streaming chat completion. Supports Ollama and LM Studio/OpenAI.

    Tries Ollama first, then falls back to LM Studio.
    """
    store = get_settings_store()
    timeout = store.get("timeout", 60)
    provider = store.get("provider", "ollama")
    providers_to_try = _get_provider_chain(provider)
    last_error = ""
    for prov_name, prov_url in providers_to_try:
        try:
            chat_path = _api_path(prov_name, "chat")
            payload = _build_payload(messages, model, stream=True, provider=prov_name)
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", f"{prov_url}{chat_path}", json=payload) as resp:
                    if resp.is_error:
                        error_text = await resp.aread()
                        last_error = f"{prov_url}: {error_text.decode()}"
                        continue
                    if prov_name in ("lmstudio", "openai"):
                        async for line in resp.aiter_lines():
                            if line.strip():
                                try:
                                    chunk = json.loads(line)
                                    choice = chunk.get("choices", [{}])[0]
                                    delta = choice.get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield f"data: {json.dumps({'c': content})}\n\n"
                                    if choice.get("finish_reason"):
                                        yield f"data: {json.dumps({'done': True})}\n\n"
                                except json.JSONDecodeError:
                                    pass
                    else:
                        async for line in resp.aiter_lines():
                            if line.strip():
                                try:
                                    chunk = json.loads(line)
                                    if "message" in chunk and "content" in chunk["message"]:
                                        content = chunk["message"]["content"]
                                        if content:
                                            yield f"data: {json.dumps({'c': content})}\n\n"
                                    if chunk.get("done"):
                                        yield f"data: {json.dumps({'done': True, 'eval_count': chunk.get('eval_count', 0)})}\n\n"
                                except json.JSONDecodeError:
                                    pass
                    return
        except Exception as e:
            last_error = f"{prov_url}: {e}"
            continue
    tried = ", ".join(u for _, u in providers_to_try)
    error_msg = f"All providers failed. Tried: {tried}. Last: {last_error}"
    yield f"data: {json.dumps({'error': error_msg})}\n\n"


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
