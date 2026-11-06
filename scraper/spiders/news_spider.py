"""Automated News & Article content extractor spider."""

from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from scraper.config import ScraperConfig
from scraper.models import ArticleItem, ScrapeResponse
from scraper.parsers.html_parser import HTMLParser
from scraper.spiders.base import BaseSpider


class NewsArticleSpider(BaseSpider):
    """Extracts news articles, blog posts, authors, dates, and clean content."""

    name = "news"

    def __init__(self, start_url: str, config: Optional[ScraperConfig] = None):
        super().__init__(config=config)
        self.start_urls = [start_url]

    def parse(self, response: ScrapeResponse, depth: int) -> Tuple[List[Any], List[str]]:
        parser = HTMLParser(html=response.html, base_url=response.url)
        page_data = parser.extract_page_data()
        soup = parser.soup

        # Extract title
        h1_tag = soup.find("h1")
        h1_text = h1_tag.get_text(" ", strip=True) if h1_tag else ""
        title = (
            page_data.metadata.open_graph.get("og:title")
            or page_data.title
            or h1_text
            or "Untitled Article"
        )

        # Extract author
        raw_author = (
            page_data.metadata.open_graph.get("article:author")
            or parser.extract_text(".author")
            or parser.extract_text("[rel='author']")
            or parser.extract_text(".byline")
            or None
        )
        if raw_author:
            author = re.sub(r"^by\s+", "", raw_author.strip(), flags=re.IGNORECASE).strip() or None
        else:
            author = None

        # Published date
        publish_date = (
            page_data.metadata.open_graph.get("article:published_time")
            or parser.extract_attr("time[datetime]", "datetime")
            or parser.extract_text("time")
            or None
        )

        # Summary
        summary = page_data.description or page_data.metadata.open_graph.get("og:description", "")

        # Article text
        article_el = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"content|post|article"))
        if article_el:
            clean_text = " ".join(article_el.stripped_strings)
        else:
            clean_text = page_data.text

        # Estimate reading time (average 200 words per minute)
        word_count = len(clean_text.split())
        reading_time = max(1, round(word_count / 200)) if word_count > 0 else 1

        article = ArticleItem(
            title=title or "Untitled Article",
            author=author,
            publish_date=publish_date,
            summary=summary,
            content=clean_text[:30000],
            reading_time_minutes=reading_time,
            url=response.url,
        )

        # Collect outgoing article links
        follow_links = [
            link.url for link in page_data.links
            if any(term in link.url.lower() for term in ["/article", "/post", "/news", "/blog", "-202"])
        ]

        return [article], follow_links
