"""Production-ready crawler for books.toscrape.com catalog."""

from __future__ import annotations

from typing import Any, List, Optional, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from scraper.config import ScraperConfig
from scraper.models import ProductItem, ScrapeResponse
from scraper.spiders.base import BaseSpider

RATING_MAP = {
    "One": 1.0,
    "Two": 2.0,
    "Three": 3.0,
    "Four": 4.0,
    "Five": 5.0,
}


class BooksSpider(BaseSpider):
    """Scrapes book catalog items including titles, prices, ratings, and stock."""

    name = "books"
    start_urls = ["https://books.toscrape.com/"]

    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config=config)

    def parse(self, response: ScrapeResponse, depth: int) -> Tuple[List[Any], List[str]]:
        soup = BeautifulSoup(response.html, "html.parser")
        products: List[ProductItem] = []
        follow_links: List[str] = []

        for article in soup.select("article.product_pod"):
            title_tag = article.select_one("h3 a")
            price_tag = article.select_one("p.price_color")
            avail_tag = article.select_one("p.instock.availability")
            rating_tag = article.select_one("p.star-rating")
            img_tag = article.select_one("div.image_container img")

            if title_tag:
                title = title_tag.get("title") or title_tag.get_text(strip=True)
                product_url = urljoin(response.url, title_tag.get("href", ""))
                price_str = price_tag.get_text(strip=True) if price_tag else None
                availability = avail_tag.get_text(" ", strip=True) if avail_tag else "Unknown"

                # Parse rating
                rating = None
                if rating_tag:
                    for cls in rating_tag.get("class", []):
                        if cls in RATING_MAP:
                            rating = RATING_MAP[cls]
                            break

                img_url = urljoin(response.url, img_tag.get("src", "")) if img_tag else None

                products.append(
                    ProductItem(
                        title=title,
                        price=price_str,  # parsed by pydantic validator
                        currency="GBP",
                        availability=availability,
                        rating=rating,
                        image_url=img_url,
                        url=product_url,
                    )
                )

        # Pagination
        next_page = soup.select_one("li.next a")
        if next_page and next_page.get("href"):
            follow_links.append(urljoin(response.url, next_page["href"]))

        return products, follow_links

