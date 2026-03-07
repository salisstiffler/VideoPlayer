
import asyncio
import os
import httpx
from bs4 import BeautifulSoup
import logging

# Mock logger
class MockLogger:
    def info(self, msg): print(f"INFO: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")

logger = MockLogger()

async def test_headers():
    base_url = "https://spankbang.party"
    url = f"{base_url}/trending_videos/1/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://www.google.com/",
        "Sec-Ch-Ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    
    # Use httpx.AsyncClient without custom transport first to see if it works
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"Success! Length: {len(resp.text)}")
            else:
                print(f"Failed with {resp.status_code}")
                # print(f"Content: {resp.text[:500]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_headers())
