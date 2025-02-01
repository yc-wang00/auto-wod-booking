"""
scheduler.py
------------
Reads "calisthenics_events.csv" produced by crawler.py,
Schedules a booking job 14 days before each event's date/time
(using APScheduler).
"""

import csv
import time
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from crawler import login_wodboard


def book_event(link, username, password):
    """
    1) Creates a new Selenium driver
    2) Log in to WODBoard using username/password
    3) Navigate to the event link
    4) Try to click the 'Book' button
    5) Close the driver
    """
    logging.info(f"[AUTO-BOOK] Attempting to book: {link}")

    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # optional if you want to run headless
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()

    try:
        # 1) Log in
        driver.get("https://www.wodboard.com/login")
        login_wodboard(driver, username, password)

        # 2) Go to event link
        driver.get(link)
        logging.info(f"Opened event page: {link}")
        time.sleep(2)  # small pause for page to load

        # 3) Attempt to find and click the Book button
        try:
            btn_xpath = (
                "//div[@class='form-footer']"
                "//a[contains(@class, 'btn btn-primary') and normalize-space(text())='Book']"
            )
            book_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, btn_xpath))
            )
            book_btn.click()
            logging.info("Clicked the 'Book' button successfully!")
            time.sleep(2)
            return True

        except NoSuchElementException:
            logging.info("No 'Book' button found. Possibly not open for booking.")
            return False

        except Exception as e:
            logging.exception(f"Error while trying to click 'Book' button: {e}")
            return False

    finally:
        driver.quit()


def schedule_events_from_csv(csv_filename):
    """
    Reads a CSV with rows: date, time, url
    For each row:
      - parse the event date/time => event_dt
      - compute booking_open_dt = event_dt - 14 days
      - schedule APScheduler job if that time is in the future
    """
    with open(csv_filename, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        # skip header
        header = next(reader, None)
        # if the first row is actually your data, remove this line

        for row in reader:
            if len(row) < 3:
                continue

            date_str = row[0].strip()  # e.g. "2025-02-14"
            time_str = row[1].strip()  # e.g. "12:00:00" or "12:00:00.000000"
            link = row[2].strip()

            # Merge date/time => "2025-02-14 12:00:00"
            combined_str = f"{date_str} {time_str}"
            # attempt parsing
            try:
                # If your time is "12:00:00", this should parse fine
                event_dt = datetime.strptime(combined_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # try partial parse if microseconds exist
                try:
                    event_dt = datetime.strptime(combined_str, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    logging.warning(f"Invalid date/time: {combined_str}")
                    continue

            booking_open_dt = event_dt - timedelta(days=14)

            # If booking_open_dt is past, schedule immediately or skip
            if booking_open_dt < datetime.now():
                logging.info(f"Booking time for {link} is past => scheduling immediate job.")
                scheduler.add_job(book_event, 'date', run_date=datetime.now(), args=[link])
            else:
                logging.info(f"Scheduling {link} for {booking_open_dt}")
                scheduler.add_job(book_event, 'date', run_date=booking_open_dt, args=[link])


############################
# APScheduler Setup
############################
executors = {
    'default': ThreadPoolExecutor(max_workers=5)
}
scheduler = BackgroundScheduler(executors=executors)

def main():
    csv_file = "calisthenics_events.csv"
    schedule_events_from_csv(csv_file)

    scheduler.start()
    logging.info("Scheduler started. Waiting for jobs to execute...")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Shutting down scheduler.")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
