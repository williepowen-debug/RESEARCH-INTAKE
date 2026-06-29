#!/usr/bin/env python3
"""Treasury auction results — recent auctions from the FiscalData API.

Standalone port of FORGE/tools/auction-data/fetch_auctions.py. Public API, no key.
Snapshots auctions from the last DAYS days with bid-to-cover, tail, and a
strength classification vs historical bid-to-cover averages.
"""
import datetime
import json
import pathlib
import re
import urllib.parse
import urllib.request

ENDPOINT = ("https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
            "/v1/accounting/od/auctions_query")
DAYS = 30
HIST_BTC = {"2Y": 2.55, "3Y": 2.50, "5Y": 2.45, "7Y": 2.40, "10Y": 2.35, "30Y": 2.25}


def _standardize(sec_type, sec_term):
    if not sec_type or not sec_term:
        return None
    m = re.search(r"(\d+)", sec_term)
    if not m:
        return None
    y = m.group(1)
    if "TIPS" in sec_type:
        return f"{y}Y-TIPS"
    if "FRN" in sec_type:
        return f"{y}Y-FRN"
    if "Bill" in sec_type:
        return f"{y}W" if "Week" in sec_term else f"{y}M"
    return f"{y}Y"  # Note / Bond


def _f(v):
    try:
        return float(v) if v not in (None, "", "null") else None
    except (ValueError, TypeError):
        return None


def _classify(sec, btc):
    if btc is None:
        return "avg"
    h = HIST_BTC.get(sec, 2.4)
    if btc >= h * 1.05:
        return "strong"
    if btc < h * 0.90:
        return "weak"
    return "avg"


def fetch(data_dir: pathlib.Path) -> dict:
    start = (datetime.date.today() - datetime.timedelta(days=DAYS)).isoformat()
    params = {
        "fields": ("auction_date,security_type,security_term,bid_to_cover_ratio,"
                   "high_yield,low_yield,total_accepted"),
        "filter": f"auction_date:gte:{start}",
        "sort": "-auction_date",
        "page[size]": 100,
    }
    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Research-Intake", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
    except Exception as exc:
        return {"status": "error", "error": repr(exc)}

    auctions = []
    for rec in data.get("data", []):
        sec = _standardize(rec.get("security_type", ""), rec.get("security_term", ""))
        if not sec:
            continue
        btc = _f(rec.get("bid_to_cover_ratio"))
        hy, ly = _f(rec.get("high_yield")), _f(rec.get("low_yield"))
        acc = _f(rec.get("total_accepted"))
        auctions.append({
            "date": rec.get("auction_date"),
            "security": sec,
            "btc": round(btc, 2) if btc else None,
            "high_yield": round(hy, 3) if hy else None,
            "tail_bp": round((hy - ly) * 100, 1) if (hy and ly) else None,
            "awarded_b": round(acc / 1e9, 1) if acc else None,
            "status": _classify(sec, btc),
        })

    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    dest = data_dir / day
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "treasury_auctions.json").write_text(
        json.dumps({"window_days": DAYS, "auctions": auctions}, indent=2) + "\n")
    weak = [f"{a['security']} {a['date']} BTC {a['btc']}"
            for a in auctions if a["status"] == "weak"]
    return {"status": "ok", "count": len(auctions), "weak": weak,
            "saved": f"data/{day}/treasury_auctions.json"}
