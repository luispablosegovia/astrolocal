"""LLM client — secure communication with local Ollama/MLX server.

Security features:
- URL validation (localhost only by default)
- Request timeouts to prevent hangs
- Rate limiting to prevent resource exhaustion
- Input size limits
- No secrets transmitted (local only)
- Retry with exponential backoff
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator

import httpx

from astrolocal.config import LLMConfig

logger = logging.getLogger("astrolocal.llm.client")

# Maximum prompt size to prevent memory issues (256KB)
MAX_PROMPT_SIZE = 256 * 1024

# Rate limiting: max requests per minute
MAX_REQUESTS_PER_MINUTE = 30


class LLMError(Exception):
    """Base exception for LLM errors."""


class LLMConnectionError(LLMError):
    """Server not reachable."""


class LLMTimeoutError(LLMError):
    """Request timed out."""


class LLMRateLimitError(LLMError):
    """Too many requests."""


class RateLimiter:
    """Simple sliding-window rate limiter."""

    def __init__(self, max_requests: int = MAX_REQUESTS_PER_MINUTE, window: float = 60.0):
        self._max = max_requests
        self._window = window
        self._timestamps: list[float] = []

    def check(self) -> None:
        now = time.monotonic()
        self._timestamps = [t for t in self._timestamps if now - t < self._window]
        if len(self._timestamps) >= self._max:
            raise LLMRateLimitError(
                f"Rate limit exceeded: {self._max} requests per {self._window}s"
            )
        self._timestamps.append(now)


class LocalLLMClient:
    """Client for local LLM servers (Ollama, MLX, or any OpenAI-compatible)."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._rate_limiter = RateLimiter()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=10.0,
                    read=float(self.config.timeout_seconds),
                    write=30.0,
                    pool=10.0,
                ),
                limits=httpx.Limits(
                    max_connections=5,
                    max_keepalive_connections=2,
                ),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _validate_prompt(self, prompt: str) -> str:
        """Validate and sanitize prompt input."""
        if not prompt or not prompt.strip():
            raise LLMError("Prompt cannot be empty")
        if len(prompt.encode("utf-8")) > MAX_PROMPT_SIZE:
            raise LLMError(f"Prompt exceeds max size of {MAX_PROMPT_SIZE} bytes")
        return prompt.strip()

    async def health_check(self) -> bool:
        """Check if the LLM server is running."""
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.config.base_url}/api/tags")
            return resp.status_code == 200
        except httpx.ConnectError:
            return False
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available models on the server."""
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.config.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.warning("Failed to list models: %s", e)
            return []

    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        temperature: float | None = None,
        max_retries: int = 2,
    ) -> str:
        """Generate a complete response (non-streaming).

        Retries with exponential backoff on transient failures.
        """
        prompt = self._validate_prompt(prompt)
        self._rate_limiter.check()

        use_model = model or self.config.model
        use_temp = temperature if temperature is not None else self.config.temperature

        payload = {
            "model": use_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": use_temp,
                "num_ctx": self.config.context_window,
                "num_predict": self.config.max_tokens,
            },
        }
        if system:
            payload["system"] = system

        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                client = await self._get_client()
                resp = await client.post(
                    f"{self.config.base_url}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                response_text = data.get("response", "")

                logger.info(
                    "LLM response: model=%s, tokens=%s, attempt=%d",
                    use_model,
                    data.get("eval_count", "?"),
                    attempt + 1,
                )
                return response_text

            except httpx.ConnectError as e:
                raise LLMConnectionError(
                    f"No se pudo conectar al servidor LLM en {self.config.base_url}. "
                    "¿Está corriendo Ollama? Iniciálo con: ollama serve"
                ) from e

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < max_retries:
                    wait = 2 ** attempt
                    logger.warning("Timeout, retrying in %ds (attempt %d)", wait, attempt + 1)
                    await asyncio.sleep(wait)
                else:
                    raise LLMTimeoutError(
                        f"La generación tardó más de {self.config.timeout_seconds}s. "
                        "Probá con un modelo más chico o reducí max_tokens."
                    ) from e

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise LLMError(
                        f"Modelo '{use_model}' no encontrado. "
                        f"Instalálo con: ollama pull {use_model}"
                    ) from e
                last_error = e
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)

        raise LLMError(f"Failed after {max_retries + 1} attempts: {last_error}")

    async def stream(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """Stream response token by token."""
        prompt = self._validate_prompt(prompt)
        self._rate_limiter.check()

        use_model = model or self.config.model
        use_temp = temperature if temperature is not None else self.config.temperature

        payload = {
            "model": use_model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": use_temp,
                "num_ctx": self.config.context_window,
                "num_predict": self.config.max_tokens,
            },
        }
        if system:
            payload["system"] = system

        try:
            client = await self._get_client()
            async with client.stream(
                "POST",
                f"{self.config.base_url}/api/generate",
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if not data.get("done", False):
                            yield data.get("response", "")
                    except json.JSONDecodeError:
                        continue

        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"No se pudo conectar a {self.config.base_url}. "
                "¿Está corriendo Ollama?"
            ) from e
