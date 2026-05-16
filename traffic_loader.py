import asyncio
import random
import string
import aiohttp
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# --- CONFIGURATION ---
TARGET_URLS = [
    "https://investmoney.online/articles/earn-100-daily-with-ai-agents-2026.html",
    "https://investmoney.online/articles/usa-tax-filing-masterclass-2026.html",
    "https://investmoney.online/articles/inflation-2026-how-to-beat-rising-prices.html"
]
BASE_URL = "https://investmoney.online/"
CONCURRENT_USERS = 10
TOTAL_VISITS = 1000
HEADLESS = True

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
]

async def fetch_proxies():
    print("[System] Fetching proxies...")
    proxies = []
    async with aiohttp.ClientSession() as session:
        for url in PROXY_SOURCES:
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        proxies.extend([f"http://{l.strip()}" for l in text.splitlines() if ":" in l])
            except Exception: continue
    return list(set(proxies))

async def simulate_human_behavior(page):
    try:
        for _ in range(random.randint(3, 7)):
            await page.mouse.wheel(0, random.randint(300, 700))
            await asyncio.sleep(random.uniform(2, 4))
    except: pass

async def run_visitor(visitor_id, p, proxy_list):
    proxy = random.choice(proxy_list) if proxy_list else None
    ua = random.choice(USER_AGENTS)
    target = random.choice(TARGET_URLS)
    
    browser = None
    try:
        browser = await p.chromium.launch(
            headless=HEADLESS, 
            proxy={"server": proxy} if proxy else None,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(user_agent=ua)
        page = await context.new_page()
        
        # Apply Stealth
        await stealth_async(page)
        
        # Add Client Hints for Vercel
        await context.set_extra_http_headers({
            "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Upgrade-Insecure-Requests": "1"
        })

        print(f"[Visitor {visitor_id}] Loading via {proxy[:20]}...")
        await page.goto(target, wait_until="domcontentloaded", referer="https://l.facebook.com/")
        await simulate_human_behavior(page)
        await asyncio.sleep(random.randint(30, 60))
        return True
    except Exception as e:
        print(f"[Visitor {visitor_id}] Failed: {str(e)[:30]}")
        return False
    finally:
        if browser: await browser.close()

async def main():
    proxy_list = await fetch_proxies()
    async with async_playwright() as p:
        sem = asyncio.Semaphore(CONCURRENT_USERS)
        
        async def bounded_visitor(v_id):
            async with sem:
                return await run_visitor(v_id, p, proxy_list)
        
        tasks = [bounded_visitor(i + 1) for i in range(TOTAL_VISITS)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
