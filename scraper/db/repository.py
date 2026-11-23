"""Persistence helpers for crawl jobs and their scraped items.

Every function here talks to PostgreSQL through the async session factory so
FastAPI handlers can stay non-blocking.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import Text, cast, delete, func, insert, or_, select

from scraper.db.models import CrawlJob, ScrapedItem, utc_now
from scraper.db.session import session_scope


async def create_job(
    *,
    target: str,
    spider: str,
    engine: str,
    max_pages: int,
    concurrency: int,
    delay: float,
) -> Dict[str, Any]:
    """Insert a job in the ``running`` state and return its summary."""
    async with session_scope() as session:
        job = CrawlJob(
            target=target,
            spider=spider,
            engine=engine,
            status="running",
            max_pages=max_pages,
            concurrency=concurrency,
            delay=delay,
        )
        session.add(job)
        await session.flush()
        return job.to_summary()


async def complete_job(
    job_id: int,
    *,
    stats: Any,
    items: Sequence[Any],
) -> Dict[str, Any]:
    """Persist the extracted items and the final crawl counters."""
    rows: List[Dict[str, Any]] = []
    for item in items:
        payload = item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)
        rows.append(
            {
                "job_id": job_id,
                "item_type": type(item).__name__ if hasattr(item, "model_dump") else "dict",
                "url": payload.get("url") or payload.get("page_url") or payload.get("_url"),
                "payload": payload,
            }
        )

    async with session_scope() as session:
        if rows:
            await session.execute(insert(ScrapedItem), rows)
        job = await session.get(CrawlJob, job_id)
        if job is None:
            raise LookupError(f"Job {job_id} not found")
        job.status = "success"
        job.pages_crawled = int(getattr(stats, "pages_crawled", 0) or 0)
        job.pages_failed = int(getattr(stats, "pages_failed", 0) or 0)
        job.total_bytes = int(getattr(stats, "total_bytes", 0) or 0)
        job.duration_seconds = float(getattr(stats, "duration_seconds", 0.0) or 0.0)
        job.items_count = len(rows)
        job.finished_at = utc_now()
        await session.flush()
        return job.to_summary()


async def update_job_progress(
    job_id: int, *, pages_crawled: int, pages_failed: int = 0
) -> None:
    """Live counter update used by the dashboard progress bar."""
    async with session_scope() as session:
        job = await session.get(CrawlJob, job_id)
        if job is None or job.status != "running":
            return
        job.pages_crawled = max(job.pages_crawled, int(pages_crawled))
        job.pages_failed = max(job.pages_failed, int(pages_failed))


async def fail_job(job_id: int, error: str, *, stats: Any = None) -> None:
    """Mark a job as failed, keeping whatever counters are known."""
    async with session_scope() as session:
        job = await session.get(CrawlJob, job_id)
        if job is None:
            return
        job.status = "failed"
        job.error = (error or "Unknown error")[:4000]
        if stats is not None:
            job.pages_crawled = int(getattr(stats, "pages_crawled", 0) or 0)
            job.pages_failed = int(getattr(stats, "pages_failed", 0) or 0)
            job.duration_seconds = float(getattr(stats, "duration_seconds", 0.0) or 0.0)
        job.finished_at = utc_now()


async def list_jobs(
    *,
    limit: int = 25,
    offset: int = 0,
    status: Optional[str] = None,
    spider: Optional[str] = None,
    search: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Paginated job list plus the total row count for the filters applied."""
    filters = []
    if status and status != "all":
        filters.append(CrawlJob.status == status)
    if spider and spider != "all":
        filters.append(CrawlJob.spider == spider)
    if search:
        needle = f"%{search.strip()}%"
        filters.append(CrawlJob.target.ilike(needle))

    async with session_scope() as session:
        total = await session.scalar(select(func.count(CrawlJob.id)).where(*filters))
        rows = (
            await session.execute(
                select(CrawlJob)
                .where(*filters)
                .order_by(CrawlJob.id.desc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()
        return [row.to_summary() for row in rows], int(total or 0)


async def get_job(job_id: int, *, with_items: bool = False) -> Optional[Dict[str, Any]]:
    async with session_scope() as session:
        job = await session.get(CrawlJob, job_id)
        if job is None:
            return None
        return job.to_dict() if with_items else job.to_summary()


async def get_job_items(
    job_id: int,
    *,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    item_type: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Items of a single job with optional free-text payload search."""
    filters = [ScrapedItem.job_id == job_id]
    if item_type and item_type != "all":
        filters.append(ScrapedItem.item_type == item_type)
    if search:
        needle = f"%{search.strip()}%"
        filters.append(
            or_(
                ScrapedItem.url.ilike(needle),
                cast(ScrapedItem.payload, Text()).ilike(needle),
            )
        )

    async with session_scope() as session:
        total = await session.scalar(
            select(func.count(ScrapedItem.id)).where(*filters)
        )
        rows = (
            await session.execute(
                select(ScrapedItem)
                .where(*filters)
                .order_by(ScrapedItem.id.asc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()
        return [row.to_dict() for row in rows], int(total or 0)


async def all_job_items(job_id: int) -> List[Dict[str, Any]]:
    """Every item of a job, used by the export endpoints."""
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(ScrapedItem)
                .where(ScrapedItem.job_id == job_id)
                .order_by(ScrapedItem.id.asc())
            )
        ).scalars().all()
        return [row.to_dict() for row in rows]


async def delete_job(job_id: int) -> bool:
    async with session_scope() as session:
        job = await session.get(CrawlJob, job_id)
        if job is None:
            return False
        await session.delete(job)
        return True


async def distinct_item_types(job_id: Optional[int] = None) -> List[str]:
    async with session_scope() as session:
        stmt = select(ScrapedItem.item_type).distinct()
        if job_id is not None:
            stmt = stmt.where(ScrapedItem.job_id == job_id)
        rows = (await session.execute(stmt)).scalars().all()
        return sorted(row for row in rows if row)


async def dashboard_stats() -> Dict[str, Any]:
    """Aggregated numbers powering the overview dashboard."""
    since = datetime.now(timezone.utc) - timedelta(days=6)

    async with session_scope() as session:
        total_jobs = int(await session.scalar(select(func.count(CrawlJob.id))) or 0)
        total_items = int(await session.scalar(select(func.count(ScrapedItem.id))) or 0)
        pages_crawled = int(await session.scalar(select(func.sum(CrawlJob.pages_crawled))) or 0)
        success = int(
            await session.scalar(
                select(func.count(CrawlJob.id)).where(CrawlJob.status == "success")
            )
            or 0
        )
        failed = int(
            await session.scalar(
                select(func.count(CrawlJob.id)).where(CrawlJob.status == "failed")
            )
            or 0
        )
        running = int(
            await session.scalar(
                select(func.count(CrawlJob.id)).where(CrawlJob.status == "running")
            )
            or 0
        )
        avg_duration = float(
            await session.scalar(
                select(func.avg(CrawlJob.duration_seconds)).where(
                    CrawlJob.status == "success"
                )
            )
            or 0.0
        )
        spider_rows = (
            await session.execute(
                select(
                    CrawlJob.spider,
                    func.count(CrawlJob.id),
                    func.coalesce(func.sum(CrawlJob.items_count), 0),
                ).group_by(CrawlJob.spider)
            )
        ).all()
        type_rows = (
            await session.execute(
                select(ScrapedItem.item_type, func.count(ScrapedItem.id)).group_by(
                    ScrapedItem.item_type
                )
            )
        ).all()
        recent = (
            await session.execute(
                select(CrawlJob).order_by(CrawlJob.id.desc()).limit(8)
            )
        ).scalars().all()
        activity_rows = (
            await session.execute(
                select(CrawlJob.created_at, CrawlJob.items_count).where(
                    CrawlJob.created_at >= since
                )
            )
        ).all()

    buckets: Dict[str, Dict[str, Any]] = {}
    for offset in range(6, -1, -1):
        day = (datetime.now(timezone.utc) - timedelta(days=offset)).date().isoformat()
        buckets[day] = {"date": day, "jobs": 0, "items": 0}
    for created_at, items_count in activity_rows:
        if created_at is None:
            continue
        key = created_at.date().isoformat()
        if key in buckets:
            buckets[key]["jobs"] += 1
            buckets[key]["items"] += int(items_count or 0)

    finished = success + failed
    return {
        "totals": {
            "jobs": total_jobs,
            "items": total_items,
            "pages": pages_crawled,
            "running": running,
            "success": success,
            "failed": failed,
            "success_rate": round(success / finished * 100, 1) if finished else 0.0,
            "avg_duration": round(avg_duration, 2),
        },
        "spiders": [
            {"name": name, "jobs": int(jobs), "items": int(items)}
            for name, jobs, items in spider_rows
        ],
        "item_types": [
            {"name": name, "count": int(count)} for name, count in type_rows
        ],
        "activity": list(buckets.values()),
        "recent_jobs": [job.to_summary() for job in recent],
    }


async def prune_jobs(keep: int = 200) -> int:
    """Delete all but the newest ``keep`` jobs; returns the number removed."""
    async with session_scope() as session:
        ids = (
            await session.execute(
                select(CrawlJob.id).order_by(CrawlJob.id.desc()).offset(keep)
            )
        ).scalars().all()
        if not ids:
            return 0
        await session.execute(delete(CrawlJob).where(CrawlJob.id.in_(ids)))
        return len(ids)
