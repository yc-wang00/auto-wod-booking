# WodBoard Auto-Booking

This project automates:

1. **Crawling** the WodBoard site to gather class/event information (especially _Calisthenics_ classes).
2. **Scheduling** automatic bookings for those classes as soon as they become available (14 days in advance, or your chosen rule).

---

## **Get Started**

### **Pre-Requirements**

- **uv** (a modern Python package manager)  
  Install **uv**: [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)

- Install project dependencies:
  ```bash
  uv sync
  ```

---

### **Environment Setup**

Provide **WODBOARD_USERNAME** and **WODBOARD_PASSWORD**:

- Either **system environment variables**, **or**
- A `.env` file:

  ```bash
  WODBOARD_USERNAME=your_email@example.com
  WODBOARD_PASSWORD=supersecret123
  ```

---

## **Usage Workflow**

### **1️⃣ Crawl Classes**

Run the crawler to collect class data:

```bash
uv run crawler.py
```

This will:

- **Log in** to WodBoard
- **Scrape** multiple months for Calisthenics events
- **Parse** each event detail page (date/time)
- **Store** results in `calisthenics_events.csv`

---

### **2️⃣ Schedule Bookings**

Start the scheduler:

```bash
uv run scheduler.py
```

This will:

- **Read** `calisthenics_events.csv`
- **Schedule bookings** (14 days before each event)
- **Run continuously** in the background

---

## **Run as a Background Process**

To **keep the scheduler running** in the background using `nohup`:

```bash
nohup uv run scheduler.py > scheduler.log 2>&1 &
```

### **Check Logs**

Monitor what’s happening in real-time:

```bash
tail -f scheduler.log
```

👉 **Stop viewing logs:** `Ctrl + C`

### **Stop the Background Process**

Find the running process:

```bash
ps aux | grep scheduler.py
```

Kill the process (replace `<PID>` with the actual process ID):

```bash
kill <PID>
```

---

## **File Overview**

- **`crawler.py`** – Scrapes WodBoard for event details, storing results in `calisthenics_events.csv`
- **`booking.py`** – Handles login and booking logic
- **`scheduler.py`** – Reads events and schedules bookings using APScheduler

---

✅ **Now, your auto-booking system runs automatically in the background!** 🚀
