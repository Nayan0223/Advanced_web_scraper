from scraper.parsers.html_parser import HTMLParser
from scraper.parsers.metadata_parser import extract_metadata
from scraper.parsers.declarative import DeclarativeScraper, DeclarativeSchema, FieldRule

__all__ = [
    "HTMLParser",
    "extract_metadata",
    "DeclarativeScraper",
    "DeclarativeSchema",
    "FieldRule",
]

