"""Last.fm API client with caching and rate limiting.

Fetches artist tags, similar artists, and track tags.
Caches responses as JSON files to avoid redundant API calls.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

import requests

# macOS / common filesystem filename limit is 255 chars. Some tracks
# in the catalog credit dozens of collaborators, which blows past
# that limit when concatenated with the track name. Hash anything
# longer to keep filenames safe; the prefix stays human-readable.
MAX_CACHE_KEY_LEN = 200

from src.config import (
    get_lastfm_api_key,
    LASTFM_BASE_URL,
    LASTFM_CACHE_DIR,
    LASTFM_RATE_LIMIT_SECONDS,
)

logger = logging.getLogger(__name__)


class LastFmClient:
    """Client for the Last.fm API with local JSON caching."""

    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: Path | str | None = None,
        rate_limit: float = LASTFM_RATE_LIMIT_SECONDS,
    ):
        """Initialize the client.

        Args:
            api_key: Last.fm API key. If None, reads from config.
            cache_dir: Directory for cached JSON responses.
            rate_limit: Minimum seconds between API requests.
        """
        self.api_key = api_key or get_lastfm_api_key()
        self.cache_dir = Path(cache_dir) if cache_dir else LASTFM_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit = rate_limit
        self._last_request_time: float = 0.0
        self._session = requests.Session()

    def _make_request(self, params: dict[str, str]) -> dict[str, Any] | None:
        """Make a rate-limited request to the Last.fm API.

        Args:
            params: Query parameters (method, artist, etc.).

        Returns:
            Parsed JSON response dict, or None on error.
        """
        # Rate limiting
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)

        params.update({
            "api_key": self.api_key,
            "format": "json",
        })

        try:
            logger.info("Last.fm API call: %s", params.get("method", "?"))
            response = self._session.get(LASTFM_BASE_URL, params=params, timeout=10)
            self._last_request_time = time.time()
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                logger.warning("Last.fm API error: %s", data.get("message", "unknown"))
                return None

            return data

        except requests.RequestException as e:
            logger.warning("Last.fm request failed: %s", e)
            return None

    def _cache_key(self, method: str, identifier: str) -> str:
        """Generate a filesystem-safe cache key.

        Short identifiers keep their human-readable form (preserves
        prior cache hits). Long ones (huge collab strings) get a
        readable prefix plus a stable SHA1 suffix so the filename
        stays under filesystem limits.
        """
        safe_id = identifier.lower().replace(" ", "_").replace("/", "_")
        if len(safe_id) > MAX_CACHE_KEY_LEN:
            digest = hashlib.sha1(safe_id.encode("utf-8")).hexdigest()[:16]
            safe_id = f"{safe_id[:80]}__{digest}"
        return f"{method}_{safe_id}"

    def _get_cached(self, cache_key: str) -> dict[str, Any] | None:
        """Load a cached response if it exists."""
        path = self.cache_dir / f"{cache_key}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None

    def _save_cache(self, cache_key: str, data: dict[str, Any]) -> None:
        """Save a response to the cache."""
        path = self.cache_dir / f"{cache_key}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def get_artist_tags(self, artist: str) -> list[str]:
        """Fetch top tags for an artist.

        Args:
            artist: Artist name.

        Returns:
            List of tag strings (e.g., ["blues rock", "guitar-driven"]),
            or empty list on error.
        """
        cache_key = self._cache_key("artist_tags", artist)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached.get("tags", [])

        data = self._make_request({
            "method": "artist.getTopTags",
            "artist": artist,
        })

        if not data:
            return []

        tags = []
        try:
            for tag in data["toptags"]["tag"]:
                tags.append(tag["name"].lower())
        except (KeyError, TypeError):
            logger.warning("Could not parse tags for artist '%s'", artist)

        self._save_cache(cache_key, {"artist": artist, "tags": tags})
        return tags

    def get_similar_artists(self, artist: str, limit: int = 20) -> list[dict]:
        """Fetch similar artists from Last.fm.

        Args:
            artist: Artist name.
            limit: Max number of similar artists to return.

        Returns:
            List of dicts with keys: name, match (similarity float).
            Empty list on error.
        """
        cache_key = self._cache_key("similar_artists", artist)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached.get("similar", [])[:limit]

        data = self._make_request({
            "method": "artist.getSimilar",
            "artist": artist,
            "limit": str(limit),
        })

        if not data:
            return []

        similar = []
        try:
            for entry in data["similarartists"]["artist"]:
                similar.append({
                    "name": entry["name"],
                    "match": float(entry.get("match", 0)),
                })
        except (KeyError, TypeError):
            logger.warning("Could not parse similar artists for '%s'", artist)

        self._save_cache(cache_key, {"artist": artist, "similar": similar})
        return similar[:limit]

    def get_track_tags(self, artist: str, track: str) -> list[str]:
        """Fetch top tags for a specific track.

        Args:
            artist: Artist name.
            track: Track name.

        Returns:
            List of tag strings, or empty list on error.
        """
        cache_key = self._cache_key("track_tags", f"{artist}_{track}")
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached.get("tags", [])

        data = self._make_request({
            "method": "track.getTopTags",
            "artist": artist,
            "track": track,
        })

        if not data:
            return []

        tags = []
        try:
            for tag in data["toptags"]["tag"]:
                tags.append(tag["name"].lower())
        except (KeyError, TypeError):
            logger.warning("Could not parse tags for track '%s' by '%s'", track, artist)

        self._save_cache(cache_key, {"artist": artist, "track": track, "tags": tags})
        return tags

    def get_artist_info(self, artist: str) -> dict[str, Any] | None:
        """Fetch artist bio and stats.

        Args:
            artist: Artist name.

        Returns:
            Dict with keys: name, bio, listeners, playcount, tags.
            None on error.
        """
        cache_key = self._cache_key("artist_info", artist)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        data = self._make_request({
            "method": "artist.getInfo",
            "artist": artist,
        })

        if not data:
            return None

        try:
            info = data["artist"]
            result = {
                "name": info["name"],
                "bio": info.get("bio", {}).get("summary", ""),
                "listeners": int(info.get("stats", {}).get("listeners", 0)),
                "playcount": int(info.get("stats", {}).get("playcount", 0)),
                "tags": [t["name"] for t in info.get("tags", {}).get("tag", [])],
            }
            self._save_cache(cache_key, result)
            return result
        except (KeyError, TypeError):
            logger.warning("Could not parse info for artist '%s'", artist)
            return None
