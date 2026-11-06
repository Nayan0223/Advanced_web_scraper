**Advanced Web Scraper**

A production-grade, asynchronous web scraping and crawling framework with a hybrid scraping engine (fast HTTP/2 via HTTPX and dynamic headless browser via Playwright), anti-detection suite, Pydantic v2 data validation, declarative YAML scraping, multi-format export (JSON, JSONL, CSV, SQLite), a Rich CLI, and an interactive FastAPI web dashboard.

---

**Key Features**

- Hybrid Scraping Engine:
  - Fast HTTP Engine (HTTPX): Asynchronous, HTTP/2 multiplexing, connection pooling, and politeness rate limiting.
  - Dynamic Headless Engine (Playwright): Headless Chromium execution for single-page applications, client-rendered JavaScript (React, Vue, Angular), and infinite-scroll pages.
- Anti-Detection and Stealth Suite:
  - Realistic User-Agent pool (macOS, Windows, Linux, iOS, Android).
  - Browser fingerprint headers (Sec-Ch-Ua, Sec-Fetch, Accept-Language).
  - Playwright stealth scripts to mask navigator.webdriver, plugins, and permissions.
  - Proxy pool manager supporting HTTP, HTTPS, and SOCKS5 with health checks and rotation (Round-Robin or Random).
- Pydantic v2 Validation and Pipelines:
  - Strongly typed data models (PageData, ProductItem, QuoteItem, ArticleItem).
  - Automatic price and currency normalization, HTML unescaping, whitespace collapsing, and UTM tracking parameter stripping.
  - Automatic deduplication by unique key or payload hash.
- Declarative Scraper:
  - Define scrapers in simple YAML or JSON schemas specifying CSS selectors, data types, and pagination without writing code.
- Multi-Format Exporter:
  - Export seamlessly to JSON, JSONL, CSV, and SQLite databases.
- Rich CLI and Interactive Web Dashboard:
  - Terminal CLI with live progress bars, summary tables, and selector testing.
  - Interactive FastAPI and Tailwind CSS web dashboard for testing selectors, running crawls, and downloading datasets from your browser.
- Robots.txt and Politeness Controls:
  - Per-domain rate limiting with jitter.
  - Local caching layer (disk and memory) with configurable time-to-live to avoid re-fetching pages during development.

---

**Installation**

```bash
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
playwright install chromium
```

---

**Quickstart CLI**

```bash
python main.py crawl quotes --pages 2 -o quotes.json
python main.py crawl books --pages 2 -f sqlite -o books.db
python main.py inspect https://quotes.toscrape.com/
python main.py test-selector https://quotes.toscrape.com/ "div.quote span.text"
python main.py inspect https://quotes.toscrape.com/ -e browser
python main.py declarative examples/declarative_quotes.yaml -o results.json
python main.py list-spiders
```

---

**Python API**

```python
from scraper.config import ScraperConfig
from scraper.spiders.quotes_spider import QuotesSpider
from scraper.pipelines.exporter import DataExporter

config = ScraperConfig(
    engine="http",
    max_pages=3,
    concurrency=3,
    delay=0.5,
    cache_enabled=True,
)

spider = QuotesSpider(config=config)
items, stats = spider.run()

print(f"Extracted {len(items)} quotes in {stats.duration_seconds}s")

DataExporter.export(items, "quotes.csv", file_format="csv")
DataExporter.export(items, "quotes.json", file_format="json")
```

---

**Declarative Scraper (YAML)**

```yaml
name: quotes_scraper
start_urls:
  - "https://quotes.toscrape.com/"
max_pages: 2
container: "div.quote"
fields:
  text: "span.text"
  author: "small.author"
  author_link: "a[href*='/author/']@href"
  tags: "a.tag | list"
pagination: "li.next a@href"
```

Run:
```bash
python main.py declarative examples/declarative_quotes.yaml -o quotes.json
```

---

**Interactive Web Dashboard**

```bash
python main.py serve --port 8000
```

Open http://127.0.0.1:8000 in your browser to inspect pages, test selectors interactively, and launch crawls with JSON downloads.

---

**Testing**

```bash
pytest tests/
```

---

**Docker Deployment**

```bash
docker-compose up --build
```
