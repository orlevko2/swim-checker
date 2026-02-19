from dataclasses import dataclass
from datetime import time, date
from typing import Dict, List, Optional, Tuple


def _t(s: str) -> time:
    """Parse 'HH:MM' (or 'HH:MM:SS') into a time object."""
    parts = s.strip()[:5].split(":")
    return time(int(parts[0]), int(parts[1]))


@dataclass(order=True)
class Slot:
    start: time
    end: time

    def __str__(self) -> str:
        return f"{self.start.strftime('%H:%M')} – {self.end.strftime('%H:%M')}"


class PoolChecker:
    name: str = ""
    url: str = ""

    # Fallback weekly schedule: 0=Mon … 6=Sun -> [("HH:MM", "HH:MM"), ...]
    FALLBACK: Dict[int, List[Tuple[str, str]]] = {}

    @property
    def has_fallback(self) -> bool:
        return bool(self.FALLBACK)

    def _fallback_for(self, d: date) -> List[Slot]:
        return [Slot(start=_t(s), end=_t(e)) for s, e in self.FALLBACK.get(d.weekday(), [])]

    def fetch_live(self, d: date) -> Optional[List[Slot]]:
        """Override to return live-scraped slots, or None on failure."""
        return None

    def get_slots(self, d: date) -> Tuple[List[Slot], bool]:
        """Return (slots, is_live_data)."""
        try:
            live = self.fetch_live(d)
            if live is not None:
                return sorted(live), True
        except Exception:
            pass
        return sorted(self._fallback_for(d)), False
