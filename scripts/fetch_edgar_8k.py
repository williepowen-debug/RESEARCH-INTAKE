#!/usr/bin/env python3
"""EDGAR 8-K monitor — recent 8-K filings from thesis banks.

Standalone port of AGENTS/REGINALD/scripts/8k_monitor.py. Public SEC EDGAR (no
key) — EDGAR requires a real User-Agent contact. Snapshots 8-Ks from the last
DAYS days with item-level severity; dedup/alerting is left to consumers.
"""
import datetime
import json
import pathlib
import re
import time
import urllib.request

TARGETS = {
    "WAL":  {"cik": "1212545", "name": "Western Alliance Bancorporation"},
    "OZK":  {"cik": "1569650", "name": "Bank OZK"},
    "EGBN": {"cik": "1050441", "name": "Eagle Bancorp Inc"},
    "ZION": {"cik": "109380",  "name": "Zions Bancorporation"},
    "VLY":  {"cik": "74260",   "name": "Valley National Bancorp"},
    # VULCAN domain (added 2026-07-16, WALTER coverage-gap note — the lane's
    # TARGETS were all regional banks; MU is the memory-cycle input-cost primary)
    "MU":   {"cik": "723125",  "name": "Micron Technology Inc"},
    # VULCAN S1 core names (added 2026-07-16 eve, WALTER hyperscaler ask, Will-
    # approved; all 4 CIKs live-verified vs data.sec.gov). SCOPE: this fetcher is
    # 8-K/item-code ONLY — these rows are an EARNINGS-EVENT TRIPWIRE (item 2.02
    # during the 7/22-7/31 Q2 cluster), NOT the useful-life datum: that lives in
    # 10-Q PP&E footnotes this fetcher cannot read. The footnote read is tasked
    # to VULCAN per filing (PROME DOCKET row 7/22-7/31); do not over-read these.
    "MSFT": {"cik": "789019",  "name": "Microsoft Corporation"},
    "GOOGL": {"cik": "1652044", "name": "Alphabet Inc"},
    "AMZN": {"cik": "1018724", "name": "Amazon.com Inc"},
    "META": {"cik": "1326801", "name": "Meta Platforms Inc"},
}

# 8-K item -> severity. red = material/credit-relevant, orange = notable.
ITEM_FLAGS = {
    "1.01": "red", "1.02": "red", "1.03": "orange", "2.01": "orange",
    "2.02": "red", "2.03": "orange", "2.04": "red", "2.05": "red",
    "2.06": "red", "3.01": "orange", "4.01": "orange", "4.02": "red",
    "5.01": "orange", "5.02": "red", "5.03": "orange",
}

DAYS = 7
HEADERS = {"User-Agent": "Research-Intake research williepowen@gmail.com"}


def _get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def _recent_8ks(cik):
    url = (f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"
           f"&type=8-K&dateb=&owner=exclude&count=20&output=atom")
    try:
        text = _get(url)
    except Exception:
        return []
    cutoff = (datetime.date.today() - datetime.timedelta(days=DAYS)).isoformat()
    out = []
    for entry in re.findall(r"<entry>(.*?)</entry>", text, re.DOTALL):
        d = re.search(r"<filing-date>([^<]+)</filing-date>", entry)
        h = re.search(r"<filing-href>([^<]+)</filing-href>", entry)
        if d and d.group(1) >= cutoff:
            out.append({"date": d.group(1), "index_url": h.group(1) if h else ""})
    return out


def _items(index_url):
    try:
        text = _get(index_url)
    except Exception:
        return []
    seen = []
    for m in re.findall(r"Item\s+(\d+\.\d+)", text, re.IGNORECASE):
        if m not in seen:
            seen.append(m)
    return seen


def fetch(data_dir: pathlib.Path) -> dict:
    filings, critical = [], []
    try:
        for tkr, info in TARGETS.items():
            for f in _recent_8ks(info["cik"]):
                items = _items(f["index_url"]) if f["index_url"] else []
                time.sleep(0.15)  # EDGAR rate limit (<10 req/s)
                sev = "gray"
                for it in items:
                    flag = ITEM_FLAGS.get(it, "gray")
                    if flag == "red":
                        sev = "red"
                    elif flag == "orange" and sev != "red":
                        sev = "orange"
                rec = {"ticker": tkr, "date": f["date"], "items": items,
                       "severity": sev, "url": f["index_url"]}
                filings.append(rec)
                if sev in ("red", "orange"):
                    critical.append(rec)
    except Exception as exc:
        return {"status": "error", "error": repr(exc)}

    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    dest = data_dir / day
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "edgar_8k.json").write_text(
        json.dumps({"window_days": DAYS, "filings": filings}, indent=2) + "\n")
    return {"status": "ok", "count": len(filings),
            "critical": [f"{r['ticker']} {r['date']} {r['items']}" for r in critical],
            "saved": f"data/{day}/edgar_8k.json"}
