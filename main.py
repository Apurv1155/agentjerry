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
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# CONFIG
# ==============================
SEARCH_KEYWORD = "Packaging machine"
MAX_RESULTS = 30
OUTPUT_FILE = "business_leads.xlsx"
PAGE_LOAD_TIMEOUT = 40  # seconds

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

ADMIN_EMAIL = "faceapp0011@gmail.com"
ADMIN_PASSWORD = "ytup bjrd pupf tuuj"
RECEIVER_EMAIL = "walaapurv@gmail.com"

# ==============================
# HELPERS
# ==============================
def extract_email(text):
    return list(set(EMAIL_REGEX.findall(text)))

def safe_text(driver, xpath):
    try:
        return driver.find_element(By.XPATH, xpath).text.strip()
    except:
        return ""

def log(msg):
    print(f"[INFO] {msg}")

# ==============================
# HEADLESS CHROME SETUP
# ==============================
log("Launching headless Chrome browser...")

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
wait = WebDriverWait(driver, 20)

# ==============================
# GOOGLE MAPS SEARCH
# ==============================
log(f"Opening Google Maps and searching: {SEARCH_KEYWORD}")
driver.get("https://www.google.com/maps")

search = wait.until(EC.presence_of_element_located((By.ID, "searchboxinput")))
search.clear()
search.send_keys(SEARCH_KEYWORD)
search.send_keys(Keys.ENTER)

wait.until(EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]')))
time.sleep(3)

# ==============================
# COLLECT PLACE LINKS
# ==============================
log("Collecting business listing URLs...")
results_panel = driver.find_element(By.XPATH, '//div[@role="feed"]')
place_links = set()

while len(place_links) < MAX_RESULTS * 2:
    cards = driver.find_elements(By.XPATH, '//a[contains(@href,"/maps/place/")]')
    for card in cards:
        href = card.get_attribute("href")
        if href:
            place_links.add(href)

    driver.execute_script("arguments[0].scrollTop += 2500", results_panel)
    time.sleep(1)

log(f"Collected {len(place_links)} business URLs")

# ==============================
# SCRAPE BUSINESS DETAILS
# ==============================
leads = []
business_count = 0

for link in place_links:
    if len(leads) >= MAX_RESULTS:
        break

    business_count += 1
    log(f"Opening business #{business_count}")

    driver.execute_script("window.open(arguments[0]);", link)
    driver.switch_to.window(driver.window_handles[1])

    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//h1")))
    except:
        log("Business page failed to load, skipping.")
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        continue

    business_name = safe_text(driver, "//h1")
    phone = safe_text(driver, '//button[contains(@data-item-id,"phone")]')
    address = safe_text(driver, '//button[@data-item-id="address"]')

    log(f"Business Name: {business_name}")

    website_elements = driver.find_elements(By.XPATH, '//a[contains(@aria-label,"Website")]')
    if not website_elements or not phone:
        log("No website or phone found, skipping business.")
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        continue

    website_url = website_elements[0].get_attribute("href")
    log(f"Website found: {website_url}")

    driver.close()
    driver.switch_to.window(driver.window_handles[0])

    # ==============================
    # CHECK WEBSITE & EXTRACT EMAIL
    # ==============================
    pages = [
        website_url,
        website_url.rstrip("/") + "/contact",
        website_url.rstrip("/") + "/about"
    ]

    email_found = ""
    source_page = ""

    log("Checking website pages for email...")

    for page in pages:
        try:
            log(f"Loading page: {page}")
            driver.get(page)

            emails = extract_email(driver.page_source)
            if emails:
                email_found = emails[0]
                source_page = page
                log(f"Email found: {email_found}")
                break
            else:
                log("No email on this page.")

        except TimeoutException:
            log("Page load exceeded 40 seconds. Skipping this business.")
            break

        except Exception as e:
            log(f"Error loading page: {e}")
            continue

    if email_found:
        leads.append({
            "Business Name": business_name,
            "Phone": phone,
            "Address": address,
            "Email": email_found,
            "Website": website_url,
            "Source URL": source_page
        })
        log(f"Lead collected successfully. Total leads: {len(leads)}")
    else:
        log("No email found for this business.")

log("Scraping completed. Closing browser.")
driver.quit()

# ==============================
# SAVE EXCEL
# ==============================
log("Saving leads to Excel file...")
df = pd.DataFrame(leads)
df.to_excel(OUTPUT_FILE, index=False)

# ==============================
# SEND EMAIL
# ==============================
log("Sending Excel file via email...")

msg = MIMEMultipart()
msg["From"] = f"Jerry <{ADMIN_EMAIL}>"
msg["To"] = RECEIVER_EMAIL
msg["Subject"] = f"Business Leads - {SEARCH_KEYWORD}"

msg.attach(MIMEText(
    f"""Hello Apurv Sir,

Please find attached the business leads collected from Google Maps.
Keyword used: {SEARCH_KEYWORD}
Total leads collected: {len(leads)}

Regards,
Jerry
""",
    "plain"
))

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

log(f"Process finished successfully. Total leads collected: {len(leads)}")
