"""Embed each cached artist's text doc with Vertex AI text-embedding.

Usage:
    python -m scripts.enrich_with_embeddings [--limit 500]

For every artist that has Last.fm tag or similar-artist data, builds a
short text doc and embeds it. Writes a single .npz cache containing
the L2-normalised matrix and a parallel array of artist names.

Resumable: artists already in the cache are skipped. Re-run after
fetching more Last.fm data to top up.
"""

from __future__ import annotations

import argparse
import logging

import numpy as np

from src.config import EMBEDDING_CACHE_PATH, LASTFM_CACHE_DIR
from src.embeddings import (
    EMBEDDING_BATCH_SIZE,
    EmbeddingClient,
    build_artist_doc,
    load_embedding_cache,
    save_embedding_cache,
)
from src.enrichment import load_similar_artist_cache, load_tag_cache

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Embed cached artists with Vertex AI text-embedding"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of NEW artists to embed (default: all uncached)",
    )
    parser.add_argument(
        "--cache-path",
        default=str(EMBEDDING_CACHE_PATH),
        help="Path to the embedding .npz cache",
    )
    args = parser.parse_args()

    # Load Last.fm caches (the source material for each doc)
    tag_data = load_tag_cache(LASTFM_CACHE_DIR)
    similar_data = load_similar_artist_cache(LASTFM_CACHE_DIR)

    # Union of artists with any data
    artists = sorted(set(tag_data.keys()) | set(similar_data.keys()))
    logger.info("Found %d artists with Last.fm data", len(artists))

    # Load existing embedding cache to skip already-embedded artists
    cache_path = args.cache_path
    from pathlib import Path
    cache_path = Path(cache_path)
    existing = load_embedding_cache(cache_path)
    if existing is not None:
        existing_matrix, existing_index = existing
        cached_artists = list(existing_index.keys())
    else:
        existing_matrix = np.zeros((0, 0), dtype=np.float32)
        existing_index = {}
        cached_artists = []

    new_artists = [a for a in artists if a not in existing_index]
    if args.limit:
        new_artists = new_artists[: args.limit]
    logger.info(
        "Already cached: %d, new to embed: %d",
        len(cached_artists), len(new_artists),
    )
    if not new_artists:
        print("Nothing to do.")
        return

    client = EmbeddingClient()

    new_matrix_rows: list[np.ndarray] = []
    new_names: list[str] = []
    for i in range(0, len(new_artists), EMBEDDING_BATCH_SIZE):
        batch_artists = new_artists[i : i + EMBEDDING_BATCH_SIZE]
        docs = []
        for a in batch_artists:
            # similar_data is dict[str, dict[name, match_score]] now;
            # sort by score desc so the strongest edges land in the doc.
            sim_map = similar_data.get(a, {})
            similar_names = [
                name for name, _ in sorted(
                    sim_map.items(), key=lambda kv: -kv[1]
                )
            ]
            docs.append(
                build_artist_doc(
                    artist=a,
                    tags=tag_data.get(a, []),
                    similar_artists=similar_names,
                )
            )
        try:
            batch_matrix = client.embed_batch(docs)
        except Exception as e:
            logger.error("Batch %d failed: %s", i // EMBEDDING_BATCH_SIZE, e)
            continue
        new_matrix_rows.append(batch_matrix)
        new_names.extend(batch_artists)
        logger.info(
            "Batch %d: embedded %d artists (cumulative new: %d / %d)",
            i // EMBEDDING_BATCH_SIZE + 1,
            len(batch_artists),
            len(new_names),
            len(new_artists),
        )

        # Save after each batch so the run is resumable
        all_artists = cached_artists + new_names
        if existing_matrix.size:
            all_matrix = np.vstack([existing_matrix] + new_matrix_rows)
        else:
            all_matrix = np.vstack(new_matrix_rows)
        save_embedding_cache(cache_path, all_artists, all_matrix)

    print(f"\nDone. Cache now holds {len(cached_artists) + len(new_names)} artist embeddings.")


if __name__ == "__main__":
    main()
