#!/usr/bin/env python3
"""CFTC Commitments of Traders — VIX futures positioning (TFF report).

Standalone port of AGENTS/VIOLET/scripts/cftc_cot.py (verified column layout).
Public, no key. Pulls the latest weekly Traders-in-Financial-Futures row for VIX
futures and writes net positioning by category.

NOTE: crude/energy COT lives in the CFTC *disaggregated* report — a different
file and column layout — so it's a separate add after live verification.
"""
import csv
import datetime
import io
import json
import pathlib
import urllib.request

WEEKLY_URL = "https://www.cftc.gov/dea/newcot/FinFutWk.txt"
VIX_MARKET_NAME = "VIX FUTURES - CBOE FUTURES EXCHANGE"
VIX_CONTRACT_CODE = "1170E1"

# TFF column indices (0-based), verified in VIOLET/scripts/cftc_cot.py
COL = dict(name=0, date=2, code=3, oi=7,
           dealer_l=8, dealer_s=9, am_l=11, am_s=12, lev_l=14, lev_s=15)

# --- alert layer (PROME 2026-06-30) -------------------------------------------
# TRACK-ONLY for now: returns a uniform `alerts` key (like fetch_fred.py) so the
# lane emits one significance vocabulary across all feeds and WALTER's gate can
# treat every feed identically. But the VIX leveraged-money-net BAND is owned by
# VIOLET/SAM and is not documented anywhere (config.py has no positioning band,
# and we have a single weekly snapshot — no history to derive an extreme). So no
# live threshold is set; activating a made-up band would false-fire and erode the
# significance gate. TODO[VIOLET/SAM] ratify a band, then set VIX_LEV_NET_BAND and
# emit alerts here. Suggested starting points for VIOLET to confirm/replace:
#   - net flips POSITIVE (lev funds net-LONG vol) = de-risking/vol-buying regime
#   - net < ~ -75000 (extreme net-short vol / max complacency)
VIX_LEV_NET_BAND = None  # (lo, hi) once VIOLET/SAM ratify; None = track-only


def _vix_alerts(row: dict) -> list:
    """Uniform alerts list. Empty until VIX_LEV_NET_BAND is ratified (track-only)."""
    if VIX_LEV_NET_BAND is None:
        return []
    lo, hi = VIX_LEV_NET_BAND
    net = row.get("lev_money_net")
    if net is None:
        return []
    if net >= hi:
        return [f"cftc_cot VIX lev-money net={net} [orange] (net-long vol / de-risking)"]
    if net <= lo:
        return [f"cftc_cot VIX lev-money net={net} [orange] (extreme net-short vol)"]
    return []


def fetch(data_dir: pathlib.Path) -> dict:
    try:
        req = urllib.request.Request(
            WEEKLY_URL, headers={"User-Agent": "Mozilla/5.0 Research-Intake/cftc"})
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode("utf-8", "replace")
    except Exception as exc:
        return {"status": "error", "error": repr(exc)}

    row = None
    for fields in csv.reader(io.StringIO(text)):
        if len(fields) < 25:
            continue
        name = fields[COL["name"]].strip().strip('"')
        code = fields[COL["code"]].strip()
        if name == VIX_MARKET_NAME or code == VIX_CONTRACT_CODE:
            try:
                row = {
                    "report_date": fields[COL["date"]].strip(),
                    "open_interest": int(fields[COL["oi"]]),
                    "dealer_net": int(fields[COL["dealer_l"]]) - int(fields[COL["dealer_s"]]),
                    "asset_mgr_net": int(fields[COL["am_l"]]) - int(fields[COL["am_s"]]),
                    "lev_money_net": int(fields[COL["lev_l"]]) - int(fields[COL["lev_s"]]),
                }
            except (ValueError, IndexError) as exc:
                return {"status": "error", "error": f"parse: {exc!r}"}
            break

    if row is None:
        return {"status": "error", "error": "no VIX row in weekly TFF file"}

    alerts = _vix_alerts(row)
    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    dest = data_dir / day
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "cftc_cot.json").write_text(
        json.dumps({"vix": row, "alerts": alerts}, indent=2) + "\n")
    return {"status": "ok", "vix_report_date": row["report_date"],
            "vix_lev_money_net": row["lev_money_net"], "alerts": alerts,
            "saved": f"data/{day}/cftc_cot.json"}
