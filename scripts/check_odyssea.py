#!/usr/bin/env python3
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

CINEMA_ID = "1052"  # OC Flora
CINEMA_SLUG = "flora"
SHOW_DATE = "2026-08-15"
FILM_ID = "7268s2r"  # Odyssea
END_DATE = "2026-08-15"
PROGRAMME_LINK = (
    f"https://www.cinemacity.cz/cinemas/{CINEMA_SLUG}/{CINEMA_ID}"
    f"#/buy-tickets-by-cinema?in-cinema={CINEMA_ID}&at={SHOW_DATE}&for-movie={FILM_ID}&view-mode=list"
)


def fetch_events(retries=3):
    url = (
        "https://www.cinemacity.cz/cz/data-api-service/v1/quickbook/10101/"
        f"film-events/in-cinema/{CINEMA_ID}/at-date/{SHOW_DATE}?attr=&lang=cs_CZ"
    )
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.load(resp)
            return data.get("body", {}).get("events", [])
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == retries:
                raise
            print(f"fetch attempt {attempt} failed ({e}), retrying...")
            time.sleep(5)


def send_telegram(message):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode()
    with urllib.request.urlopen(url, data=data, timeout=30) as resp:
        print("telegram response:", resp.read().decode())


def main():
    today = subprocess.check_output(["date", "-u", "+%F"]).decode().strip()
    if today > END_DATE:
        print(f"Past end date {END_DATE} (today {today}), nothing to do.")
        return

    events = fetch_events()
    matches = [
        e
        for e in events
        if e.get("filmId") == FILM_ID and "70-mm" in (e.get("attributeIds") or [])
    ]

    if not matches:
        print("No 70mm showtimes published yet.")
        return

    available = [e for e in matches if not e.get("soldOut")]

    if available:
        best = max(available, key=lambda e: e.get("availabilityRatio", 0))
        others = len(available) - 1
        pct = round(best.get("availabilityRatio", 0) * 100)
        time_str = best["eventDateTime"].split("T")[1][:5]
        extra = f" (+{others} more)" if others > 0 else ""
        msg = f"Odyssea 70mm 15.8 Flora LIVE! {time_str} avail {pct}%{extra} -> {PROGRAMME_LINK}"
    else:
        msg = f"Odyssea 70mm 15.8 Flora: showtimes published but already SOLD OUT. -> {PROGRAMME_LINK}"

    send_telegram(msg)


if __name__ == "__main__":
    main()
