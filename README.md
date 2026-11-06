# ⚡ Advanced Web Scraper

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-e92063.svg)](https://docs.pydantic.dev/)
[![HTTPX](https://img.shields.io/badge/HTTPX-HTTP%2F2-16a34a.svg)](https://www.python-httpx.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium-2ea44f.svg)](https://playwright.dev/python/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Dashboard-009688.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-16%20passed-success.svg)](https://docs.pytest.org/)

A production-grade, asynchronous web scraping and crawling framework with a **hybrid scraping engine** (fast HTTP/2 via HTTPX and dynamic headless browser via Playwright), **anti-detection suite**, **Pydantic v2 data validation**, **declarative YAML scraping**, **multi-format export** (JSON, JSONL, CSV, SQLite), a **Rich CLI**, and an **interactive Web UI playground**.

---

## 🌟 Key Features

- **🚀 Hybrid Scraping Engine**:
  - **Fast HTTP Engine (`httpx`)**: Asynchronous, HTTP/2 multiplexing, connection pooling, and politeness rate limiting.
  - **Dynamic Headless Engine (`playwright`)**: Headless Chromium execution for SPAs, client-rendered JavaScript (React/Vue/Angular), and infinite-scroll pages.
- **🛡️ Anti-Detection & Stealth Suite**:
  - Realistic User-Agent pool (macOS, Windows, Linux, iOS, Android).
  - Browser fingerprint headers (`Sec-Ch-Ua`, `Sec-Fetch-*`, `Accept-Language`).
  - Playwright stealth scripts to mask `navigator.webdriver`, plugins, and permissions.
  - Proxy pool manager supporting HTTP, HTTPS, and SOCKS5 with health checks and rotation (Round-Robin or Random).
- **📋 Pydantic v2 Validation & Pipelines**:
  - Strongly typed data models (`PageData`, `ProductItem`, `QuoteItem`, `ArticleItem`).
  - Automatic price/currency normalization, HTML unescaping, whitespace collapsing, and UTM tracking parameter stripping.
  - Automatic deduplication by unique key or payload hash.
- **⚙️ Declarative Scraper (No Code Required)**:
  - Define scrapers in simple YAML or JSON schemas specifying CSS selectors, data types, and pagination.
- **💾 Multi-Format Exporter**:
  - Export seamlessly to **JSON**, **JSONL**, **CSV**, and **SQLite** databases.
- **🖥️ Rich CLI & Interactive Web Dashboard**:
  - Terminal CLI with live progress bars, summary tables, and selector testing (`advanced-web-scraper`).
  - Interactive FastAPI + Tailwind CSS web dashboard (`scraper serve`) for testing selectors, running crawls, and downloading datasets from your browser.
- **⚡ Robots.txt & Politeness Controls**:
  - Per-domain rate limiting with jitter.
  - Local caching layer (disk/memory) with configurable TTL to avoid re-fetching pages during development.

---

## 🏗️ Architecture

```mermaid
flowchart TD
    Seed["Seed URL(s) / Spider"] --> Crawler["Async Frontier Crawler\n(BFS Queue & Concurrency Control)"]
    Crawler --> Cache{"Cache\nHit?"}
    Cache -- Yes --> Parser["Parsers & Extractors"]
    Cache -- No --> RateLimiter["Rate Limiter & Robots.txt"]
    RateLimiter --> Engine{"Engine Selection"}
    Engine -- Static / Fast --> HTTP["Async HTTP/2 Engine (HTTPX)\n+ Anti-Detection Headers"]
    Engine -- Dynamic / JS --> Browser["Playwright Headless Browser\n+ Stealth Evasion Scripts"]
    HTTP --> Response["Raw HTML Response"]
    Browser --> Response
    Response --> CacheStore["Save to Cache"]
    Response --> Parser
    Parser --> Pydantic["Validation Pipeline (Pydantic v2)"]
    Pydantic --> Dedup["Deduplication & Cleaner"]
    Dedup --> Exporter{"Data Exporter"}
    Exporter --> JSON["JSON / JSONL"]
    Exporter --> CSV["CSV"]
    Exporter --> SQLite["SQLite Database"]
```

---

## 📦 Installation

Clone the repository and install dependencies inside your virtual environment:

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Install dependencies & package
pip install -r requirements.txt
pip install -e .

# 3. (Optional) Install Playwright Chromium browser for dynamic scraping
playwright install chromium
```

---

## ⚡ Quickstart

### 1. Command-Line Interface (CLI)

The CLI can be invoked using `advanced-web-scraper`, `scraper`, or `python main.py`:

```bash
# Run the built-in Quotes spider (2 pages, output to JSON)
python main.py crawl quotes --pages 2 -o quotes.json

# Run the built-in Books spider with SQLite export
python main.py crawl books --pages 2 -f sqlite -o books.db

# Inspect a single page's metadata, status, headings, and links
python main.py inspect https://quotes.toscrape.com/

# Test a CSS selector against any live URL
python main.py test-selector https://quotes.toscrape.com/ "div.quote span.text"

# Use the dynamic browser engine (Playwright)
python main.py inspect https://quotes.toscrape.com/ -e browser

# Run declarative scraping from a YAML configuration
python main.py declarative examples/declarative_quotes.yaml -o results.json

# List all available built-in spiders
python main.py list-spiders
```

---

### 2. Python API

You can use the framework programmatically in your own scripts:

```python
from scraper.config import ScraperConfig
from scraper.spiders.quotes_spider import QuotesSpider
from scraper.pipelines.exporter import DataExporter

# Configure scraper
config = ScraperConfig(
    engine="http",        # or "browser" for JavaScript-heavy pages
    max_pages=3,
    concurrency=3,
    delay=0.5,            # Politeness delay
    cache_enabled=True,   # Cache responses locally
)

# Run spider
spider = QuotesSpider(config=config)
items, stats = spider.run()

print(f"Extracted {len(items)} quotes in {stats.duration_seconds}s!")

# Export to CSV and JSON
DataExporter.export(items, "quotes.csv", file_format="csv")
DataExporter.export(items, "quotes.json", file_format="json")
```

---

### 3. Declarative Scraper (YAML)

Scrape custom websites without writing any Python code:

```yaml
# examples/declarative_quotes.yaml
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

Execute:
```bash
python main.py declarative examples/declarative_quotes.yaml -o quotes.json
```

---

### 4. Interactive Web Dashboard & API

Launch the interactive control center:

```bash
python main.py serve --port 8000
```

Open your browser at `http://127.0.0.1:8000`:
- **Quick Inspector**: Test any page with HTTP or Playwright, view latency, metadata, headings, and images.
- **Selector Tester**: Test CSS selectors live against any URL with real-time match previews.
- **Multi-Page Crawler**: Launch background crawls and download results directly as JSON.

---

## 🛡️ Anti-Detection & Proxies

To route traffic through a proxy pool with automatic rotation and health tracking:

```bash
python main.py crawl quotes --proxy "http://user:password@proxy-host:8080"
```

Or configure via Python:

```python
config = ScraperConfig(
    proxies=[
        "http://proxy1:8080",
        "http://proxy2:8080",
    ],
    proxy_rotation_strategy="round_robin",  # or "random"
    stealth=True,                           # masks navigator.webdriver in browser
    user_agent_rotation=True,
)
```

---

## 🧪 Running Tests

A comprehensive test suite covers models, parsers, pipelines, anti-detection, spiders, and the async crawler:

```bash
pytest tests/
```

Output:
```text
======================== 16 passed in 0.22s ========================
```

---

## 🐳 Docker Deployment

Run the complete scraper dashboard with Docker:

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build standalone image
docker build -t advanced-web-scraper .
docker run -p 8000:8000 advanced-web-scraper
```

---

## 📁 Project Structure

```text
advanced_web_scraper/
├── scraper/
│   ├── __init__.py
│   ├── cli.py                     # Typer CLI with Rich terminal formatting
│   ├── config.py                  # Pydantic configuration & crawl settings
│   ├── models.py                  # Pydantic v2 schemas (PageData, ProductItem, QuoteItem, ArticleItem)
│   ├── anti_detection/
│   │   ├── headers.py             # Realistic browser HTTP headers
│   │   ├── proxy.py               # Proxy manager with health check & rotation
│   │   ├── stealth.py             # Playwright stealth scripts (navigator.webdriver mask)
│   │   └── user_agents.py         # Curated realistic desktop/mobile User-Agents
│   ├── core/
│   │   ├── cache.py               # Disk/memory response caching with TTL
│   │   ├── crawler.py             # Async BFS crawler with frontier queue & domain limits
│   │   ├── engine.py              # Hybrid engine (AsyncHttpEngine & PlaywrightEngine)
│   │   └── rate_limiter.py        # Token bucket & politeness controller with jitter
│   ├── parsers/
│   │   ├── declarative.py         # YAML/JSON schema-driven scraper
│   │   ├── html_parser.py         # Fast BeautifulSoup + lxml parser
│   │   └── metadata_parser.py     # OpenGraph, Twitter Cards, Schema.org JSON-LD
│   ├── pipelines/
│   │   ├── cleaner.py             # Whitespace normalizer & UTM tracker remover
│   │   ├── exporter.py            # Multi-format exporter (JSON, JSONL, CSV, SQLite)
│   │   └── validator.py           # Pydantic validation & deduplication pipeline
│   ├── spiders/
│   │   ├── base.py                # Abstract BaseSpider class
│   │   ├── books_spider.py        # BooksToScrape catalog spider
│   │   ├── generic.py             # Universal domain & sitemap crawler
│   │   ├── news_spider.py         # Article & blog post extractor
│   │   └── quotes_spider.py       # QuotesToScrape crawler
│   └── ui/
│       └── app.py                 # FastAPI Web Dashboard & Selector Playground
├── tests/
│   ├── test_anti_detection.py
│   ├── test_crawler.py
│   ├── test_declarative.py
│   ├── test_models.py
│   ├── test_parsers.py
│   ├── test_pipelines.py
│   └── test_spiders.py
├── examples/
│   ├── custom_spider.py           # Writing custom spiders with Pydantic models
│   ├── declarative_quotes.yaml    # Declarative YAML scraping config
│   └── quickstart.py              # Python API quickstart demo
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── main.py                        # Universal entrypoint
└── README.md
```

---

## 📜 License

MIT License. Educational and ethical web scraping project.
