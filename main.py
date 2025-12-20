import time
import random
import re
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

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
    "Drone propellers India",
    "Wooden furniture frame India",
    "Steel fabrication India",
]

MAX_RESULTS = 30
OUTPUT_FILE = "gasket_business_leads.xlsx"
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Email credentials for sending Excel
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

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

wait = WebDriverWait(driver, 30)

# ==============================
# SCRAPING LOGIC
# ==============================
all_data = []

for keyword in KEYWORDS:
    driver.get(f"https://www.google.com/maps/search/{keyword.replace(' ','+')}")
    pause(5,7)

    # Scroll to load results
    for _ in range(3):
        driver.execute_script("window.scrollBy(0, 500);")
        pause(2,3)

    businesses = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')[:MAX_RESULTS]
    for biz in businesses:
        try:
            name = biz.find_element(By.CSS_SELECTOR, 'h3 span').text
        except:
            name = ""
        try:
            address = biz.find_element(By.CSS_SELECTOR, '.a4gq8e-alt').text
        except:
            address = ""
        try:
            phone = biz.find_element(By.CSS_SELECTOR, 'button[data-tooltip="Copy phone number"]').get_attribute("aria-label")
        except:
            phone = ""
        try:
            website = biz.find_element(By.CSS_SELECTOR, 'a[data-tooltip="Open website"]').get_attribute("href")
        except:
            website = ""

        # Extract public email from website
        email = ""
        if website:
            try:
                driver.get(website)
                pause(2,4)
                page_text = driver.page_source
                emails = extract_email(page_text)
                if emails:
                    email = emails[0]
            except:
                email = ""

        all_data.append([name, address, phone, email, website])

# ==============================
# SAVE TO EXCEL
# ==============================
df = pd.DataFrame(all_data, columns=["Business Name", "Address", "Phone", "Email", "Website"])
df.to_excel(OUTPUT_FILE, index=False)

# ==============================
# SEND EMAIL WITH EXCEL
# ==============================
msg = MIMEMultipart()
msg['From'] = ADMIN_EMAIL
msg['To'] = RECEIVER_EMAIL
msg['Subject'] = "Gasket Business Leads - Ahmedabad"

body = "Please find attached the latest list of potential gasket customers in Ahmedabad."
msg.attach(MIMEText(body, 'plain'))

with open(OUTPUT_FILE, "rb") as attachment:
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f"attachment; filename= {OUTPUT_FILE}")
    msg.attach(part)

try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    server.send_message(msg)
    server.quit()
    print("Email sent successfully.")
except Exception as e:
    print("Failed to send email:", e)

driver.quit()
