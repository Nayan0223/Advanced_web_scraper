"""Configuration management for Advanced Web Scraper."""

from __future__ import annotations

from pathlib import Path
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ScraperConfig(BaseModel):
    # Engine Settings
    engine: Literal["http", "browser"] = Field(
        default="http",
        description="Scraping engine: 'http' for fast async HTTP, 'browser' for Playwright dynamic JS execution"
    )
    timeout: float = Field(default=20.0, description="HTTP/Browser timeout in seconds")
    concurrency: int = Field(default=5, ge=1, le=50, description="Concurrent crawler workers")
    delay: float = Field(default=0.5, ge=0.0, description="Politeness delay between requests (seconds)")

    # Resilience & Anti-Detection
    max_retries: int = Field(default=3, ge=0, description="Maximum retries for failed requests")
    retry_backoff_factor: float = Field(default=1.5, description="Exponential backoff multiplier")
    user_agent_rotation: bool = Field(default=True, description="Rotate realistic desktop/mobile User-Agents")
    custom_user_agent: Optional[str] = Field(default=None, description="Custom User-Agent header")
    proxies: List[str] = Field(default_factory=list, description="List of proxy URLs (http://, https://, socks5://)")
    proxy_rotation_strategy: Literal["round_robin", "random"] = Field(default="round_robin")
    stealth: bool = Field(default=True, description="Enable Playwright stealth browser masking")

    # Crawling Scope
    max_pages: int = Field(default=10, ge=1, description="Maximum total pages to crawl")
    max_depth: int = Field(default=2, ge=0, description="Maximum crawl depth from starting URL")
    allowed_domains: List[str] = Field(default_factory=list, description="Limit crawling to these domains")
    follow_external_links: bool = Field(default=False, description="Whether to follow cross-domain links")
    respect_robots_txt: bool = Field(default=False, description="Check robots.txt rules before crawling")

    # Browser Specific Options
    headless: bool = Field(default=True, description="Run browser in headless mode")
    browser_wait_selector: Optional[str] = Field(default=None, description="CSS selector to wait for before extracting")
    browser_wait_timeout_ms: int = Field(default=10000, description="Wait timeout in milliseconds")
    scroll_to_bottom: bool = Field(default=False, description="Scroll page to bottom for infinite scroll content")
    scroll_pause: float = Field(default=1.0, description="Pause between scroll steps in seconds")

    # Caching
    cache_enabled: bool = Field(default=False, description="Cache raw HTML responses locally")
    cache_dir: Path = Field(default=Path(".cache"), description="Cache storage directory")
    cache_ttl_seconds: int = Field(default=3600, description="Cache time to live in seconds")

    # Output & Export
    output_path: Optional[Path] = Field(default=None, description="Destination path for scraped results")
    export_format: Literal["json", "jsonl", "csv", "sqlite"] = Field(default="json", description="Export format")
    sqlite_table: str = Field(default="scraped_items", description="SQLite table name if sqlite format is selected")

