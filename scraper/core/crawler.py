"""Asynchronous URL Frontier Crawler with concurrency, depth control, and politeness."""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urldefrag, urljoin, urlparse
import urllib.robotparser

from scraper.config import ScraperConfig
from scraper.core.cache import ResponseCache
from scraper.core.engine import BaseEngine, get_engine
from scraper.core.rate_limiter import AsyncRateLimiter
from scraper.models import CrawlStats, ScrapeResponse


class AsyncCrawler:
    """Asynchronous BFS crawler managing frontier queues, politeness, and concurrency."""

    def __init__(
        self,
        config: ScraperConfig,
        engine: Optional[BaseEngine] = None,
        on_progress: Optional[Callable[[str, int, int], None]] = None,
    ):
        self.config = config
        self.engine = engine or get_engine(config)
        self.rate_limiter = AsyncRateLimiter(delay_seconds=config.delay)
        self.cache = ResponseCache(
            cache_dir=config.cache_dir,
            ttl_seconds=config.cache_ttl_seconds,
            enabled=config.cache_enabled,
        )
        self.on_progress = on_progress

        self._semaphore = asyncio.Semaphore(config.concurrency)
        self._visited: Set[str] = set()
        self._queued: Set[str] = set()
        self._robots_cache: Dict[str, urllib.robotparser.RobotFileParser] = {}
        self.stats = CrawlStats()

    @staticmethod
    def normalize_url(url: str, base_url: Optional[str] = None) -> Optional[str]:
        """Normalize, strip fragment, and validate URL."""
        try:
            if base_url:
                url = urljoin(base_url, url)
            clean, _ = urldefrag(url.strip())
            parsed = urlparse(clean)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                return clean
            return None
        except Exception:
            return None

    def _is_allowed_domain(self, target_url: str, start_domains: Set[str]) -> bool:
        if self.config.follow_external_links:
            return True

        domain = urlparse(target_url).netloc.lower()
        if self.config.allowed_domains:
            return any(domain == d.lower() or domain.endswith("." + d.lower()) for d in self.config.allowed_domains)

        return any(domain == d or domain.endswith("." + d) for d in start_domains)

    def _is_allowed_by_robots(self, url: str) -> bool:
        if not self.config.respect_robots_txt:
            return True

        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base not in self._robots_cache:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{base}/robots.txt")
            try:
                rp.read()
            except Exception:
                pass
            self._robots_cache[base] = rp

        return self._robots_cache[base].can_fetch("*", url)

    async def fetch_url(self, url: str) -> ScrapeResponse:
        """Fetch a single URL respecting rate limits, caching, and semaphore."""
        # Check cache first
        cached = self.cache.get(url)
        if cached:
            return cached

        # Check robots.txt
        if not self._is_allowed_by_robots(url):
            return ScrapeResponse(
                url=url,
                status_code=403,
                html="",
                engine_name="robots_txt",
                error="Disallowed by robots.txt",
            )

        # Apply rate limiting
        await self.rate_limiter.wait_for(url)

        async with self._semaphore:
            response = await self.engine.fetch(url)

        if response.is_success:
            self.cache.set(response)

        return response

    async def crawl(
        self,
        seeds: List[str],
        page_handler: Callable[[ScrapeResponse, int], Tuple[List[Any], List[str]]],
    ) -> Tuple[List[Any], CrawlStats]:
        """Execute crawl starting from seeds using a page processing callback.

        page_handler receives (response, depth) and returns (extracted_items, discovered_links).
        """
        start_time = time.monotonic()
        self.stats.start_time = datetime.now(timezone.utc)

        start_domains: Set[str] = set()
        queue: deque[Tuple[str, int]] = deque()

        for seed in seeds:
            clean = self.normalize_url(seed)
            if clean:
                domain = urlparse(clean).netloc.lower()
                start_domains.add(domain)
                queue.append((clean, 0))
                self._queued.add(clean)

        extracted_all: List[Any] = []

        try:
            while queue and len(self._visited) < self.config.max_pages:
                current_url, depth = queue.popleft()
                if current_url in self._visited:
                    continue

                self._visited.add(current_url)

                response = await self.fetch_url(current_url)

                if response.is_success:
                    self.stats.pages_crawled += 1
                    self.stats.total_bytes += len(response.html.encode("utf-8"))

                    items, links = page_handler(response, depth)
                    extracted_all.extend(items)
                    self.stats.items_extracted += len(items)

                    if self.on_progress:
                        self.on_progress(current_url, self.stats.pages_crawled, self.config.max_pages)

                    # Enqueue discovered links if within depth limit
                    if depth < self.config.max_depth:
                        for raw_link in links:
                            link = self.normalize_url(raw_link, base_url=current_url)
                            if (
                                link
                                and link not in self._visited
                                and link not in self._queued
                                and self._is_allowed_domain(link, start_domains)
                            ):
                                self._queued.add(link)
                                queue.append((link, depth + 1))
                else:
                    self.stats.pages_failed += 1

        finally:
            await self.engine.close()

        self.stats.duration_seconds = round(time.monotonic() - start_time, 2)
        return extracted_all, self.stats
