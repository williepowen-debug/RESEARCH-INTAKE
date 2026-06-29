#!/usr/bin/env python3
"""News sweep — thesis-tagged headlines from Google News RSS + direct RSS.

Revival of FORGE/tools/news-sweep (its cron died with the VPS). Lane-appropriate
scope: FETCH + CLASSIFY only. The original also ROUTED headlines to agent inboxes
— that's a consumer concern (and tied to the file-messaging system being
replaced), so it's intentionally dropped here. Agents read data/<date>/news.json
and route on their side.

Cross-run dedup: a persistent `news_seen.json` at the repo root records headlines
already reported (title key -> last-seen UTC date). Items seen within DEDUP_DAYS
are skipped, so news.json holds only what's NEW since the last run rather than the
same list every day. Entries older than DEDUP_DAYS are pruned, so a story can
re-surface if it returns after a gap.

Classification logic + sources are ported verbatim in newsweep_config.py. Public
sources, no key. The config's WEB_SCRAPE and dead WORKSPACE path are inert here.
"""
import datetime
import json
import pathlib
import time
import urllib.request
import xml.etree.ElementTree as ET

import newsweep_config as cfg

UA = {"User-Agent": "Mozilla/5.0 Research-Intake/newsweep"}
DEDUP_DAYS = 5  # re-surface a headline only if unseen for this many days


def _get(url, timeout=10):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _parse_rss(raw):
    """Return [{title, link, source, date}] from RSS 2.0 XML bytes."""
    items = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return items
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        if not title:
            continue
        src_el = it.find("source")
        items.append({
            "title": title,
            "link": (it.findtext("link") or "").strip(),
            "date": (it.findtext("pubDate") or "").strip(),
            "source": (src_el.text.strip() if src_el is not None and src_el.text else ""),
        })
    return items


def _load_seen(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _age_days(today_iso, then_iso):
    try:
        return (datetime.date.fromisoformat(today_iso)
                - datetime.date.fromisoformat(then_iso)).days
    except Exception:
        return 999


def fetch(data_dir: pathlib.Path) -> dict:
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    seen_path = data_dir.parent / "news_seen.json"
    seen = _load_seen(seen_path)
    seen = {k: v for k, v in seen.items() if _age_days(today, v) <= DEDUP_DAYS}  # prune

    within_run = set()
    collected = []
    skipped_seen = 0

    def add(items, default_agents, label, fallback_source=""):
        nonlocal skipped_seen
        for it in items[:cfg.MAX_ARTICLES_PER_SOURCE]:
            key = it["title"].lower()[:120]
            if key in within_run:
                continue
            within_run.add(key)
            if key in seen:            # already reported in a recent run
                seen[key] = today       # refresh recency, don't re-report
                skipped_seen += 1
                continue
            c = cfg.classify_article(it["title"])
            if c["suppressed"]:         # NOISE / KNOWN-no-escalation (not tracked)
                continue
            seen[key] = today           # mark newly reported
            agents = list(default_agents)
            if c["entity_info"]:
                agents += [a for a in c["entity_info"].get("agents", []) if a not in agents]
            collected.append({
                "title": it["title"],
                "source": it["source"] or fallback_source,
                "link": it["link"], "date": it["date"],
                "classification": c["classification"], "level": c["level"],
                "keyword": c["keyword"], "entity": c["entity"],
                "watch_hits": c["watch_hits"], "agents": agents, "label": label,
            })

    try:
        for q in cfg.GOOGLE_NEWS_QUERIES:
            try:
                raw = _get(cfg.google_news_rss_url(q["query"]), cfg.REQUEST_TIMEOUT)
                add(_parse_rss(raw), q.get("agents", []), q.get("label", ""))
            except Exception:
                pass
            time.sleep(cfg.GOOGLE_NEWS_DELAY)
        for feed in cfg.RSS_FEEDS:
            try:
                raw = _get(feed["url"], cfg.REQUEST_TIMEOUT)
                add(_parse_rss(raw), [], feed.get("name", ""), fallback_source=feed.get("name", ""))
            except Exception:
                pass
    except Exception as exc:
        return {"status": "error", "error": repr(exc)}

    seen_path.write_text(json.dumps(seen, indent=0, sort_keys=True) + "\n")  # persist

    by_class = {}
    for c in collected:
        by_class[c["classification"]] = by_class.get(c["classification"], 0) + 1
    alerts = [f"{c['title'][:80]} [{c['classification']}]" for c in collected
              if c["classification"] in ("NEW_ALERT", "NEW_WATCH_HIT", "DEVELOPMENT")]

    day = today
    dest = data_dir / day
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "news.json").write_text(
        json.dumps({"by_class": by_class, "items": collected}, indent=2) + "\n")
    return {"status": "ok", "new": len(collected), "skipped_already_seen": skipped_seen,
            "by_class": by_class, "alerts": alerts[:15], "saved": f"data/{day}/news.json"}
