"""
crawler.py
----------
Script that:
1) Logs into WODBoard
2) Goes to Aldgate CF (423) Month view
3) Applies "Calisthenics" filter
4) Loops over multiple months to gather event details
5) Writes them to a CSV (date, time, link)
"""

import os
import re
import csv
import time
import logging
import datetime

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

########################################
# ENV + Logging
########################################
load_dotenv()  # to load .env if present
USERNAME = os.getenv("WODBOARD_USERNAME")
PASSWORD = os.getenv("WODBOARD_PASSWORD")
if not USERNAME or not PASSWORD:
    raise ValueError("WODBOARD_USERNAME or WODBOARD_PASSWORD not set.")

logging.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", level=logging.INFO)

########################################
# Helper Functions
########################################

def login_wodboard(driver, username=USERNAME, password=PASSWORD):
    """Log into WODBoard using USERNAME/PASSWORD from environment."""
    logging.info("Logging into WODBoard...")
    driver.get("https://www.wodboard.com/login")

    username_input = driver.find_element(By.ID, "user_session_email")
    password_input = driver.find_element(By.ID, "user_session_password")
    username_input.send_keys(username)
    password_input.send_keys(password)

    sign_in_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
    sign_in_button.click()

    # Wait until the dashboard link appears (meaning we've logged in)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a[href='/dashboard']"))
    )
    logging.info("Login successful.")


def go_to_calendar_423(driver):
    """Navigate to Aldgate CF Timetable (/calendars/423) & ensure loaded."""
    logging.info("Navigating to Aldgate CF Timetable (423)...")
    driver.get("https://www.wodboard.com/calendars/423")

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".fullCalendar-wrapper .calendar"))
    )
    logging.info("Calendar page loaded.")


def switch_to_month_view(driver):
    """Click the '.fc-month-button' to ensure FullCalendar is in Month view."""
    logging.info("Switching to Month view...")
    month_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".fc-month-button"))
    )
    month_button.click()
    time.sleep(2)


def apply_filter_calisthenics(driver):
    """Open the filter dropdown, select 'Calisthenics', click 'Update'."""
    logging.info("Applying Calisthenics filter...")
    filter_link = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.ID, "filter-link"))
    )
    filter_link.click()

    label_for_calis = driver.find_element(
        By.CSS_SELECTOR, "label.custom-control-label[for='ct-ClassType4458']"
    )
    label_for_calis.click()

    update_button = driver.find_element(
        By.CSS_SELECTOR, "input.btn.btn-primary[type='submit'][value='Update']"
    )
    update_button.click()

    logging.info("Filter applied. Waiting for refresh...")
    time.sleep(2)  # or a more explicit wait if needed


def find_nonfull_calisthenics_events(driver):
    """
    Gather links + date/time from the visible month's calendar,
    but only for non-full Calisthenics events.
    This version also tries to read the "Date & Time" from the detail page
    or from the month cell. We'll do a simpler version that
    only collects the link from the main page to be faster.

    Returns list of (date_str, time_str, event_link) tuples
    or you can do partial here & parse date/time in detail page.
    """
    logging.info("Collecting non-full Calisthenics events from the visible calendar...")
    WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".wb-event"))
    )

    event_elements = driver.find_elements(By.CSS_SELECTOR, ".wb-event")
    results = []

    for event_el in event_elements:
        event_html = event_el.get_attribute("outerHTML")

        if "Calisthenics" not in event_html:
            continue

        # Check if full => look for bottom-row .count.float-right
        try:
            count_el = event_el.find_element(By.CSS_SELECTOR, ".bottom-row .count.float-right")
            count_text = count_el.text.strip()  # e.g. "10/10 +3"
        except NoSuchElementException:
            continue

        match = re.search(r"(\d+)/(\d+)", count_text)
        if match:
            booked = int(match.group(1))
            capacity = int(match.group(2))
            if booked >= capacity:
                logging.info(f"Skipping full class: {count_text}")
                continue

        # Not full => gather the link
        try:
            link_el = event_el.find_element(By.CSS_SELECTOR, ".top-row a")
            href = link_el.get_attribute("href")
            # We won't parse date/time from the month view, let's store "link only" for now
            # You could climb the DOM to get data-date if you prefer
            results.append(href)
        except NoSuchElementException:
            pass

    logging.info(f"Found {len(results)} non-full Calisthenics event links.")
    return results


def scrape_multiple_months(driver, months_to_scrape=6):
    """
    Scrapes non-full Calisthenics event links across multiple months.
    By default, scrapes current + next 5 months (total=6).

    Returns a list of links (strings).
    """
    all_links = []
    for i in range(months_to_scrape):
        month_links = find_nonfull_calisthenics_events(driver)
        all_links.extend(month_links)

        # Move to next month, except after last iteration
        if i < (months_to_scrape - 1):
            next_btn = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".fc-next-button"))
            )
            logging.info(f"Clicking NEXT (month {i+1}/{months_to_scrape})...")
            next_btn.click()
            time.sleep(3)

    return all_links


def parse_detail_date_time(driver):
    """
    On an event detail page, parse the "Date & Time" label => p,
    e.g. "14/02/2025 12:00" => return (date_str, time_str).
    """
    label_xpath = "//label[normalize-space(text())='Date & Time']/following-sibling::p"
    date_time_p = driver.find_element(By.XPATH, label_xpath)
    date_time_str = date_time_p.text.strip()  # e.g. "14/02/2025 12:00"

    try:
        dt = datetime.datetime.strptime(date_time_str, "%d/%m/%Y %H:%M")
        return dt.date().isoformat(), dt.time().isoformat()
    except ValueError:
        logging.warning(f"Could not parse date string: '{date_time_str}'")
        return ("UNKNOWN", "UNKNOWN")


def main():
    """
    Main crawler flow:
    1) Setup Selenium & log in
    2) Go to 423 Calendar, switch to Month, apply Calisthenics filter
    3) Scrape multiple months
    4) For each link, visit detail page & parse date/time
    5) Write results to CSV
    """
    # Set up Selenium
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # if desired
    driver = webdriver.Chrome(options=options)

    try:
        # 1) Login
        login_wodboard(driver)

        # 2) Calendar stuff
        go_to_calendar_423(driver)
        switch_to_month_view(driver)
        apply_filter_calisthenics(driver)

        # 3) Scrape multiple months
        all_event_links = scrape_multiple_months(driver, months_to_scrape=6)

        # 4) For each link, parse date/time from detail page
        rows = []
        for link in all_event_links:
            logging.info(f"Visiting event page: {link}")
            driver.get(link)
            time.sleep(2)

            date_str, time_str = parse_detail_date_time(driver)
            rows.append((date_str, time_str, link))

        # 5) Write to CSV
        csv_filename = "calisthenics_events.csv"
        logging.info(f"Writing {len(rows)} rows to {csv_filename} ...")

        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Optionally write header
            writer.writerow(["date", "time", "url"])
            for row in rows:
                writer.writerow(row)

        logging.info("Done scraping!")
        time.sleep(3)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
