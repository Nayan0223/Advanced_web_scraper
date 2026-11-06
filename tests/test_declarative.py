from scraper.parsers.declarative import DeclarativeScraper, DeclarativeSchema

HTML_CONTENT = """
<div class="container">
    <div class="product">
        <h3 class="name">Laptop Pro</h3>
        <span class="price">$1,299.99</span>
        <a class="details" href="/product/123">View Product</a>
        <div class="tags">
            <span class="badge">electronics</span>
            <span class="badge">portable</span>
        </div>
    </div>
    <div class="product">
        <h3 class="name">Wireless Mouse</h3>
        <span class="price">$49.50</span>
        <a class="details" href="/product/456">View Product</a>
        <div class="tags">
            <span class="badge">accessories</span>
        </div>
    </div>
    <div class="pagination">
        <a class="next-page" href="/page/2">Next</a>
    </div>
</div>
"""


def test_declarative_scraper_parsing():
    schema = DeclarativeSchema(
        name="test_products",
        start_urls=["https://store.example.com"],
        container="div.product",
        fields={
            "title": "h3.name",
            "price": "span.price | float",
            "url": "a.details@href",
            "badges": "div.tags span.badge | list",
        },
        pagination="a.next-page@href",
    )

    scraper = DeclarativeScraper(schema)
    items = scraper.parse(HTML_CONTENT, "https://store.example.com")

    assert len(items) == 2
    assert items[0]["title"] == "Laptop Pro"
    assert items[0]["price"] == 1299.99
    assert items[0]["url"] == "https://store.example.com/product/123"
    assert items[0]["badges"] == ["electronics", "portable"]

    assert items[1]["title"] == "Wireless Mouse"
    assert items[1]["price"] == 49.50

    next_url = scraper.get_next_page(HTML_CONTENT, "https://store.example.com")
    assert next_url == "https://store.example.com/page/2"

