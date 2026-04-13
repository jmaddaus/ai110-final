"""Enrich the song catalog with Last.fm tags and similar artist data.

Merges external data into the catalog so the similarity engine
can use both audio features and tag information.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def load_tag_cache(cache_dir: Path) -> dict[str, list[str]]:
    """Load all cached artist tags into a dict.

    Args:
        cache_dir: Path to the Last.fm cache directory.

    Returns:
        Dict mapping artist name (lowercase) to list of tags.
    """
    tag_data: dict[str, list[str]] = {}

    if not cache_dir.exists():
        logger.warning("Cache directory does not exist: %s", cache_dir)
        return tag_data

    for path in cache_dir.glob("artist_tags_*.json"):
        try:
            with open(path) as f:
                data = json.load(f)
            artist = data.get("artist", "").lower()
            tags = data.get("tags", [])
            if artist:
                tag_data[artist] = tags
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load tag cache %s: %s", path.name, e)

    logger.info("Loaded tags for %d artists from cache", len(tag_data))
    return tag_data


def load_similar_artist_cache(cache_dir: Path) -> dict[str, list[str]]:
    """Load all cached similar-artist data into a dict.

    Args:
        cache_dir: Path to the Last.fm cache directory.

    Returns:
        Dict mapping artist name (lowercase) to list of similar artist names.
    """
    similar_data: dict[str, list[str]] = {}

    if not cache_dir.exists():
        logger.warning("Cache directory does not exist: %s", cache_dir)
        return similar_data

    for path in cache_dir.glob("similar_artists_*.json"):
        try:
            with open(path) as f:
                data = json.load(f)
            artist = data.get("artist", "").lower()
            similar = [s["name"] for s in data.get("similar", [])]
            if artist:
                similar_data[artist] = similar
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load similar cache %s: %s", path.name, e)

    logger.info("Loaded similar artists for %d artists from cache", len(similar_data))
    return similar_data


def enrich_catalog(
    df: pd.DataFrame,
    tag_data: dict[str, list[str]],
    similar_data: dict[str, list[str]],
) -> pd.DataFrame:
    """Add tag and similar-artist columns to the catalog DataFrame.

    Args:
        df: Catalog DataFrame.
        tag_data: Dict from load_tag_cache().
        similar_data: Dict from load_similar_artist_cache().

    Returns:
        DataFrame with added columns: 'tags' (list[str]) and
        'similar_artists' (list[str]).
    """
    df = df.copy()
    df["tags"] = df["artist"].str.lower().map(
        lambda a: tag_data.get(a, [])
    )
    df["similar_artists"] = df["artist"].str.lower().map(
        lambda a: similar_data.get(a, [])
    )
    return df


def get_enrichment_stats(df: pd.DataFrame) -> dict[str, int]:
    """Return coverage statistics for enrichment.

    Args:
        df: Enriched catalog DataFrame (must have 'tags' and 'similar_artists' columns).

    Returns:
        Dict with keys: total_tracks, tracks_with_tags,
        tracks_with_similar_artists, unique_artists_enriched.
    """
    has_tags = df["tags"].apply(lambda t: len(t) > 0 if isinstance(t, list) else False)
    has_similar = df["similar_artists"].apply(lambda s: len(s) > 0 if isinstance(s, list) else False)

    artists_with_tags = df[has_tags]["artist"].str.lower().nunique()

    return {
        "total_tracks": len(df),
        "tracks_with_tags": int(has_tags.sum()),
        "tracks_with_similar_artists": int(has_similar.sum()),
        "unique_artists_enriched": artists_with_tags,
    }
