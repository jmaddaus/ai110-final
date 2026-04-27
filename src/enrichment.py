"""Enrich the song catalog with Last.fm tags and similar artist data.

Merges external data into the catalog so the similarity engine
can use both audio features and tag information.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def compute_tag_idf(
    tag_data: dict[str, list[str]],
    smoothing: float = 1.0,
) -> dict[str, float]:
    """Compute inverse-document-frequency for each tag in the corpus.

    IDF(t) = log((N + smoothing) / (df(t) + smoothing))

    The smoothing term avoids divide-by-zero and damps the boost on
    extremely rare tags (which often reflect typos rather than
    meaningful niches).

    Args:
        tag_data: Dict mapping artist name (lowercase) to list of tags.
        smoothing: Additive smoothing for both N and df(t).

    Returns:
        Dict mapping tag (lowercase) to IDF weight.
    """
    if not tag_data:
        return {}
    n_docs = len(tag_data)
    doc_freq: dict[str, int] = {}
    for tags in tag_data.values():
        seen = {t.lower() for t in tags}
        for tag in seen:
            doc_freq[tag] = doc_freq.get(tag, 0) + 1
    return {
        tag: math.log((n_docs + smoothing) / (count + smoothing))
        for tag, count in doc_freq.items()
    }


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


def load_instrument_cache(cache_dir: Path) -> dict[str, list[str]]:
    """Load all cached MusicBrainz artist instrument lists into a dict.

    Args:
        cache_dir: Path to the MusicBrainz cache directory.

    Returns:
        Dict mapping artist name (lowercase) to list of instruments played
        by band members. Empty lists are skipped (solo artists, no data).
    """
    instrument_data: dict[str, list[str]] = {}

    if not cache_dir.exists():
        logger.warning("MusicBrainz cache directory does not exist: %s", cache_dir)
        return instrument_data

    for path in cache_dir.glob("artist_instruments_*.json"):
        try:
            with open(path) as f:
                data = json.load(f)
            artist = data.get("name", "").lower()
            instruments = data.get("instruments", [])
            if artist and instruments:
                instrument_data[artist] = instruments
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load instrument cache %s: %s", path.name, e)

    logger.info("Loaded instruments for %d artists from cache", len(instrument_data))
    return instrument_data


def load_track_tag_cache(cache_dir: Path) -> dict[tuple[str, str], list[str]]:
    """Load all cached Last.fm track-level tags.

    Track tags describe a specific song (eg. 'ballad', 'guitar riff',
    'epic'), in contrast to artist tags which describe the whole
    catalog. They are the song-level signal the engine has been
    missing.

    Args:
        cache_dir: Path to the Last.fm cache directory.

    Returns:
        Dict mapping (artist_lower, track_name_lower) to list of tags.
        Tracks with empty tag lists are skipped.
    """
    track_tag_data: dict[tuple[str, str], list[str]] = {}
    if not cache_dir.exists():
        logger.warning("Cache directory does not exist: %s", cache_dir)
        return track_tag_data

    cached = 0
    for path in cache_dir.glob("track_tags_*.json"):
        cached += 1
        try:
            with open(path) as f:
                data = json.load(f)
            artist = (data.get("artist") or "").lower()
            track = (data.get("track") or "").lower()
            tags = data.get("tags") or []
            if artist and track and tags:
                track_tag_data[(artist, track)] = tags
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load track-tag cache %s: %s", path.name, e)

    logger.info(
        "Loaded track tags for %d / %d cached tracks (%.1f%% had usable tags)",
        len(track_tag_data), cached,
        100 * len(track_tag_data) / cached if cached else 0,
    )
    return track_tag_data


def load_similar_artist_cache(cache_dir: Path) -> dict[str, dict[str, float]]:
    """Load all cached similar-artist data, preserving Last.fm match scores.

    Args:
        cache_dir: Path to the Last.fm cache directory.

    Returns:
        Dict mapping artist name (lowercase) to a sub-dict of
        {similar_artist_name (lowercase): match_score (0.0-1.0)}.
        Match scores let the similarity engine weight the Last.fm
        bonus by edge confidence rather than treating every link the
        same.
    """
    similar_data: dict[str, dict[str, float]] = {}

    if not cache_dir.exists():
        logger.warning("Cache directory does not exist: %s", cache_dir)
        return similar_data

    for path in cache_dir.glob("similar_artists_*.json"):
        try:
            with open(path) as f:
                data = json.load(f)
            artist = data.get("artist", "").lower()
            if not artist:
                continue
            edges: dict[str, float] = {}
            for entry in data.get("similar", []):
                name = entry.get("name", "")
                if not name:
                    continue
                try:
                    match = float(entry.get("match", 0.0))
                except (TypeError, ValueError):
                    match = 0.0
                key = name.lower()
                # Same target sometimes appears twice with different
                # scores; keep the higher one.
                if match > edges.get(key, 0.0):
                    edges[key] = match
            similar_data[artist] = edges
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
