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


# --- threshold->alert layer (PROME 2026-06-30) --------------------------------
# Gives EIA the same uniform `alerts` shape as fetch_fred.py so the lane emits
# one significance vocabulary across all feeds; the consumer (WALTER) gates on it
# and de-dupes on persistence. Bands:
#   Cushing  — DOCUMENTED: <20M = operational min / WTI dislocation
#              (FORGE config.py L189 "ROUTING_TABLE Boundary #3"; BRENT STATUS
#              "20M operational floor", breached 2026-06-24). red <20, orange <21.
#   crude WoW — PROME conservative default (TODO[BRENT] confirm): a large single-
#              week swing is notable-INFO at |Δ|>=8 MMbbl. No red (one weekly
#              inventory print rarely warrants ACTION alone). spr/gasoline/
#              distillate left raw (no band) until BRENT supplies levels.
def _eia_alerts(metrics: dict) -> tuple:
    """Return (alerts:list[str], statuses:dict[label,str]) from the metrics dict.
    Each metric carries {value, wow, period}; statuses map label->red/orange/green."""
    alerts, statuses = [], {}

    cush = metrics.get("cushing_mbbl") or {}
    v = cush.get("value")
    if v is not None:
        st = "red" if v < 20.0 else "orange" if v < 21.0 else "green"
        statuses["cushing_mbbl"] = st
        if st in ("orange", "red"):
            alerts.append(f"cushing_mbbl Cushing={v}M [{st}] (<20M=Boundary#3 operational floor)")

    crude = metrics.get("commercial_crude_mbbl") or {}
    wow = crude.get("wow")
    if wow is not None and abs(wow) >= 8.0:
        statuses["commercial_crude_mbbl"] = "orange"
        kind = "draw" if wow < 0 else "build"
        alerts.append(f"commercial_crude_mbbl crude WoW {kind} {abs(wow)}M [orange]")

    return alerts, statuses


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
    # EIA v2 returns values as strings; cast at the boundary so downstream math works.
    return [{"date": r["period"], "value": float(r["value"])}
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

    alerts, statuses = _eia_alerts(metrics)
    for label, st in statuses.items():       # fold status into the saved metric
        metrics[label]["status"] = st

    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    dest = data_dir / day
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "eia_petroleum.json").write_text(
        json.dumps({"metrics": metrics, "raw": raw, "alerts": alerts}, indent=2) + "\n")

    return {
        "status": "ok",
        "metrics": {k: v["value"] for k, v in metrics.items()},
        "alerts": alerts,
        "saved": f"data/{day}/eia_petroleum.json",
    }
