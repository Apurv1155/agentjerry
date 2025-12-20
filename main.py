import time
import random
import re
import os
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# CONFIG KEYWORDS (Ahmedabad Gasket Related)
# ==============================
KEYWORDS = [
    "Drone propellers india",
    "Wooden furniture frame india",
    "Steel fabrication india"
]

SEARCH_KEYWORD = random.choice(KEYWORDS)
MAX_RESULTS = 30
OUTPUT_FILE = "gasket_business_leads.xlsx"
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Email account to send Excel
ADMIN_EMAIL = "faceapp0011@gmail.com"
ADMIN_PASSWORD = "ytup bjrd pupf tuuj"
RECEIVER_EMAIL = "walaapurv@gmail.com"

# ==============================
# HELPER FUNCTIONS
# ==============================
def pause(a=2, b=5):
    time.sleep(random.uniform(a, b))

def extract_email(text):
    emails = EMAIL_REGEX.findall(text)
    return list(set(emails))

# ==============================
# CHROME SETUP
# ==============================
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)
wait = WebDriverWait(driver, 30)

# ==============================
# GOOGLE MAPS SEARCH
# ==============================
driver.get("https://www.google.com/maps")
wait.until(EC.presence_of_element_located((By.ID, "searchboxinput")))
pause()

search = driver.find_element(By.ID, "searchboxinput")
for ch in SEARCH_KEYWORD:
    search.send_keys(ch)
    time.sleep(random.uniform(0.1, 0.25))
search.send_keys(Keys.ENTER)
pause(6, 9)

results_panel = wait.until(
    EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
)

# ==============================
# COLLECT PLACE LINKS
# ==============================
place_links = set()

while len(place_links) < MAX_RESULTS * 2:
    cards = driver.find_elements(By.XPATH, '//a[contains(@href,"/maps/place/")]')
    for c in cards:
        href = c.get_attribute("href")
        if href:
            place_links.add(href)

    driver.execute_script("arguments[0].scrollTop += 1500", results_panel)
    pause(2, 4)

# ==============================
# SCRAPE BUSINESS DETAILS
# ==============================
leads = []

for link in place_links:
    if len(leads) >= MAX_RESULTS:
        break

    driver.execute_script("window.open(arguments[0]);", link)
    driver.switch_to.window(driver.window_handles[1])

    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//h1")))
    except:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        continue

    pause(2, 4)
    business_name = driver.find_element(By.XPATH, "//h1").text.strip()

    def safe_text(xpath):
        try:
            return driver.find_element(By.XPATH, xpath).text.strip()
        except:
            return ""

    phone = safe_text('//button[contains(@data-item-id,"phone")]')
    address = safe_text('//button[@data-item-id="address"]')

    website_links = driver.find_elements(By.XPATH, '//a[contains(@aria-label,"Website")]')
    if not website_links or not phone:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        continue

    website_url = website_links[0].get_attribute("href")
    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    # Visit website pages to find emails
    pages_to_check = [
        website_url,
        website_url.rstrip("/") + "/contact",
        website_url.rstrip("/") + "/about"
    ]

    email_found = ""
    for page in pages_to_check:
        try:
            driver.get(page)
            pause(3, 6)
            page_source = driver.page_source
            emails = extract_email(page_source)
            if emails:
                email_found = emails[0]
                break
        except:
            continue

    if email_found:
        leads.append({
            "Business Name": business_name,
            "Phone": phone,
            "Address": address,
            "Email": email_found,
            "Website": website_url,
            "Source URL": page
        })

pause()
driver.quit()

# ==============================
# SAVE TO EXCEL / GOOGLE SHEET
# ==============================
df = pd.DataFrame(leads)
df.to_excel(OUTPUT_FILE, index=False)

# ==============================
# SEND EXCEL TO YOUR EMAIL
# ==============================
msg = MIMEMultipart()
msg["From"] = f"Jerry <{ADMIN_EMAIL}>"
msg["To"] = RECEIVER_EMAIL
msg["Subject"] = f"Business Leads - {SEARCH_KEYWORD}"

body = f"""
Hello Apurv Sir,

Please find attached the gasket-related business leads collected from Google Maps.
Keyword used: {SEARCH_KEYWORD}
Total leads collected: {len(leads)}

Regards,
Jerry
"""
msg.attach(MIMEText(body, "plain"))

with open(OUTPUT_FILE, "rb") as f:
    part = MIMEBase("application", "octet-stream")
    part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{OUTPUT_FILE}"')
    msg.attach(part)

server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login(ADMIN_EMAIL, ADMIN_PASSWORD)
server.send_message(msg)
server.quit()

os.remove(OUTPUT_FILE)
print(f"✅ Extraction & email completed. Total leads: {len(leads)}")
