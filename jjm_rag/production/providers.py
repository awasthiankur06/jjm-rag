from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Sequence


class ProviderError(RuntimeError):
    """Safe provider failure without exposing credentials or response bodies."""


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str
    api_key: str
    timeout_seconds: float = 20.0
    max_retries: int = 2

    @classmethod
    def from_env(cls, prefix: str, default_base_url: str) -> "ProviderConfig":
        return cls(
            base_url=os.getenv(f"{prefix}_API_BASE", os.getenv(f"{prefix}_BASE_URL", default_base_url)).rstrip("/"),
            api_key=os.getenv(f"{prefix}_API_KEY", ""),
            timeout_seconds=float(os.getenv(f"{prefix}_TIMEOUT_SECONDS", "20")),
            max_retries=int(os.getenv(f"{prefix}_MAX_RETRIES", "2")),
        )


def _post_json(config: ProviderConfig, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not config.api_key:
        raise ProviderError("provider is not configured")
    request = urllib.request.Request(
        f"{config.base_url}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(config.max_retries + 1):
        try:
            # Desktop environments can inherit stale localhost proxy values.
            # Cloud providers are contacted directly, matching the Gemini
            # adapter's ``trust_env=False`` policy.
            direct_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with direct_opener.open(request, timeout=config.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code in {400, 401, 403, 404, 422}:
                raise ProviderError(f"provider rejected request with HTTP {error.code}") from error
            last_error = error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
        if attempt < config.max_retries:
            time.sleep(0.25 * (2**attempt))
    raise ProviderError(f"provider request failed after {config.max_retries + 1} attempts") from last_error


class CloudEmbeddingProvider:
    """OpenAI-compatible cloud embeddings adapter; never performs local inference."""

    def __init__(self, config: ProviderConfig | None = None, model: str | None = None, dimension: int | None = None):
        self.config = config or ProviderConfig.from_env("EMBEDDING", "https://api.openai.com/v1")
        self.model_name = model or os.getenv("EMBEDDING_MODEL", "")
        self.model_version = os.getenv("EMBEDDING_MODEL_VERSION")
        configured_dimension = dimension or os.getenv("EMBEDDING_DIMENSION")
        self.dimension = int(configured_dimension) if configured_dimension else 0

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        vectors = self._embed([text])
        return vectors[0]

    def _embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not self.model_name:
            raise ProviderError("EMBEDDING_MODEL is not configured")
        response = _post_json(self.config, "/embeddings", {"model": self.model_name, "input": list(texts)})
        data = response.get("data")
        if not isinstance(data, list) or len(data) != len(texts):
            raise ProviderError("embedding provider returned an invalid response")
        vectors = [item.get("embedding") for item in data]
        if any(not isinstance(vector, list) or not vector for vector in vectors):
            raise ProviderError("embedding provider returned invalid vectors")
        actual_dimension = len(vectors[0])
        if any(len(vector) != actual_dimension for vector in vectors):
            raise ProviderError("embedding provider returned inconsistent dimensions")
        self.dimension = actual_dimension
        return vectors


class XaiLLMProvider:
    """Official xAI-compatible chat-completions adapter with bounded retries."""

    def __init__(self, config: ProviderConfig | None = None, model: str | None = None):
        self.config = config or ProviderConfig.from_env("XAI", "https://api.x.ai/v1")
        self.model = model or os.getenv("XAI_MODEL", "grok-2-latest")

    def generate(self, system: str, user: str, *, max_tokens: int = 800, temperature: float = 0.0) -> dict[str, Any]:
        response = _post_json(self.config, "/chat/completions", {"model": self.model, "temperature": temperature, "max_tokens": max_tokens, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        try:
            message = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderError("xAI provider returned an invalid response") from error
        return {"text": message, "model": response.get("model", self.model), "usage": response.get("usage", {})}
