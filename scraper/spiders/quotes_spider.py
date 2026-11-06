"""Production-ready crawler for quotes.toscrape.com."""

from __future__ import annotations

from typing import Any, List, Optional, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from scraper.config import ScraperConfig
from scraper.models import QuoteItem, ScrapeResponse
from scraper.spiders.base import BaseSpider


class QuotesSpider(BaseSpider):
    """Spider for crawling quotes, authors, and tags across paginated pages."""

    name = "quotes"
    start_urls = ["https://quotes.toscrape.com/"]

    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config=config)

    def parse(self, response: ScrapeResponse, depth: int) -> Tuple[List[Any], List[str]]:
        soup = BeautifulSoup(response.html, "html.parser")
        quotes: List[QuoteItem] = []
        follow_links: List[str] = []

        # Extract quote blocks
        for quote_div in soup.select("div.quote"):
            text_el = quote_div.select_one("span.text")
            author_el = quote_div.select_one("small.author")
            author_link = quote_div.select_one("a[href*='/author/']")
            tag_els = quote_div.select("div.tags a.tag")

            if text_el and author_el:
                author_url = urljoin(response.url, author_link["href"]) if author_link else None
                tags = [t.get_text(strip=True) for t in tag_els]

                quotes.append(
                    QuoteItem(
                        text=text_el.get_text(strip=True).strip('“"”'),
                        author=author_el.get_text(strip=True),
                        tags=tags,
                        author_url=author_url,
                    )
                )

        # Pagination
        next_btn = soup.select_one("li.next a")
        if next_btn and next_btn.get("href"):
            follow_links.append(urljoin(response.url, next_btn["href"]))

        return quotes, follow_links

