"""Example: Writing a custom e-commerce product spider."""

import sys
from pathlib import Path
from typing import Any, List, Optional, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from pydantic import BaseModel

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.config import ScraperConfig
from scraper.models import ScrapeResponse
from scraper.pipelines.exporter import DataExporter
from scraper.spiders.base import BaseSpider


# 1. Define custom data schema
class CustomItem(BaseModel):
    title: str
    price: float
    stock_status: str
    page_url: str


# 2. Subclass BaseSpider
class BookCatalogSpider(BaseSpider):
    name = "custom_books"
    start_urls = ["https://books.toscrape.com/catalogue/category/books/travel_2/index.html"]

    def parse(self, response: ScrapeResponse, depth: int) -> Tuple[List[Any], List[str]]:
        soup = BeautifulSoup(response.html, "html.parser")
        items: List[CustomItem] = []
        follow_links: List[str] = []

        # Extract items
        for article in soup.select("article.product_pod"):
            title_tag = article.select_one("h3 a")
            price_tag = article.select_one("p.price_color")
            avail_tag = article.select_one("p.instock.availability")

            if title_tag and price_tag:
                title = title_tag.get("title") or title_tag.get_text(strip=True)
                raw_price = price_tag.get_text(strip=True).replace("£", "").replace("$", "")
                price = float(raw_price) if raw_price else 0.0
                availability = avail_tag.get_text(" ", strip=True) if avail_tag else "Unknown"

                items.append(
                    CustomItem(
                        title=title,
                        price=price,
                        stock_status=availability,
                        page_url=response.url,
                    )
                )

        # Pagination
        next_btn = soup.select_one("li.next a")
        if next_btn and next_btn.get("href"):
            follow_links.append(urljoin(response.url, next_btn["href"]))

        return items, follow_links


if __name__ == "__main__":
    config = ScraperConfig(max_pages=2, delay=0.2)
    spider = BookCatalogSpider(config=config)

    items, stats = spider.run()
    print(f"Scraped {len(items)} items from {stats.pages_crawled} pages.")
    DataExporter.export(items, "custom_travel_books.json")
    print("Saved to custom_travel_books.json")
