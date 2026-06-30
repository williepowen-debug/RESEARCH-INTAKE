#!/usr/bin/env python3
"""Research-Intake collector entry point.

Writes liveness.json every run and invokes each enabled fetcher. Fetchers skip
gracefully when their required secret/key is absent, and a failing fetcher is
recorded as an error WITHOUT aborting the run — so the lane stays alive and the
failure is visible in liveness.json rather than dying silently.
"""
import datetime
import json
import pathlib
import traceback

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LIVENESS = ROOT / "liveness.json"


def utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# (job name, module name) — each module exposes fetch(data_dir) -> status dict.
# Add a new feed by writing fetch_<x>.py with a fetch() and listing it here.
FETCHERS = [
    ("eia_petroleum",     "fetch_eia_petroleum"),
    ("edgar_8k",          "fetch_edgar_8k"),
    ("treasury_auctions", "fetch_treasury_auctions"),
    ("cftc_cot",          "fetch_cftc_cot"),
    ("fred",              "fetch_fred"),
    ("newsweep",          "fetch_newsweep"),
]


ATTEMPTS = 2      # one retry on failure
BACKOFF_S = 3     # brief wait before the retry


def run_fetchers() -> dict:
    """Run each enabled fetcher, capturing per-job status. Never raises — a
    failing fetcher is recorded as an error WITHOUT aborting the run, so the
    lane stays alive and the failure is visible in liveness.json.

    Each feed gets one retry (after a short backoff) on failure — whether it
    raised or returned status="error" — so a transient network blip (e.g. a
    dropped connection) is absorbed instead of surfacing as `degraded`. A feed
    that recovers is flagged `recovered_after_retry`; one that fails both
    attempts stays an error (a real problem worth seeing)."""
    import importlib
    import time
    jobs = {}
    for name, module in FETCHERS:
        result = {"status": "error", "error": "not run"}
        for attempt in range(ATTEMPTS):
            try:
                mod = importlib.import_module(module)
                result = mod.fetch(DATA)
            except Exception as exc:  # fail-loud per job, never abort the whole run
                result = {
                    "status": "error",
                    "error": repr(exc),
                    "trace": traceback.format_exc(limit=3),
                }
            if result.get("status") != "error":
                if attempt > 0:
                    result["recovered_after_retry"] = True
                break
            if attempt < ATTEMPTS - 1:
                time.sleep(BACKOFF_S)
        jobs[name] = result
    return jobs


def render_summary(liveness: dict) -> str:
    """Render a glanceable human digest (SUMMARY.md) from the run summary."""
    j = liveness.get("jobs", {})
    L = ["# Research-Intake — latest run", "",
         f"**{liveness.get('last_run_utc')}** · overall: **{liveness.get('status')}**",
         "", "## Highlights", ""]

    eia = j.get("eia_petroleum", {})
    if eia.get("status") == "ok" and eia.get("metrics"):
        m = eia["metrics"]
        al = eia.get("alerts", [])
        L.append(f"- **EIA** Cushing {m.get('cushing_mbbl')}M · crude {m.get('commercial_crude_mbbl')}M "
                 f"· gasoline {m.get('gasoline_mbbl')}M"
                 + (f" · ⚠ {'; '.join(al)}" if al else "  *(WoW in data file)*"))

    fred = j.get("fred", {})
    if fred.get("status") in ("ok", "degraded"):
        al = fred.get("alerts", [])
        L.append(f"- **FRED** {fred.get('series_count', '?')} series · "
                 + ("⚠ " + "; ".join(al) if al else "no threshold flags"))

    nw = j.get("newsweep", {})
    if nw.get("status") == "ok":
        L.append(f"- **News** {nw.get('new', nw.get('total', '?'))} new "
                 f"(skipped {nw.get('skipped_already_seen', 0)} already-seen) "
                 f"· {len(nw.get('alerts', []))} alerts")
        for a in nw.get("alerts", [])[:8]:
            L.append(f"    - {a}")

    cf = j.get("cftc_cot", {})
    if cf.get("status") == "ok":
        al = cf.get("alerts", [])
        L.append(f"- **CFTC VIX** lev-money net {cf.get('vix_lev_money_net')} ({cf.get('vix_report_date')})"
                 + (f" · ⚠ {'; '.join(al)}" if al else ""))

    tr = j.get("treasury_auctions", {})
    if tr.get("status") == "ok":
        weak = tr.get("weak", [])
        L.append(f"- **Treasury** {tr.get('count')} auctions"
                 + (f" · ⚠ {len(weak)} weak: {weak}" if weak else " · none weak"))

    eg = j.get("edgar_8k", {})
    if eg.get("status") == "ok":
        crit = eg.get("critical", [])
        L.append(f"- **EDGAR 8-K** {eg.get('count')} filings (thesis banks)"
                 + (f" · ⚠ {len(crit)} critical: {crit}" if crit else ""))

    L += ["", "## Feed status", "", "| feed | status |", "|---|---|"]
    for k, v in j.items():
        L.append(f"| {k} | {v.get('status')} |")
    L += ["", "_Machine detail: `liveness.json` + `data/<UTC-date>/*.json`._", ""]
    return "\n".join(L)


def main() -> None:
    DATA.mkdir(exist_ok=True)
    jobs = run_fetchers()
    errors = [name for name, r in jobs.items() if r.get("status") == "error"]
    liveness = {
        "last_run_utc": utcnow(),
        "status": "ok" if not errors else "degraded",
        "jobs": jobs,
        "errors": errors,
    }
    LIVENESS.write_text(json.dumps(liveness, indent=2) + "\n")
    (ROOT / "SUMMARY.md").write_text(render_summary(liveness))
    print(json.dumps(liveness, indent=2))


if __name__ == "__main__":
    main()
