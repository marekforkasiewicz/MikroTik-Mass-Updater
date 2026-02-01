#!/usr/bin/env python3
"""
Comprehensive UI Testing for MikroTik Mass Updater
===================================================
Tests all pages, buttons, modals, and functionality
"""

import time
import os
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains

# Configuration
SELENIUM_URL = os.getenv("SELENIUM_URL", "http://selenium-chrome:4444/wd/hub")
APP_URL = os.getenv("APP_URL", "http://192.168.1.14:8000")
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "/screenshots")
LOGIN_USER = os.getenv("LOGIN_USER", "admin")
LOGIN_PASS = os.getenv("LOGIN_PASS", "admin123")

# Test results
results = {
    "timestamp": datetime.now().isoformat(),
    "pages": {},
    "summary": {"passed": 0, "failed": 0, "warnings": 0}
}

def setup_driver():
    print("🔌 Connecting to Selenium Grid...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Remote(command_executor=SELENIUM_URL, options=options)
    driver.implicitly_wait(5)
    print("✅ Connected")
    return driver

def screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(path)
    return path

def login(driver):
    print(f"\n🔐 Logging in as {LOGIN_USER}...")
    driver.get(APP_URL)
    time.sleep(2)
    
    try:
        username = driver.find_element(By.CSS_SELECTOR, "input[type='text'], input[name='username']")
        password = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        username.send_keys(LOGIN_USER)
        password.send_keys(LOGIN_PASS)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(3)
        
        if "/login" not in driver.current_url:
            print("✅ Login successful")
            return True
    except Exception as e:
        print(f"❌ Login failed: {e}")
    return False

def test_element(driver, selector, description, click=False):
    """Test if element exists and optionally click it"""
    try:
        el = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        if click:
            try:
                el.click()
                return {"status": "pass", "message": f"{description} - clicked"}
            except ElementClickInterceptedException:
                return {"status": "warning", "message": f"{description} - found but not clickable"}
        return {"status": "pass", "message": f"{description} - found"}
    except TimeoutException:
        return {"status": "fail", "message": f"{description} - NOT FOUND"}

def count_elements(driver, selector):
    """Count elements matching selector"""
    return len(driver.find_elements(By.CSS_SELECTOR, selector))

def close_modal(driver):
    """Try to close any open modal"""
    try:
        close_btns = driver.find_elements(By.CSS_SELECTOR, ".btn-close, .modal .btn-secondary, button[data-bs-dismiss='modal']")
        for btn in close_btns:
            try:
                btn.click()
                time.sleep(0.5)
            except:
                pass
    except:
        pass

def test_dashboard(driver):
    print("\n" + "="*60)
    print("📊 Testing DASHBOARD")
    print("="*60)
    
    page_results = {"tests": [], "screenshots": []}
    driver.get(f"{APP_URL}/")
    time.sleep(3)
    
    screenshot(driver, "01-dashboard")
    page_results["screenshots"].append("01-dashboard.png")
    
    # Test stat cards
    cards = count_elements(driver, ".card")
    page_results["tests"].append({"test": "Stat cards visible", "status": "pass" if cards >= 4 else "fail", "details": f"Found {cards} cards"})
    
    # Test specific cards
    for card_text in ["Configured", "Discovered", "Online", "Needs Update"]:
        found = card_text.lower() in driver.page_source.lower()
        page_results["tests"].append({"test": f"Card '{card_text}'", "status": "pass" if found else "fail"})
    
    # Test refresh button
    try:
        refresh_btn = driver.find_element(By.CSS_SELECTOR, "button.btn-outline-secondary")
        refresh_btn.click()
        time.sleep(2)
        page_results["tests"].append({"test": "Refresh button", "status": "pass"})
        screenshot(driver, "01-dashboard-refreshed")
    except Exception as e:
        page_results["tests"].append({"test": "Refresh button", "status": "fail", "error": str(e)})
    
    # Test router table
    rows = count_elements(driver, "table tbody tr")
    page_results["tests"].append({"test": "Router table rows", "status": "pass" if rows > 0 else "warning", "details": f"Found {rows} rows"})
    
    return page_results

def test_routers(driver):
    print("\n" + "="*60)
    print("🖥️ Testing ROUTERS")
    print("="*60)
    
    page_results = {"tests": [], "screenshots": []}
    driver.get(f"{APP_URL}/routers")
    time.sleep(3)
    
    screenshot(driver, "02-routers")
    page_results["screenshots"].append("02-routers.png")
    
    # Count routers
    rows = count_elements(driver, "table tbody tr")
    page_results["tests"].append({"test": "Router list loaded", "status": "pass" if rows > 0 else "fail", "details": f"Found {rows} routers"})
    
    # Test search
    try:
        search = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='Search']")
        search.send_keys("192.168")
        time.sleep(1)
        filtered_rows = count_elements(driver, "table tbody tr")
        page_results["tests"].append({"test": "Search filter", "status": "pass", "details": f"Filtered to {filtered_rows} rows"})
        search.clear()
        time.sleep(1)
    except Exception as e:
        page_results["tests"].append({"test": "Search filter", "status": "fail", "error": str(e)})
    
    # Test status filter
    try:
        select = driver.find_element(By.CSS_SELECTOR, "select.form-select")
        select.click()
        time.sleep(0.5)
        options = driver.find_elements(By.CSS_SELECTOR, "select.form-select option")
        page_results["tests"].append({"test": "Status filter options", "status": "pass", "details": f"Found {len(options)} options"})
    except Exception as e:
        page_results["tests"].append({"test": "Status filter", "status": "fail", "error": str(e)})
    
    # Test Add Router button
    try:
        add_btn = driver.find_element(By.CSS_SELECTOR, "button.btn-primary")
        add_btn.click()
        time.sleep(1)
        
        modal_visible = count_elements(driver, ".modal.show, .modal[style*='block']") > 0
        page_results["tests"].append({"test": "Add Router modal", "status": "pass" if modal_visible else "fail"})
        screenshot(driver, "02-routers-add-modal")
        page_results["screenshots"].append("02-routers-add-modal.png")
        
        close_modal(driver)
        time.sleep(1)
    except Exception as e:
        page_results["tests"].append({"test": "Add Router button", "status": "fail", "error": str(e)})
    
    # Test action buttons on first row
    try:
        action_btns = driver.find_elements(By.CSS_SELECTOR, "table tbody tr:first-child .btn-group .btn")
        btn_count = len(action_btns)
        page_results["tests"].append({"test": "Action buttons per row", "status": "pass" if btn_count >= 5 else "warning", "details": f"Found {btn_count} buttons"})
        
        # Test Quick Scan button
        if btn_count > 0:
            scan_btn = action_btns[0]
            scan_btn.click()
            time.sleep(3)
            screenshot(driver, "02-routers-after-scan")
            page_results["tests"].append({"test": "Quick Scan button", "status": "pass"})
        
        # Check if FW and ROS buttons exist
        btn_titles = [btn.get_attribute("title") or "" for btn in action_btns]
        has_fw = any("firmware" in t.lower() for t in btn_titles)
        has_ros = any("routeros" in t.lower() for t in btn_titles)
        page_results["tests"].append({"test": "FW upgrade button exists", "status": "pass" if has_fw else "fail", "details": str(btn_titles)})
        page_results["tests"].append({"test": "ROS upgrade button exists", "status": "pass" if has_ros else "fail"})
        
    except Exception as e:
        page_results["tests"].append({"test": "Action buttons", "status": "fail", "error": str(e)})
    
    # Test checkbox selection
    try:
        checkbox = driver.find_element(By.CSS_SELECTOR, "table tbody tr:first-child input[type='checkbox']")
        checkbox.click()
        time.sleep(0.5)
        
        selected_text = driver.find_element(By.CSS_SELECTOR, ".col-md-6.text-end span").text
        page_results["tests"].append({"test": "Row selection", "status": "pass", "details": selected_text})
        screenshot(driver, "02-routers-selected")
        
        # Deselect
        checkbox.click()
    except Exception as e:
        page_results["tests"].append({"test": "Row selection", "status": "warning", "error": str(e)})
    
    return page_results

def test_operations(driver):
    print("\n" + "="*60)
    print("⚙️ Testing OPERATIONS")
    print("="*60)
    
    page_results = {"tests": [], "screenshots": []}
    driver.get(f"{APP_URL}/operations")
    time.sleep(3)
    
    screenshot(driver, "03-operations")
    page_results["screenshots"].append("03-operations.png")
    
    # Test tabs
    tabs = driver.find_elements(By.CSS_SELECTOR, ".nav-tabs .nav-link, [role='tab']")
    page_results["tests"].append({"test": "Operation tabs", "status": "pass" if len(tabs) > 0 else "fail", "details": f"Found {len(tabs)} tabs"})
    
    # Click through tabs
    for i, tab in enumerate(tabs):
        try:
            tab_text = tab.text
            tab.click()
            time.sleep(1)
            screenshot(driver, f"03-operations-tab{i+1}")
            page_results["screenshots"].append(f"03-operations-tab{i+1}.png")
            page_results["tests"].append({"test": f"Tab '{tab_text}'", "status": "pass"})
        except Exception as e:
            page_results["tests"].append({"test": f"Tab {i+1}", "status": "fail", "error": str(e)})
    
    return page_results

def test_monitoring(driver):
    print("\n" + "="*60)
    print("📈 Testing MONITORING")
    print("="*60)
    
    page_results = {"tests": [], "screenshots": []}
    driver.get(f"{APP_URL}/monitoring")
    time.sleep(3)
    
    screenshot(driver, "04-monitoring")
    page_results["screenshots"].append("04-monitoring.png")
    
    # Test monitoring elements
    cards = count_elements(driver, ".card")
    page_results["tests"].append({"test": "Monitoring cards", "status": "pass" if cards > 0 else "warning", "details": f"Found {cards} cards"})
    
    # Test alerts section
    alerts_found = "alert" in driver.page_source.lower()
    page_results["tests"].append({"test": "Alerts section", "status": "pass" if alerts_found else "warning"})
    
    return page_results

def test_automation(driver):
    print("\n" + "="*60)
    print("🤖 Testing AUTOMATION")
    print("="*60)
    
    page_results = {"tests": [], "screenshots": []}
    driver.get(f"{APP_URL}/automation")
    time.sleep(3)
    
    screenshot(driver, "05-automation")
    page_results["screenshots"].append("05-automation.png")
    
    # Test tabs
    tabs = driver.find_elements(By.CSS_SELECTOR, ".nav-tabs .nav-link, [role='tab']")
    page_results["tests"].append({"test": "Automation tabs", "status": "pass" if len(tabs) > 0 else "fail", "details": f"Found {len(tabs)} tabs"})
    
    # Click through tabs
    for i, tab in enumerate(tabs):
        try:
            tab_text = tab.text
            tab.click()
            time.sleep(1)
            screenshot(driver, f"05-automation-tab{i+1}")
            page_results["screenshots"].append(f"05-automation-tab{i+1}.png")
            page_results["tests"].append({"test": f"Tab '{tab_text}'", "status": "pass"})
        except Exception as e:
            page_results["tests"].append({"test": f"Tab {i+1}", "status": "fail", "error": str(e)})
    
    return page_results

def test_reports(driver):
    print("\n" + "="*60)
    print("📋 Testing REPORTS")
    print("="*60)
    
    page_results = {"tests": [], "screenshots": []}
    driver.get(f"{APP_URL}/reports")
    time.sleep(3)
    
    screenshot(driver, "06-reports")
    page_results["screenshots"].append("06-reports.png")
    
    # Test tabs
    tabs = driver.find_elements(By.CSS_SELECTOR, ".nav-tabs .nav-link, [role='tab']")
    page_results["tests"].append({"test": "Report tabs", "status": "pass" if len(tabs) > 0 else "warning", "details": f"Found {len(tabs)} tabs"})
    
    # Click through tabs
    for i, tab in enumerate(tabs[:3]):  # Limit to first 3 tabs
        try:
            tab_text = tab.text
            tab.click()
            time.sleep(1)
            screenshot(driver, f"06-reports-tab{i+1}")
            page_results["screenshots"].append(f"06-reports-tab{i+1}.png")
            page_results["tests"].append({"test": f"Tab '{tab_text}'", "status": "pass"})
        except Exception as e:
            page_results["tests"].append({"test": f"Tab {i+1}", "status": "fail", "error": str(e)})
    
    return page_results

def test_settings(driver):
    print("\n" + "="*60)
    print("⚙️ Testing SETTINGS")
    print("="*60)
    
    page_results = {"tests": [], "screenshots": []}
    driver.get(f"{APP_URL}/settings")
    time.sleep(3)
    
    screenshot(driver, "07-settings")
    page_results["screenshots"].append("07-settings.png")
    
    # Test tabs
    tabs = driver.find_elements(By.CSS_SELECTOR, ".nav-tabs .nav-link, [role='tab']")
    page_results["tests"].append({"test": "Settings tabs", "status": "pass" if len(tabs) > 0 else "warning", "details": f"Found {len(tabs)} tabs"})
    
    # Click through tabs
    for i, tab in enumerate(tabs[:4]):  # Limit to first 4 tabs
        try:
            tab_text = tab.text
            tab.click()
            time.sleep(1)
            screenshot(driver, f"07-settings-tab{i+1}")
            page_results["screenshots"].append(f"07-settings-tab{i+1}.png")
            page_results["tests"].append({"test": f"Tab '{tab_text}'", "status": "pass"})
        except Exception as e:
            page_results["tests"].append({"test": f"Tab {i+1}", "status": "fail", "error": str(e)})
    
    return page_results

def test_groups(driver):
    print("\n" + "="*60)
    print("📁 Testing GROUPS")
    print("="*60)
    
    page_results = {"tests": [], "screenshots": []}
    driver.get(f"{APP_URL}/groups")
    time.sleep(3)
    
    screenshot(driver, "08-groups")
    page_results["screenshots"].append("08-groups.png")
    
    # Test page loaded
    page_loaded = "group" in driver.page_source.lower()
    page_results["tests"].append({"test": "Groups page loaded", "status": "pass" if page_loaded else "warning"})
    
    return page_results

def print_summary(results):
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    total_pass = 0
    total_fail = 0
    total_warn = 0
    
    for page, data in results["pages"].items():
        page_pass = sum(1 for t in data["tests"] if t.get("status") == "pass")
        page_fail = sum(1 for t in data["tests"] if t.get("status") == "fail")
        page_warn = sum(1 for t in data["tests"] if t.get("status") == "warning")
        
        total_pass += page_pass
        total_fail += page_fail
        total_warn += page_warn
        
        status_icon = "✅" if page_fail == 0 else "❌"
        print(f"{status_icon} {page}: {page_pass} passed, {page_fail} failed, {page_warn} warnings")
        
        for test in data["tests"]:
            icon = {"pass": "✓", "fail": "✗", "warning": "⚠"}[test["status"]]
            details = f" ({test.get('details', '')})" if test.get('details') else ""
            print(f"   {icon} {test['test']}{details}")
    
    results["summary"] = {"passed": total_pass, "failed": total_fail, "warnings": total_warn}
    
    print("\n" + "="*60)
    print(f"TOTAL: ✅ {total_pass} passed | ❌ {total_fail} failed | ⚠ {total_warn} warnings")
    print("="*60)

def main():
    print("="*60)
    print("🧪 MikroTik Mass Updater - Comprehensive UI Test")
    print("="*60)
    
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    
    driver = None
    try:
        driver = setup_driver()
        
        if not login(driver):
            print("❌ Cannot proceed without login")
            return
        
        # Run all tests
        results["pages"]["Dashboard"] = test_dashboard(driver)
        results["pages"]["Routers"] = test_routers(driver)
        results["pages"]["Operations"] = test_operations(driver)
        results["pages"]["Monitoring"] = test_monitoring(driver)
        results["pages"]["Automation"] = test_automation(driver)
        results["pages"]["Reports"] = test_reports(driver)
        results["pages"]["Settings"] = test_settings(driver)
        results["pages"]["Groups"] = test_groups(driver)
        
        # Print summary
        print_summary(results)
        
        # Save results to JSON
        with open(os.path.join(SCREENSHOT_DIR, "test-results.json"), "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📁 Results saved to {SCREENSHOT_DIR}/test-results.json")
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
            print("\n✅ Tests completed!")

if __name__ == "__main__":
    main()
