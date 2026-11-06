from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.config import ScraperConfig
from scraper.pipelines.exporter import DataExporter
from scraper.spiders.quotes_spider import QuotesSpider


def main():
    config = ScraperConfig(
        engine="http",
        max_pages=2,
        concurrency=3,
        delay=0.3,
        cache_enabled=True,
    )

    spider = QuotesSpider(config=config)

    print("Starting crawler...")
    items, stats = spider.run()

    print(f"\nCrawling complete in {stats.duration_seconds}s!")
    print(f"Total quotes extracted: {len(items)}")

    output_json = Path("quotes_result.json")
    output_csv = Path("quotes_result.csv")

    DataExporter.export(items, output_json, file_format="json")
    DataExporter.export(items, output_csv, file_format="csv")

    print(f"Exported data to {output_json} and {output_csv}")

    if items:
        first = items[0]
        print(f"\nSample Quote:\n\"{first.text}\" - {first.author} (Tags: {', '.join(first.tags)})")


if __name__ == "__main__":
    main()
