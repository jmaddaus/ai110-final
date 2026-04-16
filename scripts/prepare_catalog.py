"""Clean and prepare the Spotify Tracks Dataset.

Usage:
    python -m scripts.prepare_catalog --input data/spotify-tracks.csv --output data/catalog.csv

Steps:
    1. Load raw CSV
    2. Drop rows with missing audio features
    3. Remove duplicate tracks (same artist + track name)
    4. Normalize loudness (dB scale) and tempo (BPM) to 0-1
    5. Select and rename columns to match our schema
    6. Save cleaned CSV
"""

from __future__ import annotations

import argparse
import logging
import sys

import pandas as pd

from src.config import AUDIO_FEATURES, DATA_DIR

logger = logging.getLogger(__name__)

# Expected columns in the Kaggle dataset
KAGGLE_COLUMNS: list[str] = [
    "track_id", "artists", "album_name", "track_name",
    "popularity", "duration_ms", "explicit", "danceability",
    "energy", "key", "loudness", "mode", "speechiness",
    "acousticness", "instrumentalness", "liveness", "valence",
    "tempo", "time_signature", "track_genre",
]

# Column rename mapping: kaggle name -> our name
RENAME_MAP: dict[str, str] = {
    "artists": "artist",
    "album_name": "album",
    "track_genre": "genre",
}

# Columns we keep in our catalog
OUTPUT_COLUMNS: list[str] = [
    "track_id", "track_name", "artist", "album", "genre",
    "popularity", "danceability", "energy", "loudness",
    "speechiness", "acousticness", "instrumentalness",
    "liveness", "valence", "tempo",
]


def load_raw(path: str) -> pd.DataFrame:
    """Load the raw Spotify tracks CSV."""
    logger.info("Loading raw data from %s", path)
    df = pd.read_csv(path)
    # Drop unnamed index column if present
    unnamed_cols = [c for c in df.columns if c.startswith("Unnamed")]
    if unnamed_cols:
        df = df.drop(columns=unnamed_cols)
    logger.info("Loaded %d rows, %d columns", len(df), len(df.columns))
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with missing audio features and rename columns."""
    df = df.rename(columns=RENAME_MAP)

    # Drop rows missing any audio feature
    before = len(df)
    df = df.dropna(subset=AUDIO_FEATURES)
    dropped = before - len(df)
    if dropped:
        logger.warning("Dropped %d rows with missing audio features", dropped)

    return df


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate tracks (same artist + track_name, keep most popular)."""
    before = len(df)
    df = df.sort_values("popularity", ascending=False)
    df = df.drop_duplicates(subset=["artist", "track_name"], keep="first")
    dropped = before - len(df)
    if dropped:
        logger.info("Removed %d duplicate tracks", dropped)
    return df


def normalize_raw_features(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize loudness (dB) and tempo (BPM) to 0-1 range.

    Other audio features from the Kaggle set are already in [0, 1].
    Loudness is in dB (typically -60 to 0), tempo is in BPM (typically 0-250).
    """
    df = df.copy()

    # Loudness: dB to 0-1
    if "loudness" in df.columns:
        l_min, l_max = df["loudness"].min(), df["loudness"].max()
        if l_max - l_min > 0:
            df["loudness"] = (df["loudness"] - l_min) / (l_max - l_min)

    # Tempo: BPM to 0-1
    if "tempo" in df.columns:
        t_min, t_max = df["tempo"].min(), df["tempo"].max()
        if t_max - t_min > 0:
            df["tempo"] = (df["tempo"] - t_min) / (t_max - t_min)

    return df


def save_catalog(df: pd.DataFrame, path: str) -> None:
    """Select output columns and save to CSV."""
    # Only keep columns that exist
    cols = [c for c in OUTPUT_COLUMNS if c in df.columns]
    df = df[cols].reset_index(drop=True)
    df.to_csv(path, index=False)
    logger.info("Saved catalog with %d tracks to %s", len(df), path)


def main() -> None:
    """Entry point: parse args, run pipeline, log summary stats."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Prepare the Spotify tracks catalog")
    parser.add_argument(
        "--input",
        default=str(DATA_DIR / "spotify-tracks.csv"),
        help="Path to raw Spotify tracks CSV",
    )
    parser.add_argument(
        "--output",
        default=str(DATA_DIR / "catalog.csv"),
        help="Path for cleaned output CSV",
    )
    args = parser.parse_args()

    df = load_raw(args.input)
    df = clean(df)
    df = deduplicate(df)
    df = normalize_raw_features(df)
    save_catalog(df, args.output)

    print(f"\nDone. {len(df)} tracks saved to {args.output}")
    print(f"Unique artists: {df['artist'].nunique()}")
    print(f"Unique genres: {df['genre'].nunique()}")


if __name__ == "__main__":
    main()
