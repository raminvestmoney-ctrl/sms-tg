import asyncio
import random
import time
import os
from datetime import datetime
import aiohttp
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# --- CONFIGURATION ---
TARGET_DOMAIN = "investmoney.online"
DAILY_CAP = 1000  # Max successful hits per day (for local mode)
BATCH_SIZE_CI = 25 # Hits per GitHub Action run
MAX_CONCURRENT = 3 # Stable for both Local and GitHub Actions

# ... existing configurations ...
TARGET_URLS = [
    f"https://{TARGET_DOMAIN}/",
    f"https://{TARGET_DOMAIN}/passive-income-in-usd-from-pakistan-7-methods-that-actually-pay-in-2026/",
    f"https://{TARGET_DOMAIN}/how-to-earn-money-online-in-pakistan-for-students-without-investment-2026-guide/",
    f"https://{TARGET_DOMAIN}/top-7-ways-to-earn-money-online-in-pakistan-for-students-in-2026/"
]

REFERRERS = [
    "https://www.google.com/search?q=earn+money+online+pakistan",
    "https://www.bing.com/search?q=passive+income+pakistan+2026",
    "https://www.facebook.com/",
    "https://www.reddit.com/r/pakistan/",
    "https://t.co/",
    "https://www.linkedin.com/",
    "https://www.pinterest.com/"
]

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all"
]

# --- GLOBAL STATE ---
success_count = 0
current_day = datetime.now().strftime("%Y-%m-%d")
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

async def fetch_proxies():
    print("[*] Refreshing Global Proxy Pool...")
    proxies = []
    async with aiohttp.ClientSession() as session:
        for url in PROXY_SOURCES:
            try:
                protocol = "socks5" if "socks5" in url else "http"
                async with session.get(url, timeout=10) as resp:
                    text = await resp.text()
                    for line in text.splitlines():
                        if ":" in line:
                            proxies.append(f"{protocol}://{line.strip()}")
            except: continue
    unique_proxies = list(set(proxies))
    print(f"[+] Loaded {len(unique_proxies)} unique proxies.")
    return unique_proxies

def get_stealth_config():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
    ]
    return {
        "user_agent": random.choice(user_agents),
        "viewport": {'width': random.randint(1366, 1920), 'height': random.randint(768, 1080)},
        "extra_http_headers": {
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "DNT": "1"
        }
    }

async def human_interaction(page):
    try:
        for _ in range(random.randint(2, 4)):
            await page.evaluate(f"window.scrollBy(0, {random.randint(200, 500)})")
            await asyncio.sleep(random.uniform(2.0, 4.0))
    except: pass

async def run_session(proxy_str, limit):
    global success_count
    if success_count >= limit: return

    async with semaphore:
        url = random.choice(TARGET_URLS)
        referrer = random.choice(REFERRERS)
        async with async_playwright() as p:
            browser = None
            try:
                browser = await p.chromium.launch(headless=True, proxy={"server": proxy_str})
                context = await browser.new_context(**get_stealth_config(), extra_http_headers={"Referer": referrer})
                page = await context.new_page()
                await stealth_async(page)
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await human_interaction(page)
                
                # Deep Dive
                links = await page.query_selector_all(f"a[href*='{TARGET_DOMAIN}']")
                if links and random.random() > 0.4:
                    target = random.choice(links)
                    await target.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
                    await human_interaction(page)
                
                success_count += 1
                print(f"[✓] Success: {success_count}/{limit} | {proxy_str}")
            except: pass
            finally:
                if browser: await browser.close()

async def main():
    ci_mode = os.getenv("CI_MODE") == "true"
    limit = BATCH_SIZE_CI if ci_mode else DAILY_CAP
    
    print(f"[*] Mode: {'GitHub Actions' if ci_mode else 'Local/Cloud'}")
    print(f"[*] Target for this run: {limit} hits.")
    
    proxies = await fetch_proxies()
    if not proxies: return

    while success_count < limit:
        batch = random.sample(proxies, min(len(proxies), MAX_CONCURRENT * 2))
        tasks = [run_session(p, limit) for p in batch]
        await asyncio.gather(*tasks)
        if ci_mode: await asyncio.sleep(2)
        else: await asyncio.sleep(10)

    print(f"[*] Target Reached ({success_count}). Exiting.")

if __name__ == "__main__":
    asyncio.run(main())

