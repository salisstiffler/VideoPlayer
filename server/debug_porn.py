import httpx
import asyncio
import re
from bs4 import BeautifulSoup

async def debug_porncom():
    url = "https://www.porn.com/videos/milf-creampie-3069111"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Referer": "https://www.porn.com/"
    }
    
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        print("Visiting home page for cookies...")
        await client.get("https://www.porn.com/")
        
        print(f"Fetching video page: {url}")
        resp = await client.get(url)
        print(f"Status Code: {resp.status_code}")
        
        with open("porn_debug.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        
        print("HTML saved to porn_debug.html")
        
        # Check if it's the age gate
        if "AGE VERIFICATION" in resp.text:
            print("Detected AGE GATE!")
        
        # Test the regex
        match = re.search(r'["\']?(?:file|url|video_url|source)["\']?\s*[:=]\s*["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', resp.text, re.I)
        if match:
            print(f"Found via regex: {match.group(1)}")
        else:
            print("Regex failed to find video URL.")
            
        all_links = re.findall(r'https?://[^\s\'"]+\.(?:m3u8|mp4)[^\s\'"]*', resp.text, re.I)
        print(f"Found {len(all_links)} total m3u8/mp4 links.")
        if all_links:
            print(f"First 3 links: {all_links[:3]}")

if __name__ == "__main__":
    asyncio.run(debug_porncom())
