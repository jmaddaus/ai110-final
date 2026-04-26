"""Configuration loader for the Music Discovery Engine.

Reads API keys from .env file and exposes application constants.
All other modules import configuration from here.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CATALOG_PATH = DATA_DIR / "catalog.csv"
LASTFM_CACHE_DIR = DATA_DIR / "lastfm_cache"
EMBEDDING_CACHE_PATH = DATA_DIR / "embeddings" / "artist_embeddings.npz"
LOG_DIR = PROJECT_ROOT / "logs"

# ---------------------------------------------------------------------------
# Audio feature columns (match the cleaned Kaggle catalog schema)
# ---------------------------------------------------------------------------
AUDIO_FEATURES: list[str] = [
    "danceability",
    "energy",
    "loudness",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
]

# Default weights for each audio feature (all equal to start)
DEFAULT_FEATURE_WEIGHTS: dict[str, float] = {f: 1.0 for f in AUDIO_FEATURES}

# ---------------------------------------------------------------------------
# Similarity blending defaults
# ---------------------------------------------------------------------------
DEFAULT_AUDIO_WEIGHT: float = 0.7
DEFAULT_TAG_WEIGHT: float = 0.3

# ---------------------------------------------------------------------------
# Last.fm API
# ---------------------------------------------------------------------------
LASTFM_BASE_URL: str = "http://ws.audioscrobbler.com/2.0/"
LASTFM_RATE_LIMIT_SECONDS: float = 0.2

# ---------------------------------------------------------------------------
# Gemini RAG (Vertex AI)
# ---------------------------------------------------------------------------
RAG_MODEL: str = "gemini-3-flash-preview"
RAG_MAX_TOKENS: int = 300

# ---------------------------------------------------------------------------
# Vertex AI text embeddings (for artist semantic similarity)
# ---------------------------------------------------------------------------
EMBEDDING_MODEL: str = "text-embedding-005"
EMBEDDING_DIM: int = 768


def load_env() -> None:
    """Load environment variables from the project .env file."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info("Loaded .env from %s", env_path)
    else:
        logger.debug("No .env file found at %s", env_path)


def get_lastfm_api_key() -> str:
    """Return the Last.fm API key or raise with a helpful message."""
    load_env()
    key = os.environ.get("LASTFM_API_KEY", "")
    if not key or key == "your_lastfm_api_key_here":
        raise ValueError(
            "LASTFM_API_KEY not set. Copy .env.example to .env and add your key. "
            "Get a free key at https://www.last.fm/api/account/create"
        )
    return key


def get_google_api_key() -> str:
    """Return the Google API key or raise with a helpful message."""
    load_env()
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key or key == "your_google_api_key_here":
        raise ValueError(
            "GOOGLE_API_KEY not set. Copy .env.example to .env and add your key. "
            "Get a key at https://aistudio.google.com/apikey"
        )
    return key


