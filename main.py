"""A small, polite command-line web scraper for static HTML pages."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class ScraperError(Exception):
    """Raised when a page cannot be fetched or the input URL is invalid."""


class WebScraper:
    """Fetch and extract useful information from static web pages."""

    def __init__(self, timeout: float = 15, user_agent: str = "AdvancedWebScraper/1.0"):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"{user_agent} (educational project; contact: scraper@example.com)",
            "Accept": "text/html,application/xhtml+xml",
        })

    @staticmethod
    def validate_url(url: str) -> str:
        url = url.strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ScraperError(f"Invalid URL {url!r}. Include http:// or https://.")
        return urldefrag(url)[0]

    def fetch_page(self, url: str) -> str:
        url = self.validate_url(url)
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as error:
            raise ScraperError(f"Could not fetch {url}: {error}") from error

        content_type = response.headers.get("Content-Type", "")
        if content_type and "html" not in content_type.lower():
            raise ScraperError(f"Skipping non-HTML response at {url} ({content_type}).")
        return response.text

    @staticmethod
    def parse_page(html: str, page_url: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()

        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        description_tag = soup.find("meta", attrs={"name": "description"})
        description = description_tag.get("content", "").strip() if description_tag else ""
        headings = [
            {"level": int(tag.name[1]), "text": tag.get_text(" ", strip=True)}
            for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
            if tag.get_text(strip=True)
        ]
        text_root = soup.find("main") or soup.body or soup
        text = " ".join(text_root.stripped_strings)
        links = []
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            absolute_url = urldefrag(urljoin(page_url, href))[0]
            if urlparse(absolute_url).scheme in {"http", "https"}:
                links.append({"text": anchor.get_text(" ", strip=True), "url": absolute_url})

        # Preserve order while removing duplicate links.
        unique_links = list({link["url"]: link for link in reversed(links)}.values())[::-1]
        return {
            "url": page_url,
            "title": title,
            "description": description,
            "headings": headings,
            "text": text[:10000],
            "links": unique_links,
        }

    def crawl(self, start_url: str, max_pages: int = 1, delay: float = 1.0) -> list[dict[str, Any]]:
        """Visit up to max_pages URLs, following links on the starting domain only."""
        start_url = self.validate_url(start_url)
        start_host = urlparse(start_url).netloc.lower()
        queue = deque([start_url])
        queued = {start_url}
        pages: list[dict[str, Any]] = []

        while queue and len(pages) < max_pages:
            page_url = queue.popleft()
            if pages and delay:
                time.sleep(delay)
            try:
                page = self.parse_page(self.fetch_page(page_url), page_url)
            except ScraperError as error:
                print(f"Warning: {error}", file=sys.stderr)
                continue
            pages.append(page)

            for link in page["links"]:
                candidate = link["url"]
                parsed = urlparse(candidate)
                if parsed.netloc.lower() == start_host and candidate not in queued:
                    queued.add(candidate)
                    queue.append(candidate)

        return pages


def write_output(pages: list[dict[str, Any]], output: Path, file_format: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if file_format == "json":
        output.write_text(json.dumps(pages, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return

    columns = ["url", "title", "description", "headings", "text", "links"]
    with output.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        for page in pages:
            writer.writerow({
                **page,
                "headings": json.dumps(page["headings"], ensure_ascii=False),
                "links": json.dumps(page["links"], ensure_ascii=False),
            })


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract titles, descriptions, headings, text, and links from static web pages."
    )
    parser.add_argument("url", nargs="?", default="https://quotes.toscrape.com/", help="Starting page URL")
    parser.add_argument("-o", "--output", type=Path, default=Path("scraped_data.json"), help="Output file path")
    parser.add_argument("-f", "--format", choices=("json", "csv"), help="Output format (defaults to the file extension)")
    parser.add_argument("-p", "--pages", type=int, default=1, help="Maximum same-domain pages to visit (default: 1)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds to wait between requests (default: 1)")
    parser.add_argument("--timeout", type=float, default=15, help="Request timeout in seconds (default: 15)")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.pages < 1:
        print("Error: --pages must be at least 1.", file=sys.stderr)
        return 2
    if args.delay < 0 or args.timeout <= 0:
        print("Error: --delay must be non-negative and --timeout must be positive.", file=sys.stderr)
        return 2

    file_format = args.format or ("csv" if args.output.suffix.lower() == ".csv" else "json")
    scraper = WebScraper(timeout=args.timeout)
    try:
        pages = scraper.crawl(args.url, max_pages=args.pages, delay=args.delay)
    except ScraperError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    if not pages:
        print("No pages were scraped.", file=sys.stderr)
        return 1

    write_output(pages, args.output, file_format)
    print(f"Scraped {len(pages)} page(s) into {args.output} ({file_format.upper()}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
