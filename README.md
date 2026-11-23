**Advanced Web Scraper**

A production-grade, asynchronous web scraping and crawling framework with a hybrid scraping engine (fast HTTP/2 via HTTPX and dynamic headless browser via Playwright), an anti-detection suite, Pydantic v2 data validation, declarative YAML scraping, multi-format exports, a Rich CLI, and a PostgreSQL-backed web control center (FastAPI + a custom dark dashboard). Everything ships in Docker.

---

**Key Features**

- Hybrid Scraping Engine
  - Fast HTTP Engine (HTTPX): asynchronous, HTTP/2 multiplexing, connection pooling, politeness rate limiting.
  - Dynamic Headless Engine (Playwright): headless Chromium for SPAs, client-rendered JavaScript and infinite scroll.
- Anti-Detection and Stealth Suite
  - Realistic User-Agent pool (macOS, Windows, Linux, iOS, Android).
  - Browser fingerprint headers (Sec-Ch-Ua, Sec-Fetch, Accept-Language).
  - Playwright stealth scripts masking `navigator.webdriver`, plugins and permissions.
  - Proxy pool manager for HTTP, HTTPS and SOCKS5 with health checks and round-robin/random rotation.
- PostgreSQL Persistence
  - Every crawl is stored as a `crawl_jobs` row plus one `scraped_items` row per record (payload as `JSONB`).
  - Job status, page counters, byte totals and runtime are tracked live while the crawl runs.
  - Searchable, paginated job history with JSON / JSONL / CSV export and cascading delete.
  - Async SQLAlchemy 2.x + asyncpg; schema is created automatically on startup.
- Pydantic v2 Validation and Pipelines
  - Strongly typed models (`PageData`, `ProductItem`, `QuoteItem`, `ArticleItem`).
  - Price/currency normalisation, HTML unescaping, whitespace collapsing, UTM stripping, deduplication.
- Declarative Scraper — define scrapers in YAML/JSON with CSS selectors, types and pagination, no code required.
- Multi-Format Exporter — JSON, JSONL, CSV, SQLite, Parquet, XLSX.
- Control Center Web UI — live crawl progress, activity charts, spider mix, page inspector, selector lab, job history with per-record drill-down.
- Politeness and Caching — per-domain rate limits with jitter and a TTL disk cache.

---

**Architecture**

```
main.py                     CLI entrypoint (Typer subcommands + legacy argparse path)
scraper/
  config.py                 ScraperConfig (Pydantic settings)
  models.py                 Pydantic v2 records and crawl stats
  cli.py                    crawl · declarative · inspect · test-selector · list-spiders · serve
  core/
    engine.py               AsyncHttpEngine (HTTPX) + PlaywrightEngine
    crawler.py              async BFS frontier, depth/domain limits, robots.txt, caching
    rate_limiter.py         per-domain politeness with jitter
    cache.py                SHA-256 keyed JSON response cache
  anti_detection/           user agents · headers · stealth · proxy rotation
  parsers/                  HTML, metadata, sitemap, markdown, declarative YAML
  spiders/                  BaseSpider + quotes · books · news · generic (registry SPIDERS)
  pipelines/                validator · cleaner · exporter
  db/
    models.py               CrawlJob + ScrapedItem ORM models (JSONB payloads)
    session.py              async engine, session scope, schema bootstrap, health
    repository.py           job/item CRUD, search, stats, cascade delete
  ui/
    app.py                  FastAPI app: REST API + static dashboard
    static/                 index.html · styles.css · app.js (no CDN dependencies)
tests/                      16 pytest tests
examples/                   quickstart, custom spider, declarative schema
```

---

**Quickstart with Docker (PostgreSQL included)**

```bash
cp .env.example .env          # optional: change POSTGRES_PASSWORD
docker compose up --build     # postgres + scraper dashboard
```

Open http://127.0.0.1:8000. Compose starts `postgres:16-alpine` with a healthcheck,
waits for it to become healthy, then starts the app with
`DATABASE_URL=postgresql+asyncpg://scraper:scraper@db:5432/scraper`.
Data survives restarts in the `pgdata` volume.

Useful commands:

```bash
docker compose ps
docker compose logs -f scraper
docker compose down          # stop, keep data
docker compose down -v       # stop and delete the database volume
docker compose exec db psql -U scraper -d scraper -c 'select count(*) from scraped_items;'
```

---

**Deploy on Railway**

`railway.json` is included: Railway builds the `Dockerfile`, probes `/api/health`, and restarts the
service on failure. The dashboard reads `$PORT` automatically.

1. **New Project → Deploy from GitHub repo** and pick `Nayan0223/Advanced_web_scraper`
   (the `main` branch that contains `railway.json`).
2. **New → Database → PostgreSQL** in the same project.
3. On the app service open **Variables** and add
   `DATABASE_URL = ${{Postgres.DATABASE_URL}}` — the reference form uses Railway's
   private network, so no SSL is needed. A public URL with `?sslmode=require` also works;
   the DSN is translated for asyncpg automatically.
4. **Settings → Networking → Generate Domain** to get a public URL.

Tables are created on first boot. The image bundles Chromium, so the `browser` engine works
there too — expect a slow first build (roughly 1–2 GB of image layers).

---

**Local development (without Docker for the app)**

```bash
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
playwright install chromium
cp .env.example .env         # DATABASE_URL defaults to localhost:5432

docker compose up -d db      # PostgreSQL only
python main.py serve --port 8000
```

Tables are created automatically on the first request. If PostgreSQL is down the
dashboard still loads: the header pill reports `Postgres offline` and job
endpoints answer `503` with a hint, while the inspector and selector lab keep working.

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
python main.py serve --port 8000
```

---

**Python API**

```python
from scraper.config import ScraperConfig
from scraper.spiders.quotes_spider import QuotesSpider
from scraper.pipelines.exporter import DataExporter

config = ScraperConfig(engine="http", max_pages=3, concurrency=3, delay=0.5, cache_enabled=True)
spider = QuotesSpider(config=config)
items, stats = spider.run()

DataExporter.export(items, "quotes.csv", file_format="csv")
```

---

**Dashboard and REST API**

| Method | Path | Description |
| --- | --- | --- |
| GET | `/` | Control center (overview, inspector, selector lab, crawler, job history) |
| GET | `/api/health` | App version and PostgreSQL status (used by Docker healthcheck) |
| GET | `/api/stats` | Totals, success rate, 7-day activity, spider mix, recent jobs |
| GET | `/api/spiders` | Registered spider names |
| POST | `/api/scrape` | Inspect one page (stateless) |
| POST | `/api/test-selector` | Run a CSS selector against a live page |
| POST | `/api/crawl` | Run a crawl, persist it, return the job record + preview |
| GET | `/api/jobs` | Paginated jobs (`limit`, `offset`, `status`, `spider`, `search`) |
| GET | `/api/jobs/{id}` | One job with counters |
| GET | `/api/jobs/{id}/items` | Records (`limit`, `offset`, `search`, `item_type`) |
| GET | `/api/jobs/{id}/types` | Distinct record types in a job |
| GET | `/api/jobs/{id}/export?format=json\|jsonl\|csv` | Download the dataset |
| DELETE | `/api/jobs/{id}` | Delete a job and cascade its records |

Interactive OpenAPI docs: http://127.0.0.1:8000/docs

### Database schema

```
crawl_jobs                                  scraped_items
  id                 serial pk                id           serial pk
  target             varchar(2048)             job_id       fk -> crawl_jobs(id) on delete cascade
  spider             varchar(64)               item_type    varchar(48)   -- QuoteItem, PageData, ...
  engine             varchar(16)               url          varchar(2048)
  status             varchar(16) index         payload      jsonb         -- full Pydantic dump
  max_pages / concurrency / delay              created_at   timestamptz
  pages_crawled / pages_failed / items_count
  total_bytes / duration_seconds / error
  created_at (index) / finished_at
```

---

**Configuration**

`ScraperConfig` (Python) covers engine, timeout, concurrency, delay, retries, UA rotation,
proxies, stealth, crawl limits, robots.txt, browser waits, caching and export format.
Environment variables (see `.env.example`):

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Async DSN, e.g. `postgresql+asyncpg://scraper:scraper@localhost:5432/scraper` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` / `POSTGRES_PORT` | Compose database credentials |
| `APP_PORT` | Host port for the dashboard (default `8000`) |

---

**Testing**

```bash
pytest tests/
```

---

**Deployment notes**

- `Dockerfile` installs Chromium with `playwright install --with-deps chromium` and exposes a
  `/api/health` healthcheck.
- `docker-compose.yml` runs PostgreSQL 16 with a persistent volume and `depends_on: service_healthy`.
- The dashboard makes no external requests (no CDN), so it works on an isolated network;
  the Google Fonts link falls back to system fonts when offline.
