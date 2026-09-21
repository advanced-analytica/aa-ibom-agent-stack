from abc import ABC, abstractmethod

from google import genai
from google.genai import types as genai_types

from app.core.config import settings as app_settings
from app.services.rag.config import RAGSettings
from app.services.rag.models import Document


def _chunk_texts(document: Document) -> list[str]:
    return [
        doc.chunk_content if doc.chunk_content else "" for doc in (document.chunked_pages or [])
    ]


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
            contents=texts,
        )
        return [e.values for e in result.embeddings]

    def embed_document(self, document: Document) -> list[list[float]]:
        contents = [chunk.chunk_content or "" for chunk in (document.chunked_pages or [])]
        result = self.client.models.embed_content(
            model=self.model,
            contents=contents,
        )
        return [e.values for e in result.embeddings]

    def embed_image(self, image_bytes: bytes, mime_type: str = "image/png") -> list[float]:
        """Returns a vector in the same embedding space as text — enables cross-modal search."""
        result = self.client.models.embed_content(
            model=self.model,
            contents=[
                genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        )
        return result.embeddings[0].values

    def warmup(self) -> None:
        pass


class EmbeddingService:
    def __init__(self, settings: RAGSettings):
        config = settings.embeddings_config
        self.expected_dim = config.dim
        self.provider = GeminiEmbeddingProvider(
            model=config.model, api_key=app_settings.GOOGLE_API_KEY
        )

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
