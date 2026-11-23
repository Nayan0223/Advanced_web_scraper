"""SQLAlchemy ORM models backing the PostgreSQL persistence layer.

Two tables are used:

* ``crawl_jobs``   -- one row per crawl run (target, engine, counters, status).
* ``scraped_items`` -- one row per extracted record, payload stored as JSONB.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def utc_now() -> datetime:
    """Timezone aware UTC timestamp used as the default for new rows."""
    return datetime.now(timezone.utc)


# JSONB on PostgreSQL, plain JSON everywhere else (keeps the layer testable).
JSONPayload = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    """Declarative base for every ORM model in the project."""


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target: Mapped[str] = mapped_column(String(2048), nullable=False)
    spider: Mapped[str] = mapped_column(String(64), nullable=False, default="generic")
    engine: Mapped[str] = mapped_column(String(16), nullable=False, default="http")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="running", index=True
    )
    max_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    delay: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    pages_crawled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pages_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    items: Mapped[List["ScrapedItem"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def to_summary(self) -> Dict[str, Any]:
        """Compact representation used by the job list endpoints."""
        return {
            "id": self.id,
            "target": self.target,
            "spider": self.spider,
            "engine": self.engine,
            "status": self.status,
            "max_pages": self.max_pages,
            "concurrency": self.concurrency,
            "delay": self.delay,
            "pages_crawled": self.pages_crawled,
            "pages_failed": self.pages_failed,
            "items_count": self.items_count,
            "total_bytes": self.total_bytes,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Full representation including the extracted items."""
        data = self.to_summary()
        data["items"] = [item.to_dict() for item in self.items]
        return data


class ScrapedItem(Base):
    __tablename__ = "scraped_items"
    __table_args__ = (Index("ix_scraped_items_job_type", "job_id", "item_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_type: Mapped[str] = mapped_column(String(48), nullable=False, default="Item")
    url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONPayload, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )

    job: Mapped[CrawlJob] = relationship(back_populates="items")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "item_type": self.item_type,
            "url": self.url,
            "payload": self.payload,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
