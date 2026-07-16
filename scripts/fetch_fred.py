#!/usr/bin/env python3
"""FRED economic series — labor, consumer health, inflation, rates.

Standalone port of the verified series set in AGENTS/CARL/scripts/consumer_pulse.py.
Pulls latest + prior + YoY for each series with a threshold-based status.
Reads FRED_API_KEY from env (set as a GH Actions secret); skips gracefully if absent.

NOTE (superseded 2026-07-01, Will-approved): HY OAS (BAMLH0A0HYM2) was originally
EXCLUDED in deference to the `liquid-hy-watch` systemd timer in the working repo.
That timer is machine-local (desktop-only; dark whenever that box is off — and
WSL2 doesn't keep user timers running without an open instance), so THIS lane is
now the machine-independent PRIMARY for the HY>280 / <260 watch; the desktop
timer is redundancy. Canonical trigger definitions:
AGENTS/LIQUID/workbook/KILL_MEMO_HY_OAS_260.md (+ KB-LIQ-062) in the working repo.
"""
import datetime
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# (series_id, label, direction_bad, thresholds|None) — series + thresholds
# verified in consumer_pulse.py; rates (DGS*/T10Y2Y) are standard FRED IDs.
SERIES = [
    ("ICSA",         "Initial jobless claims",    "rising",  (200000, 250000, 300000, 350000)),
    ("CCSA",         "Continuing claims",         "rising",  (1700000, 1900000, 2000000, 2200000)),
    ("UMCSENT",      "UMich sentiment",           "falling", (80, 65, 55, 45)),
    ("PSAVERT",      "Personal savings rate %",   "falling", (6, 4, 3, 2)),
    ("DRCCLACBS",    "Credit-card delinquency %", "rising",  (3, 4, 5, 6)),
    ("DRCLACBS",     "Consumer-loan delinq %",    "rising",  (2, 3, 4, 5)),
    ("PCEPILFE",     "Core PCE index",            "rising",  None),
    ("CPIUFDNS",     "CPI food index",            "rising",  None),
    ("CPIENGNS",     "CPI energy index",          "rising",  None),
    ("RSXFS",        "Retail sales ex food",      "falling", None),
    ("TOTALNS",      "Total consumer credit",     "rising",  None),
    ("MORTGAGE30US", "30yr mortgage rate %",      "rising",  (5.5, 6.0, 6.5, 7.0)),
    ("DGS10",        "10Y Treasury yield",        "rising",  None),
    ("DGS2",         "2Y Treasury yield",         "rising",  None),
    ("T10Y2Y",       "10Y-2Y spread",             "falling", None),
    ("BAMLH0A0HYM2", "HY OAS bps",                "rising",  (240, 260, 270, 280)),
]


# --- HY OAS canonical trigger lines (PROME 2026-07-01, Will-approved) ----------
def _hy_trigger_alerts(val, obs):
    """Named trigger lines beyond the generic status bands, so a breach reads as
    the decision it is, not just a color. >=280 = X1 credit-recognition trigger,
    LIQUID's half (BROCK's half = wrapper basket leading managers down; BOTH must
    fire; sustain judgment stays with LIQUID). <260 on two consecutive closes =
    credit-bear re-kill line (KILL_MEMO_HY_OAS_260)."""
    out = []
    if val >= 280:
        out.append(
            f"BAMLH0A0HYM2 HY OAS={val:.0f}bps [red] >=280 X1-trigger breach "
            "(LIQUID half of X1; sustain-check owner LIQUID; BROCK wrapper-half must also fire)")
    prior = None
    if len(obs) > 1:
        try:
            prior = float(obs[1]["value"])
        except ValueError:
            prior = None
    if val < 260 and prior is not None and prior < 260:
        out.append(
            f"BAMLH0A0HYM2 HY OAS={val:.0f}bps (prior {prior:.0f}) [orange] "
            "<260 two consecutive closes = credit-bear re-kill line (KILL_MEMO_HY_OAS_260)")
    return out


# Transient upstream conditions worth a retry. 4xx (bad key / unknown series) is
# PERMANENT — retrying it wastes the run and risks rate-limiting, so it fails fast.
_RETRY_HTTP = {429, 500, 502, 503, 504}
_RETRY_BACKOFF = (2, 5)  # seconds between attempts 1→2 and 2→3


def _fred(series_id, key, limit=15):
    """Pull a FRED series, retrying transient upstream failures.

    Added 2026-07-16 after the 2026-07-15 run lost ICSA/CCSA/RSXFS/MORTGAGE30US to
    read-timeouts + a 504 while the other 12 series succeeded — i.e. FRED had a slow
    spell, not a broken key/series. With a single 20s attempt and no retry, one slow
    response silently drops a series for the whole day. ICSA feeds two registered
    fleet triggers (RED-FT-05 >250k, REG-T-05 >300k), so a silent one-day hole in it
    is the real exposure. History: 13 consecutive clean runs before 7/15 → the
    failure is transient and retry-shaped, not structural.
    """
    params = {"series_id": series_id, "api_key": key, "file_type": "json",
              "sort_order": "desc", "limit": limit}
    url = f"{FRED_BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Research-Intake/fred"})
    attempts = len(_RETRY_BACKOFF) + 1
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code not in _RETRY_HTTP or attempt == attempts - 1:
                raise  # permanent (4xx) or out of attempts → caller records it as today
            time.sleep(_RETRY_BACKOFF[attempt])
        except (TimeoutError, urllib.error.URLError, json.JSONDecodeError):
            if attempt == attempts - 1:
                raise
            time.sleep(_RETRY_BACKOFF[attempt])
    return [{"date": o["date"], "value": o["value"]}
            for o in data.get("observations", []) if o["value"] != "."]


def _yoy_pct(obs, latest_val):
    """YoY % vs the observation closest to one year before the latest."""
    if len(obs) < 2:
        return None
    try:
        latest_dt = datetime.datetime.strptime(obs[0]["date"], "%Y-%m-%d")
        target = latest_dt.replace(year=latest_dt.year - 1)
    except ValueError:
        return None
    best, best_diff = None, 10 ** 9
    for o in obs[1:]:
        try:
            dt = datetime.datetime.strptime(o["date"], "%Y-%m-%d")
        except ValueError:
            continue
        diff = abs((dt - target).days)
        if diff < best_diff:
            best_diff, best = diff, o
    if best and best_diff < 45:
        try:
            yv = float(best["value"])
            return round((latest_val - yv) / yv * 100, 2) if yv else None
        except ValueError:
            return None
    return None


def _status(value, thresholds, direction_bad):
    if thresholds is None:
        return "track"
    g, y, o, r = thresholds
    if direction_bad == "rising":
        return "red" if value >= r else "orange" if value >= o else "yellow" if value >= y else "green"
    return "red" if value <= r else "orange" if value <= o else "yellow" if value <= y else "green"


def fetch(data_dir: pathlib.Path) -> dict:
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        return {"status": "skipped", "reason": "no FRED_API_KEY"}

    out, alerts, errors = {}, [], []
    for sid, label, dirbad, thr in SERIES:
        try:
            obs = _fred(sid, key)
            if sid == "BAMLH0A0HYM2":
                # FRED serves this series in PERCENT (2.75 = 275bps); the fleet
                # speaks bps — convert the whole series once so value/prior/
                # change/alerts stay unit-consistent (thresholds above are bps).
                obs = [{**o, "value": str(float(o["value"]) * 100)} for o in obs]
            if not obs:
                out[sid] = {"label": label, "error": "no observations"}
                errors.append(sid)
                continue
            val = float(obs[0]["value"])
            prior = float(obs[1]["value"]) if len(obs) > 1 else None
            st = _status(val, thr, dirbad)
            out[sid] = {
                "label": label, "value": val, "date": obs[0]["date"],
                "change": round(val - prior, 4) if prior is not None else None,
                "yoy_pct": _yoy_pct(obs, val), "status": st,
            }
            if st in ("orange", "red"):
                alerts.append(f"{sid} {label}={val} [{st}]")
            if sid == "BAMLH0A0HYM2":
                alerts.extend(_hy_trigger_alerts(val, obs))
        except Exception as exc:
            out[sid] = {"label": label, "error": repr(exc)}
            errors.append(sid)

    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    dest = data_dir / day
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "fred.json").write_text(json.dumps({"series": out}, indent=2) + "\n")
    return {"status": "ok" if not errors else "degraded",
            "series_count": len(SERIES), "errored": errors,
            "alerts": alerts, "saved": f"data/{day}/fred.json"}
