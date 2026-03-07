
import asyncio
import os
import httpx
from bs4 import BeautifulSoup
import logging
import sys

# Mock logger
class MockLogger:
    def info(self, msg): print(f"INFO: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")

logger = MockLogger()

def get_proxy():
    return os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("ALL_PROXY")

def get_client(headers=None, timeout=30.0, follow_redirects=True):
    proxy = get_proxy()
    mounts = {"all://": httpx.AsyncHTTPTransport(proxy=proxy)} if proxy else None
    return httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=follow_redirects, mounts=mounts)

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
            
            print(f"Found {len(video_items)} video items")
            
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

async def main():
    results = await scrape_spankbang(1)
    print(f"Scraped {len(results)} videos")
    for v in results[:3]:
        print(f" - {v['title']} ({v['duration']}) -> {v['url']}")

if __name__ == "__main__":
    asyncio.run(main())
