"""Command-Line Interface for Advanced Web Scraper with Rich formatting."""
from __future__ import annotations 
import asyncio 
from pathlib import Path 
from typing import Optional 
import typer 
from rich .console import Console 
from rich .panel import Panel 
from rich .progress import Progress ,SpinnerColumn ,TextColumn ,BarColumn ,TaskProgressColumn 
from rich .table import Table 
from scraper .config import ScraperConfig 
from scraper .core .engine import get_engine 
from scraper .parsers .declarative import DeclarativeScraper 
from scraper .parsers .html_parser import HTMLParser 
from scraper .pipelines .exporter import DataExporter 
from scraper .spiders import SPIDERS ,GenericSpider 
app =typer .Typer (
name ="advanced-web-scraper",
help ="High-Performance Resilient Web Scraping Framework & CLI",
add_completion =False ,
)
console =Console ()
@app .command ("crawl")
def crawl_command (
target :str =typer .Argument (...,help ="Target URL or Spider name ('quotes', 'books', or URL)"),
engine :str =typer .Option ("http","--engine","-e",help ="Engine: 'http' or 'browser'"),
pages :int =typer .Option (5 ,"--pages","-p",help ="Maximum pages to crawl"),
depth :int =typer .Option (2 ,"--depth","-d",help ="Maximum link traversal depth"),
concurrency :int =typer .Option (3 ,"--concurrency","-c",help ="Concurrent request limit"),
delay :float =typer .Option (0.5 ,"--delay",help ="Politeness delay between requests (seconds)"),
timeout :float =typer .Option (20.0 ,"--timeout","-t",help ="Timeout in seconds"),
output :Optional [Path ]=typer .Option (None ,"--output","-o",help ="Output file path"),
export_format :str =typer .Option ("json","--format","-f",help ="Output format: json, jsonl, csv, sqlite"),
cache :bool =typer .Option (False ,"--cache",help ="Enable disk caching"),
headless :bool =typer .Option (True ,"--headless/--head",help ="Run browser in headless mode"),
proxy :Optional [str ]=typer .Option (None ,"--proxy",help ="Proxy URL (e.g. http://127.0.0.1:8080)"),
):
    """Crawl a website or run a built-in spider with progress tracking and multi-format export."""
    console .print (
    Panel .fit (
    f"[bold cyan]Advanced Web Scraper[/bold cyan]\n"
    f"[bold yellow]Target:[/bold yellow] {target }\n"
    f"[bold yellow]Engine:[/bold yellow] {engine .upper ()} | [bold yellow]Max Pages:[/bold yellow] {pages } | [bold yellow]Concurrency:[/bold yellow] {concurrency }",
    border_style ="cyan",
    )
    )
    config =ScraperConfig (
    engine ="browser"if engine .lower ()in {"browser","playwright"}else "http",
    max_pages =pages ,
    max_depth =depth ,
    concurrency =concurrency ,
    delay =delay ,
    timeout =timeout ,
    cache_enabled =cache ,
    headless =headless ,
    proxies =[proxy ]if proxy else [],
    )
    target_lower =target .lower ()
    if target_lower in SPIDERS and target_lower !="generic":
        spider_cls =SPIDERS [target_lower ]
        spider =spider_cls (config =config )
    else :
        spider =GenericSpider (start_url =target ,config =config )
    items =[]
    stats =None 
    with Progress (
    SpinnerColumn (),
    TextColumn ("[progress.description]{task.description}"),
    BarColumn (),
    TaskProgressColumn (),
    console =console ,
    )as progress :
        task_id =progress .add_task ("[green]Crawling...",total =pages )
        async def run_crawl ():
            nonlocal items ,stats 
            async with get_engine (config )as engine_inst :
                items ,stats =await spider .run_async (engine =engine_inst )
        asyncio .run (run_crawl ())
    table =Table (title ="Crawl Execution Summary",border_style ="green")
    table .add_column ("Metric",style ="bold white")
    table .add_column ("Value",style ="bold green")
    table .add_row ("Pages Crawled",str (stats .pages_crawled if stats else len (items )))
    table .add_row ("Pages Failed",str (stats .pages_failed if stats else 0 ))
    table .add_row ("Items Extracted",str (len (items )))
    table .add_row ("Duration",f"{stats .duration_seconds if stats else 0 :.2f}s")
    console .print (table )
    out_file =output or Path (f"scraped_data.{export_format }")
    DataExporter .export (items ,out_file ,file_format =export_format )
    console .print (f"\n[bold green]Saved[/bold green] [bold]{len (items )}[/bold] items to [cyan]{out_file }[/cyan]\n")
@app .command ("declarative")
def declarative_command (
config_path :Path =typer .Argument (...,help ="Path to YAML/JSON scraping configuration"),
output :Optional [Path ]=typer .Option (None ,"--output","-o",help ="Output file path"),
export_format :str =typer .Option ("json","--format","-f",help ="Output format: json, csv, etc."),
engine :str =typer .Option ("http","--engine","-e",help ="Engine: http or browser"),
):
    """Run a configuration-driven scraper defined in a YAML or JSON file."""
    if not config_path .exists ():
        console .print (f"[bold red]Error:[/bold red] File not found: {config_path }")
        raise typer .Exit (code =1 )
    scraper =DeclarativeScraper .from_file (config_path )
    console .print (f"[bold green]Loaded schema:[/bold green] [cyan]{scraper .schema .name }[/cyan] ({len (scraper .schema .start_urls )} seed URL(s))")
    cfg =ScraperConfig (
    engine ="browser"if engine .lower ()=="browser"else "http",
    max_pages =scraper .schema .max_pages ,
    )
    all_items =[]
    async def run_declarative ():
        async with get_engine (cfg )as eng :
            for url in scraper .schema .start_urls :
                current_url :Optional [str ]=url 
                pages_visited =0 
                while current_url and pages_visited <scraper .schema .max_pages :
                    console .print (f"Fetching [dim]{current_url }[/dim]...")
                    resp =await eng .fetch (current_url )
                    if not resp .is_success :
                        console .print (f"[yellow]Failed fetching {current_url }: {resp .error }[/yellow]")
                        break 
                    extracted =scraper .parse (resp .html ,resp .url )
                    all_items .extend (extracted )
                    pages_visited +=1 
                    current_url =scraper .get_next_page (resp .html ,resp .url )
    asyncio .run (run_declarative ())
    out_file =output or Path (f"{scraper .schema .name }.{export_format }")
    DataExporter .export (all_items ,out_file ,file_format =export_format )
    console .print (f"[bold green]Extracted[/bold green] {len (all_items )} item(s) to [cyan]{out_file }[/cyan]")
@app .command ("inspect")
def inspect_command (
url :str =typer .Argument (...,help ="URL to inspect"),
engine :str =typer .Option ("http","--engine","-e",help ="Engine: http or browser"),
):
    """Fetch a single URL and inspect its metadata, headers, headings, and links."""
    console .print (f"Inspecting [cyan]{url }[/cyan] with engine [bold]{engine .upper ()}[/bold]...")
    async def run_inspect ():
        cfg =ScraperConfig (engine ="browser"if engine =="browser"else "http")
        async with get_engine (cfg )as eng :
            resp =await eng .fetch (url )
            if not resp .is_success :
                console .print (f"[bold red]Fetch Failed:[/bold red] {resp .error } (Status: {resp .status_code })")
                return 
            parser =HTMLParser (resp .html ,resp .url )
            page =parser .extract_page_data ()
            table =Table (title =f"Page Inspection: {url }",border_style ="cyan")
            table .add_column ("Property",style ="bold yellow")
            table .add_column ("Details",style ="white")
            table .add_row ("Status Code",str (resp .status_code ))
            table .add_row ("Latency",f"{resp .execution_time_seconds *1000 :.1f} ms")
            table .add_row ("Title",page .title or "[dim]None[/dim]")
            table .add_row ("Description",page .description [:80 ]+("..."if len (page .description )>80 else "")or "[dim]None[/dim]")
            table .add_row ("Headings Found",f"{len (page .headings )} headings")
            table .add_row ("Outgoing Links",f"{len (page .links )} links")
            table .add_row ("Images",f"{len (page .images )} images")
            table .add_row ("JSON-LD Schemas",f"{len (page .metadata .json_ld )} blocks")
            console .print (table )
            if page .headings :
                console .print ("\n[bold cyan]Top Headings:[/bold cyan]")
                for h in page .headings [:5 ]:
                    console .print (f"  [dim]H{h .level }:[/dim] {h .text }")
    asyncio .run (run_inspect ())
@app .command ("test-selector")
def test_selector_command (
url :str =typer .Argument (...,help ="Web page URL"),
selector :str =typer .Argument (...,help ="CSS Selector to test"),
):
    """Test a CSS selector against a live webpage to quickly verify extraction."""
    async def run_test ():
        cfg =ScraperConfig (engine ="http")
        async with get_engine (cfg )as eng :
            resp =await eng .fetch (url )
            if not resp .is_success :
                console .print (f"[bold red]Error fetching URL:[/bold red] {resp .error }")
                return 
            parser =HTMLParser (resp .html ,resp .url )
            matches =parser .select (selector )
            console .print (f"\nFound [bold green]{len (matches )}[/bold green] match(es) for selector '[cyan]{selector }[/cyan]':\n")
            for idx ,el in enumerate (matches [:5 ],1 ):
                preview =el .get_text (" ",strip =True )[:100 ]
                console .print (f"[dim]{idx }.[/dim] <{el .name }>: {preview }")
            if len (matches )>5 :
                console .print (f"[dim]... and {len (matches )-5 } more matches.[/dim]")
    asyncio .run (run_test ())
@app .command ("list-spiders")
def list_spiders ():
    """List built-in spiders ready to run."""
    table =Table (title ="Available Built-in Spiders",border_style ="magenta")
    table .add_column ("Spider Name",style ="bold cyan")
    table .add_column ("Description",style ="white")
    table .add_column ("Default Target",style ="dim")
    table .add_row ("quotes","Extracts quotes, authors, and tags with pagination","https://quotes.toscrape.com/")
    table .add_row ("books","Extracts book titles, prices, ratings, and stock status","https://books.toscrape.com/")
    table .add_row ("news","Extracts news / blog articles, authors, publish dates","Any article URL")
    table .add_row ("generic","Crawls any domain extracting title, headings, text, links","Custom URL")
    console .print (table )
@app .command ("serve")
def serve_ui (
host :str =typer .Option ("127.0.0.1","--host","-h",help ="Bind host"),
port :int =typer .Option (8000 ,"--port","-p",help ="Bind port"),
reload :bool =typer .Option (False ,"--reload",help ="Enable auto-reload for development"),
):
    """Launch the interactive web UI and API server."""
    import uvicorn 
    console .print (f"[bold green]Starting Advanced Web Scraper UI on http://{host }:{port }[/bold green]")
    uvicorn .run ("scraper.ui.app:app",host =host ,port =port ,reload =reload )
if __name__ =="__main__":
    app ()
