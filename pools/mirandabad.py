"""
Scrapes De Mirandabad's lane swimming schedule from ikwilalleenmaarzwemmen.nl,
an Amsterdam pool aggregator that fetches times daily.

Page structure:
  - div.days: text list of day labels ("do 19 februari", "vr 20 februari", ...)
  - div.day (multiple, one per day shown): contains div.pool-list-item entries
    Each item has: "<time> | <activity> | @<pool>"

Fallback: none — Mirandabad's schedule changes every week, so a static
fallback would mislead. When scraping fails the user is directed to the URL.
"""
import re
from datetime import date
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from .base import PoolChecker, Slot, _t

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9",
}

_NL_MONTHS = {
    1: "januari", 2: "februari", 3: "maart", 4: "april", 5: "mei", 6: "juni",
    7: "juli", 8: "augustus", 9: "september", 10: "oktober",
    11: "november", 12: "december",
}

# Dutch weekday abbreviations for matching day labels
_NL_DAYS_ABBR = {0: "ma", 1: "di", 2: "wo", 3: "do", 4: "vr", 5: "za", 6: "zo"}

_TIME_RE = re.compile(r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})")


class MirandabadChecker(PoolChecker):
    name = "De Mirandabad"
    url = "https://www.amsterdam.nl/demirandabad/activiteiten/banenzwemmen/"
    _agg_url = "https://ikwilalleenmaarzwemmen.nl/"

    # No reliable static fallback — schedule changes weekly
    FALLBACK = {}

    def fetch_live(self, d: date) -> Optional[List[Slot]]:
        resp = requests.get(self._agg_url, headers=_HEADERS, timeout=12)
        resp.raise_for_status()
        return self._parse(resp.text, d)

    def _parse(self, html: str, d: date) -> Optional[List[Slot]]:
        soup = BeautifulSoup(html, "lxml")

        # Build the Dutch date label to look for, e.g. "do 19 februari"
        day_abbr = _NL_DAYS_ABBR[d.weekday()]
        month_name = _NL_MONTHS[d.month]
        date_label = f"{day_abbr} {d.day} {month_name}"  # e.g. "do 19 februari"

        # Find the index of our target date within div.days
        days_container = soup.find("div", class_="days")
        if not days_container:
            return None

        day_labels = [t.strip().lower() for t in days_container.stripped_strings]
        try:
            day_index = next(
                i for i, lbl in enumerate(day_labels) if date_label in lbl
            )
        except StopIteration:
            return None

        # Get the corresponding div.day at that index
        day_divs = soup.find_all("div", class_="day")
        if day_index >= len(day_divs):
            return None

        target_day_div = day_divs[day_index]

        # Within that day, find pool-list-items for Mirandabad + Banenzwemmen.
        # Return [] (not None) when the day section is found — empty means
        # "no lane swimming today", not "couldn't fetch".
        slots = []
        for item in target_day_div.find_all("div", class_="pool-list-item"):
            text = item.get_text(separator=" | ", strip=True)
            if "Mirandabad" not in text:
                continue
            if "banen" not in text.lower():
                continue
            m = _TIME_RE.search(text)
            if m:
                slots.append(Slot(start=_t(m.group(1)), end=_t(m.group(2))))

        return slots
