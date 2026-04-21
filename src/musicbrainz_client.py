"""MusicBrainz API client with caching and rate limiting.

Fetches artist member lists and their instruments so the similarity
engine can compare band compositions, not just audio features.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import requests

from src.config import DATA_DIR

logger = logging.getLogger(__name__)

MUSICBRAINZ_BASE_URL = "https://musicbrainz.org/ws/2"
MUSICBRAINZ_CACHE_DIR = DATA_DIR / "musicbrainz_cache"
MUSICBRAINZ_RATE_LIMIT_SECONDS = 1.0  # required by MusicBrainz ToS

# Attributes returned by artist-rels that are roles/statuses, not instruments.
NON_INSTRUMENT_ATTRS = {
    "original", "founder", "current", "additional", "member",
    "guest", "session", "ghost writer", "eponymous", "honorary",
    "co-founder",
}


class MusicBrainzClient:
    """Client for the MusicBrainz API with local JSON caching."""

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        rate_limit: float = MUSICBRAINZ_RATE_LIMIT_SECONDS,
        user_agent: str = "MusicDiscoveryEngine/1.0 (ai110-final)",
    ):
        self.cache_dir = Path(cache_dir) if cache_dir else MUSICBRAINZ_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit = rate_limit
        self._last_request_time: float = 0.0
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": user_agent})

    def _cache_key(self, method: str, identifier: str) -> str:
        safe = identifier.lower().replace(" ", "_").replace("/", "_")
        return f"{method}_{safe}"

    def _get_cached(self, cache_key: str) -> dict[str, Any] | None:
        path = self.cache_dir / f"{cache_key}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None

    def _save_cache(self, cache_key: str, data: dict[str, Any]) -> None:
        path = self.cache_dir / f"{cache_key}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _request(self, path: str, params: dict[str, str]) -> dict[str, Any] | None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        params = {**params, "fmt": "json"}
        url = f"{MUSICBRAINZ_BASE_URL}/{path}"
        try:
            logger.info("MusicBrainz call: %s", path)
            resp = self._session.get(url, params=params, timeout=10)
            self._last_request_time = time.time()
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.warning("MusicBrainz request failed (%s): %s", path, e)
            return None

    def search_artist(self, name: str) -> str | None:
        """Return the MBID for the top search hit, or None."""
        cache_key = self._cache_key("artist_search", name)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached.get("mbid")
        data = self._request("artist", {"query": f'artist:"{name}"', "limit": "1"})
        if not data:
            return None
        artists = data.get("artists", [])
        mbid = artists[0]["id"] if artists else None
        self._save_cache(cache_key, {"name": name, "mbid": mbid})
        return mbid

    def get_artist_instruments(self, name: str) -> list[str]:
        """Return the instruments played by members of the given artist.

        Returns an empty list when the artist isn't found or has no
        structured member data (common for solo pop/hip-hop artists).
        """
        cache_key = self._cache_key("artist_instruments", name)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached.get("instruments", [])

        mbid = self.search_artist(name)
        if not mbid:
            self._save_cache(cache_key, {"name": name, "instruments": []})
            return []

        data = self._request(f"artist/{mbid}", {"inc": "artist-rels"})
        if not data:
            return []

        raw_attrs: list[str] = []
        for rel in data.get("relations", []):
            if "member" in rel.get("type", "").lower():
                raw_attrs.extend(rel.get("attributes", []))

        instruments = sorted({
            a.lower()
            for a in raw_attrs
            if a.lower() not in NON_INSTRUMENT_ATTRS
        })

        self._save_cache(cache_key, {
            "name": name,
            "mbid": mbid,
            "instruments": instruments,
        })
        return instruments
