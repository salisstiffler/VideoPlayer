import json
import asyncio
import httpx
import base64
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Optional, Callable, Dict, Any
import urllib.parse
import yt_dlp
import logging
import re
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PornGemini Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Registry for modular site support ---

SITES = [
    {"id": "pornhub", "name": "Pornhub", "url": "https://www.pornhub.com/video"},
    {"id": "xvideos", "name": "XVideos", "url": "https://www.xvideos.com/"},
    {"id": "xnxx", "name": "XNXX", "url": "https://www.xnxx.com/"},
    {"id": "xhamster", "name": "XHamster", "url": "https://xhamster.com/"},
    {"id": "thumbzilla", "name": "Thumbzilla", "url": "https://www.thumbzilla.com/"},
    {"id": "hqporner", "name": "HQPorner", "url": "https://hqporner.com/"},
    {"id": "tnaflix", "name": "TNAFlix", "url": "https://www.tnaflix.com/"},
    {"id": "51cg1", "name": "51cg1", "url": "https://51cg1.com/"},
    {"id": "jable", "name": "Jable", "url": "https://jable.tv/latest-updates/"},
    {"id": "missav", "name": "MissAV", "url": "https://missav.com/new"},
    {"id": "youporn", "name": "YouPorn", "url": "https://www.youporn.com/"},
    {"id": "redtube", "name": "RedTube", "url": "https://www.redtube.com/"},
    {"id": "eporner", "name": "EPorner", "url": "https://www.eporner.com/"},
    {"id": "porncom", "name": "Porn.com", "url": "https://www.porn.com/"},
    {"id": "spankbang", "name": "SpankBang", "url": "https://spankbang.com/"},
]

# --- Shared HTTP Client with Proxy Support ---

def get_proxy():
    # Priority: HTTP_PROXY > HTTPS_PROXY > ALL_PROXY
    return os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("ALL_PROXY")

def get_client(headers=None, timeout=30.0, follow_redirects=True):
    proxy = get_proxy()
    mounts = {"all://": httpx.AsyncHTTPTransport(proxy=proxy)} if proxy else None
    return httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=follow_redirects, mounts=mounts)

async def fetch_image_as_base64(url: str) -> str:
    """Helper to fetch a remote image and return it as a base64 data URI."""
    if not url or url.startswith('data:image') or not url.startswith('http'):
        return url
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "/".join(url.split("/")[:3]) + "/"
    }
    try:
        async with get_client(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                content_type = resp.headers.get("Content-Type", "image/jpeg")
                b64 = base64.b64encode(resp.content).decode('utf-8')
                return f"data:{content_type};base64,{b64}"
    except Exception as e:
        logger.warning(f"Failed to fetch image {url}: {e}")
    return url

# --- Scraper Functions ---

async def scrape_pornhub(page: int = 1):
    url = f"https://www.pornhub.com/video?page={page}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}
    async with get_client(headers=headers) as client:
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_items = soup.select('li.videoblock')
        results = []
        for item in video_items:
            if 'videoBox' not in item.get('class', []): continue
            title_tag = item.select_one('.title a')
            if not title_tag: continue
            video_id = item.get('data-video-vkey')
            title = title_tag.get('title', '').strip()
            link = "https://www.pornhub.com" + title_tag.get('href', '')
            img_tag = item.select_one('img')
            thumbnail = img_tag.get('data-src') or img_tag.get('src', '') if img_tag else ""
            duration = item.select_one('.duration').text.strip() if item.select_one('.duration') else ""
            results.append({"id": video_id, "title": title, "thumbnail": thumbnail, "url": link, "duration": duration, "site": "pornhub"})
        return results

async def scrape_xvideos_xnxx(site_id: str, page: int = 1):
    base_domain = "https://www.xvideos.com" if site_id == "xvideos" else "https://www.xnxx.com"
    url = f"{base_domain}/hits" if page == 1 else f"{base_domain}/hits/{page-1}"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": f"{base_domain}/"}
    async with get_client(headers=headers) as client:
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_items = soup.select('.mozaique .thumb-block')
        results = []
        for item in video_items:
            if 'thumb-cat' in item.get('class', []) or 'thumb-ad' in item.get('class', []): continue
            title_tag = item.select_one('.thumb-under p a') or item.select_one('.thumb a')
            if not title_tag: continue
            title = title_tag.get('title', '').strip() or title_tag.text.strip()
            href = title_tag.get('href', '')
            if not href or href == '#': continue
            link = href if href.startswith('http') else base_domain + href
            img_tag = item.select_one('img')
            thumbnail = img_tag.get('data-mzl') or img_tag.get('data-src') or img_tag.get('src', '') if img_tag else ""
            duration = ""
            metadata = item.select_one('.metadata')
            if metadata:
                m = re.search(r'(\d+(?:h\s*)?\d*min)', metadata.get_text(strip=True))
                duration = m.group(1) if m else metadata.get_text(strip=True).split('\n')[-1].strip()
            results.append({"id": item.get('data-id') or link, "title": title, "thumbnail": thumbnail, "url": link, "duration": duration, "site": site_id})
        return results


async def scrape_51cg1(page: int = 1):
    url = f"https://51cg1.com/page/{page}/"
    async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}, timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_items = soup.select('div.post-card')
        results = []
        for item in video_items:
            parent_a = item.find_parent('a')
            if not parent_a: continue
            link = parent_a.get('href', '')
            if not link.startswith('http'): link = "https://51cg1.com" + link
            title_tag = item.select_one('.post-card-title')
            if not title_tag: continue
            title = title_tag.get_text(" ", strip=True).replace("热搜 HOT", "").strip()
            thumbnail = ""
            bg_div = item.select_one('.blog-background')
            if bg_div and bg_div.get('style'):
                match = re.search(r'url\([\'"&quot;]*(.+?)[\'"&quot;]*\)', bg_div['style'])
                if match: thumbnail = match.group(1)
            results.append({"id": link.rstrip('/').split('/')[-1], "title": title, "thumbnail": thumbnail, "url": link, "duration": "", "site": "51cg1"})
        return results

async def scrape_jable(page: int = 1):
    url = "https://jable.tv/latest-updates/" if page == 1 else f"https://jable.tv/latest-updates/{page}/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"}
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        # Visit home page to get cookies
        try: await client.get("https://jable.tv/")
        except: pass
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_items = soup.select('.img-box')
        results = []
        for item in video_items:
            a_tag = item.select_one('a')
            if not a_tag: continue
            link = a_tag.get('href', '')
            img_tag = item.select_one('img')
            thumbnail = img_tag.get('data-src') or img_tag.get('src', '') if img_tag else ""
            duration = item.select_one('.absolute-bottom-right .label').text.strip() if item.select_one('.absolute-bottom-right .label') else ""
            title_tag = item.find_next('h6') or item.find_next('h4')
            title = title_tag.text.strip() if title_tag else "No Title"
            results.append({"id": link.rstrip('/').split('/')[-1], "title": title, "thumbnail": thumbnail, "url": link, "duration": duration, "site": "jable"})
        return results

async def scrape_missav(page: int = 1):
    missav_base = "https://missav.com"
    urls = [
        f"{missav_base}/cn/new?page={page}" if page > 1 else f"{missav_base}/cn/new",
        f"{missav_base}/new?page={page}" if page > 1 else f"{missav_base}/new",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Referer": f"{missav_base}/",
    }
    
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        for url in urls:
            try:
                # Get cookies
                await client.get(missav_base)
                resp = await client.get(url)
                if resp.status_code != 200: continue
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # The video items are usually in a grid, inside relative div wrappers
                video_items = soup.select('div.relative.group') or soup.select('.grid > div')
                if not video_items: continue
                
                results = []
                for item in video_items:
                    a_tag = item.select_one('a[href*="/watch/"]') or item.select_one('a.text-secondary') or item.select_one('a')
                    if not a_tag: continue
                    link = a_tag.get('href', '')
                    if not link or "/watch/" not in link: continue
                    if not link.startswith('http'): link = missav_base + (link if link.startswith('/') else '/' + link)
                    
                    title_tag = item.select_one('h4') or item.select_one('a.text-secondary') or a_tag
                    title = title_tag.text.strip()
                    if not title: continue
                    
                    img_tag = item.select_one('img')
                    thumbnail = img_tag.get('data-src') or img_tag.get('src', '') if img_tag else ""
                    
                    duration_tag = item.select_one('span.absolute.bottom-1.right-1') or item.select_one('.duration')
                    duration = duration_tag.text.strip() if duration_tag else ""
                    
                    results.append({"id": link.rstrip('/').split('/')[-1], "title": title, "thumbnail": thumbnail, "url": link, "duration": duration, "site": "missav"})
                if results: return results
            except Exception as e:
                logger.warning(f"Failed to scrape MissAV via {url}: {e}")
        return []

async def scrape_youporn(page: int = 1):
    url = f"https://www.youporn.com/?page={page}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_items = soup.select('.video-box')
        results = []
        for item in video_items:
            a_tag = item.select_one('a[href*="/watch/"]') or item.select_one('a')
            if not a_tag: continue
            href = a_tag.get('href', '')
            link = href if href.startswith('http') else "https://www.youporn.com" + href
            
            title_tag = item.select_one('.video-title-text') or item.select_one('.title') or a_tag
            title = title_tag.get('title') or title_tag.text.strip() if title_tag else "No Title"
            
            img_tag = item.select_one('img.thumb-image') or item.select_one('img')
            thumbnail = img_tag.get('data-src') or img_tag.get('src', '') if img_tag else ""
            
            duration_tag = item.select_one('.video-duration') or item.select_one('.duration')
            duration = duration_tag.text.strip() if duration_tag else ""
            
            results.append({"id": link.rstrip('/').split('/')[-2 if link.endswith('/') else -1], "title": title, "thumbnail": thumbnail, "url": link, "duration": duration, "site": "youporn"})
        return results

async def scrape_redtube(page: int = 1):
    url = f"https://www.redtube.com/?page={page}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Updated selectors for RedTube
        video_items = soup.select('li[data-video-id]') or soup.select('.video_block') or soup.select('.video-item')
        results = []
        for item in video_items:
            a_tag = item.select_one('a.tm_video_link') or item.select_one('a[href*="/"]')
            if not a_tag: continue
            href = a_tag.get('href', '')
            if not href or href == '#' or 'javascript' in href: continue
            link = "https://www.redtube.com" + (href if href.startswith('/') else '/' + href)
            
            # Title can be in a dedicated span or anchor title
            title_tag = item.select_one('.video_title') or item.select_one('.title')
            title = title_tag.text.strip() if title_tag else (a_tag.get('title') or "No Title")
            
            img_tag = item.select_one('img')
            thumbnail = img_tag.get('data-src') or img_tag.get('src', '') if img_tag else ""
            
            duration_tag = item.select_one('.duration') or item.select_one('.time')
            duration = duration_tag.text.strip() if duration_tag else ""
            
            results.append({"id": item.get('data-video-id') or link.rstrip('/').split('/')[-1], "title": title, "thumbnail": thumbnail, "url": link, "duration": duration, "site": "redtube"})
        return results

async def scrape_eporner(page: int = 1):
    url = "https://www.eporner.com/" if page == 1 else f"https://www.eporner.com/{page}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_items = soup.select('div.mb') or soup.select('.post-g')
        results = []
        for item in video_items:
            a_tag = item.select_one('a[href*="/video-"]') or item.select_one('a[href*="/hd-porn/"]') or item.select_one('a')
            if not a_tag: continue
            href = a_tag.get('href', '')
            link = href if href.startswith('http') else "https://www.eporner.com" + href
            
            title_tag = item.select_one('.mbtit') or a_tag
            title = title_tag.get('title') or title_tag.text.strip()
            
            img_tag = item.select_one('img')
            thumbnail = img_tag.get('data-src') or img_tag.get('src', '') or img_tag.get('data-original', '')
            
            duration_tag = item.select_one('.mbtim')
            duration = duration_tag.text.strip() if duration_tag else ""
            
            results.append({"id": link.split('/')[-2 if link.endswith('/') else -1], "title": title, "thumbnail": thumbnail, "url": link, "duration": duration, "site": "eporner"})
        return results

async def scrape_porncom(page: int = 1):
    url = f"https://www.porn.com/videos?page={page}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://www.porn.com/"
    }
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_items = soup.select('.list-global__item') or soup.select('.video-item')
        results = []
        for item in video_items:
            a_tag = item.select_one('a[href*="porn.com/"]') or item.select_one('a')
            if not a_tag: continue
            href = a_tag.get('href', '')
            link = href if href.startswith('http') else "https://www.porn.com" + href
            
            title = a_tag.get('title') or item.select_one('.list-global__meta').text.strip() if item.select_one('.list-global__meta') else a_tag.text.strip()
            
            img_tag = item.select_one('img')
            thumbnail = img_tag.get('data-src') or img_tag.get('src', '') or img_tag.get('data-original', '')
            
            duration_tag = item.select_one('.list-global__details') or item.select_one('.duration')
            duration = duration_tag.text.strip() if duration_tag else ""
            
            results.append({"id": link.rstrip('/').split('/')[-1], "title": title, "thumbnail": thumbnail, "url": link, "duration": duration, "site": "porncom"})
        return results

async def scrape_spankbang(page: int = 1):
    # Use .party mirror as .com is often behind Cloudflare
    base_url = "https://spankbang.party"
    url = f"{base_url}/trending_videos/{page}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Referer": f"{base_url}/",
    }
    async with get_client(headers=headers) as client:
        try:
            # Try to get cookies if needed, though .party seems more lenient
            await client.get(f"{base_url}/")
            resp = await client.get(url)
            if resp.status_code != 200: 
                logger.error(f"Spankbang returned status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Updated selectors for new Spankbang structure
            video_items = soup.select('div[data-testid="video-item"]') or \
                          soup.select('.video-item') or \
                          soup.select('.video-list .video-item')
            
            results = []
            for item in video_items:
                # Find the main video link
                a_tag = item.select_one('a[href*="/video/"]')
                if not a_tag: continue
                
                href = a_tag.get('href', '')
                if not href: continue
                link = base_url + (href if href.startswith('/') else '/' + href)
                
                # Title is often in img alt or a title or a span
                img_tag = item.select_one('img')
                title = ""
                if img_tag:
                    title = img_tag.get('alt', '').strip()
                
                if not title:
                    title_link = item.select_one('a[title]')
                    if title_link:
                        title = title_link.get('title', '').strip()
                
                if not title:
                    title = a_tag.text.strip()
                
                thumbnail = ""
                if img_tag:
                    thumbnail = img_tag.get('data-src') or img_tag.get('src', '')
                
                # Duration
                duration_tag = item.select_one('div[data-testid="video-item-length"]') or \
                               item.select_one('.l') or \
                               item.select_one('.duration')
                duration = duration_tag.text.strip() if duration_tag else ""
                
                # Extract ID from link
                video_id = link.rstrip('/').split('/')[-2]
                
                results.append({
                    "id": video_id, 
                    "title": title or "No Title", 
                    "thumbnail": thumbnail, 
                    "url": link, 
                    "duration": duration, 
                    "site": "spankbang"
                })
            return results
        except Exception as e:
            logger.error(f"Spankbang error: {e}")
            return []

async def get_info_porncom(url: str, request: Request):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Referer": "https://www.porn.com/"
    }
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        # Age gate bypass
        client.cookies.set('age_verified', '1', domain='www.porn.com')
        resp = await client.get(url)
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Porn.com often uses an iframe or a direct link to the source site
    source_url = ""
    
    # 1. Check for iframe
    iframe = soup.select_one('iframe.video-player__iframe')
    if iframe:
        source_url = iframe.get('data-origsrc') or iframe.get('src')
        if source_url and ("logo_dark.svg" in source_url or "logo.svg" in source_url):
            source_url = "" # Reset if it's just the logo
            
    # 2. Check for premium/source buttons if iframe is not useful
    if not source_url:
        btn = soup.select_one('a.video-player__premium-btn') or soup.select_one('a.video-player__src')
        if btn:
            source_url = btn.get('href')
            
    # 3. If it's an /out/ link, we might need to follow it or parse it
    if source_url and "/out/" in source_url:
        if not source_url.startswith('http'):
            source_url = "https://www.porn.com" + source_url
        # Many /out/ links contain the base64 encoded destination or just redirect
        # For simplicity, let's try to follow it
        async with httpx.AsyncClient(headers=headers, timeout=10.0, follow_redirects=True) as client:
            out_resp = await client.get(source_url)
            source_url = str(out_resp.url)

    if not source_url:
        # Final fallback: search for any m3u8/mp4
        match = re.search(r'["\']?(?:file|url|video_url|source)["\']?\s*[:=]\s*["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', resp.text, re.I)
        if match: source_url = match.group(1)

    if not source_url or source_url == url:
        raise HTTPException(status_code=500, detail="Could not find external video source on Porn.com")

    # Now treat the source_url as a new video request
    # This allows us to reuse existing extractors for XVideos, Pornhub, etc.
    return await get_video_info(request, source_url)

async def scrape_xhamster(page: int = 1):
    base_url = "https://xhamster.com"
    url = f"{base_url}/new/{page}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"}
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_items = soup.select('div[data-test="video-item"]') or soup.select('.video-thumb')
        results = []
        for item in video_items:
            a_tag = item.select_one('a[href*="/videos/"]')
            if not a_tag: continue
            link = a_tag.get('href', '')
            if not link.startswith('http'): link = base_url + link
            
            title_tag = item.select_one('.video-thumb__title') or a_tag
            title = title_tag.get_text(strip=True)
            
            img_tag = item.select_one('img')
            thumbnail = img_tag.get('data-src') or img_tag.get('src', '') if img_tag else ""
            
            duration_tag = item.select_one('.video-thumb__duration')
            duration = duration_tag.get_text(strip=True) if duration_tag else ""
            
            results.append({"id": link.rstrip('/').split('/')[-1], "title": title, "thumbnail": thumbnail, "url": link, "duration": duration, "site": "xhamster"})
        return results

async def scrape_thumbzilla(page: int = 1):
    base_url = "https://www.thumbzilla.com"
    # Use the /newest endpoint which is often cleaner
    url = f"{base_url}/newest?page={page}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"}
    async with get_client(headers=headers) as client:
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Based on analysis: .video-box is the container
        video_items = soup.select('.video-box') or soup.select('.js_video-box') or soup.select('a.js-thumb')
        results = []
        for item in video_items:
            # The item itself might be the link, or contain it
            if item.name == 'a':
                a_tag = item
            else:
                a_tag = item.select_one('a.js-thumb') or item.select_one('a')
            
            if not a_tag: continue
            href = a_tag.get('href', '')
            if '/video/' not in href: continue
            
            link = base_url + href if href.startswith('/') else href
            
            # Title is often in a data attribute or child span
            title = a_tag.get('title') or a_tag.get('data-title') or ""
            if not title:
                title_tag = item.select_one('.title') or item.select_one('.video-title')
                if title_tag: title = title_tag.get_text(strip=True)
            
            if not title: title = "Thumbzilla Video"

            img_tag = item.select_one('img')
            thumbnail = ""
            if img_tag:
                thumbnail = img_tag.get('data-src') or img_tag.get('src', '')
            
            duration_tag = item.select_one('.duration') or item.select_one('.time')
            duration = duration_tag.get_text(strip=True) if duration_tag else ""
            
            results.append({"id": link.rstrip('/').split('/')[-1], "title": title, "thumbnail": thumbnail, "url": link, "duration": duration, "site": "thumbzilla"})
        return results

async def scrape_hqporner(page: int = 1):
    base_url = "https://hqporner.com"
    url = f"{base_url}/" if page == 1 else f"{base_url}/latest/{page}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with get_client(headers=headers) as client:
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Based on analysis: .featured, .atfib are common classes for items
        # Also try generic block selectors
        video_items = soup.select('.featured') or soup.select('.atfib') or soup.select('div[class*="item"]')
        results = []
        for item in video_items:
            a_tag = item.select_one('a[href*="/hdporn/"]')
            if not a_tag: continue
            
            href = a_tag.get('href', '')
            link = base_url + href if href.startswith('/') else href
            
            title = a_tag.get('title', '') or a_tag.get_text(strip=True)
            
            img_tag = item.select_one('img')
            thumbnail = ""
            if img_tag:
                src = img_tag.get('data-src') or img_tag.get('src', '')
                # Handle schemeless urls
                if src.startswith('//'): thumbnail = "https:" + src
                elif src.startswith('/'): thumbnail = base_url + src
                else: thumbnail = src
            
            duration = item.select_one('.duration')
            duration = duration.get_text(strip=True) if duration else ""
            
            results.append({"id": link.rstrip('/').split('/')[-1], "title": title, "thumbnail": thumbnail, "url": link, "duration": duration, "site": "hqporner"})
        return results

async def scrape_tnaflix(page: int = 1):
    base_url = "https://www.tnaflix.com"
    url = f"{base_url}/most-recent/{page}"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with get_client(headers=headers) as client:
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Based on analysis: .thumb, .col-xs-6 are containers
        video_items = soup.select('.thumb') or soup.select('.video-item')
        results = []
        for item in video_items:
            a_tag = item.select_one('a[href*="/video"]')
            if not a_tag: continue
            
            href = a_tag.get('href', '')
            if not href: continue
            
            link = href if href.startswith('http') else base_url + href
            
            title = a_tag.get('title')
            if not title:
                info = item.select_one('.title') or item.select_one('.video-title')
                if info: title = info.get_text(strip=True)
            if not title: title = "TNAFlix Video"
            
            img_tag = item.select_one('img')
            thumbnail = ""
            if img_tag:
                thumbnail = img_tag.get('data-original') or img_tag.get('data-src') or img_tag.get('src', '')
            
            duration = item.select_one('.duration') or item.select_one('.time')
            duration = duration.get_text(strip=True) if duration else ""
            
            results.append({"id": link.rstrip('/').split('/')[-1], "title": title, "thumbnail": thumbnail, "url": link, "duration": duration, "site": "tnaflix"})
        return results

# --- Site Scraper Registry ---

SCRAPERS: Dict[str, Callable[[int], Any]] = {
    "pornhub": scrape_pornhub,
    "xvideos": lambda p: scrape_xvideos_xnxx("xvideos", p),
    "xnxx": lambda p: scrape_xvideos_xnxx("xnxx", p),
    "xhamster": scrape_xhamster,
    "thumbzilla": scrape_thumbzilla,
    "hqporner": scrape_hqporner,
    "tnaflix": scrape_tnaflix,
    "51cg1": scrape_51cg1,
    "jable": scrape_jable,
    "missav": scrape_missav,
    "youporn": scrape_youporn,
    "redtube": scrape_redtube,
    "eporner": scrape_eporner,
    "porncom": scrape_porncom,
    "spankbang": scrape_spankbang,
}

# --- Info Extraction Logic ---

async def get_info_51cg1(url: str, request: Request):
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, 'html.parser')
    players = soup.select('div.dplayer')
    formats = []
    base_url = str(request.base_url).rstrip('/')
    for i, player in enumerate(players):
        video_url = ""
        config_str = player.get('data-config', '').replace('&quot;', '"')
        if config_str:
            try: video_url = json.loads(config_str).get('video', {}).get('url', '')
            except: pass
        if not video_url and player.select_one('video'): video_url = player.select_one('video').get('src', '')
        if video_url:
            proxy_url = f"{base_url}/stream?url={urllib.parse.quote(video_url)}"
            note = player.get('data-video_title', f"Source {i+1}").split("！")[-1]
            formats.append({"id": f"51cg_{i}", "url": proxy_url, "ext": "m3u8" if "m3u8" in video_url else "mp4", "height": 720 + (i * 360), "note": note})
    return {"title": soup.title.string if soup.title else "51cg1 Video", "thumbnail": "", "formats": formats, "best_url": formats[0]['url'] if formats else None}

async def get_info_jable_missav(url: str, request: Request):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"}
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        # Visit home page to get cookies
        try:
            domain = urllib.parse.urlparse(url).netloc
            await client.get(f"https://{domain}/")
        except: pass
        resp = await client.get(url)
    
    # Try different variable names for hlsUrl
    match = re.search(r"var hlsUrl\s*=\s*['\"](.*?)['\"];", resp.text) or \
            re.search(r"hlsUrl\s*:\s*['\"](.*?)['\"];", resp.text) or \
            re.search(r"['\"]?(?:hls|video)Url['\"]?\s*[:=]\s*['\"](.*?)['\"]", resp.text)
            
    if not match:
        m3u8_matches = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', resp.text)
        if m3u8_matches:
            hls_url = m3u8_matches[0]
        else:
            raise HTTPException(status_code=500, detail="HLS URL not found")
    else:
        hls_url = match.group(1)
        
    if not hls_url.startswith('http'):
        parsed_url = urllib.parse.urlparse(url)
        hls_url = f"{parsed_url.scheme}://{parsed_url.netloc}{hls_url if hls_url.startswith('/') else '/' + hls_url}"
        
    base_url = str(request.base_url).rstrip('/')
    proxy_url = f"{base_url}/stream?url={urllib.parse.quote(hls_url)}"
    soup = BeautifulSoup(resp.text, 'html.parser')
    title = soup.title.string.replace(" - Jable.TV", "").replace(" - MissAV.com", "").replace(" - MissAV", "") if soup.title else "Video"
    formats = [{"id": "hls", "url": proxy_url, "ext": "m3u8", "height": 720, "note": "HLS"}]
    return {"title": title, "thumbnail": "", "formats": formats, "best_url": proxy_url}

async def get_info_ytdlp(url: str, request: Request):
    ydl_opts = {'quiet': True, 'no_warnings': True, 'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'}
    loop = asyncio.get_event_loop()
    try:
        data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False))
        formats = []
        base_url = str(request.base_url).rstrip('/')
        for f in data.get('formats', []):
            if f.get('url') and (f.get('ext') == 'mp4' or f.get('protocol') in ['m3u8_native', 'https']):
                orig_url = f.get('url')
                headers = f.get('http_headers') or data.get('http_headers') or {}
                proxy_url = f"{base_url}/stream?url={urllib.parse.quote(orig_url)}&headers={urllib.parse.quote(json.dumps(headers))}"
                formats.append({"id": f.get('format_id'), "url": proxy_url, "ext": f.get('ext'), "height": f.get('height'), "note": f.get('format_note') or f.get('resolution')})
        formats.sort(key=lambda x: x.get('height') or 0, reverse=True)
        return {"title": data.get('title'), "thumbnail": data.get('thumbnail'), "formats": formats, "best_url": formats[0]['url'] if formats else None}
    except Exception as e:
        logger.error(f"yt-dlp error for {url}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Routes ---

@app.get("/sites")
async def get_sites():
    return SITES

@app.get("/videos")
async def get_videos(site: str = "pornhub", page: int = 1):
    scraper = SCRAPERS.get(site)
    if not scraper: raise HTTPException(status_code=404, detail="Site not supported")
    try:
        videos = await scraper(page)
        if not videos: return []
        tasks = [fetch_image_as_base64(v['thumbnail']) for v in videos]
        b64_thumbnails = await asyncio.gather(*tasks)
        for i, v in enumerate(videos): v['thumbnail'] = b64_thumbnails[i]
        return videos
    except Exception as e:
        logger.error(f"Error scraping {site}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video_info")
async def get_video_info(request: Request, url: str):
    try:
        if "51cg1.com" in url: return await get_info_51cg1(url, request)
        if "jable.tv" in url or "missav.com" in url: return await get_info_jable_missav(url, request)
        if "porn.com" in url: return await get_info_porncom(url, request)
        return await get_info_ytdlp(url, request)
    except Exception as e:
        logger.error(f"Error extracting video info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stream")
async def stream_video(request: Request, url: str, headers: str = "{}"):
    try:
        header_dict = json.loads(headers)
        client_range = request.headers.get("Range")
        if client_range: header_dict["Range"] = client_range
        
        if "User-Agent" not in header_dict:
            header_dict["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        
        jable_domains = ["jable.tv", "mushroomtrack", "as-lefty.com", "mushroom-track", "mushroomtrack.com", "hot-box-gen", "fsvid.com", "vidth.com", "vidm.com"]
        missav_domains = ["missav.com", "missav.ai", "missav.li", "missav.ws", "surrit.com", "eight-box.com", "six-box.com", "nine-box.com", "seven-box.com"]
        
        is_jable = any(d in url for d in jable_domains) or "jable" in str(request.headers.get("Referer", ""))
        is_missav = any(d in url for d in missav_domains) or "missav" in str(request.headers.get("Referer", ""))
        
        if is_jable:
            header_dict["Referer"] = "https://jable.tv/"
        elif is_missav:
            header_dict["Referer"] = "https://missav.com/"

        async def stream_generator(source_url, source_headers):
            async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
                async with client.stream("GET", source_url, headers=source_headers) as response:
                    async for chunk in response.aiter_bytes(chunk_size=256*1024):
                        yield chunk

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as header_client:
            async with header_client.stream("GET", url, headers=header_dict) as source_resp:
                content_type = source_resp.headers.get("Content-Type", "")
                
                if "application/vnd.apple.mpegurl" in content_type or "application/x-mpegurl" in content_type or url.endswith(".m3u8"):
                    content = await source_resp.aread()
                    text_content = content.decode("utf-8", errors="ignore")
                    
                    parsed_source = urllib.parse.urlparse(str(source_resp.url))
                    base_url_dir = str(source_resp.url).rsplit('/', 1)[0]
                    local_base_url = str(request.base_url).rstrip('/')
                    
                    lines = text_content.splitlines()
                    new_lines = []
                    for line in lines:
                        if line.startswith("#EXT-X-KEY") or line.startswith("#EXT-X-MAP"):
                            uri_match = re.search(r'URI=["\'](.*?)["\']', line)
                            if uri_match:
                                original_uri = uri_match.group(1)
                                full_uri = original_uri
                                if not original_uri.startswith("http"):
                                    if original_uri.startswith("/"):
                                        full_uri = f"{parsed_source.scheme}://{parsed_source.netloc}{original_uri}"
                                    else:
                                        full_uri = f"{base_url_dir}/{original_uri}"
                                
                                encoded_headers = urllib.parse.quote(json.dumps(header_dict))
                                proxied_uri = f"{local_base_url}/stream?url={urllib.parse.quote(full_uri)}&headers={encoded_headers}"
                                line = line.replace(original_uri, proxied_uri)
                        elif line and not line.startswith("#"):
                            full_segment_url = line
                            if not line.startswith("http"):
                                if line.startswith("/"):
                                    full_segment_url = f"{parsed_source.scheme}://{parsed_source.netloc}{line}"
                                else:
                                    full_segment_url = f"{base_url_dir}/{line}"
                            
                            encoded_headers = urllib.parse.quote(json.dumps(header_dict))
                            line = f"{local_base_url}/stream?url={urllib.parse.quote(full_segment_url)}&headers={encoded_headers}"
                        new_lines.append(line)
                    
                    rewritten_content = "\n".join(new_lines).encode("utf-8")
                    return Response(content=rewritten_content, status_code=source_resp.status_code, headers={"Content-Type": content_type})
                
                forward_headers = {}
                for h in ["Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"]:
                    if h in source_resp.headers: forward_headers[h] = source_resp.headers[h]
                
                return StreamingResponse(stream_generator(url, header_dict), status_code=source_resp.status_code, headers=forward_headers, media_type=content_type)
    except Exception as e:
        logger.error(f"Stream error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
