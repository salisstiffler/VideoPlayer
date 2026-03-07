import asyncio
import os
import httpx
from bs4 import BeautifulSoup

def get_proxy():
    return os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("ALL_PROXY")

def get_client(headers=None, timeout=30.0):
    proxy = get_proxy()
    mounts = {"all://": httpx.AsyncHTTPTransport(proxy=proxy)} if proxy else None
    return httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True, mounts=mounts)

async def debug_thumbzilla():
    print("\n--- Debugging Thumbzilla ---")
    url = "https://www.thumbzilla.com/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"}
    async with get_client(headers=headers) as client:
        resp = await client.get(url)
        print(f"Status: {resp.status_code}")
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Test selectors
        video_items = soup.select('.video-item') or soup.select('li.videoblock') or soup.select('div.item')
        print(f"Found {len(video_items)} raw items")
        
        for i, item in enumerate(video_items[:3]):
            print(f"Item {i}: class={item.get('class')}")
            a_tag = item.select_one('a.linkVideoThumb') or item.select_one('a[href*="/video/"]')
            if not a_tag:
                # Try finding any a tag
                print(f"  No a_tag matching criteria. Found a tags: {[a.get('href') for a in item.select('a')]}")
                continue
                
            href = a_tag.get('href', '')
            print(f"  Href: {href}")
            title = a_tag.get('title', '')
            print(f"  Title: {title}")

async def debug_hqporner():
    print("\n--- Debugging HQPorner ---")
    url = "https://hqporner.com/"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with get_client(headers=headers) as client:
        resp = await client.get(url)
        print(f"Status: {resp.status_code}")
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        video_items = soup.select('.video-item') or soup.select('div.post') or soup.select('li.item')
        print(f"Found {len(video_items)} raw items")
        
        for i, item in enumerate(video_items[:3]):
            print(f"Item {i}: class={item.get('class')}")
            a_tag = item.select_one('a[href*="/hdporn/"]')
            if not a_tag:
                print(f"  No a_tag matching /hdporn/. Found a tags: {[a.get('href') for a in item.select('a')]}")
                continue
            print(f"  Href: {a_tag.get('href')}")

async def debug_tnaflix():
    print("\n--- Debugging TNAFlix ---")
    url = "https://www.tnaflix.com/most-recent/"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with get_client(headers=headers) as client:
        resp = await client.get(url)
        print(f"Status: {resp.status_code}")
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        video_items = soup.select('.video-item') or soup.select('div[data-id]') or soup.select('li.video-item')
        print(f"Found {len(video_items)} raw items")
        
        for i, item in enumerate(video_items[:3]):
            print(f"Item {i}: class={item.get('class')}")
            a_tag = item.select_one('a[href*="/video"]')
            if not a_tag:
                 print(f"  No a_tag matching /video. Found a tags: {[a.get('href') for a in item.select('a')]}")
                 continue
            print(f"  Href: {a_tag.get('href')}")

async def main():
    await debug_thumbzilla()
    await debug_hqporner()
    await debug_tnaflix()

if __name__ == "__main__":
    asyncio.run(main())
