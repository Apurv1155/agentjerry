import time
import random
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# CONFIG
# ==============================
KEYWORDS = [
    "Motor repair Ahmedabad",
    "Pump repair Ahmedabad",
    "Engine repair Ahmedabad",
    "Industrial maintenance Ahmedabad",
    "Automobile service Ahmedabad",
    "Mechanical workshop Ahmedabad",
    "HVAC repair Ahmedabad",
    "Compressor service Ahmedabad",
    "Manufacturing plant Ahmedabad",
    "Fabrication industry Ahmedabad",
    "Machine repair Ahmedabad",
    "Hydraulic service Ahmedabad"
]

MAX_RESULTS = 20
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
OUTPUT_FILE = "gasket_business_leads.xlsx"

def pause(a=2, b=4):
    time.sleep(random.uniform(a, b))

def extract_email(text):
    emails = EMAIL_REGEX.findall(text)
    return list(set(emails))

# ==============================
# CHROME SETUP (HEADLESS)
# ==============================
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--start-maximized")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 15)

# ==============================
# SCRAPING LOGIC
# ==============================
all_data = []

for keyword in KEYWORDS:
    driver.get(f"https://www.google.com/maps/search/{keyword.replace(' ','+')}")
    pause(5,7)

    # Wait for first results to appear
    try:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[role="article"]')))
    except:
        continue

    businesses = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')[:MAX_RESULTS]

    for biz in businesses:
        try:
            name = biz.find_element(By.CSS_SELECTOR, 'h3 span').text
        except:
            name = ""
        try:
            address = biz.find_element(By.CSS_SELECTOR, '.Io6YTe.fontBodyMedium').text
        except:
            address = ""
        try:
            phone_btn = biz.find_element(By.CSS_SELECTOR, 'button[data-tooltip="Copy phone number"]')
            phone = phone_btn.get_attribute("aria-label")
        except:
            phone = ""
        try:
            website_btn = biz.find_element(By.CSS_SELECTOR, 'a[data-tooltip="Open website"]')
            website = website_btn.get_attribute("href")
        except:
            website = ""

        # Extract public email from website
        email = ""
        if website:
            try:
                driver.get(website)
                pause(3,5)
                page_text = driver.page_source
                emails = extract_email(page_text)
                if emails:
                    email = emails[0]
            except:
                email = ""

        all_data.append([name, address, phone, email, website])
        pause(1,2)  # small delay per business

# ==============================
# SAVE TO EXCEL
# ==============================
df = pd.DataFrame(all_data, columns=["Business Name", "Address", "Phone", "Email", "Website"])
df.to_excel(OUTPUT_FILE, index=False)

driver.quit()
print(f"Data collected for {len(all_data)} businesses. Saved to {OUTPUT_FILE}")
