import asyncio
import os
import httpx

def get_proxy():
    return os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("ALL_PROXY")

def get_client(headers=None, timeout=30.0):
    proxy = get_proxy()
    mounts = {"all://": httpx.AsyncHTTPTransport(proxy=proxy)} if proxy else None
    return httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True, mounts=mounts)

async def dump_thumbzilla():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"}
    async with get_client(headers=headers) as client:
        resp = await client.get("https://www.thumbzilla.com/")
        with open("thumbzilla_home.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print(f"Dumped {len(resp.text)} chars to thumbzilla_home.html")

if __name__ == "__main__":
    asyncio.run(dump_thumbzilla())
