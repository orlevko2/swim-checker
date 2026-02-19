"""
Scrapes De Mirandabad's lane swimming schedule from the official
Amsterdam zwembaden API: https://zwembaden.api-amsterdam.nl/

Discovered by reverse-engineering the Vue.js SPA embedded in
https://www.amsterdam.nl/demirandabad/activiteiten/banenzwemmen/

API endpoint: GET /nl/api/de-mirandabad/date/{YYYY-MM-DD}/
Returns JSON: {"pool": "...", "schedule": [{"activity", "start", "end", "extra", "dow"}, ...]}
Times are in Dutch decimal format: "7.00", "12.00", "21.45" (dot separator, not colon).

Fallback: none — schedule changes weekly, no reliable static fallback.
"""
from datetime import date, time
from typing import List, Optional

import primp

from .base import PoolChecker, Slot

_API_BASE = "https://zwembaden.api-amsterdam.nl/nl/api/de-mirandabad"


def _parse_dutch_time(s: str) -> time:
    """Parse Dutch decimal time like '7.00' or '21.45' into a time object."""
    h, m = s.strip().split(".")
    return time(int(h), int(m))


class MirandabadChecker(PoolChecker):
    name = "De Mirandabad"
    url = "https://www.amsterdam.nl/demirandabad/activiteiten/banenzwemmen/"

    # Schedule changes weekly — no reliable static fallback
    FALLBACK = {}

    def fetch_live(self, d: date) -> Optional[List[Slot]]:
        client = primp.Client(impersonate="chrome_120")
        resp = client.get(f"{_API_BASE}/date/{d.isoformat()}/")
        if resp.status_code != 200:
            raise RuntimeError(f"API returned {resp.status_code}")
        data = resp.json()
        slots = []
        for entry in data.get("schedule", []):
            if "banen" not in entry.get("activity", "").lower():
                continue
            try:
                slots.append(Slot(
                    start=_parse_dutch_time(entry["start"]),
                    end=_parse_dutch_time(entry["end"]),
                ))
            except (KeyError, ValueError):
                pass
        return slots
