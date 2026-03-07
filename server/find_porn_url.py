import httpx
import asyncio
from bs4 import BeautifulSoup

async def get_valid_url():
    url = "https://www.porn.com/videos"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"}
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        await client.get("https://www.porn.com/")
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_items = soup.select('.list-global__item')
        if video_items:
            print("First item all links:")
            for a in video_items[0].select('a'):
                print(f"HREF: {a.get('href')} | TITLE: {a.get('title')} | TEXT: {a.text.strip()}")
                link = a.get('href', '')
                if any(char.isdigit() for char in link) and not "report" in link:
                    if not link.startswith('http'): link = "https://www.porn.com" + (link if link.startswith('/') else '/' + link)
                    return link
    return None

if __name__ == "__main__":
    link = asyncio.run(get_valid_url())
    if link:
        print(f"SUCCESS_URL:{link}")
    else:
        print("FAILED_TO_FIND_URL")
