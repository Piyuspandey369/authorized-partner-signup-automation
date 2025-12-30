import time
from faker import Faker
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

fake = Faker()

def wait_click(wait, locator):
    wait.until(EC.element_to_be_clickable(locator)).click()

def wait_type(wait, locator, text):
    el = wait.until(EC.visibility_of_element_located(locator))
    el.clear()
    el.send_keys(text)

def main():
    # 1) Start Chrome
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    wait = WebDriverWait(driver, 20)
    driver.maximize_window()

    # Test data (unique every run)
    agency_name = fake.company()
    full_name = fake.name()
    email = f"qa.{int(time.time())}.{fake.user_name()}@example.com"
    phone = "98" + str(fake.random_number(digits=8, fix_len=True))
    password = "Test@12345"

    try:
        # 2) Open website
        driver.get("https://authorized-partner.vercel.app/")

        # 3) Click Get Started / Join Us Now
        wait_click(wait, (By.XPATH, "//a[contains(.,'Get Started') or contains(.,'Join Us Now')]"))
        wait.until(lambda d: "/register" in d.current_url)

        # 4) Step-1: tick checkbox + Continue
        wait_click(wait, (By.CSS_SELECTOR, "input[type='checkbox']"))
        wait_click(wait, (By.XPATH, "//button[contains(.,'Continue')]"))

        # -------------------------
        # ✅ Step-2: Fill the form
        # -------------------------
        # IMPORTANT: If these fields don't match, you will change ONLY the locators.
        # First try: NAME / ID
        # Backup: placeholder or label-based XPath

        # Agency Name
        wait_type(wait, (By.XPATH,
            "//input[@name='agencyName' or @id='agencyName' or contains(@placeholder,'Agency')]"
        ), agency_name)

        # Email
        wait_type(wait, (By.XPATH,
            "//input[@type='email' or @name='email' or @id='email' or contains(@placeholder,'Email')]"
        ), email)

        # Phone (if exists)
        try:
            wait_type(wait, (By.XPATH,
                "//input[@type='tel' or @name='phone' or @id='phone' or contains(@placeholder,'Phone')]"
            ), phone)
        except:
            pass  # phone might not exist on the page

        # Full name (if exists)
        try:
            wait_type(wait, (By.XPATH,
                "//input[@name='fullName' or @id='fullName' or contains(@placeholder,'Full')]"
            ), full_name)
        except:
            pass

        # Click Next/Continue
        wait_click(wait, (By.XPATH, "//button[contains(.,'Next') or contains(.,'Continue')]"))

        # -------------------------
        # ✅ Step-3: Password page
        # -------------------------
        # Password
        try:
            wait_type(wait, (By.XPATH,
                "//input[@type='password' or @name='password' or @id='password']"
            ), password)

            # Confirm Password (if exists)
            try:
                wait_type(wait, (By.XPATH,
                    "//input[contains(@name,'confirm') or contains(@id,'confirm') or contains(@placeholder,'Confirm')]"
                ), password)
            except:
                pass

            # Submit/Register/Create
            wait_click(wait, (By.XPATH,
                "//button[contains(.,'Submit') or contains(.,'Register') or contains(.,'Create') or contains(.,'Continue')]"
            ))
        except:
            # If password wasn't on this step, ignore (some flows combine steps)
            pass

        # -------------------------
        # ✅ Final: Verify success
        # -------------------------
        wait.until(lambda d: ("success" in d.page_source.lower())
                           or ("/login" in d.current_url)
                           or ("welcome" in d.page_source.lower()))

        print("✅ Signup automation completed successfully!")
        print("Test account used:", email)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
