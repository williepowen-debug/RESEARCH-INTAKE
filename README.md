# Research-Intake

**Automated data-collection lane for the research operation.**
Scheduled collectors write here; research agents read it **read-only**.

## The contract

- **Collectors** (GitHub Actions in this repo) fetch calendar-anchored data releases,
  organize them under `data/`, and update `liveness.json` every run.
- **Research agents** (over in the `Research-workspace` repo) **only ever read** this
  repo — they pull it and consume `data/` + `liveness.json`. They never write here.
- This repo's git history is **completely separate** from `Research-workspace`. By
  construction, nothing here can diverge from or interfere with the working branch.
  That isolation is the entire point of keeping it a separate repo.

## Layout

```
data/                       # collected releases, namespaced by date
  2026-06-29/
    eia_petroleum.json      # raw payload
liveness.json               # health pulse — overwritten every run (see below)
scripts/
  collect.py                # entry point: writes liveness, runs enabled fetchers
  fetch_eia_petroleum.py    # EIA Weekly Petroleum (needs EIA_API_KEY; skips without it)
  requirements.txt
.github/workflows/
  collect.yml               # schedule + manual trigger
```

## liveness.json — the silent-death guard

Every collector run overwrites `liveness.json` with a timestamp and per-job status.
Consumers read it and flag if it's older than expected ("collector stale Nd"). This is
the guard against the failure mode where a feed dies quietly and nobody notices for
weeks (which is exactly what happened to the old news-sweep cron).

```json
{
  "last_run_utc": "2026-06-29T15:00:02Z",
  "status": "ok",
  "jobs": {"eia_petroleum": {"status": "skipped", "reason": "no EIA_API_KEY"}},
  "errors": []
}
```

## Secrets

Set under **Settings → Secrets and variables → Actions** (never committed):

- `EIA_API_KEY` — free from <https://www.eia.gov/opendata/register.php>

Collectors **skip gracefully** when a required key is absent, so the lane never breaks
waiting on configuration.

## Running it

- **Manual:** Actions tab → **collect** → **Run workflow**.
- **Scheduled:** see the `cron` in `.github/workflows/collect.yml` (UTC; no DST — retune seasonally).
