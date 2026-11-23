"""PostgreSQL persistence layer for Advanced Web Scraper."""

from scraper.db import repository
from scraper.db.models import Base, CrawlJob, ScrapedItem
from scraper.db.session import (
    database_status,
    dispose_engine,
    get_database_url,
    get_engine,
    get_sessionmaker,
    init_db,
    ping,
    redact_database_url,
    session_scope,
)

__all__ = [
    "Base",
    "CrawlJob",
    "ScrapedItem",
    "repository",
    "database_status",
    "dispose_engine",
    "get_database_url",
    "get_engine",
    "get_sessionmaker",
    "init_db",
    "ping",
    "redact_database_url",
    "session_scope",
]
