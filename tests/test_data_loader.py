"""Tests for src/data_loader.py.

Uses small test CSV files to verify loading, normalization, and search.
"""

import pandas as pd
import pytest

from src.data_loader import (
    load_catalog,
    normalize_features,
    search_catalog,
    get_unique_artists,
    get_artist_tracks,
)


@pytest.fixture
def tiny_catalog_path(tmp_path):
    """Write a small CSV with known values and return its path."""
    csv_content = (
        "track_id,track_name,artist,album,genre,popularity,"
        "danceability,energy,loudness,speechiness,acousticness,"
        "instrumentalness,liveness,valence,tempo\n"
        "1,Song A,Artist X,Album 1,rock,80,0.6,0.8,0.7,0.1,0.2,0.0,0.1,0.9,0.5\n"
        "2,Song B,Artist Y,Album 2,pop,90,0.9,0.5,0.4,0.05,0.5,0.0,0.2,0.7,0.6\n"
        "3,Song C,Artist X,Album 1,rock,70,0.4,0.9,0.8,0.02,0.1,0.3,0.3,0.4,0.7\n"
        "4,Song D,Artist Z,Album 3,jazz,60,0.3,0.3,0.3,0.04,0.8,0.6,0.1,0.5,0.4\n"
    )
    path = tmp_path / "test_catalog.csv"
    path.write_text(csv_content)
    return path


def test_load_catalog_returns_dataframe(tiny_catalog_path):
    """load_catalog should return a pandas DataFrame."""
    df = load_catalog(tiny_catalog_path)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 4


def test_load_catalog_missing_file_raises():
    """Should raise FileNotFoundError for nonexistent path."""
    with pytest.raises(FileNotFoundError):
        load_catalog("/nonexistent/path/catalog.csv")


def test_normalize_features_range(tiny_catalog_path):
    """After normalization, values should be in [0, 1]."""
    df = load_catalog(tiny_catalog_path)
    for col in ["danceability", "energy", "loudness", "valence", "tempo"]:
        assert df[col].min() >= 0.0
        assert df[col].max() <= 1.0


def test_search_catalog_case_insensitive(tiny_catalog_path):
    """Search should be case-insensitive."""
    df = load_catalog(tiny_catalog_path)
    results = search_catalog(df, "artist x", field="artist")
    assert len(results) == 2


def test_search_catalog_no_results(tiny_catalog_path):
    """Search for nonexistent artist should return empty DataFrame."""
    df = load_catalog(tiny_catalog_path)
    results = search_catalog(df, "Nonexistent Band", field="artist")
    assert len(results) == 0


def test_search_catalog_empty_query(tiny_catalog_path):
    """Empty query should return empty DataFrame."""
    df = load_catalog(tiny_catalog_path)
    results = search_catalog(df, "", field="artist")
    assert len(results) == 0


def test_get_unique_artists(tiny_catalog_path):
    """Should return deduplicated sorted artist list."""
    df = load_catalog(tiny_catalog_path)
    artists = get_unique_artists(df)
    assert artists == ["Artist X", "Artist Y", "Artist Z"]


def test_get_artist_tracks(tiny_catalog_path):
    """Should return all tracks by a given artist."""
    df = load_catalog(tiny_catalog_path)
    tracks = get_artist_tracks(df, "Artist X")
    assert len(tracks) == 2
