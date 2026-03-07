import httpx
import asyncio
from bs4 import BeautifulSoup
import os

# Set proxy for local testing if needed
# os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"

def get_proxy():
    return os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("ALL_PROXY")

def get_client(headers=None, timeout=30.0):
    proxy = get_proxy()
    mounts = {"all://": httpx.AsyncHTTPTransport(proxy=proxy)} if proxy else None
    return httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True, mounts=mounts)

async def debug_site(name, url):
    print(f"\n--- Debugging {name}: {url} ---")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"}
    async with get_client(headers=headers) as client:
        try:
            resp = await client.get(url)
            print(f"Status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"Error content: {resp.text[:200]}")
                return
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            if name == "thumbzilla":
                items = soup.select('li.videoblock') or soup.select('.video-item') or soup.select('a.linkVideoThumb')
                print(f"Found {len(items)} potential items")
                if items: print(str(items[0])[:500])
                
            elif name == "hqporner":
                items = soup.select('.video-item') or soup.select('div.post') or soup.select('a[href*="/hdporn/"]')
                print(f"Found {len(items)} potential items")
                if items: print(str(items[0])[:500])
                
            elif name == "tnaflix":
                items = soup.select('.video-item') or soup.select('div[data-id]') or soup.select('li.video-item')
                print(f"Found {len(items)} potential items")
                if items: print(str(items[0])[:500])
                
        except Exception as e:
            print(f"Failed to fetch {name}: {e}")

async def main():
    await debug_site("thumbzilla", "https://www.thumbzilla.com/video")
    await debug_site("hqporner", "https://hqporner.com/latest/1/")
    await debug_site("tnaflix", "https://www.tnaflix.com/most-recent/1")

if __name__ == "__main__":
    asyncio.run(main())
