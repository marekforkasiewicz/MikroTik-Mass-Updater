#!/usr/bin/env python3
"""
Screenshot Service for MikroTik Mass Updater
=============================================
Automatically takes screenshots of all pages in the application
Uses Selenium with Chrome headless
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os
import sys

# Configuration
SELENIUM_URL = os.getenv("SELENIUM_URL", "http://localhost:4444/wd/hub")
APP_URL = os.getenv("APP_URL", "http://192.168.1.14:8000")
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "/tmp/mikrotik-screenshots")

# Default credentials (admin sees all pages)
LOGIN_USER = os.getenv("LOGIN_USER", "admin")
LOGIN_PASS = os.getenv("LOGIN_PASS", "admin123")

# Pages to screenshot
PAGES = [
    {"url": "/", "name": "dashboard", "label": "Dashboard"},
    {"url": "/routers", "name": "routers", "label": "Router List"},
    {"url": "/groups", "name": "groups", "label": "Groups"},
    {"url": "/operations", "name": "operations", "label": "Batch Operations"},
    {"url": "/automation", "name": "automation", "label": "Automation"},
    {"url": "/monitoring", "name": "monitoring", "label": "Monitoring Dashboard"},
    {"url": "/reports", "name": "reports", "label": "Reports and Logs"},
    {"url": "/settings", "name": "settings", "label": "Settings"},
]


def setup_driver():
    """Setup Selenium WebDriver"""
    print("Connecting to Selenium Grid...")

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
    print("Connected to Selenium Grid")
    return driver


def login(driver):
    """Login to the application"""
    print(f"\nLogging in as {LOGIN_USER}...")

    try:
        driver.get(f"{APP_URL}/login")
        time.sleep(3)

        # Find login form inputs
        username_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[name='username']")
        password_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
        login_buttons = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button.btn-primary")

        if username_inputs and password_inputs and login_buttons:
            # Enter credentials
            username_inputs[0].clear()
            username_inputs[0].send_keys(LOGIN_USER)
            password_inputs[0].clear()
            password_inputs[0].send_keys(LOGIN_PASS)

            time.sleep(1)

            # Click login
            login_buttons[0].click()

            # Wait for login to complete
            time.sleep(3)

            # Check if login was successful (not on login page anymore)
            current_url = driver.current_url
            if '/login' not in current_url:
                print("Logged in successfully")
                return True
            else:
                print("Login may have failed - still on login page")
                return False
        else:
            print("Could not find login form elements")
            return False

    except Exception as e:
        print(f"Login error: {e}")
        return False


def take_screenshot(driver, page_url, page_name, page_label):
    """Take screenshot of a specific page"""
    print(f"\nCapturing: {page_label}")

    try:
        # Navigate to URL
        full_url = f"{APP_URL}{page_url}"
        driver.get(full_url)

        # Wait for content to load
        time.sleep(2)

        # Wait for Vue content to render
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".container-fluid, .container, main, #app"))
            )
        except TimeoutException:
            pass  # Continue anyway

        # Additional wait for dynamic content
        time.sleep(2)

        # Take screenshot
        screenshot_path = os.path.join(SCREENSHOT_DIR, f"{page_name}.png")
        driver.save_screenshot(screenshot_path)
        print(f"   Saved: {screenshot_path}")

        return True

    except Exception as e:
        print(f"   Error: {str(e)[:80]}")
        return False


def main():
    """Main screenshot routine"""
    print("=" * 60)
    print("MikroTik Mass Updater - Screenshot Service")
    print("=" * 60)
    print(f"App URL: {APP_URL}")
    print(f"Selenium: {SELENIUM_URL}")
    print(f"Output: {SCREENSHOT_DIR}")
    print("=" * 60)

    # Ensure screenshot directory exists
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    driver = None
    try:
        # Setup driver
        driver = setup_driver()

        # Login
        if not login(driver):
            print("\nLogin failed - some pages may not be accessible")

        # Take screenshots of all pages
        successful = 0
        failed = 0

        for page in PAGES:
            if take_screenshot(driver, page["url"], page["name"], page["label"]):
                successful += 1
            else:
                failed += 1

            # Small delay between pages
            time.sleep(1)

        # Summary
        print("\n" + "=" * 60)
        print(f"Results:")
        print(f"   Success: {successful}")
        print(f"   Failed: {failed}")
        print(f"   Output: {SCREENSHOT_DIR}")
        print("=" * 60)

        # List generated files
        print("\nGenerated files:")
        for f in sorted(os.listdir(SCREENSHOT_DIR)):
            if f.endswith('.png'):
                fpath = os.path.join(SCREENSHOT_DIR, f)
                size = os.path.getsize(fpath)
                print(f"   {f} ({size / 1024:.1f} KB)")

        return 0 if failed == 0 else 1

    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        if driver:
            print("\nClosing browser...")
            driver.quit()
            print("Done!")


if __name__ == "__main__":
    sys.exit(main())
