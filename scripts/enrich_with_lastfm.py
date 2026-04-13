"""Batch fetch Last.fm tags and similar artists for the catalog.

Usage:
    python -m scripts.enrich_with_lastfm [--limit 1000] [--artists-only]

This script is resumable: it skips artists already in the cache.
Respects Last.fm rate limits (1 request/second).
"""

from __future__ import annotations

import argparse
import logging
import sys

from src.config import CATALOG_PATH, LASTFM_CACHE_DIR
from src.data_loader import load_catalog, get_unique_artists
from src.lastfm_client import LastFmClient

logger = logging.getLogger(__name__)


def enrich_artists(
    artists: list[str],
    client: LastFmClient,
    limit: int | None = None,
) -> dict[str, int]:
    """Fetch tags and similar artists for a list of artists.

    Args:
        artists: List of artist names to enrich.
        client: Initialized LastFmClient (handles caching internally).
        limit: Max number of artists to process (None = all).

    Returns:
        Dict with counts: fetched, skipped (already cached), errors.
    """
    if limit:
        artists = artists[:limit]

    stats = {"fetched": 0, "skipped": 0, "errors": 0}
    total = len(artists)

    for i, artist in enumerate(artists, 1):
        logger.info("[%d/%d] Processing: %s", i, total, artist)

        try:
            # get_artist_tags and get_similar_artists handle caching internally
            # If already cached, no API call is made
            tags = client.get_artist_tags(artist)
            similar = client.get_similar_artists(artist)

            if tags or similar:
                stats["fetched"] += 1
            else:
                stats["skipped"] += 1

        except Exception as e:
            logger.error("Error processing '%s': %s", artist, e)
            stats["errors"] += 1

    return stats


def main() -> None:
    """Entry point: parse args, load catalog, run enrichment."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Fetch Last.fm tags and similar artists for catalog artists"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of artists to process (default: all)",
    )
    parser.add_argument(
        "--catalog",
        default=str(CATALOG_PATH),
        help="Path to catalog CSV",
    )
    args = parser.parse_args()

    # Load catalog and get unique artists
    logger.info("Loading catalog from %s", args.catalog)
    df = load_catalog(args.catalog)
    artists = get_unique_artists(df)
    logger.info("Found %d unique artists", len(artists))

    # Initialize client
    client = LastFmClient()
    logger.info("Cache directory: %s", LASTFM_CACHE_DIR)

    # Run enrichment
    stats = enrich_artists(artists, client, limit=args.limit)

    print(f"\nDone.")
    print(f"  Fetched: {stats['fetched']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Errors:  {stats['errors']}")


if __name__ == "__main__":
    main()
