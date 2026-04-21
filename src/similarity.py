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

AUDIO_CANDIDATE_POOL_SIZE = 500
DEFAULT_MAX_PER_ARTIST = 2


def _diversify(results: list[dict], top_k: int, max_per_artist: int) -> list[dict]:
    """Greedy pass that caps each artist to max_per_artist in the top_k.

    Walks the pre-sorted results, keeping a result unless that artist
    already has max_per_artist picks. If the cap leaves us short of
    top_k, we backfill with the skipped results in their original order.
    """
    if max_per_artist <= 0:
        return results[:top_k]
    kept: list[dict] = []
    skipped: list[dict] = []
    counts: dict[str, int] = {}
    for r in results:
        key = r["artist"].lower()
        if counts.get(key, 0) < max_per_artist:
            kept.append(r)
            counts[key] = counts.get(key, 0) + 1
            if len(kept) >= top_k:
                break
        else:
            skipped.append(r)
    if len(kept) < top_k:
        kept.extend(skipped[: top_k - len(kept)])
    return kept


def _lookup_artist_data(artist_string: str, data: dict[str, list[str]] | None) -> list[str]:
    """Look up tag or similar-artist data for an artist string.

    Catalog rows use "A;B;C" for collaborations. The Last.fm cache keys
    individual artists. This tries the full string first, then falls back
    to splitting on ';' and unioning data from any parts that are cached.
    """
    if not data or not artist_string:
        return []
    full = artist_string.lower()
    if full in data:
        return data[full]
    combined: list[str] = []
    seen: set[str] = set()
    for part in full.split(";"):
        part = part.strip()
        if part and part in data:
            for item in data[part]:
                key = item.lower() if isinstance(item, str) else str(item).lower()
                if key not in seen:
                    seen.add(key)
                    combined.append(item)
    return combined


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

    # Audio alone is a weak discriminator on this catalog (most results
    # come back at 0.95+), so we only count it when the seed and candidate
    # are essentially identical sonically.
    if audio_score >= 0.9:
        signals += 1
    # Jaccard on small tag sets is noisy; 0.15 is a more realistic
    # threshold than 0.3 for "these artists share a meaningful portion
    # of their community framing".
    if tag_score is not None and tag_score >= 0.15:
        signals += 1
    if lastfm_confirms:
        signals += 1
    if score_margin >= 0.03:
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
    max_per_artist: int = DEFAULT_MAX_PER_ARTIST,
    include_low_confidence: bool = True,
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

    # Build feature matrix and pull a wide audio pool so the tag layer
    # has real candidates to rerank. If the pool is tiny, audio alone
    # decides the result set and the tag signal is wasted.
    feature_matrix = build_feature_matrix(df, feature_columns, weights)
    pool_size = max(top_k * 2, AUDIO_CANDIDATE_POOL_SIZE)
    audio_results = find_similar_by_audio(seed_index, feature_matrix, df, top_k=pool_size)

    seed_artist_raw = str(df.iloc[seed_index].get("artist", ""))
    seed_tags = _lookup_artist_data(seed_artist_raw, tag_data)
    seed_similar = _lookup_artist_data(seed_artist_raw, lastfm_similar)
    seed_similar_lower = [a.lower() for a in seed_similar]

    # Enrich each result with tag similarity and confidence
    enriched = []
    for result in audio_results:
        candidate_artist_raw = result["artist"]
        candidate_artist = candidate_artist_raw.lower()
        candidate_tags = _lookup_artist_data(candidate_artist_raw, tag_data)

        # Tag similarity
        tag_score = compute_tag_similarity(seed_tags, candidate_tags) if (seed_tags or candidate_tags) else None

        # Last.fm corroboration: any artist in the candidate string appearing in the seed's similar list
        lastfm_confirms = any(
            p.strip() in seed_similar_lower
            for p in candidate_artist.split(";")
        )

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

    # Sort the full pool, then rate confidence using the margin to the next
    # entry in the full list (not the post-diversify slice). That way a
    # confidence rating does not flip just because diversification removed
    # the neighbor it was being compared against.
    enriched.sort(key=lambda r: r["blended_score"], reverse=True)
    for i, result in enumerate(enriched):
        next_score = enriched[i + 1]["blended_score"] if i + 1 < len(enriched) else 0.0
        margin = result["blended_score"] - next_score
        result["confidence"] = compute_confidence(
            result["audio_score"], result["tag_score"],
            result["lastfm_confirms"], margin,
        )

    if not include_low_confidence:
        enriched = [r for r in enriched if r["confidence"] != "low"]

    return _diversify(enriched, top_k, max_per_artist)
