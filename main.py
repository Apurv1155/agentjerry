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
# CONFIG KEYWORDS
# ==============================
KEYWORDS = [
    "Drone propellers india",
    "Drone propellers india"
]

SEARCH_KEYWORD = random.choice(KEYWORDS)
MAX_RESULTS = 30
OUTPUT_FILE = "gasket_business_leads.xlsx"

# Improved email regex (matches most common formats)
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')

ADMIN_EMAIL = "faceapp0011@gmail.com"
ADMIN_PASSWORD = "ytup bjrd pupf tuuj"
RECEIVER_EMAIL = "walaapurv@gmail.com"

# ==============================
# HELPERS
# ==============================
def pause(a=2, b=5):
    time.sleep(random.uniform(a, b))

def extract_email(text):
    if not text:
        return []
    # Find all emails and remove duplicates
    emails = EMAIL_REGEX.findall(text)
    # Clean: lowercase, strip, remove obvious garbage
    cleaned = []
    for email in emails:
        email = email.strip().lower()
        # Skip very short or very long emails
        if len(email) < 5 or len(email) > 50:
            continue
        # Skip common spam patterns
        if any(bad in email for bad in ["@", "noreply", "no-reply", "donotreply", "do-not-reply"]):
            continue
        cleaned.append(email)
    return list(set(cleaned))

# ==============================
# CHROME SETUP (HEADLESS)
# ==============================
options = Options()
options.add_argument("--headless=new")   # IMPORTANT
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--lang=en-US")

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
search.clear()
for ch in SEARCH_KEYWORD:
    search.send_keys(ch)
    time.sleep(random.uniform(0.08, 0.18))
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

    # ==============================
    # VISIT WEBSITE FOR EMAIL
    # ==============================
    pages_to_check = [
        website_url,
        website_url.rstrip("/") + "/contact",
        website_url.rstrip("/") + "/about",
        website_url.rstrip("/") + "/contact-us",
        website_url.rstrip("/") + "/about-us",
        website_url.rstrip("/") + "/support",
        website_url.rstrip("/") + "/help"
    ]

    email_found = ""
    source_url = ""

    for page in pages_to_check:
        try:
            driver.get(page)
            pause(3, 6)

            # Extract text from visible elements (skip scripts, styles, etc.)
            try:
                # Remove script and style tags from text
                text = driver.find_element(By.TAG_NAME, "body").text
            except:
                text = driver.page_source

            # Also search in page source (for mailto, hidden emails)
            combined_text = text + " " + driver.page_source

            # Extract emails
            emails = extract_email(combined_text)
            if emails:
                # Prefer emails that look like contact/support
                for email in emails:
                    if any(kw in email for kw in ["contact", "info", "sales", "support", "hello", "help", "admin", "office"]):
                        email_found = email
                        source_url = page
                        break
                if not email_found:
                    email_found = emails[0]
                    source_url = page
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
            "Source URL": source_url
        })

pause()
driver.quit()

# ==============================
# SAVE TO EXCEL
# ==============================
df = pd.DataFrame(leads)
df.to_excel(OUTPUT_FILE, index=False)

# ==============================
# SEND EMAIL
# ==============================
msg = MIMEMultipart()
msg["From"] = f"Jerry <{ADMIN_EMAIL}>"
msg["To"] = RECEIVER_EMAIL
msg["Subject"] = f"Business Leads - {SEARCH_KEYWORD}"

body = f"""
Hello Apurv Sir,

Please find attached the business leads collected from Google Maps.

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
print(f"✅ COMPLETED SUCCESSFULLY | Total leads: {len(leads)}")
