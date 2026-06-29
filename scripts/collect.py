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
]


def run_fetchers() -> dict:
    """Run each enabled fetcher, capturing per-job status. Never raises — a
    failing fetcher is recorded as an error WITHOUT aborting the run, so the
    lane stays alive and the failure is visible in liveness.json."""
    import importlib
    jobs = {}
    for name, module in FETCHERS:
        try:
            mod = importlib.import_module(module)
            jobs[name] = mod.fetch(DATA)
        except Exception as exc:  # fail-loud per job, never abort the whole run
            jobs[name] = {
                "status": "error",
                "error": repr(exc),
                "trace": traceback.format_exc(limit=3),
            }
    return jobs


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
    print(json.dumps(liveness, indent=2))


if __name__ == "__main__":
    main()
