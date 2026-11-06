"""Advanced Web Scraper entrypoint supporting both modern Typer CLI and legacy execution."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

from scraper.cli import app as cli_app
from scraper.config import ScraperConfig
from scraper.core.engine import get_engine
from scraper.pipelines.exporter import DataExporter
from scraper.spiders.generic import GenericSpider


def run_legacy(args: list[str]) -> int:
    """Fallback handler preserving compatibility with original single-file CLI arguments."""
    parser = argparse.ArgumentParser(
        description="High-performance web crawler and data extractor."
    )
    parser.add_argument("url", nargs="?", default="https://quotes.toscrape.com/", help="Starting URL or seed page")
    parser.add_argument("-o", "--output", type=Path, default=Path("scraped_data.json"), help="Output file path")
    parser.add_argument("-f", "--format", choices=("json", "jsonl", "csv", "sqlite"), help="Export format")
    parser.add_argument("-p", "--pages", type=int, default=1, help="Max pages to crawl")
    parser.add_argument("-d", "--depth", type=int, default=2, help="Max crawl depth")
    parser.add_argument("-c", "--concurrency", type=int, default=3, help="Concurrent request limit")
    parser.add_argument("--delay", type=float, default=0.5, help="Politeness delay in seconds")
    parser.add_argument("--timeout", type=float, default=20.0, help="Request timeout in seconds")
    parser.add_argument("-e", "--engine", choices=("http", "browser"), default="http", help="Scraping engine")

    parsed = parser.parse_args(args)

    fmt = parsed.format or (
        "csv" if parsed.output.suffix.lower() == ".csv"
        else "sqlite" if parsed.output.suffix.lower() in {".sqlite", ".db"}
        else "json"
    )

    config = ScraperConfig(
        engine=parsed.engine,
        max_pages=parsed.pages,
        max_depth=parsed.depth,
        concurrency=parsed.concurrency,
        delay=parsed.delay,
        timeout=parsed.timeout,
    )

    print(f"🚀 Launching Advanced Web Scraper on: {parsed.url}")
    print(f"⚙️  Engine: {parsed.engine.upper()} | Pages: {parsed.pages} | Concurrency: {parsed.concurrency}")

    spider = GenericSpider(start_url=parsed.url, config=config)

    async def _execute():
        async with get_engine(config) as engine:
            return await spider.run_async(engine=engine)

    items, stats = asyncio.run(_execute())

    DataExporter.export(items, parsed.output, file_format=fmt)
    print(f"✓ Crawled {stats.pages_crawled} page(s) in {stats.duration_seconds}s. Saved to {parsed.output} ({fmt.upper()}).")
    return 0


def main() -> int:
    subcommands = {"crawl", "declarative", "inspect", "test-selector", "list-spiders", "serve"}
    if len(sys.argv) > 1 and sys.argv[1] in subcommands:
        cli_app()
        return 0

    # If first arg starts with http or flags matching legacy style, run legacy
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1].startswith(("http://", "https://", "-o", "-f", "-p", "-d", "--delay"))):
        return run_legacy(sys.argv[1:])

    # Otherwise delegate to modern CLI
    cli_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
