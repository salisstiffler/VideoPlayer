import json
import asyncio
import httpx
import base64
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Optional
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

SITES = [
    {"id": "pornhub", "name": "Pornhub", "url": "https://www.pornhub.com/video"},
    {"id": "xvideos", "name": "XVideos", "url": "https://www.xvideos.com/"},
    {"id": "xnxx", "name": "XNXX", "url": "https://www.xnxx.com/"},
    {"id": "51cg1", "name": "51cg1", "url": "https://51cg1.com/"},
]

async def fetch_image_as_base64(url: str) -> str:
    """Helper to fetch a remote image and return it as a base64 data URI."""
    if not url or url.startswith('data:image'):
        return url
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            if resp.status_code == 200:
                content_type = resp.headers.get("Content-Type", "image/jpeg")
                b64 = base64.b64encode(resp.content).decode('utf-8')
                return f"data:{content_type};base64,{b64}"
    except Exception as e:
        logger.error(f"Failed to fetch image {url}: {e}")
    return url

@app.get("/sites")
async def get_sites():
    return SITES

async def scrape_pornhub(page: int = 1):
    url = f"https://www.pornhub.com/video?page={page}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch Pornhub: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch Pornhub")
        
        soup = BeautifulSoup(response.text, 'html.parser')
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
            duration_tag = item.select_one('.duration')
            duration = duration_tag.text.strip() if duration_tag else ""
            
            results.append({
                "id": video_id, "title": title, "thumbnail": thumbnail,
                "url": link, "duration": duration, "site": "pornhub"
            })
        return results

async def scrape_xvideos_xnxx(site_id: str, page: int = 1):
    """Unified scraper for XVideos and XNXX as they share the same layout."""
    base_domain = "https://www.xvideos.com" if site_id == "xvideos" else "https://www.xnxx.com"
    if page == 1:
        url = f"{base_domain}/hits"
    else:
        url = f"{base_domain}/hits/{page-1}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": f"{base_domain}/",
    }
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch {site_id.upper()}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch {site_id.upper()}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        video_items = soup.select('.mozaique .thumb-block')
        
        results = []
        for item in video_items:
            # Skip non-video blocks (like ads or cats)
            if 'thumb-cat' in item.get('class', []) or 'thumb-ad' in item.get('class', []):
                continue
                
            video_id = item.get('data-id')
            
            # Title & Link: Usually in .thumb-under p a
            title_tag = item.select_one('.thumb-under p a') or item.select_one('.thumb a')
            if not title_tag: continue
            
            title = title_tag.get('title', '').strip() or title_tag.text.strip()
            href = title_tag.get('href', '')
            if not href or href == '#': continue
            
            link = href if href.startswith('http') else base_domain + href
            
            # Thumbnail: Try data-mzl (mozaique listing), then data-src, then src
            img_tag = item.select_one('img')
            thumbnail = ""
            if img_tag:
                thumbnail = img_tag.get('data-mzl') or img_tag.get('data-src') or img_tag.get('src', '')
            
            # Duration: In .metadata p
            metadata = item.select_one('.metadata')
            duration = ""
            if metadata:
                # Duration is usually text nodes directly in metadata or a specific span
                duration_text = metadata.get_text(strip=True)
                # Regex to find time pattern (e.g. 10min, 1h 20min)
                m = re.search(r'(\d+(?:h\s*)?\d*min)', duration_text)
                duration = m.group(1) if m else duration_text.split('\n')[-1].strip()

            results.append({
                "id": video_id or link,
                "title": title,
                "thumbnail": thumbnail,
                "url": link,
                "duration": duration,
                "site": site_id
            })
        return results

async def scrape_51cg1(page: int = 1):
    url = f"https://51cg1.com/page/{page}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    }
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch 51cg1: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch 51cg1")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        video_items = soup.select('div.post-card')
        
        results = []
        for item in video_items:
            parent_a = item.find_parent('a')
            if not parent_a: continue
            link = parent_a.get('href', '')
            if not link.startswith('http'): link = "https://51cg1.com" + link
            video_id = link.rstrip('/').split('/')[-1]
            title_tag = item.select_one('.post-card-title')
            if not title_tag: continue
            title = title_tag.get_text(" ", strip=True).replace("热搜 HOT", "").strip()
            
            thumbnail = ""
            bg_div = item.select_one('.blog-background')
            if bg_div and bg_div.get('style'):
                style = bg_div['style']
                match = re.search(r'url\([\'"&quot;]*(.+?)[\'"&quot;]*\)', style)
                if match:
                    thumbnail = match.group(1)

            results.append({
                "id": video_id, "title": title, "thumbnail": thumbnail,
                "url": link, "duration": "", "site": "51cg1"
            })
        return results

@app.get("/videos")
async def get_videos(site: str = "pornhub", page: int = 1):
    videos = []
    if site == "pornhub": 
        videos = await scrape_pornhub(page)
    elif site == "xvideos":
        videos = await scrape_xvideos_xnxx("xvideos", page)
    elif site == "xnxx":
        videos = await scrape_xvideos_xnxx("xnxx", page)
    elif site == "51cg1":
        videos = await scrape_51cg1(page)
    
    if not videos:
        return []

    # Convert ALL thumbnails to base64 before returning
    tasks = [fetch_image_as_base64(v['thumbnail']) for v in videos]
    b64_thumbnails = await asyncio.gather(*tasks)
    
    for i, v in enumerate(videos):
        v['thumbnail'] = b64_thumbnails[i]
        
    return videos

@app.get("/video_info")
async def get_video_info(request: Request, url: str):
    if "51cg1.com" in url:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            players = soup.select('div.dplayer')
            formats = []
            base_url = str(request.base_url).rstrip('/')
            
            for i, player in enumerate(players):
                video_url = ""
                config_str = player.get('data-config')
                if config_str:
                    try:
                        config_str = config_str.replace('&quot;', '"')
                        config = json.loads(config_str)
                        video_url = config.get('video', {}).get('url', '')
                    except: pass
                
                if not video_url:
                    video_tag = player.select_one('video')
                    if video_tag: video_url = video_tag.get('src', '')
                
                if video_url:
                    proxy_url = f"{base_url}/stream?url={urllib.parse.quote(video_url)}"
                    note = player.get('data-video_title', f"Source {i+1}")
                    note = note.split("！")[-1] if "！" in note else note
                    formats.append({
                        "id": player.get('data-video_id', f"51cg_{i}"),
                        "url": proxy_url, "ext": "m3u8" if "m3u8" in video_url else "mp4",
                        "height": 720 + (i * 360), "note": note,
                    })
            
            return {
                "title": soup.title.string if soup.title else "51cg1 Video",
                "thumbnail": "", "formats": formats, "best_url": formats[0]['url'] if formats else None
            }
        except Exception as e:
            logger.error(f"Error parsing 51cg1 detail: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    ydl_opts = {
        'quiet': True, 'no_warnings': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    }
    try:
        def extract_info():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, extract_info)
        formats = []
        base_url = str(request.base_url).rstrip('/')
        for f in data.get('formats', []):
            if f.get('url') and (f.get('ext') == 'mp4' or f.get('protocol') in ['m3u8_native', 'https']):
                original_url = f.get('url')
                headers = f.get('http_headers') or data.get('http_headers') or {}
                proxy_url = f"{base_url}/stream?url={urllib.parse.quote(original_url)}&headers={urllib.parse.quote(json.dumps(headers))}"
                formats.append({
                    "id": f.get('format_id'), "url": proxy_url, "ext": f.get('ext'),
                    "height": f.get('height'), "note": f.get('format_note') or f.get('resolution') or f.get('format_id'),
                })
        formats.sort(key=lambda x: x.get('height') or 0, reverse=True)
        return {
            "title": data.get('title'), "thumbnail": data.get('thumbnail'),
            "formats": formats, "best_url": formats[0]['url'] if formats else None
        }
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
            header_dict["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

        async def stream_generator(source_url, source_headers):
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", source_url, headers=source_headers, follow_redirects=True) as response:
                    async for chunk in response.aiter_bytes(chunk_size=256*1024):
                        yield chunk

        async with httpx.AsyncClient(timeout=10.0) as header_client:
            async with header_client.stream("GET", url, headers=header_dict, follow_redirects=True) as source_resp:
                content_type = source_resp.headers.get("Content-Type", "")
                if "application/vnd.apple.mpegurl" in content_type or "application/x-mpegurl" in content_type or url.endswith(".m3u8"):
                    content = await source_resp.aread()
                    text_content = content.decode("utf-8", errors="ignore")
                    base_url = str(source_resp.url).rsplit('/', 1)[0]
                    lines = text_content.splitlines()
                    new_lines = []
                    for line in lines:
                        if line and not line.startswith("#"):
                            if not line.startswith("http"):
                                if line.startswith("/"):
                                    parsed_url = urllib.parse.urlparse(url)
                                    line = f"{parsed_url.scheme}://{parsed_url.netloc}{line}"
                                else:
                                    line = f"{base_url}/{line}"
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
