"""Tests for src/similarity.py.

Uses small synthetic DataFrames to verify cosine similarity,
tag similarity, blending, and confidence scoring.
"""

import numpy as np
import pandas as pd
import pytest

from src.similarity import (
    build_feature_matrix,
    find_similar_by_audio,
    compute_tag_similarity,
    compute_blended_score,
    compute_confidence,
)

from src.config import AUDIO_FEATURES


# --- Fixtures ---

@pytest.fixture
def sample_catalog() -> pd.DataFrame:
    """Create a small 5-track catalog with known audio features."""
    data = {
        "track_name": ["Track A", "Track B", "Track C", "Track D", "Track E"],
        "artist": ["Artist 1", "Artist 2", "Artist 3", "Artist 1", "Artist 4"],
        "genre": ["rock", "rock", "pop", "rock", "jazz"],
        "popularity": [80, 70, 90, 60, 50],
    }
    # Add audio features — Track A and Track B are very similar
    features = {
        "danceability":      [0.5, 0.5, 0.9, 0.3, 0.2],
        "energy":            [0.8, 0.8, 0.6, 0.9, 0.3],
        "loudness":          [0.7, 0.7, 0.4, 0.8, 0.2],
        "speechiness":       [0.1, 0.1, 0.3, 0.1, 0.05],
        "acousticness":      [0.2, 0.2, 0.1, 0.3, 0.8],
        "instrumentalness":  [0.0, 0.0, 0.0, 0.1, 0.6],
        "liveness":          [0.1, 0.1, 0.2, 0.2, 0.1],
        "valence":           [0.6, 0.6, 0.8, 0.4, 0.5],
        "tempo":             [0.5, 0.5, 0.7, 0.6, 0.3],
    }
    data.update(features)
    return pd.DataFrame(data)


@pytest.fixture
def sample_feature_matrix(sample_catalog) -> np.ndarray:
    """Build an unweighted feature matrix from sample catalog."""
    return build_feature_matrix(sample_catalog, AUDIO_FEATURES)


# --- build_feature_matrix tests ---

def test_build_feature_matrix_shape(sample_catalog):
    """Feature matrix should have shape (n_tracks, n_features)."""
    matrix = build_feature_matrix(sample_catalog, AUDIO_FEATURES)
    assert matrix.shape == (5, 9)


def test_build_feature_matrix_with_weights(sample_catalog):
    """Weights should scale the corresponding feature columns."""
    weights = {"energy": 2.0, "danceability": 0.0}
    matrix = build_feature_matrix(sample_catalog, AUDIO_FEATURES, weights)
    # Energy column (index 1) should be doubled
    raw_matrix = build_feature_matrix(sample_catalog, AUDIO_FEATURES)
    energy_idx = AUDIO_FEATURES.index("energy")
    np.testing.assert_array_almost_equal(matrix[:, energy_idx], raw_matrix[:, energy_idx] * 2.0)
    # Danceability column (index 0) should be zeroed
    dance_idx = AUDIO_FEATURES.index("danceability")
    np.testing.assert_array_almost_equal(matrix[:, dance_idx], np.zeros(5))


# --- find_similar_by_audio tests ---

def test_identical_track_has_similarity_one(sample_catalog, sample_feature_matrix):
    """Tracks A and B have identical features, so similarity should be ~1.0."""
    results = find_similar_by_audio(0, sample_feature_matrix, sample_catalog, top_k=4)
    # Track B (index 1) should be the top result with score ~1.0
    assert results[0]["index"] == 1
    assert results[0]["audio_score"] > 0.99


def test_find_similar_excludes_seed(sample_catalog, sample_feature_matrix):
    """The seed track should not appear in its own results."""
    results = find_similar_by_audio(0, sample_feature_matrix, sample_catalog, top_k=4)
    indices = [r["index"] for r in results]
    assert 0 not in indices


def test_find_similar_returns_correct_count(sample_catalog, sample_feature_matrix):
    """Should return exactly top_k results (or fewer if catalog is smaller)."""
    results = find_similar_by_audio(0, sample_feature_matrix, sample_catalog, top_k=3)
    assert len(results) == 3


# --- compute_tag_similarity tests ---

def test_tag_similarity_identical_tags():
    """Identical tag lists should have Jaccard similarity 1.0."""
    assert compute_tag_similarity(["rock", "blues"], ["rock", "blues"]) == 1.0


def test_tag_similarity_no_overlap():
    """Disjoint tag lists should have Jaccard similarity 0.0."""
    assert compute_tag_similarity(["rock", "metal"], ["jazz", "funk"]) == 0.0


def test_tag_similarity_partial_overlap():
    """Tags ['rock', 'blues'] vs ['blues', 'jazz'] should be 1/3."""
    score = compute_tag_similarity(["rock", "blues"], ["blues", "jazz"])
    assert abs(score - 1 / 3) < 0.001


def test_tag_similarity_empty_lists():
    """Two empty tag lists should return 0.0."""
    assert compute_tag_similarity([], []) == 0.0


def test_tag_similarity_case_insensitive():
    """Tags should be compared case-insensitively."""
    assert compute_tag_similarity(["Rock", "BLUES"], ["rock", "blues"]) == 1.0


# --- compute_blended_score tests ---

def test_blended_score_audio_only():
    """With tag_weight=0, blended score should equal audio_score."""
    score = compute_blended_score(0.8, 0.5, audio_weight=1.0, tag_weight=0.0)
    assert abs(score - 0.8) < 0.001


def test_blended_score_default_weights():
    """Default 70/30 blend."""
    score = compute_blended_score(0.8, 0.6)
    expected = 0.8 * 0.7 + 0.6 * 0.3
    assert abs(score - expected) < 0.001


def test_blended_score_clamped():
    """Blended score with lastfm_bonus should not exceed 1.0."""
    score = compute_blended_score(1.0, 1.0, lastfm_bonus=0.1)
    assert score == 1.0


# --- compute_confidence tests ---

def test_confidence_high():
    """High confidence: strong audio + tags + lastfm + good margin."""
    assert compute_confidence(0.9, 0.5, True, 0.1) == "high"


def test_confidence_medium():
    """Medium confidence: decent audio, no tags, no lastfm, decent margin."""
    assert compute_confidence(0.8, 0.1, False, 0.06) == "medium"


def test_confidence_low():
    """Low confidence: weak audio, no tags, no lastfm, small margin."""
    assert compute_confidence(0.4, None, False, 0.01) == "low"
