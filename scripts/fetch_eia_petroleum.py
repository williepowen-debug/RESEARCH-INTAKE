#!/usr/bin/env python3
"""Fetch EIA Weekly Petroleum Status figures via the EIA v2 API.

Standalone port of the VALIDATED fetcher in the working repo
(FORGE/tools/market-data/fetch.py::eia_fetch + AGENTS/BRENT/scripts/eia_weekly.py).
Series IDs were validated against known weekly prints on 2026-06-22. This repo
can't import FORGE (separate repo), so the logic is inlined here.

Writes data/<date>/eia_petroleum.json and returns a status dict. Skips gracefully
(status="skipped") when EIA_API_KEY is absent, so the lane never breaks waiting on
the secret.

API key: free from https://www.eia.gov/opendata/register.php
"""
import datetime
import json
import os
import pathlib
import urllib.parse

import requests

EIA_BASE = "https://api.eia.gov/v2"

# canonical metric -> (series_id, route, multiply-to-display-unit)
# Stock series report THOUSAND barrels; x0.001 -> MILLION barrels for display.
EIA_SERIES = {
    "commercial_crude_mbbl": ("WCESTUS1",              "petroleum/stoc/wstk", 0.001),
    "spr_mbbl":              ("WCSSTUS1",              "petroleum/stoc/wstk", 0.001),
    "cushing_mbbl":          ("W_EPC0_SAX_YCUOK_MBBL", "petroleum/stoc/wstk", 0.001),
    "gasoline_mbbl":         ("WGTSTUS1",              "petroleum/stoc/wstk", 0.001),
    "distillate_mbbl":       ("WDISTUS1",              "petroleum/stoc/wstk", 0.001),
}


def eia_fetch(key, series_id, route, limit=2):
    """Pull a weekly EIA v2 series, newest-first. Returns [{date, value}, ...]."""
    params = {
        "api_key": key,
        "frequency": "weekly",
        "data[0]": "value",
        "facets[series][]": series_id,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": limit,
    }
    url = f"{EIA_BASE}/{route}/data/?{urllib.parse.urlencode(params)}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    rows = resp.json().get("response", {}).get("data", [])
    return [{"date": r["period"], "value": r["value"]}
            for r in rows if r.get("value") is not None]


def fetch(data_dir: pathlib.Path) -> dict:
    key = os.environ.get("EIA_API_KEY", "").strip()
    if not key:
        return {"status": "skipped", "reason": "no EIA_API_KEY"}

    metrics, raw = {}, {}
    try:
        for label, (series_id, route, mult) in EIA_SERIES.items():
            rows = eia_fetch(key, series_id, route, limit=2)
            raw[label] = rows
            if rows:
                latest = rows[0]["value"] * mult
                wow = (rows[0]["value"] - rows[1]["value"]) * mult if len(rows) > 1 else None
                metrics[label] = {
                    "value": round(latest, 3),
                    "wow": round(wow, 3) if wow is not None else None,
                    "period": rows[0]["date"],
                }
    except Exception as exc:
        return {"status": "error", "error": repr(exc)}

    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    dest = data_dir / day
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "eia_petroleum.json").write_text(
        json.dumps({"metrics": metrics, "raw": raw}, indent=2) + "\n")

    return {
        "status": "ok",
        "metrics": {k: v["value"] for k, v in metrics.items()},
        "saved": f"data/{day}/eia_petroleum.json",
    }
