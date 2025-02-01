# scheduler.py
# ------------
# Reads "calisthenics_events.csv" produced by crawler.py,
# and schedules an auto-book job 14 days before each event's date/time.

import csv
import time
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor

# Import your booking code & credentials
from booking import book_event, USERNAME, PASSWORD

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    level=logging.INFO
)

# Create a background scheduler with a thread-pool executor
executors = {
    'default': ThreadPoolExecutor(max_workers=1)
}
scheduler = BackgroundScheduler(executors=executors)


def schedule_events_from_csv(csv_filename):
    """
    Reads CSV rows: date, time, link
      - date_str like "2025-02-14"
      - time_str like "12:00:00"
      - link like "https://www.wodboard.com/events/3107715"

    For each row:
      1) parse the event datetime => event_dt
      2) compute (event_dt - 14 days) => booking_open_dt
      3) schedule a job to call book_event(link, USERNAME, PASSWORD) at booking_open_dt
         or if booking_open_dt < now, schedule job immediately.
    """
    with open(csv_filename, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        # If your CSV has a header line, uncomment this:
        # next(reader, None)  # Skip header row

        for row in reader:
            if len(row) < 3:
                continue  # skip incomplete lines

            date_str = row[0].strip()  # e.g. "2025-02-14"
            time_str = row[1].strip()  # e.g. "12:00:00"
            link = row[2].strip()      # e.g. "https://www.wodboard.com/events/3107715"

            # Merge into "2025-02-14 12:00:00"
            dt_str = f"{date_str} {time_str}"

            # Attempt parsing
            try:
                event_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Some CSV might have partial seconds, e.g. "12:00:00.000000"
                # Let's do a second try with microseconds
                try:
                    event_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    logging.warning(f"Could not parse date/time from row: {row}")
                    continue

            # booking_open_dt is 14 days before the event
            booking_open_dt = event_dt - timedelta(days=14)

            # If booking_open_dt is in the past, either schedule immediately or skip
            if booking_open_dt < datetime.now():
                logging.info(f"Booking window for {link} is in the past => scheduling immediate job.")
                scheduler.add_job(
                    book_event,
                    'date',
                    run_date=datetime.now(),
                    args=[link, USERNAME, PASSWORD]
                )
            else:
                # schedule a job at booking_open_dt
                logging.info(f"Scheduling booking for {link} at {booking_open_dt}.")
                scheduler.add_job(
                    book_event,
                    'date',
                    run_date=booking_open_dt,
                    args=[link, USERNAME, PASSWORD]
                )


def main():
    csv_file = "calisthenics_events.csv"
    schedule_events_from_csv(csv_file)

    # Start APScheduler
    scheduler.start()
    logging.info("Scheduler started. Waiting for jobs to execute...")

    try:
        # Keep the script alive so APScheduler can run jobs in the background
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Exiting... shutting down scheduler.")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
