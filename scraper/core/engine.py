"""Hybrid scraping engines: Async HTTP (HTTPX) and Dynamic Headless Browser (Playwright)."""
from __future__ import annotations 
import abc 
import asyncio 
import time 
from typing import Optional 
import httpx 
from tenacity import (
AsyncRetrying ,
retry_if_exception_type ,
stop_after_attempt ,
wait_exponential ,
)
from scraper .anti_detection .headers import generate_realistic_headers 
from scraper .anti_detection .proxy import ProxyManager 
from scraper .anti_detection .stealth import apply_stealth 
from scraper .anti_detection .user_agents import get_random_user_agent 
from scraper .config import ScraperConfig 
from scraper .models import ScrapeResponse 
try :
    import h2 
    HAS_HTTP2 =True 
except ImportError :
    HAS_HTTP2 =False 
class BaseEngine (abc .ABC ):
    """Abstract base class for scraping engines."""
    def __init__ (self ,config :ScraperConfig ):
        self .config =config 
        self .proxy_manager =ProxyManager (
        proxies =config .proxies ,
        strategy =config .proxy_rotation_strategy ,
        )
    @abc .abstractmethod 
    async def fetch (self ,url :str )->ScrapeResponse :
        """Fetch page content from URL and return a ScrapeResponse."""
        raise NotImplementedError 
    async def close (self )->None :
        """Cleanup resources, connections, or browser instances."""
        pass 
    async def __aenter__ (self ):
        return self 
    async def __aexit__ (self ,exc_type ,exc_val ,exc_tb ):
        await self .close ()
class AsyncHttpEngine (BaseEngine ):
    """High-performance asynchronous HTTP engine with HTTP/2 and anti-detection."""
    def __init__ (self ,config :ScraperConfig ):
        super ().__init__ (config )
        self ._client :Optional [httpx .AsyncClient ]=None 
    def _get_headers (self )->dict [str ,str ]:
        ua =self .config .custom_user_agent 
        if not ua and self .config .user_agent_rotation :
            ua =get_random_user_agent ("desktop")
        return generate_realistic_headers (user_agent =ua )
    async def _get_client (self ,proxy :Optional [str ]=None )->httpx .AsyncClient :
        client_kwargs ={
        "timeout":httpx .Timeout (self .config .timeout ),
        "follow_redirects":True ,
        "http2":HAS_HTTP2 ,
        }
        if proxy :
            return httpx .AsyncClient (proxy =proxy ,**client_kwargs )
        if self ._client is None or self ._client .is_closed :
            self ._client =httpx .AsyncClient (**client_kwargs )
        return self ._client 
    async def fetch (self ,url :str )->ScrapeResponse :
        proxy =self .proxy_manager .get_proxy ()
        headers =self ._get_headers ()
        start_time =time .monotonic ()
        retryer =AsyncRetrying (
        stop =stop_after_attempt (max (1 ,self .config .max_retries +1 )),
        wait =wait_exponential (multiplier =self .config .retry_backoff_factor ,min =1 ,max =10 ),
        retry =retry_if_exception_type ((httpx .RequestError ,httpx .HTTPStatusError )),
        reraise =False ,
        )
        last_error =None 
        try :
            async for attempt in retryer :
                with attempt :
                    client =await self ._get_client (proxy )
                    try :
                        resp =await client .get (url ,headers =headers )
                        if resp .status_code in {429 ,500 ,502 ,503 ,504 }:
                            resp .raise_for_status ()
                        elapsed =time .monotonic ()-start_time 
                        if proxy :
                            self .proxy_manager .report_success (proxy )
                        return ScrapeResponse (
                        url =str (resp .url ),
                        status_code =resp .status_code ,
                        headers =dict (resp .headers ),
                        html =resp .text ,
                        execution_time_seconds =round (elapsed ,4 ),
                        engine_name ="http",
                        )
                    except (httpx .RequestError ,httpx .HTTPStatusError )as e :
                        if proxy :
                            self .proxy_manager .report_failure (proxy )
                        last_error =str (e )
                        raise 
        except Exception as e :
            last_error =str (e )
        elapsed =time .monotonic ()-start_time 
        return ScrapeResponse (
        url =url ,
        status_code =0 ,
        headers ={},
        html ="",
        execution_time_seconds =round (elapsed ,4 ),
        engine_name ="http",
        error =last_error or "Unknown HTTP request failure",
        )
    async def close (self )->None :
        if self ._client and not self ._client .is_closed :
            await self ._client .aclose ()
class PlaywrightEngine (BaseEngine ):
    """Dynamic browser engine powered by Playwright with stealth evasions and JS execution."""
    def __init__ (self ,config :ScraperConfig ):
        super ().__init__ (config )
        self ._playwright =None 
        self ._browser =None 
    async def _init_browser (self ):
        from playwright .async_api import async_playwright 
        if self ._playwright is None :
            self ._playwright =await async_playwright ().start ()
        if self ._browser is None :
            proxy_url =self .proxy_manager .get_proxy ()
            proxy_dict ={"server":proxy_url }if proxy_url else None 
            self ._browser =await self ._playwright .chromium .launch (
            headless =self .config .headless ,
            proxy =proxy_dict ,
            args =[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            ],
            )
    async def fetch (self ,url :str )->ScrapeResponse :
        start_time =time .monotonic ()
        try :
            await self ._init_browser ()
            ua =self .config .custom_user_agent or (
            get_random_user_agent ("desktop")if self .config .user_agent_rotation else None 
            )
            context =await self ._browser .new_context (
            user_agent =ua ,
            viewport ={"width":1440 ,"height":900 },
            device_scale_factor =1 ,
            )
            page =await context .new_page ()
            if self .config .stealth :
                await apply_stealth (page )
            timeout_ms =int (self .config .timeout *1000 )
            response =await page .goto (url ,wait_until ="domcontentloaded",timeout =timeout_ms )
            if self .config .browser_wait_selector :
                await page .wait_for_selector (
                self .config .browser_wait_selector ,
                timeout =self .config .browser_wait_timeout_ms ,
                )
            if self .config .scroll_to_bottom :
                await page .evaluate ("""
                    async () => {
                        await new Promise((resolve) => {
                            let totalHeight = 0;
                            const distance = 300;
                            const timer = setInterval(() => {
                                const scrollHeight = document.body.scrollHeight;
                                window.scrollBy(0, distance);
                                totalHeight += distance;
                                if (totalHeight >= scrollHeight || totalHeight > 10000) {
                                    clearInterval(timer);
                                    resolve();
                                }
                            }, 100);
                        });
                    }
                """)
                await asyncio .sleep (self .config .scroll_pause )
            html =await page .content ()
            status =response .status if response else 200 
            headers =response .headers if response else {}
            await context .close ()
            elapsed =time .monotonic ()-start_time 
            return ScrapeResponse (
            url =page .url ,
            status_code =status ,
            headers =headers ,
            html =html ,
            execution_time_seconds =round (elapsed ,4 ),
            engine_name ="browser",
            )
        except Exception as e :
            elapsed =time .monotonic ()-start_time 
            return ScrapeResponse (
            url =url ,
            status_code =0 ,
            headers ={},
            html ="",
            execution_time_seconds =round (elapsed ,4 ),
            engine_name ="browser",
            error =str (e ),
            )
    async def close (self )->None :
        if self ._browser :
            await self ._browser .close ()
            self ._browser =None 
        if self ._playwright :
            await self ._playwright .stop ()
            self ._playwright =None 
def get_engine (config :ScraperConfig )->BaseEngine :
    """Factory to retrieve appropriate engine according to config."""
    if config .engine =="browser":
        return PlaywrightEngine (config )
    return AsyncHttpEngine (config )
