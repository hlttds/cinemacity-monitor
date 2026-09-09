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
SHOW_DATE = "2026-12-19"
FILM_ID = "8105s2r"  # Duna: cast treti (Dune: Part Three)
END_DATE = "2026-12-19"
PREFERRED_HOUR_MINUTES = 17 * 60  # user wants a showtime around 17:00
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
    try:
        with urllib.request.urlopen(url, data=data, timeout=30) as resp:
            print("telegram response:", resp.read().decode())
    except urllib.error.HTTPError as e:
        print("telegram error body:", e.read().decode())
        raise


def minutes_from_preferred(event):
    hh, mm = event["eventDateTime"].split("T")[1][:5].split(":")
    return abs(int(hh) * 60 + int(mm) - PREFERRED_HOUR_MINUTES)


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
        # Prefer the showtime closest to 17:00, not just the most available one
        best = min(available, key=minutes_from_preferred)
        others = len(available) - 1
        pct = round(best.get("availabilityRatio", 0) * 100)
        time_str = best["eventDateTime"].split("T")[1][:5]
        extra = f" (+{others} more)" if others > 0 else ""
        msg = f"Duna3 70mm 19.12 Flora LIVE! {time_str} avail {pct}%{extra} -> {PROGRAMME_LINK}"
    else:
        msg = f"Duna3 70mm 19.12 Flora: showtimes published but already SOLD OUT. -> {PROGRAMME_LINK}"

    send_telegram(msg)


if __name__ == "__main__":
    main()
