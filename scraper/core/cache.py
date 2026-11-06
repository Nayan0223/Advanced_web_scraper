"""Asynchronous disk and memory cache for HTTP responses."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Optional
from scraper.models import ScrapeResponse


class ResponseCache:
    """Cache responses to local disk or memory to avoid redundant network hits."""

    def __init__(self, cache_dir: Path = Path(".cache"), ttl_seconds: int = 3600, enabled: bool = True):
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.enabled = enabled
        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _hash_url(self, url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def get(self, url: str) -> Optional[ScrapeResponse]:
        """Retrieve a cached response if valid and not expired."""
        if not self.enabled:
            return None

        file_path = self.cache_dir / f"{self._hash_url(url)}.json"
        if not file_path.exists():
            return None

        try:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
            cached_time = raw.get("_cached_at", 0)
            if time.time() - cached_time > self.ttl_seconds:
                file_path.unlink(missing_ok=True)
                return None

            return ScrapeResponse(
                url=raw["url"],
                status_code=raw["status_code"],
                headers=raw.get("headers", {}),
                html=raw.get("html", ""),
                execution_time_seconds=0.001,
                engine_name="cache",
            )
        except Exception:
            return None

    def set(self, response: ScrapeResponse) -> None:
        """Save a response into the cache."""
        if not self.enabled or not response.is_success:
            return

        file_path = self.cache_dir / f"{self._hash_url(response.url)}.json"
        try:
            data = {
                "url": response.url,
                "status_code": response.status_code,
                "headers": response.headers,
                "html": response.html,
                "_cached_at": time.time(),
            }
            file_path.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass

    def clear(self) -> None:
        """Clear all cache files."""
        if self.cache_dir.exists():
            for f in self.cache_dir.glob("*.json"):
                f.unlink(missing_ok=True)

