from abc import ABC, abstractmethod
from typing import Any, cast

from google import genai
from google.genai import types as genai_types

from app.core.config import settings as app_settings
from app.services.rag.config import RAGSettings
from app.services.rag.models import Document


def _chunk_texts(document: Document) -> list[str]:
    return [
        doc.chunk_content if doc.chunk_content else "" for doc in (document.chunked_pages or [])
    ]


def _embedding_values(result: Any) -> list[list[float]]:
    embeddings = result.embeddings or []
    return [list(embedding.values or []) for embedding in embeddings]


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        pass

    @abstractmethod
    def embed_document(self, document: Document) -> list[list[float]]:
        pass

    @abstractmethod
    def warmup(self) -> None:
        """Ensures the model is loaded and ready for inference."""
        pass


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Multimodal: text, images, and documents share the same embedding space."""

    def __init__(self, model: str, api_key: str = "") -> None:
        self.model = model
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        result = self.client.models.embed_content(
            model=self.model,
            contents=cast(Any, texts),
        )
        return _embedding_values(result)

    def embed_document(self, document: Document) -> list[list[float]]:
        contents = [chunk.chunk_content or "" for chunk in (document.chunked_pages or [])]
        result = self.client.models.embed_content(
            model=self.model,
            contents=cast(Any, contents),
        )
        return _embedding_values(result)

    def embed_image(self, image_bytes: bytes, mime_type: str = "image/png") -> list[float]:
        """Returns a vector in the same embedding space as text — enables cross-modal search."""
        result = self.client.models.embed_content(
            model=self.model,
            contents=[
                genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        )
        values = _embedding_values(result)
        if not values:
            raise ValueError("Gemini image embedding response did not include an embedding")
        return values[0]

    def warmup(self) -> None:
        pass


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI text embeddings provider."""

    def __init__(self, model: str, api_key: str) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings")
        from openai import OpenAI

        self.model = model
        self.client = OpenAI(api_key=api_key)

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        result = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in result.data]

    def embed_document(self, document: Document) -> list[list[float]]:
        return self.embed_queries(_chunk_texts(document))

    def warmup(self) -> None:
        pass


class EmbeddingService:
    def __init__(self, settings: RAGSettings):
        config = settings.embeddings_config
        self.expected_dim = config.dim
        if config.provider == "openai":
            self.provider = OpenAIEmbeddingProvider(
                model=config.model,
                api_key=app_settings.OPENAI_API_KEY,
            )
        elif config.provider == "gemini":
            if not app_settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY is required for Gemini embeddings")
            self.provider = GeminiEmbeddingProvider(
                model=config.model,
                api_key=app_settings.GOOGLE_API_KEY,
            )
        else:
            raise ValueError(f"Unsupported embeddings provider: {config.provider}")

    def embed_query(self, query: str) -> list[float]:
        result = self.provider.embed_queries([query])[0]
        if len(result) != self.expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.expected_dim}, "
                f"got {len(result)}. Check your embedding model configuration."
            )
        return result

    def embed_document(self, document: Document) -> list[list[float]]:
        results = self.provider.embed_document(document)
        if results and len(results[0]) != self.expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.expected_dim}, "
                f"got {len(results[0])}. Check your embedding model configuration."
            )
        return results

    def warmup(self) -> None:
        self.provider.warmup()
