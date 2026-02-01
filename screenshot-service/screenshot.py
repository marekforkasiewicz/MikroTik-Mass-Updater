#!/usr/bin/env python3
"""
Screenshot Service for MikroTik Mass Updater
=============================================
Takes screenshots of app pages via Selenium Grid
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Configuration
SELENIUM_URL = os.getenv("SELENIUM_URL", "http://selenium-chrome:4444/wd/hub")
APP_URL = os.getenv("APP_URL", "http://mikrotik-updater:8000")
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "/screenshots")

# Credentials
LOGIN_USER = os.getenv("LOGIN_USER", "admin")
LOGIN_PASS = os.getenv("LOGIN_PASS", "admin123")

# Pages to screenshot
PAGES = [
    {"url": "/", "name": "dashboard", "label": "Dashboard"},
    {"url": "/routers", "name": "routers", "label": "Routers"},
    {"url": "/operations", "name": "operations", "label": "Operations"},
    {"url": "/monitoring", "name": "monitoring", "label": "Monitoring"},
    {"url": "/automation", "name": "automation", "label": "Automation"},
    {"url": "/reports", "name": "reports", "label": "Reports"},
    {"url": "/settings", "name": "settings", "label": "Settings"},
]

def setup_driver():
    """Setup Selenium WebDriver"""
    print("🔌 Connecting to Selenium Grid...")

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')

    driver = webdriver.Remote(
        command_executor=SELENIUM_URL,
        options=options
    )

    driver.implicitly_wait(10)
    print("✅ Connected to Selenium Grid")
    return driver

def login(driver):
    """Login to the application"""
    print(f"\n🔐 Logging in as {LOGIN_USER}...")

    try:
        driver.get(APP_URL)
        time.sleep(3)

        # Find login form
        username_input = driver.find_element(By.CSS_SELECTOR, "input[type='text'], input[name='username']")
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")

        username_input.clear()
        username_input.send_keys(LOGIN_USER)
        password_input.clear()
        password_input.send_keys(LOGIN_PASS)

        time.sleep(1)

        # Click login button
        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()

        time.sleep(3)

        # Check if logged in
        if "/login" not in driver.current_url:
            print("✅ Logged in successfully")
            return True
        else:
            print("⚠️ Login may have failed")
            return False

    except Exception as e:
        print(f"❌ Login error: {e}")
        return False

def take_screenshot(driver, page_url, page_name, page_label):
    """Take screenshot of a page"""
    print(f"\n📸 {page_label}")

    try:
        full_url = f"{APP_URL}{page_url}"
        driver.get(full_url)
        time.sleep(3)

        # Wait for content
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".card, .table, main, .container"))
            )
        except TimeoutException:
            pass

        screenshot_path = os.path.join(SCREENSHOT_DIR, f"{page_name}.png")
        driver.save_screenshot(screenshot_path)
        print(f"   ✅ Saved: {screenshot_path}")
        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("📷 MikroTik Mass Updater Screenshot Service")
    print("=" * 60)

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    driver = None
    try:
        driver = setup_driver()

        if not login(driver):
            print("\n⚠️ Continuing without login...")

        successful = 0
        for page in PAGES:
            if take_screenshot(driver, page["url"], page["name"], page["label"]):
                successful += 1
            time.sleep(1)

        print("\n" + "=" * 60)
        print(f"📊 Results: {successful}/{len(PAGES)} screenshots")
        print(f"📁 Folder: {SCREENSHOT_DIR}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
            print("✅ Done!")

if __name__ == "__main__":
    main()
