"""Data schemas and Pydantic models for Advanced Web Scraper."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HeadingItem(BaseModel):
    level: int = Field(..., ge=1, le=6, description="Heading level 1 to 6")
    text: str = Field(..., min_length=1, description="Heading text content")


class LinkItem(BaseModel):
    text: str = Field(default="", description="Anchor text")
    url: str = Field(..., description="Absolute URL destination")


class ImageItem(BaseModel):
    src: str = Field(..., description="Image source URL")
    alt: str = Field(default="", description="Alternative text")


class PageMetadata(BaseModel):
    title: str = ""
    description: str = ""
    keywords: List[str] = Field(default_factory=list)
    canonical: Optional[str] = None
    open_graph: Dict[str, str] = Field(default_factory=dict)
    twitter_card: Dict[str, str] = Field(default_factory=dict)
    json_ld: List[Dict[str, Any]] = Field(default_factory=list)


class PageData(BaseModel):
    url: str
    status_code: int = 200
    timing_ms: float = 0.0
    title: str = ""
    description: str = ""
    headings: List[HeadingItem] = Field(default_factory=list)
    text: str = ""
    links: List[LinkItem] = Field(default_factory=list)
    images: List[ImageItem] = Field(default_factory=list)
    metadata: PageMetadata = Field(default_factory=PageMetadata)
    scraped_at: datetime = Field(default_factory=utc_now)


class ProductItem(BaseModel):
    title: str = Field(..., min_length=1)
    price: Optional[float] = None
    currency: str = "USD"
    availability: str = "In Stock"
    rating: Optional[float] = None
    description: str = ""
    image_url: Optional[str] = None
    sku: Optional[str] = None
    url: str
    scraped_at: datetime = Field(default_factory=utc_now)

    @field_validator("price", mode="before")
    @classmethod
    def parse_price(cls, v: Any) -> Optional[float]:
        if v is None or v == "":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        # Handle string price with currency symbols like "$19.99" or "£24.50"
        cleaned = "".join(ch for ch in str(v) if ch.isdigit() or ch == ".")
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None


class QuoteItem(BaseModel):
    text: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)
    author_url: Optional[str] = None
    scraped_at: datetime = Field(default_factory=utc_now)


class ArticleItem(BaseModel):
    title: str = Field(..., min_length=1)
    author: Optional[str] = None
    publish_date: Optional[str] = None
    summary: str = ""
    content: str = ""
    reading_time_minutes: Optional[int] = None
    url: str
    scraped_at: datetime = Field(default_factory=utc_now)


class ScrapeResponse(BaseModel):
    url: str
    status_code: int
    headers: Dict[str, str] = Field(default_factory=dict)
    html: str = ""
    execution_time_seconds: float = 0.0
    engine_name: str = "http"
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 400 and self.error is None


class CrawlStats(BaseModel):
    pages_crawled: int = 0
    pages_failed: int = 0
    items_extracted: int = 0
    total_bytes: int = 0
    duration_seconds: float = 0.0
    start_time: datetime = Field(default_factory=utc_now)
    end_time: Optional[datetime] = None
