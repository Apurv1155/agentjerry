import time
import pandas as pd
import smtplib
import random
import os
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
# RANDOM KEYWORDS
# ==============================
KEYWORDS = [
    "cafes in Ahmedabad",
    "restaurants in Ahmedabad",
    "salon in Ahmedabad",
    "beauty parlour in Ahmedabad",
    "gym in Ahmedabad",
    "coaching classes in Ahmedabad",
    "spa in Ahmedabad",
    "bakery in Ahmedabad",
    "mobile repair shop Ahmedabad",
    "dental clinic Ahmedabad"
]

keyword = random.choice(KEYWORDS)
MAX_RESULTS = 20
OUTPUT_FILE = "leads.xlsx"

# ==============================
# SMTP (FROM GITHUB SECRETS)
# ==============================
ADMIN_EMAIL = "faceapp0011@gmail.com"
ADMIN_PASSWORD = "ytup bjrd pupf tuuj"
RECEIVER_EMAIL = "walaapurv@gmail.com"


# ==============================
# HEADLESS CHROME (CLOUD SAFE)
# ==============================
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
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

search = driver.find_element(By.ID, "searchboxinput")
search.send_keys(keyword)
search.send_keys(Keys.ENTER)
time.sleep(10)

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
    time.sleep(2)

# ==============================
# SCRAPE DETAILS
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

    time.sleep(2)

    name = driver.find_element(By.XPATH, "//h1").text.strip()

    def safe(xpath):
        try:
            return driver.find_element(By.XPATH, xpath).text.strip()
        except:
            return ""

    phone = safe('//button[contains(@data-item-id,"phone")]')
    address = safe('//button[@data-item-id="address"]')
    rating = safe('//div[contains(@aria-label,"stars")]')

    if not phone:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        continue

    if driver.find_elements(By.XPATH, '//a[contains(@aria-label,"Website")]'):
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        continue

    leads.append({
        "Business Name": name,
        "Mobile Number": phone,
        "Address": address,
        "Google Maps Link": link,
        "Rating": rating
    })

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

driver.quit()

# ==============================
# CREATE TEMP EXCEL
# ==============================
df = pd.DataFrame(leads)
df.to_excel(OUTPUT_FILE, index=False)

# ==============================
# SEND EMAIL
# ==============================
msg = MIMEMultipart()
msg["From"] = "Jerry <{}>".format(ADMIN_EMAIL)
msg["To"] = RECEIVER_EMAIL
msg["Subject"] = "Today's Google Maps Leads Catalogue"

body = f"""
Hi Apurv Sir,

This is today’s leads catalogue ({keyword}).

Please find the attached file.

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
print("✅ Email sent & temp file removed")
