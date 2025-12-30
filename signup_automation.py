import os
import re
import time
import imaplib
import email as email_lib
from email.header import decode_header
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup
from faker import Faker

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# =========================
# CONFIG
# =========================
BASE_URL = "https://authorized-partner.vercel.app/"
SLOW_MODE = True
STEP_PAUSE = 0.60
TYPE_DELAY = 0.02

fake = Faker()


# =========================
# UTIL
# =========================
def slow_sleep(sec: float) -> None:
    if SLOW_MODE:
        time.sleep(sec)


def slow_type(el, text: str) -> None:
    for ch in text:
        el.send_keys(ch)
        slow_sleep(TYPE_DELAY)


def scroll_center(driver, el) -> None:
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)


def js_click(driver, el) -> None:
    driver.execute_script("arguments[0].click();", el)


def wvisible(wait: WebDriverWait, locator):
    return wait.until(EC.visibility_of_element_located(locator))


def wclick(wait: WebDriverWait, driver, locator):
    el = wait.until(EC.element_to_be_clickable(locator))
    scroll_center(driver, el)
    js_click(driver, el)
    slow_sleep(STEP_PAUSE)
    return el


def wtype(wait: WebDriverWait, driver, locator, text: str):
    el = wvisible(wait, locator)
    scroll_center(driver, el)
    try:
        el.clear()
    except Exception:
        pass
    slow_type(el, text)
    slow_sleep(0.10)
    return el


def click_button_by_text(wait: WebDriverWait, driver, *texts: str):
    cond = " or ".join([f"contains(normalize-space(.),'{t}')" for t in texts])
    locator = (By.XPATH, f"//button[{cond}]")
    return wclick(wait, driver, locator)


def fill_input_by_label(wait: WebDriverWait, driver, label_text: str, value: str):
    locator = (By.XPATH, f"//label[contains(normalize-space(.), '{label_text}')]/following::input[1]")
    return wtype(wait, driver, locator, value)


def fill_input_by_placeholder(wait: WebDriverWait, driver, placeholder: str, value: str):
    locator = (By.XPATH, f"//input[@placeholder='{placeholder}']")
    return wtype(wait, driver, locator, value)


def safe_click_checkbox_by_text(wait: WebDriverWait, driver, text: str) -> bool:
    locators = [
        (By.XPATH, f"//*[self::label or self::span or self::p][normalize-space()='{text}']"),
        (By.XPATH, f"//*[contains(normalize-space(.),'{text}')]/ancestor::*[self::label or self::button or @role='checkbox'][1]"),
        (By.XPATH, f"//button[contains(.,'{text}')]"),
    ]
    for loc in locators:
        try:
            el = wait.until(EC.element_to_be_clickable(loc))
            scroll_center(driver, el)
            js_click(driver, el)
            slow_sleep(0.15)
            return True
        except Exception:
            continue
    return False


def wait_header_contains(wait: WebDriverWait, text: str):
    return wait.until(EC.visibility_of_element_located(
        (By.XPATH, f"//*[contains(normalize-space(.),'{text}')]")
    ))


# =========================
# TERMS PAGE
# =========================
def accept_terms_and_continue(driver, wait: WebDriverWait) -> None:
    cb = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button#remember[role='checkbox']")))
    scroll_center(driver, cb)
    js_click(driver, cb)
    slow_sleep(0.5)

    cont = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Continue']")))
    scroll_center(driver, cont)
    js_click(driver, cont)
    slow_sleep(0.8)


# =========================
# OTP via Gmail IMAP (6-digit ONLY, fresh)
# =========================
def fetch_latest_otp_from_gmail_imap(imap_login_email: str, app_password: str, timeout_sec: int = 180) -> str:
    start = time.time()
    otp_regex = re.compile(r"\b(\d{6})\b")

    while time.time() - start < timeout_sec:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(imap_login_email, app_password)
        mail.select("INBOX")

        status, data = mail.search(None, "UNSEEN")
        ids = data[0].split() if status == "OK" else []

        if not ids:
            status, data = mail.search(None, "ALL")
            if status != "OK":
                mail.logout()
                time.sleep(3)
                continue
            ids = data[0].split()[-50:]

        for msg_id in ids[::-1]:
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)

            # ignore old emails (>6 minutes)
            try:
                dt = parsedate_to_datetime(msg.get("Date"))
                if dt and dt.timestamp() < (time.time() - 6 * 60):
                    continue
            except Exception:
                pass

            subject = decode_header(msg.get("Subject", ""))[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode(errors="ignore")
            subject = str(subject)

            body_text = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    disp = str(part.get("Content-Disposition"))
                    if ctype in ("text/plain", "text/html") and "attachment" not in disp:
                        payload = part.get_payload(decode=True) or b""
                        body_text = payload.decode(errors="ignore")
                        if ctype == "text/html":
                            body_text = BeautifulSoup(body_text, "html.parser").get_text(" ", strip=True)
                        break
            else:
                payload = msg.get_payload(decode=True) or b""
                body_text = payload.decode(errors="ignore")

            text = f"{subject} {body_text}"
            m = otp_regex.search(text)
            if m:
                otp = m.group(1)
                try:
                    mail.store(msg_id, "+FLAGS", "\\Seen")
                except Exception:
                    pass
                mail.logout()
                return otp

        mail.logout()
        time.sleep(3)

    raise TimeoutError("OTP not received within timeout.")


def enter_otp_and_verify(driver, wait: WebDriverWait, otp: str) -> None:
    print("✅ Entering OTP:", otp)

    otp_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input")))
    scroll_center(driver, otp_input)
    try:
        otp_input.clear()
    except Exception:
        pass
    otp_input.send_keys(otp)
    slow_sleep(0.2)

    verify_btn = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//button[.//span[contains(.,'Verify Code')] or contains(.,'Verify Code')]")
    ))
    scroll_center(driver, verify_btn)
    js_click(driver, verify_btn)
    slow_sleep(0.8)

    # wait until Step 2 visible
    wait.until(EC.visibility_of_element_located(
        (By.XPATH, "//*[contains(.,'Agency Details') or contains(.,'About your Agency')]")
    ))


# =========================
# Page 4: Agency Details
# =========================
def select_region_australia(wait: WebDriverWait, driver) -> None:
    # open dropdown - DO NOT assume role=combobox
    dd_btn = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//label[contains(.,'Region of Operation')]/following::button[1]")
    ))
    scroll_center(driver, dd_btn)
    js_click(driver, dd_btn)
    slow_sleep(0.3)

    # search input inside popover
    search_input = wait.until(EC.visibility_of_element_located(
        (By.XPATH, "//input[contains(@placeholder,'Search')]")
    ))
    search_input.clear()
    search_input.send_keys("Australia")
    slow_sleep(0.3)

    # click visible result row (your DOM shows div.flex cursor-pointer…)
    australia_row = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//div[contains(@class,'cursor-pointer') and contains(.,'Australia')]")
    ))
    scroll_center(driver, australia_row)
    js_click(driver, australia_row)
    slow_sleep(0.3)

    # ensure dropdown closes
    search_input.send_keys(Keys.ESCAPE)
    slow_sleep(0.15)


def fill_agency_details(wait: WebDriverWait, driver, agency_name: str, role: str, email: str, website_domain: str, address: str) -> None:
    wait_header_contains(wait, "Agency Details")

    fill_input_by_placeholder(wait, driver, "Enter Agency Name", agency_name)
    fill_input_by_placeholder(wait, driver, "Enter Your Role in Agency", role)
    fill_input_by_placeholder(wait, driver, "Enter Your Agency Email Address", email)

    # Website must be domain only, because field already has https:// prefix
    wtype(
        wait, driver,
        (By.XPATH, "//input[contains(@placeholder,'Agency Website') or contains(@placeholder,'Website')]"),
        website_domain
    )

    fill_input_by_placeholder(wait, driver, "Enter Your Agency Address", address)

    select_region_australia(wait, driver)

    click_button_by_text(wait, driver, "Next")

    # Step 3 header visible
    wait_header_contains(wait, "Professional Experience")


# =========================
# Page 5: Professional Experience
# =========================
def open_years_experience_dropdown(wait: WebDriverWait, driver) -> None:
    # UI might change; try multiple strategies
    locators = [
        (By.XPATH, "//label[contains(.,'Years of Experience')]/following::button[1]"),
        (By.XPATH, "//*[contains(normalize-space(.),'Years of Experience')]/following::button[1]"),
        (By.XPATH, "//button[contains(@aria-haspopup,'dialog') or contains(@aria-haspopup,'listbox')][1]"),
    ]

    dd = None
    for loc in locators:
        try:
            dd = wait.until(EC.element_to_be_clickable(loc))
            break
        except Exception:
            continue

    if dd is None:
        raise RuntimeError("Years of Experience dropdown not found.")

    scroll_center(driver, dd)
    js_click(driver, dd)
    slow_sleep(0.25)

    # select first option via keyboard
    active = driver.switch_to.active_element
    active.send_keys(Keys.ARROW_DOWN)
    slow_sleep(0.08)
    active.send_keys(Keys.ENTER)
    slow_sleep(0.25)


def fill_professional_experience(wait: WebDriverWait, driver) -> None:
    wait_header_contains(wait, "Professional Experience")

    open_years_experience_dropdown(wait, driver)

    fill_input_by_label(wait, driver, "Number of Students Recruited Annually", "50")
    fill_input_by_label(wait, driver, "Focus Area", "Undergraduate admissions to Canada")
    fill_input_by_label(wait, driver, "Success Metrics", "90")

    # click some services (non-fatal if text mismatch)
    for svc in ["Career Counseling", "Admission Applications"]:
        clicked = safe_click_checkbox_by_text(wait, driver, svc)
        if not clicked:
            print(f"⚠️ Service not found: {svc}")

    click_button_by_text(wait, driver, "Next")

    wait.until(EC.visibility_of_element_located(
        (By.XPATH, "//*[contains(.,'Verification') or contains(.,'Preferences')]")
    ))


# =========================
# Page 6: Verification & Preferences
# =========================
def select_preferred_country(wait: WebDriverWait, driver, country_name: str = "Canada") -> None:
    # Open the Preferred Countries dropdown (button next to label)
    dd_btn = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//label[contains(.,'Preferred Countries')]/following::button[1]")
    ))
    scroll_center(driver, dd_btn)
    js_click(driver, dd_btn)
    slow_sleep(0.3)

    # Search box inside popover
    search_input = wait.until(EC.visibility_of_element_located(
        (By.XPATH, "//input[contains(@placeholder,'Search')]")
    ))
    search_input.clear()
    search_input.send_keys(country_name)
    slow_sleep(0.3)

    # Click the result row (Radix items are usually div.cursor-pointer)
    row = wait.until(EC.element_to_be_clickable(
        (By.XPATH, f"//div[contains(@class,'cursor-pointer') and contains(.,'{country_name}')]")
    ))
    scroll_center(driver, row)
    js_click(driver, row)
    slow_sleep(0.3)

    # Close dropdown
    search_input.send_keys(Keys.ESCAPE)
    slow_sleep(0.2)

    # Try to find by label; fallback to first dropdown-looking button on page
    locators = [
        (By.XPATH, "//label[contains(.,'Preferred Countries')]/following::button[1]"),
        (By.XPATH, "//*[contains(normalize-space(.),'Preferred Countries')]/following::button[1]"),
    ]
    dd = None
    for loc in locators:
        try:
            dd = wait.until(EC.element_to_be_clickable(loc))
            break
        except Exception:
            continue

    if dd is None:
        raise RuntimeError("Preferred Countries dropdown not found.")

    scroll_center(driver, dd)
    js_click(driver, dd)
    slow_sleep(0.25)

    # pick first option
    active = driver.switch_to.active_element
    active.send_keys(Keys.ARROW_DOWN)
    slow_sleep(0.08)
    active.send_keys(Keys.ENTER)
    slow_sleep(0.25)


def fill_verification_and_preferences(wait: WebDriverWait, driver, doc1: str, doc2: str) -> None:
    wait.until(EC.visibility_of_element_located(
        (By.XPATH, "//*[contains(.,'Verification') or contains(.,'Preferences')]")
    ))

    fill_input_by_label(wait, driver, "Business Registration Number", "BRN-" + str(int(time.time()))[-6:])

    select_preferred_country(wait, driver,"Canada")

    # institution types
    for t in ["Universities", "Colleges"]:
        ok = safe_click_checkbox_by_text(wait, driver, t)
        if not ok:
            print(f"⚠️ Institution type not found: {t}")

    # certification (optional)
    try:
        fill_input_by_label(wait, driver, "Certification Details", "ICEF Certified Education Agent (Sample)")
    except Exception:
        pass

    # uploads
    file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
    if len(file_inputs) >= 2:
        scroll_center(driver, file_inputs[0])
        file_inputs[0].send_keys(doc1)
        slow_sleep(0.4)
        scroll_center(driver, file_inputs[1])
        file_inputs[1].send_keys(doc2)
        slow_sleep(0.4)
    elif len(file_inputs) == 1:
        scroll_center(driver, file_inputs[0])
        file_inputs[0].send_keys(doc1)
        slow_sleep(0.4)
        file_inputs[0].send_keys(doc2)
        slow_sleep(0.4)
    else:
        raise RuntimeError("No file upload inputs found on Step 4.")

    click_button_by_text(wait, driver, "Submit")

    WebDriverWait(driver, 30).until(
        lambda d: ("success" in d.page_source.lower())
        or ("added successfully" in d.page_source.lower())
        or ("/login" in d.current_url)
    )


# =========================
# MAIN
# =========================
def main() -> None:
    base_email = os.getenv("OTP_EMAIL") or "p98962310@gmail.com"
    app_password = os.getenv("OTP_EMAIL_APP_PASSWORD")

    if not app_password:
        raise RuntimeError('Set PowerShell: $env:OTP_EMAIL_APP_PASSWORD="YOUR_16_CHAR_APP_PASSWORD_NO_SPACES"')

    # unique email each run (Gmail plus addressing)
    run_tag = str(int(time.time()))
    signup_email = base_email.replace("@gmail.com", f"+tap{run_tag}@gmail.com")

    # Step 1 data
    first_name = fake.first_name()
    last_name = fake.last_name()
    password = "Test@12345"
    phone = "98" + str(int(time.time()))[-8:]

    # Step 2 data
    agency_name = f"{fake.company()} Consultancy"
    role_in_agency = "Owner"
    website_domain = "www.google.com"   # ✅ required by you
    address = "Sankhamul, Kathmandu"

    # Upload docs
    doc1 = os.path.abspath("test_data/company_registration.pdf")
    doc2 = os.path.abspath("test_data/education_certificate.pdf")
    if not os.path.exists(doc1) or not os.path.exists(doc2):
        raise RuntimeError("Missing: test_data/company_registration.pdf and/or test_data/education_certificate.pdf")

    options = Options()
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 30)

    try:
        driver.get(BASE_URL)
        slow_sleep(0.8)

        # go to register
        wclick(wait, driver, (By.XPATH, "//a[contains(.,'Get Started') or contains(.,'Join Us Now')]"))
        wait.until(lambda d: "/register" in d.current_url)
        slow_sleep(0.6)

        # terms
        accept_terms_and_continue(driver, wait)

        # Step 1 form
        fill_input_by_label(wait, driver, "First Name", first_name)
        fill_input_by_label(wait, driver, "Last Name", last_name)
        fill_input_by_label(wait, driver, "Email Address", signup_email)

        try:
            fill_input_by_label(wait, driver, "Phone Number", phone)
        except Exception:
            wtype(wait, driver, (By.CSS_SELECTOR, "input[type='tel']"), phone)

        fill_input_by_label(wait, driver, "Password", password)
        fill_input_by_label(wait, driver, "Confirm Password", password)

        click_button_by_text(wait, driver, "Next")

        # OTP (always goes to base_email inbox even for plus addressing)
        print("📩 Waiting for OTP in inbox:", base_email)
        otp = fetch_latest_otp_from_gmail_imap(base_email, app_password, timeout_sec=180)
        print("✅ OTP fetched:", otp)

        enter_otp_and_verify(driver, wait, otp)

        # Step 2
        fill_agency_details(wait, driver, agency_name, role_in_agency, signup_email, website_domain, address)

        # Step 3
        fill_professional_experience(wait, driver)

        # Step 4
        fill_verification_and_preferences(wait, driver, doc1, doc2)

        print("\n✅ FULL SIGNUP COMPLETED SUCCESSFULLY.")
        print("Signup email used:", signup_email)
        time.sleep(5)

    except Exception as e:
        print("\n❌ SCRIPT ERROR:", repr(e))
        print("Browser will stay open for debugging.")
        input("Press Enter to close browser...")
        raise
    

    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
