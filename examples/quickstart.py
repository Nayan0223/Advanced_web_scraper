"""Quickstart guide for using the Advanced Web Scraper framework in Python."""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.config import ScraperConfig
from scraper.pipelines.exporter import DataExporter
from scraper.spiders.quotes_spider import QuotesSpider


def main():
    # 1. Configure the scraper
    config = ScraperConfig(
        engine="http",        # Use "browser" for JavaScript-rendered SPAs
        max_pages=2,          # Number of pages to crawl
        concurrency=3,        # Concurrent asynchronous workers
        delay=0.3,            # Politeness delay between requests
        cache_enabled=True,   # Cache HTML responses locally
    )

    # 2. Instantiate spider
    spider = QuotesSpider(config=config)

    print("Starting crawler...")
    items, stats = spider.run()

    print(f"\nCrawling complete in {stats.duration_seconds}s!")
    print(f"Total quotes extracted: {len(items)}")

    # 3. Export to JSON & CSV
    output_json = Path("quotes_result.json")
    output_csv = Path("quotes_result.csv")

    DataExporter.export(items, output_json, file_format="json")
    DataExporter.export(items, output_csv, file_format="csv")

    print(f"Exported data to {output_json} and {output_csv}")

    # Preview first item
    if items:
        first = items[0]
        print(f"\nSample Quote:\n\"{first.text}\" — {first.author} (Tags: {', '.join(first.tags)})")


if __name__ == "__main__":
    main()
