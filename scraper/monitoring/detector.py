from __future__ import annotations
import hashlib
from typing import Optional
from pydantic import BaseModel
from scraper.parsers.html_parser import HTMLParser


class ChangeDetectionResult(BaseModel):
    url: str
    has_changed: bool
    previous_value: Optional[str] = None
    current_value: str
    target_selector: Optional[str] = None


class ContentChangeDetector:
    def __init__(self, target_selector: Optional[str] = None):
        self.target_selector = target_selector
        self.last_value: Optional[str] = None

    def compute_value(self, html: str, url: str) -> str:
        if not self.target_selector:
            return hashlib.sha256(html.encode("utf-8")).hexdigest()
        parser = HTMLParser(html, url)
        return parser.extract_text(self.target_selector)

    def check(self, html: str, url: str) -> ChangeDetectionResult:
        current_val = self.compute_value(html, url)
        has_changed = (self.last_value is not None) and (self.last_value != current_val)
        result = ChangeDetectionResult(
            url=url,
            has_changed=has_changed,
            previous_value=self.last_value,
            current_value=current_val,
            target_selector=self.target_selector,
        )
        self.last_value = current_val
        return result

