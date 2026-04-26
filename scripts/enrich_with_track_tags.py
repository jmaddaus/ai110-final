"""Batch fetch Last.fm track-level tags, prioritised by popularity.

Where artist tags describe the band's overall character, track tags
describe a specific song. A Led Zeppelin track called "Black Dog" gets
tags like 'guitar riff', 'hard rock', 'loud'; "Stairway to Heaven"
gets 'ballad', 'epic', 'acoustic'. This is the per-song signal the
similarity engine has been missing.

Usage:
    python -m scripts.enrich_with_track_tags [--limit 10000] [--min-popularity 0]

Resumable: anything already in the Last.fm cache is skipped.
"""

from __future__ import annotations

import argparse
import logging
import time

import pandas as pd

from src.config import CATALOG_PATH, LASTFM_CACHE_DIR
from src.data_loader import load_catalog
from src.lastfm_client import LastFmClient

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Fetch Last.fm track-level tags ordered by popularity"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10000,
        help="Max number of NEW tracks to fetch this run (default: 10000)",
    )
    parser.add_argument(
        "--min-popularity",
        type=int,
        default=0,
        help="Skip tracks below this popularity threshold",
    )
    parser.add_argument(
        "--catalog",
        default=str(CATALOG_PATH),
        help="Path to catalog CSV",
    )
    args = parser.parse_args()

    logger.info("Loading catalog from %s", args.catalog)
    df = load_catalog(args.catalog)
    logger.info("Catalog has %d tracks", len(df))

    # Order by popularity desc so the seeds people are most likely to
    # search for get tagged first.
    df_sorted = df[df["popularity"] >= args.min_popularity].sort_values(
        "popularity", ascending=False
    )
    logger.info(
        "Queue has %d tracks (popularity >= %d)",
        len(df_sorted), args.min_popularity,
    )

    client = LastFmClient()
    logger.info("Cache directory: %s", LASTFM_CACHE_DIR)

    fetched = 0
    skipped = 0
    not_found = 0
    errors = 0
    start = time.time()

    for _, row in df_sorted.iterrows():
        if fetched >= args.limit:
            break

        artist = str(row["artist"])
        track = str(row["track_name"])
        popularity = int(row["popularity"])

        # Cheap pre-check: if the cache key already exists, skip.
        cache_key = client._cache_key("track_tags", f"{artist}_{track}")
        if (LASTFM_CACHE_DIR / f"{cache_key}.json").exists():
            skipped += 1
            continue

        try:
            tags = client.get_track_tags(artist, track)
            if tags:
                fetched += 1
            else:
                not_found += 1
                fetched += 1  # still counts toward --limit
        except Exception as e:
            logger.error(
                "Error fetching '%s' / '%s': %s", artist, track, e,
            )
            errors += 1

        if fetched > 0 and fetched % 100 == 0:
            elapsed = time.time() - start
            rate = fetched / elapsed if elapsed > 0 else 0
            remaining = args.limit - fetched
            eta_min = (remaining / rate / 60) if rate > 0 else 0
            logger.info(
                "Progress: %d / %d new (%.2f/s, %.1f min remaining). "
                "Latest: '%s' by %s (pop=%d).",
                fetched, args.limit, rate, eta_min, track, artist, popularity,
            )

    elapsed = (time.time() - start) / 60
    print(f"\nDone.")
    print(f"  Newly fetched:  {fetched}")
    print(f"  Already cached: {skipped}")
    print(f"  Not found:      {not_found}")
    print(f"  Errors:         {errors}")
    print(f"  Elapsed:        {elapsed:.1f} min")


if __name__ == "__main__":
    main()
