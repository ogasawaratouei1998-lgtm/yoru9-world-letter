#!/usr/bin/env python3
"""Daily audit of verified cultural highlights for countries in the published issue.

Never generates or publishes editorial claims. Only reports imminent coverage
gaps so a human/verified editorial step can replenish source-backed topics.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

from build_site import validate_country_highlights
from country_codes import country_codes

JST = timezone(timedelta(hours=9))


def missing_topic_dates(registry, code, today: date, horizon: int = 7):
    """Use the edition day, verified publication windows and 30-day freshness."""
    if not 1 <= horizon <= 31:
        raise ValueError("invalid audit horizon")
    rows=registry.get(code,[])
    return [(today+timedelta(days=offset)).isoformat()
            for offset in range(horizon)
            if not any(entry["checkedOn"] <= today.isoformat()
                       and entry["validFrom"] <= (today+timedelta(days=offset)).isoformat() <= entry["validThrough"]
                       and (today-date.fromisoformat(entry["checkedOn"])).days <= 30
                       for entry in rows)]


def require_country_topics(root: Path, stories, day):
    """Enforce the same two-day urgent coverage rule as the live-topic audit.
    Seven-day coverage remains visible as advance replenishment work.
    """
    today=date.fromisoformat(day) if isinstance(day,str) else day
    registry=validate_country_highlights(root)["highlights"]
    codes=set()
    for story in stories:
        found=country_codes(story.get("country",""))
        if not found:raise ValueError("Unrecognized country for topic coverage")
        codes.update(found)
    missing={code:missing_topic_dates(registry,code,today,2) for code in sorted(codes)}
    missing={code:days for code,days in missing.items() if days}
    if missing:
        raise ValueError("Missing verified country topics: "+json.dumps(missing,sort_keys=True))
    return True


def audit(root: Path, today: date, horizon: int = 7, urgent_days: int = 2) -> dict:
    if not 1 <= horizon <= 31 or not 1 <= urgent_days <= horizon:
        raise ValueError("invalid audit horizon")
    registry = validate_country_highlights(root)["highlights"]
    current = json.loads((root / "data/current.json").read_text(encoding="utf-8"))
    release_date = str(current.get("editionDate") or "")
    release = date.fromisoformat(release_date) if current.get("status") == "published" else None
    # Ignore old cached issues: no need to alert over a stale front page.
    recent = bool(release and timedelta(0) <= today - release <= timedelta(days=3))
    countries, unknown = set(), []
    if recent:
        for story in current.get("stories", []):
            codes = country_codes(story.get("country"))
            if not codes:
                unknown.append(str(story.get("country") or "国名不明"))
            countries.update(codes)

    coverage, urgent, upcoming = [], [], []
    for code in sorted(countries):
        rows = registry.get(code, [])
        missing = missing_topic_dates(registry,code,today,horizon)
        item = {"country": code, "missingDates": missing, "reviewedTopicCount": len(rows)}
        coverage.append(item)
        if missing:
            last_urgent = (today + timedelta(days=urgent_days - 1)).isoformat()
            (urgent if any(day <= last_urgent for day in missing) else upcoming).append(item)

    return {
        "asOfJST": today.isoformat(), "editionDate": release_date if release else None,
        "editionIsRecent": recent, "countriesChecked": sorted(countries),
        "unknownCountryLabels": sorted(set(unknown)), "horizonDays": horizon,
        "urgentDays": urgent_days, "coverage": coverage, "urgent": urgent,
        "upcoming": upcoming, "needsEditorialReview": bool(urgent),
        "policy": "Never publish unverified or expired cultural news automatically."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--today", type=date.fromisoformat, default=datetime.now(JST).date())
    parser.add_argument("--horizon", type=int, default=7)
    parser.add_argument("--urgent-days", type=int, default=2)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = audit(args.root, args.today, args.horizon, args.urgent_days)
    result = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    print(result)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(result, encoding="utf-8")
    # This audit reports independent enrichment gaps; it never gates news release.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
