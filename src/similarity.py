"""Cosine similarity engine with confidence scoring.

Computes audio feature similarity, tag similarity, and
blended scores for music recommendation across genre boundaries.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from src.config import AUDIO_FEATURES, DEFAULT_FEATURE_WEIGHTS

logger = logging.getLogger(__name__)


def build_feature_matrix(
    df: pd.DataFrame,
    feature_columns: list[str] | None = None,
    weights: dict[str, float] | None = None,
) -> np.ndarray:
    """Extract and weight audio features into a numpy matrix.

    Args:
        df: Catalog DataFrame with normalized audio feature columns.
        feature_columns: Column names to include. Defaults to AUDIO_FEATURES.
        weights: Dict mapping feature name to weight multiplier.
                 Features not in dict get weight 1.0.

    Returns:
        2D numpy array of shape (n_tracks, n_features).
    """
    feature_columns = feature_columns or AUDIO_FEATURES
    weights = weights or DEFAULT_FEATURE_WEIGHTS

    matrix = df[feature_columns].values.astype(np.float64)

    # Apply weights by scaling each column
    weight_vector = np.array([weights.get(col, 1.0) for col in feature_columns])
    matrix = matrix * weight_vector

    return matrix


def find_similar_by_audio(
    seed_index: int,
    feature_matrix: np.ndarray,
    df: pd.DataFrame,
    top_k: int = 10,
) -> list[dict]:
    """Find the top_k most similar tracks by audio feature cosine similarity.

    Args:
        seed_index: Row index of the seed track in df / feature_matrix.
        feature_matrix: Weighted feature matrix from build_feature_matrix().
        df: Catalog DataFrame (for returning metadata with results).
        top_k: Number of results to return.

    Returns:
        List of dicts, each with keys: index, track_name, artist, genre,
        audio_score (float 0-1).
    """
    seed_vector = feature_matrix[seed_index].reshape(1, -1)
    similarities = cosine_similarity(seed_vector, feature_matrix).flatten()

    # Zero out the seed itself so it doesn't appear in results
    similarities[seed_index] = -1.0

    # Get top_k indices by descending similarity
    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = []
    for idx in top_indices:
        row = df.iloc[idx]
        results.append({
            "index": int(idx),
            "track_name": row.get("track_name", ""),
            "artist": row.get("artist", ""),
            "genre": row.get("genre", ""),
            "audio_score": float(similarities[idx]),
        })

    return results


def compute_tag_similarity(tags_a: list[str], tags_b: list[str]) -> float:
    """Jaccard similarity between two tag lists.

    Args:
        tags_a: List of tags for artist/track A.
        tags_b: List of tags for artist/track B.

    Returns:
        Float between 0.0 and 1.0. Returns 0.0 if both lists are empty.
    """
    set_a = set(t.lower() for t in tags_a)
    set_b = set(t.lower() for t in tags_b)

    if not set_a and not set_b:
        return 0.0

    intersection = set_a & set_b
    union = set_a | set_b

    return len(intersection) / len(union)


def compute_blended_score(
    audio_score: float,
    tag_score: float,
    audio_weight: float = 0.7,
    tag_weight: float = 0.3,
    lastfm_bonus: float = 0.0,
) -> float:
    """Blend audio and tag similarity into a single score.

    Args:
        audio_score: Cosine similarity on audio features (0-1).
        tag_score: Jaccard similarity on tags (0-1).
        audio_weight: Weight for audio score.
        tag_weight: Weight for tag score.
        lastfm_bonus: Additional bonus if Last.fm similar-artist data
                      confirms the connection (0.0-0.1).

    Returns:
        Blended score clamped to [0.0, 1.0].
    """
    score = (audio_score * audio_weight) + (tag_score * tag_weight) + lastfm_bonus
    return max(0.0, min(1.0, score))


def compute_confidence(
    audio_score: float,
    tag_score: float | None,
    lastfm_confirms: bool,
    score_margin: float,
) -> str:
    """Rate confidence of a recommendation as 'high', 'medium', or 'low'.

    Based on how many data signals agree and the margin over the next result.

    Args:
        audio_score: Audio cosine similarity.
        tag_score: Tag Jaccard similarity, or None if tags unavailable.
        lastfm_confirms: Whether Last.fm similar-artist data corroborates.
        score_margin: Gap between this result's score and the next-best.

    Returns:
        One of 'high', 'medium', 'low'.
    """
    signals = 0

    if audio_score >= 0.7:
        signals += 1
    if tag_score is not None and tag_score >= 0.3:
        signals += 1
    if lastfm_confirms:
        signals += 1
    if score_margin >= 0.05:
        signals += 1

    if signals >= 3:
        return "high"
    elif signals >= 2:
        return "medium"
    else:
        return "low"


def find_similar(
    seed_track: str | int,
    df: pd.DataFrame,
    feature_columns: list[str] | None = None,
    weights: dict[str, float] | None = None,
    tag_data: dict[str, list[str]] | None = None,
    lastfm_similar: dict[str, list[str]] | None = None,
    audio_weight: float = 0.7,
    tag_weight: float = 0.3,
    top_k: int = 10,
) -> list[dict]:
    """Top-level similarity search combining all signals.

    This is the main function called by the Streamlit app.

    Args:
        seed_track: Track name or integer index to use as seed.
        df: Full catalog DataFrame with normalized audio features.
        feature_columns: Audio feature columns for cosine similarity.
        weights: Feature weight overrides from user sliders.
        tag_data: Dict mapping artist names (lowercase) to tag lists.
        lastfm_similar: Dict mapping artist names (lowercase) to similar artist lists.
        audio_weight: Blend weight for audio similarity.
        tag_weight: Blend weight for tag similarity.
        top_k: Number of results.

    Returns:
        List of result dicts sorted by blended_score descending. Each dict has:
        track_name, artist, genre, blended_score, audio_score, tag_score,
        confidence, shared_tags.
    """
    feature_columns = feature_columns or AUDIO_FEATURES

    # Resolve seed index. Accept numpy integer types too, since pandas
    # row labels come back as numpy.int64 and fail isinstance(..., int).
    if isinstance(seed_track, (int, np.integer)):
        seed_index = int(seed_track)
    else:
        matches = df[df["track_name"].str.lower() == seed_track.strip().lower()]
        if matches.empty:
            logger.warning("Seed track '%s' not found in catalog", seed_track)
            return []
        seed_index = matches.index[0]

    logger.info(
        "Finding similar tracks for '%s' by %s",
        df.iloc[seed_index].get("track_name", "?"),
        df.iloc[seed_index].get("artist", "?"),
    )

    # Build feature matrix and get audio-based results
    feature_matrix = build_feature_matrix(df, feature_columns, weights)
    audio_results = find_similar_by_audio(seed_index, feature_matrix, df, top_k=top_k * 2)

    seed_artist = str(df.iloc[seed_index].get("artist", "")).lower()
    seed_tags = (tag_data or {}).get(seed_artist, [])
    seed_similar = (lastfm_similar or {}).get(seed_artist, [])
    seed_similar_lower = [a.lower() for a in seed_similar]

    # Enrich each result with tag similarity and confidence
    enriched = []
    for result in audio_results:
        candidate_artist = result["artist"].lower()
        candidate_tags = (tag_data or {}).get(candidate_artist, [])

        # Tag similarity
        tag_score = compute_tag_similarity(seed_tags, candidate_tags) if (seed_tags or candidate_tags) else None

        # Last.fm corroboration
        lastfm_confirms = candidate_artist in seed_similar_lower

        # Last.fm bonus
        lastfm_bonus = 0.05 if lastfm_confirms else 0.0

        # Blended score
        effective_tag_score = tag_score if tag_score is not None else 0.0
        blended = compute_blended_score(
            result["audio_score"], effective_tag_score,
            audio_weight, tag_weight, lastfm_bonus,
        )

        # Shared tags
        shared_tags = sorted(set(t.lower() for t in seed_tags) & set(t.lower() for t in candidate_tags))

        result.update({
            "blended_score": blended,
            "tag_score": tag_score,
            "lastfm_confirms": lastfm_confirms,
            "shared_tags": shared_tags,
        })
        enriched.append(result)

    # Sort by blended score and take top_k
    enriched.sort(key=lambda r: r["blended_score"], reverse=True)
    enriched = enriched[:top_k]

    # Add confidence (needs score margin from sorted list)
    for i, result in enumerate(enriched):
        next_score = enriched[i + 1]["blended_score"] if i + 1 < len(enriched) else 0.0
        margin = result["blended_score"] - next_score
        result["confidence"] = compute_confidence(
            result["audio_score"], result["tag_score"],
            result["lastfm_confirms"], margin,
        )

    return enriched
