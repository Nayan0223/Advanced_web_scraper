from scraper.spiders.base import BaseSpider
from scraper.spiders.generic import GenericSpider
from scraper.spiders.quotes_spider import QuotesSpider
from scraper.spiders.books_spider import BooksSpider
from scraper.spiders.news_spider import NewsArticleSpider

SPIDERS = {
    "generic": GenericSpider,
    "quotes": QuotesSpider,
    "books": BooksSpider,
    "news": NewsArticleSpider,
}

__all__ = [
    "BaseSpider",
    "GenericSpider",
    "QuotesSpider",
    "BooksSpider",
    "NewsArticleSpider",
    "SPIDERS",
]

