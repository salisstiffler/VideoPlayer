import httpx
import asyncio
from bs4 import BeautifulSoup
import os

def get_proxy():
    return os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("ALL_PROXY")

def get_client(headers=None, timeout=30.0):
    proxy = get_proxy()
    mounts = {"all://": httpx.AsyncHTTPTransport(proxy=proxy)} if proxy else None
    return httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True, mounts=mounts)

async def check_url(name, url):
    print(f"\n--- Checking {name}: {url} ---")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"}
    async with get_client(headers=headers) as client:
        try:
            resp = await client.get(url)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Look for links that might be videos
                links = [a.get('href') for a in soup.select('a') if a.get('href') and ('/video' in a.get('href') or '/hdporn' in a.get('href'))]
                print(f"Found {len(links)} potential video links.")
                if links: print(f"Sample links: {links[:5]}")
                
                # Check for thumbnails
                imgs = [img.get('src') or img.get('data-src') for img in soup.select('img') if img.get('src') or img.get('data-src')]
                print(f"Found {len(imgs)} images.")
        except Exception as e:
            print(f"Error: {e}")

async def main():
    # Try different combinations
    await check_url("thumbzilla_main", "https://www.thumbzilla.com/")
    await check_url("hqporner_main", "https://hqporner.com/")
    await check_url("tnaflix_main", "https://www.tnaflix.com/")

if __name__ == "__main__":
    asyncio.run(main())
