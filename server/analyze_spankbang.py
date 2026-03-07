
import asyncio
import os
import httpx
from bs4 import BeautifulSoup
from collections import Counter
import re

def get_proxy():
    # In Windows environment, we may need to check more environment variables
    return os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("ALL_PROXY")

def get_client(headers=None, timeout=30.0):
    proxy = get_proxy()
    mounts = {"all://": httpx.AsyncHTTPTransport(proxy=proxy)} if proxy else None
    return httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True, mounts=mounts)

async def analyze_structure(name, url):
    print(f"\n--- Analyzing {name}: {url} ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/",
    }
    async with get_client(headers=headers) as client:
        try:
            resp = await client.get(url)
            print(f"Status: {resp.status_code}")
            if resp.status_code != 200: 
                print(f"Content: {resp.text[:500]}")
                return

            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Count classes on divs and lis to find video containers
            classes = Counter()
            for tag in soup.find_all(['div', 'li', 'a', 'article', 'section']):
                c_list = tag.get('class')
                if c_list:
                    if isinstance(c_list, list):
                        classes.update(c_list)
                    else:
                        classes.update([c_list])
            
            print("Most common classes:")
            for cls, count in classes.most_common(10):
                print(f"  {cls}: {count}")
                
            # Try to find a link that looks like a video
            print("\nPotential video links:")
            video_links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/video/' in href or '/v/' in href or (re.search(r'/\w{5,}/', href) and not href.startswith('http') and len(href) > 10):
                    video_links.append(href)
            
            for l in video_links[:10]:
                print(f"  {l}")
        except Exception as e:
            print(f"Error: {e}")

async def main():
    await analyze_structure("SpankBang", "https://spankbang.com/trending_videos/1/")

if __name__ == "__main__":
    asyncio.run(main())
