"""FastAPI dashboard and REST API for Advanced Web Scraper.

Crawl runs are persisted in PostgreSQL (jobs + JSONB records), the single page
dashboard lives in ``scraper/ui/static`` and every endpoint degrades carefully
when the database is unreachable.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from scraper.config import ScraperConfig
from scraper.core.engine import get_engine as create_scrape_engine
from scraper.db import repository as repo
from scraper.db.session import database_status, dispose_engine, init_db, ping
from scraper.parsers.html_parser import HTMLParser
from scraper.spiders import SPIDERS, GenericSpider

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"
PREVIEW_ITEMS = 50
_progress_tasks: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Create the PostgreSQL schema once, and close the pool on shutdown."""
    await init_db()
    yield
    for task in list(_progress_tasks):
        task.cancel()
    await dispose_engine()


app = FastAPI(
    title="Advanced Web Scraper API & Dashboard",
    description=(
        "Hybrid HTTP/Playwright scraping framework with a PostgreSQL-backed "
        "job history, live crawl progress and multi-format exports."
    ),
    version="2.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class ScrapeRequest(BaseModel):
    url: str = Field(..., description="Page to inspect")
    engine: str = Field("http", description="'http' or 'browser'")


class SelectorTestRequest(BaseModel):
    url: str
    selector: str
    engine: str = "http"


class CrawlRequest(BaseModel):
    target: str = Field(..., description="Spider name ('quotes', 'books', 'news') or a URL")
    engine: str = "http"
    max_pages: int = Field(5, ge=1, le=200)
    concurrency: int = Field(3, ge=1, le=20)
    delay: float = Field(0.5, ge=0.0, le=60.0)
    depth: int = Field(2, ge=0, le=10)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _resolve_engine(engine: str) -> str:
    return "browser" if engine.strip().lower() in {"browser", "playwright"} else "http"


def _serialize(item: Any) -> Any:
    if hasattr(item, "model_dump"):
        return item.model_dump(mode="json")
    return item


def _db_unavailable(exc: Exception) -> HTTPException:
    logger.warning("Database request failed: %s", exc)
    return HTTPException(
        status_code=503,
        detail="PostgreSQL is unavailable. Start it (docker compose up -d db) and retry.",
    )


def _spawn(coro: Any) -> None:
    """Fire-and-forget a background task while keeping a strong reference."""
    task = asyncio.create_task(coro)
    _progress_tasks.add(task)
    task.add_done_callback(_progress_tasks.discard)


def _flatten_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    row: Dict[str, Any] = {}
    for key, value in (payload or {}).items():
        if isinstance(value, (dict, list)):
            row[key] = json.dumps(value, ensure_ascii=False, default=str)
        else:
            row[key] = value
    return row


def _csv_body(records: Sequence[Dict[str, Any]]) -> str:
    rows = [_flatten_payload(record) for record in records]
    fieldnames: List[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    buffer = io.StringIO()
    if fieldnames:
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    return buffer.getvalue()


# --------------------------------------------------------------------------- #
# Dashboard + system
# --------------------------------------------------------------------------- #
@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    """Serve the single page control center."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health", tags=["system"])
async def api_health() -> Dict[str, Any]:
    """Liveness probe plus the PostgreSQL connection state."""
    ready = await ping()
    status = database_status()
    return {
        "status": "ok",
        "version": app.version,
        "database": {
            "ready": ready,
            "url": status["url"],
            "error": status["error"],
        },
    }


@app.get("/api/ready", tags=["system"])
async def api_ready() -> JSONResponse:
    """Readiness probe: fails with 503 when PostgreSQL is unreachable.

    Used as the container/Railway healthcheck so a missing ``DATABASE_URL``
    wiring shows up as an unhealthy deployment instead of a silently degraded app.
    """
    ready = await ping()
    status = database_status()
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "ready": ready,
            "database": {"ready": ready, "url": status["url"], "error": status["error"]},
        },
    )


@app.get("/api/stats", tags=["system"])
async def api_stats() -> Dict[str, Any]:
    """Aggregated counters, 7-day activity and recent jobs for the overview."""
    try:
        return await repo.dashboard_stats()
    except SQLAlchemyError as exc:
        raise _db_unavailable(exc) from exc
    except OSError as exc:
        raise _db_unavailable(exc) from exc


@app.get("/api/spiders", tags=["system"])
async def api_list_spiders() -> List[str]:
    return list(SPIDERS.keys())


# --------------------------------------------------------------------------- #
# Inspector + selector lab (stateless)
# --------------------------------------------------------------------------- #
@app.post("/api/scrape", tags=["scraping"])
async def api_scrape(request: ScrapeRequest) -> Dict[str, Any]:
    """Fetch a page and return its metadata, headings, links and images."""
    config = ScraperConfig(engine=_resolve_engine(request.engine))
    async with create_scrape_engine(config) as engine:
        response = await engine.fetch(request.url)
        if not response.is_success:
            raise HTTPException(status_code=400, detail=response.error or "Fetch failed")
        parser = HTMLParser(response.html, response.url)
        page = parser.extract_page_data()
        page.timing_ms = round(response.execution_time_seconds * 1000, 2)
        page.status_code = response.status_code
        return page.model_dump(mode="json")


@app.post("/api/test-selector", tags=["scraping"])
async def api_test_selector(request: SelectorTestRequest) -> Dict[str, Any]:
    """Evaluate a CSS selector against a live page."""
    config = ScraperConfig(engine=_resolve_engine(request.engine))
    async with create_scrape_engine(config) as engine:
        response = await engine.fetch(request.url)
        if not response.is_success:
            raise HTTPException(status_code=400, detail=response.error or "Fetch failed")
        parser = HTMLParser(response.html, response.url)
        elements = parser.select(request.selector)
        matches = [el.get_text(" ", strip=True) for el in elements]
        return {"selector": request.selector, "count": len(matches), "matches": matches}


# --------------------------------------------------------------------------- #
# Crawl runs
# --------------------------------------------------------------------------- #
@app.post("/api/crawl", tags=["crawling"])
async def api_crawl(request: CrawlRequest) -> Dict[str, Any]:
    """Run a crawl, persist it to PostgreSQL and return a preview of its data."""
    engine_name = _resolve_engine(request.engine)
    config = ScraperConfig(
        engine=engine_name,
        max_pages=request.max_pages,
        max_depth=request.depth,
        concurrency=request.concurrency,
        delay=request.delay,
    )

    target = request.target.strip()
    key = target.lower()
    if key in SPIDERS and key != "generic":
        spider_name = key
        spider = SPIDERS[key](config=config)
    else:
        spider_name = "generic"
        spider = GenericSpider(start_url=target, config=config)

    job_id: Optional[int] = None
    try:
        job = await repo.create_job(
            target=target,
            spider=spider_name,
            engine=engine_name,
            max_pages=request.max_pages,
            concurrency=request.concurrency,
            delay=request.delay,
        )
        job_id = int(job["id"])
    except Exception as exc:  # database optional for a one-off crawl
        logger.warning("Crawl will not be persisted (database error: %s)", exc)

    def on_progress(url: str, pages: int, total: int) -> None:
        if job_id is not None:
            _spawn(repo.update_job_progress(job_id, pages_crawled=pages))

    try:
        items, stats = await spider.run_async(on_progress=on_progress)
    except Exception as exc:
        if job_id is not None:
            try:
                await repo.fail_job(job_id, str(exc))
            except Exception:  # pragma: no cover - best effort
                pass
        logger.exception("Crawl failed for %s", target)
        raise HTTPException(status_code=500, detail=f"Crawl failed: {exc}") from exc

    job_data: Optional[Dict[str, Any]] = None
    if job_id is not None:
        try:
            job_data = await repo.complete_job(job_id, stats=stats, items=items)
        except Exception as exc:
            logger.warning("Could not persist crawl results for job %s: %s", job_id, exc)
            try:
                await repo.fail_job(job_id, f"Persist failed: {exc}", stats=stats)
            except Exception:  # pragma: no cover - best effort
                pass

    serialized = [_serialize(item) for item in items]
    return {
        "job": job_data,
        "persisted": job_data is not None,
        "items": serialized[:PREVIEW_ITEMS],
        "items_total": len(serialized),
        "items_truncated": len(serialized) > PREVIEW_ITEMS,
        "stats": stats.model_dump(mode="json"),
    }


# --------------------------------------------------------------------------- #
# Job history
# --------------------------------------------------------------------------- #
@app.get("/api/jobs", tags=["jobs"])
async def api_jobs(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    spider: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Paginated, filterable list of stored crawl jobs."""
    try:
        jobs, total = await repo.list_jobs(
            limit=limit, offset=offset, status=status, spider=spider, search=search
        )
    except (SQLAlchemyError, OSError) as exc:
        raise _db_unavailable(exc) from exc
    return {"jobs": jobs, "total": total, "limit": limit, "offset": offset}


@app.get("/api/jobs/{job_id}", tags=["jobs"])
async def api_job(job_id: int) -> Dict[str, Any]:
    try:
        job = await repo.get_job(job_id)
    except (SQLAlchemyError, OSError) as exc:
        raise _db_unavailable(exc) from exc
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@app.get("/api/jobs/{job_id}/items", tags=["jobs"])
async def api_job_items(
    job_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    item_type: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Records of one job with pagination and payload search."""
    try:
        if await repo.get_job(job_id) is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        items, total = await repo.get_job_items(
            job_id, limit=limit, offset=offset, search=search, item_type=item_type
        )
    except (SQLAlchemyError, OSError) as exc:
        raise _db_unavailable(exc) from exc
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@app.get("/api/jobs/{job_id}/types", tags=["jobs"])
async def api_job_types(job_id: int) -> List[str]:
    try:
        return await repo.distinct_item_types(job_id)
    except (SQLAlchemyError, OSError) as exc:
        raise _db_unavailable(exc) from exc


@app.get("/api/jobs/{job_id}/export", tags=["jobs"])
async def api_job_export(
    job_id: int,
    format: str = Query("json", pattern="^(json|jsonl|csv)$"),
) -> Response:
    """Download every record of a job as JSON, JSONL or CSV."""
    try:
        job = await repo.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        rows = await repo.all_job_items(job_id)
    except (SQLAlchemyError, OSError) as exc:
        raise _db_unavailable(exc) from exc

    records = [row["payload"] for row in rows]
    if format == "csv":
        body = _csv_body(records)
        media_type = "text/csv; charset=utf-8"
    elif format == "jsonl":
        body = "\n".join(json.dumps(record, ensure_ascii=False, default=str) for record in records)
        body = f"{body}\n" if body else ""
        media_type = "application/x-ndjson; charset=utf-8"
    else:
        body = json.dumps(
            {"job": job, "items": records}, ensure_ascii=False, indent=2, default=str
        )
        media_type = "application/json; charset=utf-8"

    filename = f"job-{job_id}-{job['spider']}.{format}"
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.delete("/api/jobs/{job_id}", tags=["jobs"])
async def api_delete_job(job_id: int) -> Dict[str, Any]:
    """Delete a job and (via cascade) all of its records."""
    try:
        deleted = await repo.delete_job(job_id)
    except (SQLAlchemyError, OSError) as exc:
        raise _db_unavailable(exc) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"deleted": True, "id": job_id}
