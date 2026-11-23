"""Async PostgreSQL connection management (SQLAlchemy 2.x + asyncpg)."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from scraper.db.models import Base

try:  # python-dotenv is part of the runtime requirements, but stay defensive.
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional

    def load_dotenv(*args, **kwargs):  # type: ignore[no-redef]
        return False


load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "postgresql+asyncpg://scraper:scraper@localhost:5432/scraper"

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None
_ready: Optional[bool] = None
_last_error: Optional[str] = None


def normalize_database_url(raw_url: str) -> str:
    """Accept ``postgres://`` URLs (e.g. from hosting panels) and force asyncpg."""
    parts = urlsplit(raw_url.strip())
    scheme = parts.scheme
    if scheme in {"postgres", "postgresql"}:
        scheme = "postgresql+asyncpg"
    # asyncpg rejects libpq-only query parameters such as sslmode.
    query = [(k, v) for k, v in parse_qsl(parts.query) if k not in {"sslmode", "channel_binding"}]
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def get_database_url() -> str:
    """Resolve the DSN from the environment (``.env`` aware)."""
    return normalize_database_url(os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL)


def redact_database_url(url: Optional[str] = None) -> str:
    """Hide the password so it is safe to log or return from the API."""
    target = url or get_database_url()
    parts = urlsplit(target)
    if parts.password:
        netloc = f"{parts.username}:***@{parts.hostname}"
        if parts.port:
            netloc += f":{parts.port}"
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, ""))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def get_engine() -> AsyncEngine:
    """Lazily build the process-wide async engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_database_url(),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=False,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), expire_on_commit=False, autoflush=False
        )
    return _session_factory


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Transactional session context: commit on success, rollback on failure."""
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> bool:
    """Create tables if they are missing. Returns ``True`` when the DB is usable."""
    global _ready, _last_error
    try:
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _ready = True
        _last_error = None
        logger.info("PostgreSQL schema ready at %s", redact_database_url())
        return True
    except Exception as exc:  # pragma: no cover - depends on the environment
        _ready = False
        _last_error = f"{type(exc).__name__}: {exc}"
        logger.warning(
            "PostgreSQL unavailable at %s (%s). Dashboard will report the database as offline.",
            redact_database_url(),
            _last_error,
        )
        return False


async def ping() -> bool:
    """Lightweight connectivity check used by ``/api/health``."""
    global _ready, _last_error
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        _ready = True
        _last_error = None
        return True
    except Exception as exc:  # pragma: no cover - depends on the environment
        _ready = False
        _last_error = f"{type(exc).__name__}: {exc}"
        return False


def database_status() -> dict:
    """Snapshot of the connection state for the dashboard badge."""
    return {
        "ready": bool(_ready),
        "url": redact_database_url(),
        "error": _last_error,
    }


async def dispose_engine() -> None:
    """Close pooled connections on application shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
