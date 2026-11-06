"""Base Spider abstraction for modular scrapers."""

from __future__ import annotations

import abc
import asyncio
from typing import Any, List, Optional, Tuple

from scraper.config import ScraperConfig
from scraper.core.crawler import AsyncCrawler
from scraper.core.engine import BaseEngine, get_engine
from scraper.models import CrawlStats, ScrapeResponse
from scraper.pipelines.validator import ItemPipeline


class BaseSpider(abc.ABC):
    """Abstract Base Class for website-specific spiders."""

    name: str = "base"
    start_urls: List[str] = []

    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self.pipeline = ItemPipeline()

    @abc.abstractmethod
    def parse(self, response: ScrapeResponse, depth: int) -> Tuple[List[Any], List[str]]:
        """Parse response and return a tuple of (extracted_items, follow_links)."""
        raise NotImplementedError

    async def run_async(self, engine: Optional[BaseEngine] = None) -> Tuple[List[Any], CrawlStats]:
        """Execute the spider asynchronously."""
        crawler = AsyncCrawler(config=self.config, engine=engine)
        items, stats = await crawler.crawl(
            seeds=self.start_urls,
            page_handler=self.parse,
        )
        validated_items = self.pipeline.process_items(items)
        stats.items_extracted = len(validated_items)
        return validated_items, stats

    def run(self, engine: Optional[BaseEngine] = None) -> Tuple[List[Any], CrawlStats]:
        """Synchronous wrapper for running the spider."""
        return asyncio.run(self.run_async(engine=engine))

