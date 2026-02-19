# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

CLI + web UI that fetches lane swimming (baanzwemmen) schedules for Amsterdam-area pools.

**CLI:**
```bash
python check.py              # today
python check.py tomorrow
python check.py 2026-03-01   # YYYY-MM-DD
```

**Web UI:**
```bash
python app.py                # serves on http://127.0.0.1:5000
```

## Setup

```bash
pip install -r requirements.txt
```

## Architecture

**`pools/base.py`** defines the base abstractions:
- `Slot` — a dataclass with `start`/`end` as `time` objects
- `PoolChecker` — base class with `fetch_live(d)` (override in subclasses), `FALLBACK` dict (weekday int → list of `("HH:MM", "HH:MM")` tuples), and `get_slots(d)` which tries live first and falls back to `FALLBACK`

**`pools/`** contains one checker per pool, each subclassing `PoolChecker`:
- `mirandabad.py` — hits the official Amsterdam zwembaden JSON API (`zwembaden.api-amsterdam.nl`), uses `primp` for browser impersonation; no static fallback (schedule changes weekly)
- `mercator.py` — scrapes a Next.js app, parses `__NEXT_DATA__` JSON embedded in the page; has a hardcoded fallback schedule
- `meerkamp.py` — tries WordPress REST API endpoints first, then HTML scraping with BeautifulSoup; has a hardcoded fallback schedule

**`check.py`** imports all checkers, calls `pool.get_slots(d)` for each, and prints formatted results.

**`app.py`** is the Flask web UI. `GET /api/slots?date=YYYY-MM-DD` fetches all pools in parallel via `ThreadPoolExecutor(max_workers=3)` and returns JSON with `source` set to `"live"`, `"fallback"`, or `"unavailable"`. `GET /` renders `templates/index.html`.

**`templates/index.html`** is a self-contained single-page UI (no build step, no framework) with inline CSS/JS. It uses `getFullYear/getMonth/getDate` (not `toISOString()`) to build the date string to avoid UTC offset issues for NL users.

## Adding a new pool

1. Create `pools/<poolname>.py` subclassing `PoolChecker`
2. Set `name`, `url`, and optionally `FALLBACK`
3. Implement `fetch_live(self, d: date) -> Optional[List[Slot]]` — return `None` on failure (don't raise; base class catches exceptions too)
4. Add an instance to the `POOLS` list in both `check.py` and `app.py`

## Notes on scraping

- Mirandabad times use Dutch decimal format (`"7.00"`, `"21.45"`) parsed by `_parse_dutch_time()`
- Mercator filters activities by checking if the title contains `"banen"` (Dutch for lane)
- Meerkamp fallback schedule changes seasonally — verify against the site before updating
- Fallback schedules are keyed by `date.weekday()` (0=Monday, 6=Sunday)
