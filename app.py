#!/usr/bin/env python3
"""Flask web UI for swim-checker."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from flask import Flask, jsonify, render_template, request

from pools.mirandabad import MirandabadChecker
from pools.mercator import MercatorChecker
from pools.meerkamp import MeerkampChecker

app = Flask(__name__)

POOLS = [MirandabadChecker(), MercatorChecker(), MeerkampChecker()]


def fetch_pool(pool, d: date) -> dict:
    slots, is_live = pool.get_slots(d)
    if is_live:
        source = "live"
    elif pool.has_fallback:
        source = "fallback"
    else:
        source = "unavailable"
    return {
        "name": pool.name,
        "url": pool.url,
        "source": source,
        "slots": [{"start": s.start.strftime("%H:%M"), "end": s.end.strftime("%H:%M")} for s in slots],
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/slots")
def api_slots():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Missing required parameter: date"}), 400
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": f"Invalid date format: '{date_str}'. Use YYYY-MM-DD."}), 400

    results = [None] * len(POOLS)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fetch_pool, pool, d): i for i, pool in enumerate(POOLS)}
        for future in as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()

    return jsonify({"date": date_str, "pools": results})


@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": str(e)}), 400


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=True)
