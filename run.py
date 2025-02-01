import csv
import time
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.base import JobLookupError

########################################
# Example: Import your booking function
########################################
# from your_booking_module import book_event
# But we'll define a placeholder here:

def book_event(link):
    """
    Placeholder function to demonstrate booking.
    In reality, you'd do:
      1) login to WODBoard
      2) driver.get(link)
      3) click Book or Waitlist
    """
    logging.info(f"[BOOKING] Attempting to book: {link}")
    # ... Your Selenium logic or other code here ...
    # e.g. login, driver.get(link), find button, etc.

########################################
# APScheduler Setup
########################################
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    level=logging.INFO
)

# We create a background scheduler with basic config
executors = {
    'default': ThreadPoolExecutor(max_workers=10)
}
scheduler = BackgroundScheduler(executors=executors)


def schedule_events_from_csv(csv_filename):
    """
    Reads a CSV with rows: DATE, TIME, URL
    For each row:
      - parse the event date/time
      - compute booking_open_time = event_datetime - 14 days
      - if booking_open_time is in the future, schedule an APScheduler job
    """
    with open(csv_filename, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        # If there's a header, skip it:
        # next(reader, None)  # uncomment if needed

        for row in reader:
            if len(row) < 3:
                continue  # skip incomplete lines

            date_str = row[0].strip()  # e.g. "2025-02-14"
            time_str = row[1].strip()  # e.g. "12:00:00"
            link = row[2].strip()      # e.g. "https://www.wodboard.com/events/3107715"

            # Combine date/time into one string => "2025-02-14 12:00:00"
            dt_string = f"{date_str} {time_str}"

            # Parse into a Python datetime object
            try:
                event_dt = datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                logging.warning(f"Invalid date/time in row: {row}")
                continue

            # Compute the earliest booking open time: 14 days before the event time
            # If your gym's policy is different, adjust accordingly
            booking_open_dt = event_dt - timedelta(days=14)

            # If we've already passed the booking open time, it means we can attempt booking now
            # or you can skip if it's too late
            if booking_open_dt < datetime.now():
                logging.info(f"Booking time for {link} is already open or in the past. Booking now.")
                # Optionally schedule immediate job, or just call book_event(link).
                scheduler.add_job(
                    book_event,
                    args=[link],
                    # 'date' trigger => run immediately if run_date < now
                    trigger='date',
                    run_date=datetime.now()
                )
            else:
                # Schedule the job to run exactly at booking_open_dt
                logging.info(f"Scheduling {link} for {booking_open_dt}.")
                scheduler.add_job(
                    book_event,
                    'date',
                    run_date=booking_open_dt,
                    args=[link]
                )


def main():
    csv_file = "calisthenics_events.csv"  # your CSV path
    schedule_events_from_csv(csv_file)

    # Start APScheduler
    scheduler.start()
    logging.info("Scheduler started. Waiting for jobs to run...")

    try:
        # Keep the main thread alive so scheduler can run
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Exiting... shutting down scheduler.")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
