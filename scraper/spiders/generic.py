"""Generic domain / website crawler extracting comprehensive page structures."""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from scraper.config import ScraperConfig
from scraper.models import PageData, ScrapeResponse
from scraper.parsers.html_parser import HTMLParser
from scraper.spiders.base import BaseSpider


class GenericSpider(BaseSpider):
    """General crawler that extracts titles, headings, metadata, body text, and links."""

    name = "generic"

    def __init__(self, start_url: str, config: Optional[ScraperConfig] = None):
        super().__init__(config=config)
        self.start_urls = [start_url]

    def parse(self, response: ScrapeResponse, depth: int) -> Tuple[List[Any], List[str]]:
        parser = HTMLParser(html=response.html, base_url=response.url)
        page_data: PageData = parser.extract_page_data()
        page_data.timing_ms = round(response.execution_time_seconds * 1000, 2)
        page_data.status_code = response.status_code

        # Extract links to follow
        outgoing_urls = [link.url for link in page_data.links]

        return [page_data], outgoing_urls

