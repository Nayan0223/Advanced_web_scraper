# Advanced Web Scraper

A small Python command-line project for collecting useful information from static HTML pages. It extracts page titles, meta descriptions, headings, visible text, and links, then saves the results as JSON or CSV.

## Setup

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Usage

Scrape the included demo site and write `scraped_data.json`:

```bash
python main.py
```

Choose a URL, output format, and number of pages:

```bash
python main.py https://quotes.toscrape.com/ --pages 5 --delay 1 -o quotes.json
python main.py https://quotes.toscrape.com/ --pages 3 -o quotes.csv
```

Run `python main.py --help` to see all options. Crawling follows same-domain links only. The default is one page and a one-second pause between requests. Set `--delay 0` to disable the pause.

## Output fields

Each scraped page has a URL, title, meta description, list of headings, visible text (limited to 10,000 characters), and links with their text and absolute URL. In CSV files, headings and links are JSON-encoded cells.

## Scope and responsible use

This project fetches static HTML with Requests; it does not run JavaScript or log in to sites. Scrape only pages you are allowed to access. Check a site's terms and robots.txt, keep request rates low, and avoid collecting personal or sensitive information.
# Advanced_web_scraper
