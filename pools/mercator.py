"""
Scrapes Sportplaza Mercator's lane swimming schedule from
mercator.sportfondsen.nl, a Next.js app that embeds all data in a
__NEXT_DATA__ JSON script tag.

Relevant JSON path:
  props.pageProps -> search all objects for "timeSlots" arrays.
  Each slot: {day, dayValue, startTime, endTime,
               activitySchedule: {activity: {title, ...}}}

We filter for slots where the activity title contains "banen" (Dutch for lane).

Fallback: hardcoded weekly schedule (verified Feb 2026).
"""
import json
import re
from datetime import date
from typing import Any, Dict, List, Optional

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

_NL_DAYS = {
    "maandag": 0, "dinsdag": 1, "woensdag": 2, "donderdag": 3,
    "vrijdag": 4, "zaterdag": 5, "zondag": 6,
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

# Verified from sportfondsen.nl, Feb 2026
_FALLBACK: Dict[int, list] = {
    0: [("12:00", "13:00"), ("19:00", "21:00")],  # Monday
    1: [("07:00", "11:00"), ("12:00", "14:00")],  # Tuesday
    2: [("12:00", "13:00"), ("19:00", "21:00")],  # Wednesday
    3: [("07:00", "11:00"), ("12:00", "14:00")],  # Thursday
    4: [("09:00", "13:00")],                        # Friday
    5: [("12:00", "13:00")],                        # Saturday
    6: [("09:00", "11:00")],                        # Sunday
}


class MercatorChecker(PoolChecker):
    name = "Sportplaza Mercator"
    url = "https://www.sportplazamercator.nl/zwemmen/"
    _source_url = "https://mercator.sportfondsen.nl/tijden-tarieven-van-mercator/"
    FALLBACK = _FALLBACK

    def fetch_live(self, d: date) -> Optional[List[Slot]]:
        resp = requests.get(self._source_url, headers=_HEADERS, timeout=12)
        resp.raise_for_status()
        return self._parse(resp.text, d)

    def _parse(self, html: str, d: date) -> Optional[List[Slot]]:
        soup = BeautifulSoup(html, "lxml")
        target_wd = d.weekday()

        # Extract Next.js __NEXT_DATA__ JSON
        next_data_tag = soup.find("script", id="__NEXT_DATA__")
        if not next_data_tag or not next_data_tag.string:
            return None

        try:
            data = json.loads(next_data_tag.string)
        except json.JSONDecodeError:
            return None

        # Search all "timeSlots" arrays anywhere in the JSON tree
        all_timeslots = self._find_timeslots(data)
        if not all_timeslots:
            return None

        slots = []
        for slot in all_timeslots:
            if not isinstance(slot, dict):
                continue

            # Determine weekday from this slot
            day_str = (slot.get("dayValue") or slot.get("day") or "").lower().strip()
            day_idx = _NL_DAYS.get(day_str, -1)
            if day_idx != target_wd:
                continue

            # Filter for lane swimming activities only
            title = ""
            activity_schedule = slot.get("activitySchedule")
            if isinstance(activity_schedule, dict):
                activity = activity_schedule.get("activity") or {}
                title = (activity.get("title") or "").lower()
            if "banen" not in title:
                continue

            start = slot.get("startTime", "")
            end = slot.get("endTime", "")
            if start and end:
                try:
                    slots.append(Slot(start=_t(start), end=_t(end)))
                except (ValueError, Exception):
                    pass

        return slots if slots else None

    def _find_timeslots(self, obj: Any) -> List[Any]:
        """Recursively find any list stored under a 'timeSlots' key."""
        if isinstance(obj, dict):
            if "timeSlots" in obj and isinstance(obj["timeSlots"], list):
                return obj["timeSlots"]
            for v in obj.values():
                result = self._find_timeslots(v)
                if result:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = self._find_timeslots(item)
                if result:
                    return result
        return []
