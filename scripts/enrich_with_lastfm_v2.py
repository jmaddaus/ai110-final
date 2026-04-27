"""Batch fetch Last.fm tags and similar artists, prioritised by catalog impact.

Improvements over enrich_with_lastfm.py:
    1. Splits collab strings ('A;B;C') into individual artist parts and
       de-dupes, so we don't waste calls on combined strings the
       Last.fm API can't resolve.
    2. Orders the fetch queue by track count in the catalog, so high
       value artists (eg George Jones, 273 tracks) get fetched first.
       Useful when we cap runtime before reaching full coverage.
    3. Optional --min-tracks filter to skip the long tail entirely.
    4. Reports running coverage and ETA.

Resumable: anything already in the Last.fm cache is skipped automatically
(LastFmClient checks the cache file before making the request).
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


def build_priority_queue(
    df: pd.DataFrame,
    min_tracks: int = 1,
) -> list[tuple[str, int]]:
    """Return [(artist_part_lower, track_count)] sorted by track count desc.

    Splits each row's artist string on ';' and counts how many catalog
    rows reference each individual part. Track count is the right
    ranking signal because that is what ultimately drives how often an
    artist appears as a candidate at query time.
    """
    weights: dict[str, int] = {}
    for artist_string in df["artist"].dropna():
        seen_in_row: set[str] = set()
        for part in str(artist_string).split(";"):
            part = part.strip()
            if not part or part in seen_in_row:
                continue
            seen_in_row.add(part)
            weights[part] = weights.get(part, 0) + 1
    items = [(name, n) for name, n in weights.items() if n >= min_tracks]
    items.sort(key=lambda x: -x[1])
    return items


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Fetch Last.fm tags and similar artists, prioritised by catalog impact"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of NEW artists to fetch this run (default: all uncached)",
    )
    parser.add_argument(
        "--min-tracks",
        type=int,
        default=1,
        help="Skip artists that appear on fewer than this many catalog tracks",
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

    queue = build_priority_queue(df, min_tracks=args.min_tracks)
    logger.info(
        "Built priority queue: %d unique artist parts (>= %d tracks each)",
        len(queue), args.min_tracks,
    )

    client = LastFmClient()
    logger.info("Cache directory: %s", LASTFM_CACHE_DIR)

    fetched = 0
    skipped = 0
    not_found = 0
    errors = 0
    start = time.time()

    target = args.limit if args.limit else len(queue)

    for i, (artist, n_tracks) in enumerate(queue, 1):
        # Cheap pre-check: if the cache key already exists, skip without
        # constructing a request. The client also caches internally,
        # but explicit-skip lets us count progress correctly.
        tag_key = client._cache_key("artist_tags", artist)
        sim_key = client._cache_key("similar_artists", artist)
        already_cached = (
            (LASTFM_CACHE_DIR / f"{tag_key}.json").exists()
            and (LASTFM_CACHE_DIR / f"{sim_key}.json").exists()
        )
        if already_cached:
            skipped += 1
            continue

        if fetched >= target:
            break

        try:
            tags = client.get_artist_tags(artist)
            similar = client.get_similar_artists(artist)
            if tags or similar:
                fetched += 1
            else:
                not_found += 1
                fetched += 1  # still counts toward --limit
        except Exception as e:
            logger.error("Error processing '%s': %s", artist, e)
            errors += 1

        if fetched % 50 == 0 and fetched > 0:
            elapsed = time.time() - start
            rate = fetched / elapsed if elapsed > 0 else 0
            remaining = target - fetched
            eta_min = (remaining / rate / 60) if rate > 0 else 0
            logger.info(
                "Progress: %d / %d new (%.2f/s, %.1f min remaining). "
                "Latest: '%s' (%d tracks).",
                fetched, target, rate, eta_min, artist, n_tracks,
            )

    print(f"\nDone.")
    print(f"  Newly fetched:  {fetched}")
    print(f"  Already cached: {skipped}")
    print(f"  Not found:      {not_found}")
    print(f"  Errors:         {errors}")
    print(f"  Elapsed:        {(time.time() - start) / 60:.1f} min")


if __name__ == "__main__":
    main()
