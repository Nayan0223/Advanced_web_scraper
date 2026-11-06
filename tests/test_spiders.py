import pytest
from scraper.models import ScrapeResponse
from scraper.spiders.books_spider import BooksSpider
from scraper.spiders.quotes_spider import QuotesSpider
from scraper.spiders.news_spider import NewsArticleSpider

SAMPLE_QUOTES_HTML = """
<div class="quote">
    <span class="text">“The truth will set you free.”</span>
    <small class="author">Anonymous</small>
    <a href="/author/Anonymous">(about)</a>
    <div class="tags">
        <a class="tag" href="/tag/truth">truth</a>
    </div>
</div>
<li class="next"><a href="/page/2">Next</a></li>
"""

SAMPLE_BOOKS_HTML = """
<article class="product_pod">
    <div class="image_container"><img src="media/book.jpg" alt="Book 1"></div>
    <p class="star-rating Four"></p>
    <h3><a href="catalogue/book_1/index.html" title="Mastering Python">Mastering Python</a></h3>
    <p class="price_color">£29.99</p>
    <p class="instock availability"><i class="icon-ok"></i> In stock</p>
</article>
<li class="next"><a href="page-2.html">Next</a></li>
"""

SAMPLE_NEWS_HTML = """
<article>
    <h1>Major Tech Breakthrough Announced</h1>
    <div class="byline">By <span class="author">Jane Doe</span></div>
    <time datetime="2026-11-06T10:00:00Z">Nov 6, 2026</time>
    <div class="content">
        <p>A new open-source system was released today that changes how data is processed.</p>
    </div>
</article>
"""


def test_quotes_spider_parsing():
    spider = QuotesSpider()
    resp = ScrapeResponse(url="https://quotes.toscrape.com/", status_code=200, html=SAMPLE_QUOTES_HTML)
    items, links = spider.parse(resp, 0)

    assert len(items) == 1
    assert items[0].author == "Anonymous"
    assert items[0].text == "The truth will set you free."
    assert items[0].tags == ["truth"]
    assert len(links) == 1
    assert links[0] == "https://quotes.toscrape.com/page/2"


def test_books_spider_parsing():
    spider = BooksSpider()
    resp = ScrapeResponse(url="https://books.toscrape.com/", status_code=200, html=SAMPLE_BOOKS_HTML)
    items, links = spider.parse(resp, 0)

    assert len(items) == 1
    assert items[0].title == "Mastering Python"
    assert items[0].price == 29.99
    assert items[0].rating == 4.0
    assert "In stock" in items[0].availability
    assert len(links) == 1


def test_news_spider_parsing():
    spider = NewsArticleSpider(start_url="https://news.example.com/article1")
    resp = ScrapeResponse(url="https://news.example.com/article1", status_code=200, html=SAMPLE_NEWS_HTML)
    items, links = spider.parse(resp, 0)

    assert len(items) == 1
    assert items[0].title == "Major Tech Breakthrough Announced"
    assert items[0].author == "Jane Doe"
    assert items[0].publish_date == "2026-11-06T10:00:00Z"
    assert items[0].reading_time_minutes >= 1

