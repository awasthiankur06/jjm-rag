from __future__ import annotations

import math
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Sequence

from .providers import ProviderError


@dataclass(frozen=True)
class GeminiConfig:
    api_key: str
    model: str = "gemini-embedding-001"
    dimension: int = 768
    batch_size: int = 32
    max_retries: int = 2
    timeout_seconds: float = 60.0
    request_delay_seconds: float = 1.0
    backoff_base_seconds: float = 2.0
    tpm_quota: int = 30000
    tpm_safety_fraction: float = 0.65
    rolling_window_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> "GeminiConfig":
        return cls(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
            dimension=int(os.getenv("GEMINI_EMBEDDING_DIMENSION", "768")),
            batch_size=int(os.getenv("GEMINI_BATCH_SIZE", "32")),
            max_retries=int(os.getenv("GEMINI_MAX_RETRIES", "2")),
            timeout_seconds=float(os.getenv("GEMINI_TIMEOUT_SECONDS", "60")),
            request_delay_seconds=float(os.getenv("GEMINI_REQUEST_DELAY_SECONDS", "1.0")),
            backoff_base_seconds=float(os.getenv("GEMINI_BACKOFF_BASE_SECONDS", "2.0")),
            tpm_quota=int(os.getenv("GEMINI_TPM_QUOTA", "30000")),
            tpm_safety_fraction=float(os.getenv("GEMINI_TPM_SAFETY_FRACTION", "0.65")),
            rolling_window_seconds=float(os.getenv("GEMINI_TPM_WINDOW_SECONDS", "60")),
        )


class GeminiRateLimitError(ProviderError):
    def __init__(self, message: str, *, retry_after: float | None = None, retries: int = 0):
        super().__init__(message)
        self.retry_after = retry_after
        self.retries = retries


@dataclass(frozen=True)
class GeminiRequestStats:
    estimated_tokens: int
    observed_tokens: int | None = None
    retry_after: float | None = None
    rate_limit_kind: str | None = None


class GeminiEmbeddingProvider:
    """Google Gemini cloud embeddings; never performs local inference."""

    def __init__(self, config: GeminiConfig | None = None, client: Any | None = None):
        self.config = config or GeminiConfig.from_env()
        self.model_name = self.config.model
        self.model_version = None
        self.dimension = self.config.dimension
        self._client = client
        self.last_request_stats: GeminiRequestStats | None = None

    @property
    def configured(self) -> bool:
        return bool(self.config.api_key)

    def _get_client(self):
        if self._client is None:
            if not self.config.api_key:
                raise ProviderError("GEMINI_API_KEY is not configured")
            try:
                from google import genai
                from google.genai import types
            except ImportError as error:
                raise ProviderError("google-genai package is not installed") from error
            # This application uses direct outbound HTTPS.  Some desktop
            # environments inherit stale localhost proxy variables even when
            # Windows itself is configured for direct access; honoring those
            # variables produces WinError 10061 before Gemini is reached.
            self._client = genai.Client(
                api_key=self.config.api_key,
                http_options=types.HttpOptions(client_args={"trust_env": False}),
            )
        return self._client

    @staticmethod
    def _validate(response: Any, expected_count: int, dimension: int) -> list[list[float]]:
        embeddings = getattr(response, "embeddings", None)
        if embeddings is None and isinstance(response, dict):
            embeddings = response.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != expected_count:
            raise ProviderError("Gemini returned an invalid embedding count")
        vectors = []
        for embedding in embeddings:
            values = getattr(embedding, "values", None)
            if values is None and isinstance(embedding, dict):
                values = embedding.get("values")
            if not isinstance(values, list) or len(values) != dimension:
                raise ProviderError(f"Gemini embedding dimension mismatch; expected {dimension}")
            vector = [float(value) for value in values]
            if any(not math.isfinite(value) for value in vector):
                raise ProviderError("Gemini returned NaN or Infinity")
            vectors.append(vector)
        return vectors

    def _embed(self, texts: Sequence[str], task_type: str) -> list[list[float]]:
        if not texts:
            return []
        client = self._get_client()
        try:
            from google.genai import types
            config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=self.config.dimension)
        except ImportError as error:
            raise ProviderError("google-genai package is not installed") from error
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                if attempt == 0 and self.config.request_delay_seconds:
                    time.sleep(self.config.request_delay_seconds)
                response = client.models.embed_content(model=self.config.model, contents=list(texts), config=config)
                vectors = self._validate(response, len(texts), self.config.dimension)
                self.last_request_stats = GeminiRequestStats(sum(self.estimate_tokens(text) for text in texts), self._response_tokens(response))
                return vectors
            except ProviderError:
                raise
            except Exception as error:
                last_error = error
                status = getattr(error, "status_code", None) or getattr(error, "code", None) or getattr(getattr(error, "response", None), "status_code", None)
                detail = f"{error} {getattr(error, 'response_json', '')}".lower()
                rate_limited = status == 429 or any(term in detail for term in ("resource_exhausted", "rate limit", "rate-limit", "too many requests"))
                transient = status in {408, 429, 500, 502, 503, 504} or rate_limited
                if not transient or status in {400, 401, 403, 404, 422}:
                    break
                if attempt < self.config.max_retries:
                    retry_after = self._retry_after(error)
                    delay = retry_after if retry_after is not None else self.config.backoff_base_seconds * (2**attempt) + random.uniform(0, 0.5)
                    time.sleep(delay)
                elif rate_limited:
                    raise GeminiRateLimitError("Gemini rate limit persisted after bounded retries", retry_after=self._retry_after(error), retries=attempt + 1) from error
        raise ProviderError("Gemini embedding request failed") from last_error

    @staticmethod
    def _retry_after(error: Exception) -> float | None:
        headers = getattr(getattr(error, "response", None), "headers", None) or getattr(error, "headers", None)
        if headers:
            value = headers.get("Retry-After") or headers.get("retry-after")
            try:
                return max(0.0, float(value)) if value is not None else None
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _response_tokens(response: Any) -> int | None:
        metadata = getattr(response, "metadata", None)
        for name in ("token_count", "tokens", "prompt_token_count", "input_token_count"):
            value = getattr(metadata, name, None) if metadata is not None else None
            if isinstance(value, int):
                return value
        return None

    @staticmethod
    def estimate_tokens(text: str) -> int:
        # Conservative local estimate; embedding responses expose no usage count.
        return max(1, (len(text) + 2) // 3)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]
