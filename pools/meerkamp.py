"""
Scrapes De Meerkamp (Amstelveen) lane swimming schedule from
amstelveensport.nl, which runs WordPress with the Modern Events Calendar
plugin. Tries the WP REST API first, then HTML scraping.

Fallback: hardcoded weekly schedule (verified Feb 2026, may change seasonally).
"""
import re
from datetime import date
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .base import PoolChecker, Slot, _t

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
}

_TIME_RE = re.compile(r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})")

# Verified from amstelveensport.nl, Feb 2026 (changes seasonally)
_FALLBACK: Dict[int, list] = {
    0: [("07:00", "15:00"), ("18:00", "21:00")],  # Monday
    1: [("07:00", "15:00"), ("18:00", "21:00")],  # Tuesday
    2: [("07:00", "15:00"), ("18:00", "21:00")],  # Wednesday
    3: [("07:00", "15:00"), ("18:00", "21:00")],  # Thursday
    4: [("07:00", "15:00"), ("18:00", "21:00")],  # Friday
    5: [("10:30", "13:30")],                        # Saturday
    6: [("09:00", "12:00")],                        # Sunday
}

_BASE = "https://amstelveensport.nl"

# WordPress REST API endpoints to try (Tribe Events Calendar + MEC)
def _api_urls(d: date) -> List[str]:
    ds = d.isoformat()
    return [
        f"{_BASE}/wp-json/tribe/events/v1/events"
        f"?tags=baanzwemmen&start_date={ds}&end_date={ds}&per_page=20",
        f"{_BASE}/wp-json/mec/v1/events?date={ds}",
    ]


class MeerkampChecker(PoolChecker):
    name = "De Meerkamp (Amstelveen)"
    url = f"{_BASE}/en/zwembad-de-meerkamp/banenzwemmen/"
    FALLBACK = _FALLBACK

    def fetch_live(self, d: date) -> Optional[List[Slot]]:
        # Try REST API endpoints
        for url in _api_urls(d):
            try:
                resp = requests.get(url, headers=_HEADERS, timeout=8)
                if resp.status_code == 200:
                    slots = self._parse_api(resp.json(), d)
                    if slots is not None:
                        return slots
            except Exception:
                continue

        # Try HTML scraping
        try:
            resp = requests.get(self.url, headers=_HEADERS, timeout=10)
            if resp.ok:
                result = self._parse_html(resp.text, d)
                if result:
                    return result
        except Exception:
            pass

        return None

    def _parse_api(self, data: dict, d: date) -> Optional[List[Slot]]:
        events = data.get("events", []) if isinstance(data, dict) else []
        if not events:
            return None
        slots = []
        date_str = d.isoformat()
        for ev in events:
            start_raw = ev.get("start_date", "")
            end_raw = ev.get("end_date", "")
            if date_str not in start_raw:
                continue
            try:
                s = start_raw[11:16]
                e = end_raw[11:16]
                if s and e:
                    slots.append(Slot(start=_t(s), end=_t(e)))
            except (IndexError, ValueError):
                pass
        return slots or None

    def _parse_html(self, html: str, d: date) -> Optional[List[Slot]]:
        soup = BeautifulSoup(html, "lxml")
        date_str = d.isoformat()
        slots = []

        # MEC renders event tiles with data-date attributes
        for tag in soup.find_all(attrs={"data-date": True}):
            if str(tag.get("data-date", "")).startswith(date_str):
                matches = _TIME_RE.findall(tag.get_text(" "))
                slots.extend(Slot(start=_t(s), end=_t(e)) for s, e in matches)

        return slots or None
