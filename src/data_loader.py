"""Data loading and preparation for the Kaggle Spotify catalog.

Separate from src/recommender.load_songs() which handles the
original 18-song CSV. This module works with the large catalog.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.config import CATALOG_PATH, AUDIO_FEATURES

logger = logging.getLogger(__name__)


def load_catalog(path: Path | str | None = None) -> pd.DataFrame:
    """Load the cleaned catalog CSV into a DataFrame.

    Args:
        path: Path to catalog.csv. Defaults to config.CATALOG_PATH.

    Returns:
        DataFrame with columns for track metadata and audio features.
        Audio feature columns are normalized to [0, 1].

    Raises:
        FileNotFoundError: If the catalog file does not exist.
        ValueError: If required audio feature columns are missing.
    """
    path = Path(path) if path else CATALOG_PATH

    if not path.exists():
        raise FileNotFoundError(f"Catalog not found at {path}")

    logger.info("Loading catalog from %s", path)
    df = pd.read_csv(path)

    # Validate required columns
    missing = [c for c in AUDIO_FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Catalog is missing required columns: {missing}")

    # Normalize audio features to [0, 1]
    df = normalize_features(df, AUDIO_FEATURES)

    logger.info("Loaded %d tracks with %d columns", len(df), len(df.columns))
    return df


def normalize_features(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Min-max normalize specified columns to [0, 1] range.

    Args:
        df: Input DataFrame.
        columns: Column names to normalize.

    Returns:
        DataFrame with specified columns scaled to [0, 1].
        Columns with zero range are left as-is.
    """
    df = df.copy()
    for col in columns:
        if col not in df.columns:
            continue
        col_min = df[col].min()
        col_max = df[col].max()
        if col_max - col_min > 0:
            df[col] = (df[col] - col_min) / (col_max - col_min)
        else:
            logger.warning("Column '%s' has zero range, skipping normalization", col)
    return df


def search_catalog(
    df: pd.DataFrame,
    query: str,
    field: str = "artist",
    max_results: int = 20,
) -> pd.DataFrame:
    """Search the catalog by artist or track name (case-insensitive substring match).

    Args:
        df: The catalog DataFrame.
        query: Search string.
        field: Column to search in ("artist", "track_name", or "both").
        max_results: Maximum number of results to return.

    Returns:
        Filtered DataFrame sorted by popularity (descending).
    """
    query_lower = query.strip().lower()
    if not query_lower:
        return df.head(0)

    if field == "both":
        mask = (
            df["artist"].str.lower().str.contains(query_lower, na=False)
            | df["track_name"].str.lower().str.contains(query_lower, na=False)
        )
    else:
        mask = df[field].str.lower().str.contains(query_lower, na=False)

    results = df[mask]

    if "popularity" in results.columns:
        results = results.sort_values("popularity", ascending=False)

    return results.head(max_results)


def get_unique_artists(df: pd.DataFrame) -> list[str]:
    """Return sorted list of unique artist names in the catalog."""
    return sorted(df["artist"].dropna().unique().tolist())


def get_artist_tracks(df: pd.DataFrame, artist: str) -> pd.DataFrame:
    """Return all tracks by a given artist (case-insensitive match)."""
    mask = df["artist"].str.lower() == artist.strip().lower()
    return df[mask]
