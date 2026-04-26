"""Vertex AI text embeddings for artist semantic similarity.

Embeds a small text doc per artist (tags + similar-artist names) into
a 768-dim vector, then uses cosine similarity at query time as another
similarity signal. Captures relationships tag Jaccard misses (eg.
anthemic vs introspective rock, synonym tags like rnb / r&b).

Embeddings are L2-normalised at save time, so cosine = dot product.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from google import genai

from src.config import EMBEDDING_MODEL, get_google_api_key

logger = logging.getLogger(__name__)

EMBEDDING_BATCH_SIZE = 100


def build_artist_doc(
    artist: str,
    tags: list[str],
    similar_artists: list[str],
    max_tags: int = 15,
    max_similar: int = 10,
) -> str:
    """Compose a short text doc representing one artist.

    The doc is what the embedding model sees, so order tags by
    importance (Last.fm returns its top-tags list ranked by use) and
    cap the length so the doc stays information-dense.
    """
    tag_part = ", ".join(tags[:max_tags]) if tags else "unknown"
    similar_part = (
        ", ".join(similar_artists[:max_similar]) if similar_artists else "unknown"
    )
    return f"Artist: {artist}. Tags: {tag_part}. Similar to: {similar_part}."


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    """Row-normalise a matrix so dot product = cosine similarity."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class EmbeddingClient:
    """Thin wrapper around the genai SDK for batched text embedding."""

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        api_key: str | None = None,
    ):
        self._client = genai.Client(
            vertexai=True, api_key=api_key or get_google_api_key()
        )
        self.model = model

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Return an (N, D) float32 matrix of embeddings.

        Caller is responsible for L2-normalising before saving so cosine
        becomes a dot product at query time.
        """
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        result = self._client.models.embed_content(
            model=self.model,
            contents=texts,
        )
        return np.array(
            [e.values for e in result.embeddings], dtype=np.float32
        )


def save_embedding_cache(
    cache_path: Path,
    artists: list[str],
    embeddings: np.ndarray,
) -> None:
    """Save embeddings + artist names. L2-normalises the matrix."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _l2_normalize(embeddings.astype(np.float32))
    np.savez(
        cache_path,
        embeddings=normalized,
        artists=np.array([a.lower() for a in artists]),
    )
    logger.info("Saved %d embeddings to %s", len(artists), cache_path)


def load_embedding_cache(
    cache_path: Path,
) -> tuple[np.ndarray, dict[str, int]] | None:
    """Load (matrix, artist_name_lower -> row index) or None if missing.

    The matrix is already L2-normalised, so cosine similarity reduces
    to a single np.dot at query time.
    """
    if not cache_path.exists():
        logger.warning("Embedding cache does not exist: %s", cache_path)
        return None
    try:
        data = np.load(cache_path, allow_pickle=False)
    except (OSError, ValueError) as e:
        logger.warning("Failed to load embedding cache: %s", e)
        return None
    embeddings = data["embeddings"]
    artists = data["artists"]
    index = {str(a): i for i, a in enumerate(artists)}
    logger.info("Loaded %d artist embeddings", len(index))
    return embeddings, index
