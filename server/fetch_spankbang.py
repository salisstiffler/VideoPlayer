
import httpx
import asyncio

async def fetch():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Referer": "https://spankbang.com/",
    }
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        try:
            resp = await client.get("https://spankbang.com/trending_videos/1/")
            with open("spankbang_debug.html", "w", encoding="utf-8") as f:
                f.write(resp.text)
            print(f"Status: {resp.status_code}")
            print(f"First 500 chars: {resp.text[:500]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(fetch())
