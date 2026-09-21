from __future__ import annotations

import math
import os
import time
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Sequence

from .providers import ProviderError


@dataclass(frozen=True)
class VoyageConfig:
    api_key: str
    model: str = "voyage-4-large"
    dimension: int = 1024
    batch_size: int = 32
    max_retries: int = 2
    timeout_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> "VoyageConfig":
        return cls(
            api_key=os.getenv("VOYAGE_API_KEY", ""),
            model=os.getenv("VOYAGE_EMBEDDING_MODEL", "voyage-4-large"),
            dimension=int(os.getenv("VOYAGE_EMBEDDING_DIMENSION", "1024")),
            batch_size=int(os.getenv("VOYAGE_BATCH_SIZE", "32")),
            max_retries=int(os.getenv("VOYAGE_MAX_RETRIES", "2")),
            timeout_seconds=float(os.getenv("VOYAGE_TIMEOUT", "60")),
        )


class VoyageEmbeddingProvider:
    """Voyage-only cloud embedding provider; never performs local inference."""

    def __init__(self, config: VoyageConfig | None = None, client: Any | None = None):
        self.config = config or VoyageConfig.from_env()
        self.model_name = self.config.model
        self.model_version = None
        self.dimension = self.config.dimension
        self._client = client

    @property
    def configured(self) -> bool:
        return bool(self.config.api_key)

    def _get_client(self):
        if self._client is None:
            if not self.config.api_key:
                raise ProviderError("VOYAGE_API_KEY is not configured")
            self._client = False
        return self._client

    @staticmethod
    def _validate(vectors: Any, expected_count: int, dimension: int) -> list[list[float]]:
        if not isinstance(vectors, list) or len(vectors) != expected_count:
            raise ProviderError("Voyage returned an invalid vector count")
        validated: list[list[float]] = []
        for vector in vectors:
            if not isinstance(vector, list) or len(vector) != dimension:
                raise ProviderError(f"Voyage vector dimension mismatch; expected {dimension}")
            values = [float(value) for value in vector]
            if any(not math.isfinite(value) for value in values):
                raise ProviderError("Voyage returned NaN or Infinity")
            validated.append(values)
        return validated

    def _embed(self, texts: Sequence[str], input_type: str) -> list[list[float]]:
        if not texts:
            return []
        client = self._get_client()
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                if client is not False:
                    response = client.embed(list(texts), model=self.config.model, input_type=input_type, output_dimension=self.config.dimension)
                    vectors = response.embeddings if hasattr(response, "embeddings") else response.get("embeddings")
                else:
                    request = urllib.request.Request(
                        "https://api.voyageai.com/v1/embeddings",
                        data=json.dumps({"input": list(texts), "model": self.config.model, "input_type": input_type, "output_dimension": self.config.dimension}).encode("utf-8"),
                        headers={"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                        payload = json.loads(response.read().decode("utf-8"))
                    vectors = [item.get("embedding") for item in payload.get("data", [])]
                return self._validate(vectors, len(texts), self.config.dimension)
            except ProviderError:
                raise
            except Exception as error:
                last_error = error
                status = getattr(error, "status_code", None)
                if isinstance(error, urllib.error.HTTPError):
                    status = error.code
                if status in {400, 401, 403, 404, 422}:
                    break
                if attempt < self.config.max_retries:
                    time.sleep(0.25 * (2**attempt))
        raise ProviderError("Voyage embedding request failed") from last_error

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(texts, "document")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "query")[0]
