from bs4 import BeautifulSoup
from scraper.parsers.html_parser import HTMLParser
from scraper.parsers.metadata_parser import extract_metadata

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Sample Scraper Page</title>
    <meta name="description" content="A test page for web scraping validation.">
    <meta property="og:title" content="OG Title">
    <meta property="og:description" content="OG Description">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="canonical" href="https://example.com/canonical-page">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Widget",
        "price": "99.00"
    }
    </script>
</head>
<body>
    <header>
        <h1>Main Page Title</h1>
    </header>
    <main>
        <h2>Subheading 1</h2>
        <p>This is paragraph text with some content.</p>
        <a href="/internal-link">Internal Page</a>
        <a href="https://other.com/external">External Link</a>
        <img src="/img/logo.png" alt="Company Logo">
    </main>
</body>
</html>
"""


def test_html_parser_extracts_headings_and_links():
    parser = HTMLParser(SAMPLE_HTML, base_url="https://example.com/start")
    page_data = parser.extract_page_data()

    assert page_data.title == "OG Title" or page_data.title == "Sample Scraper Page"
    assert len(page_data.headings) == 2
    assert page_data.headings[0].level == 1
    assert page_data.headings[0].text == "Main Page Title"

    assert len(page_data.links) == 2
    urls = [link.url for link in page_data.links]
    assert "https://example.com/internal-link" in urls
    assert "https://other.com/external" in urls

    assert len(page_data.images) == 1
    assert page_data.images[0].src == "https://example.com/img/logo.png"
    assert page_data.images[0].alt == "Company Logo"


def test_metadata_extraction():
    soup = BeautifulSoup(SAMPLE_HTML, "html.parser")
    meta = extract_metadata(soup, base_url="https://example.com/start")

    assert meta.description == "OG Description" or meta.description == "A test page for web scraping validation."
    assert meta.canonical == "https://example.com/canonical-page"
    assert meta.twitter_card.get("twitter:card") == "summary_large_image"
    assert len(meta.json_ld) == 1
    assert meta.json_ld[0]["name"] == "Widget"

