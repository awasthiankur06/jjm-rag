import pytest

from jjm_rag.production.gemini import GeminiConfig, GeminiEmbeddingProvider
from jjm_rag.production.providers import ProviderError


class Embedding:
    def __init__(self, values):
        self.values = values


class Response:
    def __init__(self, values):
        self.embeddings = [Embedding(vector) for vector in values]


class Models:
    def __init__(self):
        self.calls = []

    def embed_content(self, *, model, contents, config):
        self.calls.append((model, contents, config))
        return Response([[float(index)] * 768 for index in range(len(contents))])


class Client:
    def __init__(self):
        self.models = Models()


def test_gemini_document_and_query_task_semantics_and_dimension():
    client = Client()
    provider = GeminiEmbeddingProvider(GeminiConfig(api_key="test", dimension=768), client=client)
    assert len(provider.embed_documents(["a", "b"])) == 2
    assert len(provider.embed_query("q")) == 768
    assert client.models.calls[0][0] == "gemini-embedding-001"
    assert client.models.calls[0][2].task_type == "RETRIEVAL_DOCUMENT"
    assert client.models.calls[1][2].task_type == "RETRIEVAL_QUERY"
    assert client.models.calls[0][2].output_dimensionality == 768


def test_gemini_rejects_wrong_dimensions_and_nonfinite_values():
    provider = GeminiEmbeddingProvider(GeminiConfig(api_key="test", dimension=768), client=Client())
    with pytest.raises(ProviderError):
        provider._validate({"embeddings": [{"values": [1.0]}]}, 1, 768)
    with pytest.raises(ProviderError):
        provider._validate({"embeddings": [{"values": [float("nan")] * 768}]}, 1, 768)


def test_gemini_requires_configuration_without_calling_provider():
    provider = GeminiEmbeddingProvider(GeminiConfig(api_key=""), client=None)
    with pytest.raises(ProviderError, match="GEMINI_API_KEY"):
        provider.embed_query("test")
