#!/usr/bin/env python3
"""Fetch EIA Weekly Petroleum Status figures via the EIA v2 API.

Writes the raw payload to data/<date>/eia_petroleum.json and returns a status dict.
Skips gracefully (status="skipped") when EIA_API_KEY is absent, so the lane never
breaks waiting on the secret.

API key: free from https://www.eia.gov/opendata/register.php

⚠️  UNVERIFIED SCHEMA: the endpoint route and series IDs below are a best-guess
template. Per our standing rule, map fields from a LIVE call before trusting them
(finding_verify_live_api_schema_over_docs). When the key is added, run once, inspect
the response, and correct EIA_V2_URL / SERIES / the row parsing as needed.
"""
import datetime
import json
import os
import pathlib

import requests

EIA_V2_URL = "https://api.eia.gov/v2/petroleum/stoc/wstk/data/"
SERIES = {
    "crude_excl_spr_mbbl": "WCESTUS1",         # US crude stocks excl SPR (weekly)
    "cushing_mbbl": "W_EPC0_SAX_YCUOK_MBBL",   # Cushing, OK stocks (weekly)
}


def fetch(data_dir: pathlib.Path) -> dict:
    key = os.environ.get("EIA_API_KEY", "").strip()
    if not key:
        return {"status": "skipped", "reason": "no EIA_API_KEY"}

    out = {}
    try:
        for label, series_id in SERIES.items():
            resp = requests.get(
                EIA_V2_URL,
                params={
                    "api_key": key,
                    "frequency": "weekly",
                    "data[0]": "value",
                    "facets[series][]": series_id,
                    "sort[0][column]": "period",
                    "sort[0][direction]": "desc",
                    "length": 1,
                },
                timeout=30,
            )
            resp.raise_for_status()
            rows = resp.json().get("response", {}).get("data", [])
            out[label] = rows[0] if rows else None
    except Exception as exc:
        return {"status": "error", "error": repr(exc)}

    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    dest = data_dir / day
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "eia_petroleum.json").write_text(json.dumps(out, indent=2) + "\n")

    return {
        "status": "ok",
        "values": {k: (v or {}).get("value") for k, v in out.items()},
        "saved": f"data/{day}/eia_petroleum.json",
    }
