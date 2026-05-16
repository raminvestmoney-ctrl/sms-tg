import asyncio
import random
import time
import os
import sys
from datetime import datetime
import aiohttp
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# --- CONFIGURATION ---
TARGET_DOMAIN = "investmoney.online"
DAILY_CAP = 1000  # Max successful hits per day (for local mode)
BATCH_SIZE_CI = 25 # Hits per GitHub Action run
MAX_CONCURRENT = 3 # Stable for both Local and GitHub Actions
MAX_RETRIES_PER_RUN = 100 # Prevent infinite loops in CI

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
total_attempts = 0
current_day = datetime.now().strftime("%Y-%m-%d")
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

async def fetch_proxies():
    print("[*] Refreshing Global Proxy Pool...")
    proxies = []
    async with aiohttp.ClientSession() as session:
        for url in PROXY_SOURCES:
            try:
                protocol = "socks5" if "socks5" in url else "http"
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        for line in text.splitlines():
                            line = line.strip()
                            if ":" in line:
                                proxies.append(f"{protocol}://{line}")
            except Exception as e:
                continue
    unique_proxies = list(set(proxies))
    print(f"[+] Loaded {len(unique_proxies)} unique proxies.")
    return unique_proxies

def get_stealth_config():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
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
        # Random scrolling
        for _ in range(random.randint(2, 5)):
            scroll_amount = random.randint(300, 800)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(1.5, 3.5))
        
        # Random mouse movement simulation (subtle)
        await page.mouse.move(random.randint(0, 500), random.randint(0, 500))
    except: pass

async def run_session(proxy_str, limit):
    global success_count, total_attempts
    if success_count >= limit: return

    async with semaphore:
        total_attempts += 1
        url = random.choice(TARGET_URLS)
        referrer = random.choice(REFERRERS)
        
        async with async_playwright() as p:
            browser = None
            try:
                # Retry logic for browser launch
                for attempt in range(3):
                    try:
                        browser = await p.chromium.launch(
                            headless=True, 
                            proxy={"server": proxy_str},
                            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox"]
                        )
                        if browser: break
                    except Exception as launch_err:
                        if attempt == 2: raise launch_err
                        await asyncio.sleep(2)

                context = await browser.new_context(
                    **get_stealth_config(), 
                    extra_http_headers={"Referer": referrer}
                )

                page = await context.new_page()
                await stealth_async(page)
                
                # Set a reasonable timeout for page load
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(random.uniform(2, 5))
                await human_interaction(page)
                
                # Internal Navigation (Deep Dive)
                if random.random() > 0.3:
                    links = await page.query_selector_all(f"a[href*='{TARGET_DOMAIN}']")
                    if links:
                        target_link = random.choice(links)
                        await target_link.click()
                        await page.wait_for_load_state("domcontentloaded", timeout=40000)
                        await human_interaction(page)
                
                success_count += 1
                print(f"[✓] Success: {success_count}/{limit} | Proxy: {proxy_str[:30]}...")
            except asyncio.TimeoutError:
                print(f"[!] Session timed out: {proxy_str[:30]}...")
            except Exception as e:
                # Silently log error type to avoid cluttering but help debugging if needed
                error_name = type(e).__name__
                if "Timeout" in error_name:
                    print(f"[!] Timeout with proxy: {proxy_str[:30]}...")
                else:
                    pass # Ignore other proxy errors
            finally:
                if browser:
                    try:
                        await browser.close()
                    except: pass

async def main():
    ci_mode = os.getenv("CI_MODE") == "true"
    limit = BATCH_SIZE_CI if ci_mode else DAILY_CAP
    max_attempts = MAX_RETRIES_PER_RUN if ci_mode else (DAILY_CAP * 5)
    session_timeout = 120 # 2 minutes per session max
    
    print(f"[*] Started Traffic Loader | Mode: {'GitHub Actions' if ci_mode else 'Local'}")
    print(f"[*] Target for this session: {limit} successful hits.")
    
    proxies = await fetch_proxies()
    if not proxies:
        print("[!] No proxies found. Exiting.")
        return

    while success_count < limit and total_attempts < max_attempts:
        # Take a batch of proxies
        batch_size = min(len(proxies), MAX_CONCURRENT * 2)
        batch = random.sample(proxies, batch_size)
        
        # Wrap each session in a timeout to ensure nothing hangs
        tasks = [asyncio.wait_for(run_session(p, limit), timeout=session_timeout) for p in batch]
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except:
            pass
        
        # Small cooldown between batches
        await asyncio.sleep(random.uniform(1, 3))

        
        if total_attempts >= max_attempts:
            print(f"[!] Reached max attempts ({max_attempts}). Stopping to avoid hanging.")
            break

    print(f"[*] Session Finished. Total Success: {success_count}/{limit} | Total Attempts: {total_attempts}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"[!!] Critical Error: {e}")


