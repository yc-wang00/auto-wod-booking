# booking.py
# ----------
# A self-contained module for logging into WODBoard and booking an event.

import time
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from crawler import login_wodboard
from crawler import USERNAME, PASSWORD


########################################
# 3) Book function
########################################


def book_event(link, username, password):
    """
    High-level booking flow:
      1) Create a new Selenium browser
      2) Log into WODBoard
      3) Navigate to the event 'link'
      4) Attempt to find & click the "Book" button
      5) Close the browser
      Returns True if booked, False otherwise.
    """
    logging.info(f"[AUTO-BOOK] Attempting to book: {link}")

    # Optionally configure headless mode or other ChromeOptions
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Uncomment if you want headless
    driver = webdriver.Chrome(options=options)

    try:
        # 1) Login
        login_wodboard(driver, username, password)

        # 2) Go to the event page
        logging.info(f"Navigating to event link: {link}")
        driver.get(link)
        time.sleep(2)  # let page render

        # 3) Attempt to find "Book" button
        try:
            # We'll wait up to 10s for the button
            book_btn_xpath = (
                "//div[@class='form-footer']"
                "//a[contains(@class, 'btn btn-primary') and normalize-space(text())='Book']"
            )
            book_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, book_btn_xpath)))
            book_btn.click()
            logging.info("Clicked the 'Book' button successfully!")
            time.sleep(2)
            return True

        except (NoSuchElementException, TimeoutException):
            logging.info("No 'Book' button found. Possibly not open for booking.")
            return False

        except Exception as e:
            logging.exception(f"Error while trying to click 'Book' button: {e}")
            return False

    finally:
        driver.quit()
        logging.info("Browser closed after booking attempt.")


# If you want to test locally, you can do something like:
if __name__ == "__main__":
    test_link = "https://www.wodboard.com/events/3083038"  # example

    success = book_event(test_link, USERNAME, PASSWORD)
    if success:
        logging.info("Booked successfully (or at least found Book button) in test mode.")
    else:
        logging.info("Booking failed or not open in test mode.")
