import pytest 
from scraper .config import ScraperConfig 
from scraper .core .crawler import AsyncCrawler 
from scraper .models import ScrapeResponse 
class MockEngine :
    def __init__ (self ):
        self .pages ={
        "https://test.com":ScrapeResponse (
        url ="https://test.com",
        status_code =200 ,
        html ='<a href="/page1">Page 1</a><a href="https://external.com">External</a>',
        ),
        "https://test.com/page1":ScrapeResponse (
        url ="https://test.com/page1",
        status_code =200 ,
        html ='<a href="/page2">Page 2</a>',
        ),
        }
    async def fetch (self ,url :str )->ScrapeResponse :
        return self .pages .get (
        url ,
        ScrapeResponse (url =url ,status_code =404 ,html ="",error ="Not found"),
        )
    async def close (self ):
        pass 
@pytest .mark .asyncio 
async def test_async_crawler_domain_scoping_and_depth ():
    config =ScraperConfig (max_pages =5 ,max_depth =1 ,delay =0.0 )
    engine =MockEngine ()
    crawler =AsyncCrawler (config =config ,engine =engine )
    def dummy_handler (resp :ScrapeResponse ,depth :int ):
        items =[{"url":resp .url }]
        links =["https://test.com/page1","https://external.com/forbidden"]
        return items ,links 
    items ,stats =await crawler .crawl (
    seeds =["https://test.com"],
    page_handler =dummy_handler ,
    )
    assert stats .pages_crawled ==2 
    visited_urls =[item ["url"]for item in items ]
    assert "https://test.com"in visited_urls 
    assert "https://test.com/page1"in visited_urls 
    assert not any ("external.com"in u for u in visited_urls )
