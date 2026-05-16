import time
import csv
from playwright.sync_api import sync_playwright

# --- CONFIGURATION (Inhe change karein) ---
LOGIN_URL = "https://www.np-enterprises.in/thegentleman/login.php"
SERVICE_URL = "https://www.np-enterprises.in/thegentleman/dashboard.php" # Isse sahi service page URL se badal dein

USERNAME = "YOUR_USERNAME_HERE"
PASSWORD = "YOUR_PASSWORD_HERE"

# Sahi IDs yahan likhein (Aap Inspect Element se dekh sakte hain)
ID_USERNAME_BOX = 'input[name="username"]' # Example: '#username' ya 'input[name="user"]'
ID_PASSWORD_BOX = 'input[name="password"]' # Example: '#password'
ID_LOGIN_BUTTON = 'button[type="submit"]'  # Example: '#login'

ID_NUMBER_INPUT = 'input[name="number"]'   # Jahan number dalna hai
ID_SEARCH_BUTTON = 'button#search'          # Search wala button
ID_RESULT_AREA = '.result-data'             # Jahan result show hota hai
# -------------------------------------------

def run_automation():
    with sync_playwright() as p:
        # Browser open karein (headless=False taaki aap dekh saken kya ho raha hai)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("Opening Login Page...")
        page.goto(LOGIN_URL)

        # Login process
        try:
            page.fill(ID_USERNAME_BOX, USERNAME)
            page.fill(ID_PASSWORD_BOX, PASSWORD)
            page.click(ID_LOGIN_BUTTON)
            page.wait_for_load_state("networkidle")
            print("Login Successful!")
        except Exception as e:
            print(f"Login failed: {e}")
            return

        # Go to service page if different
        page.goto(SERVICE_URL)

        # Read numbers from your CSV
        numbers = []
        with open('numbers_list.csv', 'r') as f:
            reader = csv.reader(f)
            next(reader) # Skip header
            for row in reader:
                if row: numbers.append(row[0].strip())

        results_data = []

        print(f"Starting checks for {len(numbers)} numbers...")
        for num in numbers:
            try:
                print(f"Checking: {num}")
                page.fill(ID_NUMBER_INPUT, num)
                page.click(ID_SEARCH_BUTTON)
                
                # Result ka wait karein (adjust time if slow)
                page.wait_for_selector(ID_RESULT_AREA, timeout=10000)
                
                result_text = page.inner_text(ID_RESULT_AREA)
                print(f"Result for {num}: {result_text[:50]}...")
                
                results_data.append([num, result_text.replace('\n', ' ')])
                
                # Clear for next number or refresh
                page.reload() 
            except Exception as e:
                print(f"Error checking {num}: {e}")
                results_data.append([num, "ERROR"])

        # Save results to a new CSV
        with open('checked_results.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Number", "Details"])
            writer.writerows(results_data)

        print("Automation Complete! Results saved in 'checked_results.csv'")
        browser.close()

if __name__ == "__main__":
    run_automation()
