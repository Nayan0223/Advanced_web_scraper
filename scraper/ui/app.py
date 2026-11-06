"""FastAPI Web UI and REST API for interactive web scraping and testing."""
from __future__ import annotations 
import asyncio 
from typing import Any ,Dict ,List ,Optional 
from fastapi import FastAPI ,HTTPException 
from fastapi .responses import HTMLResponse ,JSONResponse 
from pydantic import BaseModel ,Field 
from scraper .config import ScraperConfig 
from scraper .core .engine import get_engine 
from scraper .parsers .html_parser import HTMLParser 
from scraper .spiders import SPIDERS ,GenericSpider 
app =FastAPI (
title ="Advanced Web Scraper API & Dashboard",
description ="Interactive control center for scraping, testing selectors, and crawling web data.",
version ="2.0.0",
)
class ScrapeRequest (BaseModel ):
    url :str 
    engine :str ="http"
class SelectorTestRequest (BaseModel ):
    url :str 
    selector :str 
    engine :str ="http"
class CrawlRequest (BaseModel ):
    target :str 
    engine :str ="http"
    max_pages :int =5 
    concurrency :int =3 
    delay :float =0.5 
DASHBOARD_HTML ="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Advanced Web Scraper Playground</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen" x-data="scraperApp()">
    <!-- Navigation Bar -->
    <header class="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50 px-6 py-4 flex items-center justify-between">
        <div class="flex items-center space-x-3">
            <div>
                <h1 class="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">Advanced Web Scraper</h1>
                <p class="text-xs text-slate-400">Hybrid Engine (HTTPX & Playwright) - Anti-Detection - Pydantic</p>
            </div>
        </div>
        <div class="flex space-x-2">
            <button @click="activeTab = 'scrape'" :class="activeTab === 'scrape' ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:text-white'" class="px-4 py-1.5 rounded-lg text-sm font-medium transition">Quick Inspector</button>
            <button @click="activeTab = 'selector'" :class="activeTab === 'selector' ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:text-white'" class="px-4 py-1.5 rounded-lg text-sm font-medium transition">Selector Tester</button>
            <button @click="activeTab = 'crawl'" :class="activeTab === 'crawl' ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:text-white'" class="px-4 py-1.5 rounded-lg text-sm font-medium transition">Multi-Page Crawler</button>
        </div>
    </header>
    <main class="max-w-6xl mx-auto p-6">
        <!-- TAB 1: QUICK INSPECTOR -->
        <section x-show="activeTab === 'scrape'" class="space-y-6">
            <div class="bg-slate-800/60 border border-slate-700/60 p-6 rounded-2xl shadow-xl">
                <h2 class="text-lg font-semibold text-slate-200 mb-4">Inspect Single Web Page</h2>
                <div class="flex flex-col sm:flex-row gap-4">
                    <input type="url" x-model="inspectUrl" placeholder="https://quotes.toscrape.com/" class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500" />
                    <select x-model="inspectEngine" class="bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500">
                        <option value="http">Fast HTTP Engine (HTTPX)</option>
                        <option value="browser">Headless Browser (Playwright)</option>
                    </select>
                    <button @click="inspectPage()" :disabled="loading" class="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold px-6 py-3 rounded-xl transition flex items-center justify-center space-x-2">
                        <span x-show="!loading">Inspect Page</span>
                        <span x-show="loading">Loading...</span>
                    </button>
                </div>
            </div>
            <!-- Inspect Result -->
            <div x-show="inspectResult" class="bg-slate-800/60 border border-slate-700/60 p-6 rounded-2xl shadow-xl space-y-6">
                <div class="flex items-center justify-between border-b border-slate-700 pb-4">
                    <div>
                        <h3 class="text-xl font-bold text-white" x-text="inspectResult?.title || 'No Title Found'"></h3>
                        <p class="text-sm text-cyan-400" x-text="inspectResult?.url"></p>
                    </div>
                    <div class="flex space-x-3 text-xs font-mono">
                        <span class="bg-emerald-950 text-emerald-400 border border-emerald-800 px-3 py-1 rounded-full" x-text="'Status: ' + inspectResult?.status_code"></span>
                        <span class="bg-blue-950 text-blue-400 border border-blue-800 px-3 py-1 rounded-full" x-text="inspectResult?.timing_ms + ' ms'"></span>
                    </div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                        <h4 class="text-xs uppercase font-semibold text-slate-400 tracking-wider mb-2">Meta Description</h4>
                        <p class="text-sm text-slate-300" x-text="inspectResult?.description || 'None detected'"></p>
                    </div>
                    <div class="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                        <h4 class="text-xs uppercase font-semibold text-slate-400 tracking-wider mb-2">Summary Stats</h4>
                        <div class="flex space-x-4 text-sm text-slate-300">
                            <span>Headings: <strong class="text-cyan-400" x-text="inspectResult?.headings?.length || 0"></strong></span>
                            <span>Links: <strong class="text-cyan-400" x-text="inspectResult?.links?.length || 0"></strong></span>
                            <span>Images: <strong class="text-cyan-400" x-text="inspectResult?.images?.length || 0"></strong></span>
                        </div>
                    </div>
                </div>
                <!-- Extracted Headings -->
                <div x-show="inspectResult?.headings?.length" class="space-y-2">
                    <h4 class="text-sm font-semibold text-slate-300">Extracted Headings</h4>
                    <div class="bg-slate-900 p-4 rounded-xl max-h-48 overflow-y-auto space-y-1 text-sm font-mono border border-slate-800">
                        <template x-for="h in inspectResult?.headings" :key="h.text">
                            <div class="text-slate-300"><span class="text-cyan-400 font-bold" x-text="'H' + h.level + ': '"></span><span x-text="h.text"></span></div>
                        </template>
                    </div>
                </div>
            </div>
        </section>
        <!-- TAB 2: SELECTOR TESTER -->
        <section x-show="activeTab === 'selector'" class="space-y-6">
            <div class="bg-slate-800/60 border border-slate-700/60 p-6 rounded-2xl shadow-xl space-y-4">
                <h2 class="text-lg font-semibold text-slate-200">Interactive CSS Selector Tester</h2>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <input type="url" x-model="testUrl" placeholder="https://quotes.toscrape.com/" class="md:col-span-2 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500" />
                    <input type="text" x-model="testSelector" placeholder="div.quote span.text" class="bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500" />
                </div>
                <button @click="testCssSelector()" :disabled="loading" class="w-full bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold px-6 py-3 rounded-xl transition">
                    Test Selector Against URL
                </button>
            </div>
            <!-- Selector Results -->
            <div x-show="selectorMatches !== null" class="bg-slate-800/60 border border-slate-700/60 p-6 rounded-2xl shadow-xl space-y-4">
                <h3 class="text-sm font-semibold text-slate-300">
                    Matches Found: <span class="text-cyan-400 font-bold" x-text="selectorMatches?.length || 0"></span>
                </h3>
                <div class="space-y-2 max-h-96 overflow-y-auto">
                    <template x-for="(match, index) in selectorMatches" :key="index">
                        <div class="p-3 bg-slate-900 border border-slate-800 rounded-xl text-sm flex items-start space-x-3">
                            <span class="text-cyan-400 font-mono text-xs mt-0.5" x-text="(index + 1) + '.'"></span>
                            <span class="text-slate-200" x-text="match"></span>
                        </div>
                    </template>
                </div>
            </div>
        </section>
        <!-- TAB 3: MULTI-PAGE CRAWLER -->
        <section x-show="activeTab === 'crawl'" class="space-y-6">
            <div class="bg-slate-800/60 border border-slate-700/60 p-6 rounded-2xl shadow-xl space-y-4">
                <h2 class="text-lg font-semibold text-slate-200">Run Crawler</h2>
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <input type="text" x-model="crawlTarget" placeholder="quotes OR https://quotes.toscrape.com/" class="md:col-span-2 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500" />
                    <div>
                        <label class="block text-xs text-slate-400 mb-1">Max Pages</label>
                        <input type="number" x-model.number="crawlPages" min="1" max="20" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500" />
                    </div>
                    <div>
                        <label class="block text-xs text-slate-400 mb-1">Concurrency</label>
                        <input type="number" x-model.number="crawlConcurrency" min="1" max="10" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500" />
                    </div>
                </div>
                <button @click="startCrawl()" :disabled="loading" class="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold px-6 py-3 rounded-xl transition">
                    <span x-show="!loading">Launch Crawl Job</span>
                    <span x-show="loading">Crawling in progress...</span>
                </button>
            </div>
            <!-- Crawl Results -->
            <div x-show="crawlResults" class="bg-slate-800/60 border border-slate-700/60 p-6 rounded-2xl shadow-xl space-y-4">
                <div class="flex items-center justify-between">
                    <h3 class="text-base font-semibold text-slate-200">
                        Extracted <span class="text-emerald-400" x-text="crawlResults?.items?.length || 0"></span> items
                    </h3>
                    <button @click="downloadJson()" class="bg-slate-700 hover:bg-slate-600 text-xs px-3 py-1.5 rounded-lg font-medium transition">
                        Download JSON
                    </button>
                </div>
                <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 max-h-96 overflow-y-auto">
                    <pre class="text-xs font-mono text-cyan-300" x-text="JSON.stringify(crawlResults?.items?.slice(0, 10), null, 2)"></pre>
                </div>
            </div>
        </section>
    </main>
    <script>
        function scraperApp() {
            return {
                activeTab: 'scrape',
                loading: false,
                inspectUrl: 'https://quotes.toscrape.com/',
                inspectEngine: 'http',
                inspectResult: null,
                testUrl: 'https://quotes.toscrape.com/',
                testSelector: 'div.quote span.text',
                selectorMatches: null,
                crawlTarget: 'quotes',
                crawlPages: 3,
                crawlConcurrency: 2,
                crawlResults: null,
                async inspectPage() {
                    this.loading = true;
                    this.inspectResult = null;
                    try {
                        const res = await fetch('/api/scrape', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({url: this.inspectUrl, engine: this.inspectEngine})
                        });
                        this.inspectResult = await res.json();
                    } catch (e) {
                        alert('Inspection failed: ' + e);
                    } finally {
                        this.loading = false;
                    }
                },
                async testCssSelector() {
                    this.loading = true;
                    this.selectorMatches = null;
                    try {
                        const res = await fetch('/api/test-selector', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({url: this.testUrl, selector: this.testSelector})
                        });
                        const data = await res.json();
                        this.selectorMatches = data.matches || [];
                    } catch (e) {
                        alert('Selector test failed: ' + e);
                    } finally {
                        this.loading = false;
                    }
                },
                async startCrawl() {
                    this.loading = true;
                    this.crawlResults = null;
                    try {
                        const res = await fetch('/api/crawl', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                target: this.crawlTarget,
                                max_pages: this.crawlPages,
                                concurrency: this.crawlConcurrency,
                            })
                        });
                        this.crawlResults = await res.json();
                    } catch (e) {
                        alert('Crawl failed: ' + e);
                    } finally {
                        this.loading = false;
                    }
                },
                downloadJson() {
                    if (!this.crawlResults?.items) return;
                    const blob = new Blob([JSON.stringify(this.crawlResults.items, null, 2)], {type: 'application/json'});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'scraped_items.json';
                    a.click();
                    URL.revokeObjectURL(url);
                }
            }
        }
    </script>
</body>
</html>
"""
@app .get ("/",response_class =HTMLResponse )
async def dashboard_home ():
    """Render interactive web dashboard."""
    return DASHBOARD_HTML 
@app .post ("/api/scrape")
async def api_scrape (request :ScrapeRequest ):
    """Fetch page and extract full metadata, headings, and text."""
    cfg =ScraperConfig (engine ="browser"if request .engine .lower ()=="browser"else "http")
    async with get_engine (cfg )as engine :
        response =await engine .fetch (request .url )
        if not response .is_success :
            raise HTTPException (status_code =400 ,detail =response .error or "Fetch failed")
        parser =HTMLParser (response .html ,response .url )
        page_data =parser .extract_page_data ()
        page_data .timing_ms =round (response .execution_time_seconds *1000 ,2 )
        page_data .status_code =response .status_code 
        return page_data .model_dump (mode ="json")
@app .post ("/api/test-selector")
async def api_test_selector (request :SelectorTestRequest ):
    """Test a CSS selector against a target URL."""
    cfg =ScraperConfig (engine ="browser"if request .engine .lower ()=="browser"else "http")
    async with get_engine (cfg )as engine :
        response =await engine .fetch (request .url )
        if not response .is_success :
            raise HTTPException (status_code =400 ,detail =response .error or "Fetch failed")
        parser =HTMLParser (response .html ,response .url )
        elements =parser .select (request .selector )
        matches =[el .get_text (" ",strip =True )for el in elements ]
        return {"selector":request .selector ,"count":len (matches ),"matches":matches }
@app .post ("/api/crawl")
async def api_crawl (request :CrawlRequest ):
    """Execute a crawl asynchronously."""
    cfg =ScraperConfig (
    engine ="browser"if request .engine .lower ()=="browser"else "http",
    max_pages =request .max_pages ,
    concurrency =request .concurrency ,
    delay =request .delay ,
    )
    target_lower =request .target .lower ()
    if target_lower in SPIDERS and target_lower !="generic":
        spider =SPIDERS [target_lower ](config =cfg )
    else :
        spider =GenericSpider (start_url =request .target ,config =cfg )
    items ,stats =await spider .run_async ()
    return {
    "items":[item .model_dump (mode ="json")if hasattr (item ,"model_dump")else item for item in items ],
    "stats":stats .model_dump (mode ="json"),
    }
@app .get ("/api/spiders")
async def api_list_spiders ():
    """List registered spiders."""
    return list (SPIDERS .keys ())
