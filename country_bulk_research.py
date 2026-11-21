#!/usr/bin/env python3
"""Plan research for every pending country, not just drafted batches.

An inventory entry, search term or Commons metadata is NEVER editorial approval.
No canonical data, reader export or public photo is written.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError

from country_photo_candidates import draft_queries, fetch_commons, valid_candidate
from country_unesco_source_catalog import build_inventory, download_feed

ROOT = Path(__file__).resolve().parent
SHARDS = 8

def make_plan(root, inventory=None):
    root = Path(root)
    canonical = json.loads((root / "country-content.json").read_text(encoding="utf-8"))["countries"]
    catalog = json.loads((root / "country-catalog.json").read_text(encoding="utf-8"))
    index = {r["code"]: r for r in catalog}
    if len(index) != 196 or len(catalog) != 196 or set(index) != set(canonical):
        raise ValueError("Catalog/canonical country mismatch")
    if inventory is not None:
        expected = {c for c, row in canonical.items() if row["status"] == "pending"}
        if set(inventory["countries"]) != expected:
            raise ValueError("Inventory and canonical pending set differ")
    drafts = {}
    for row in draft_queries(root):
        drafts.setdefault(row["countryCode"], []).append(row)
    countries = []
    for code, entry in sorted(canonical.items()):
        if entry["status"] != "pending":
            continue
        country = index[code]
        english = next((a for a in country.get("aliases", []) if isinstance(a, str) and a.strip()), country["name"])
        # Prefer explicit longer aliases over an abbreviation, e.g. UAE.
        english = max((a for a in country.get("aliases", []) if isinstance(a, str) and a.strip()), key=len, default=english)
        source = (inventory or {}).get("countries", {}).get(code, {})
        official = source.get("sampleSourcePages", [])
        existing = drafts.get(code, [])
        slots = []
        for slot in range(3):
            role = "cover" if slot == 0 else "quizAndTravel"
            item = {"slot": slot, "role": role, "place": None, "searchQuery": None,
                    "officialSourceCandidate": None, "publicationEligible": False}
            if existing:
                if len(existing) != 3 or existing[slot]["role"] != role:
                    raise ValueError("Draft photo roles invalid: " + code)
                item.update(place=existing[slot]["place"], searchQuery=existing[slot]["searchQuery"],
                            origin="existing_draft")
            elif slot == 0:
                item.update(searchQuery=english + " landscape city architecture", origin="country_cover_research")
            elif len(official) >= slot:
                site = official[slot - 1]
                item.update(place=site["name"], searchQuery=site["name"] + " " + english,
                            officialSourceCandidate=site["sourceUrl"], origin="unesco_inventory_candidate")
            else:
                item["origin"] = "independent_source_required"
            slots.append(item)
        countries.append({"code": code, "country": entry["name"], "region": country["region"],
                          "portraitDraftExists": bool((entry.get("portrait") or {}).get("body")),
                          "officialInventoryAvailable": inventory is not None,
                          "officialSourceCandidates": official, "slots": slots,
                          "publicationEligible": False})
    for i, row in enumerate(countries):
        row["shard"] = i % SHARDS
    return {"version": 1, "catalogCount": len(canonical), "approvedCount": len(canonical)-len(countries),
            "pendingCount": len(countries), "slotCount": 3*len(countries), "shards": SHARDS,
            "officialInventoryAvailable": inventory is not None, "countries": countries,
            "rule": "Research only. Source evidence, visual identity, exact license and full editorial review required. No automatic approval."}

def research_shard(plan, shard, fetch=fetch_commons, sleep_seconds=1.0):
    if not 0 <= shard < plan["shards"]:
        raise ValueError("Invalid shard")
    rows = []
    throttled = False
    for country in plan["countries"]:
        if country["shard"] != shard:
            continue
        for slot in country["slots"]:
            row = dict(slot, countryCode=country["code"], country=country["country"],
                       candidates=[], manualVisualReviewRequired=True)
            query = slot["searchQuery"]
            if not query:
                row["status"] = "independent_source_required"
            elif throttled:
                row["status"] = "rate_limited_deferred"
            else:
                row["status"] = "no_matching_metadata"
                try:
                    seen = set()
                    for page in fetch(query):
                        candidate = valid_candidate(page)
                        if candidate and candidate["commonsPage"] not in seen:
                            row["candidates"].append(candidate)
                            seen.add(candidate["commonsPage"])
                            if len(seen) == 3:
                                break
                    if seen:
                        row["status"] = "metadata_candidates_only"
                except HTTPError as exc:
                    row["status"] = "search_failed"
                    row["httpStatus"] = exc.code
                    if exc.code in (429, 503):
                        throttled = True
                except (URLError, TimeoutError, ValueError, OSError) as exc:
                    row["status"] = "search_failed"
                    row["errorType"] = type(exc).__name__
                if sleep_seconds:
                    time.sleep(sleep_seconds)
            rows.append(row)
    return {"shard": shard, "results": rows, "statusCounts": dict(Counter(r["status"] for r in rows))}

def combine(plan, reports):
    expected = {(c["code"], s["slot"]) for c in plan["countries"] for s in c["slots"]}
    seen = {}
    for report in reports:
        for row in report["results"]:
            key = (row["countryCode"], row["slot"])
            if key in seen or key not in expected:
                raise ValueError("Duplicate or unknown research slot")
            seen[key] = row
    missing = sorted(expected - set(seen))
    return {"catalogCount": plan["catalogCount"], "approvedCount": plan["approvedCount"],
            "pendingCount": plan["pendingCount"], "plannedSlots": len(expected),
            "reportedSlots": len(seen), "missingSlots": missing,
            "statusCounts": dict(Counter(r["status"] for r in seen.values())),
            "results": [seen[key] for key in sorted(seen)],
            "publicationEligible": False}

def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("plan")
    a.add_argument("--output", required=True)
    b = sub.add_parser("research")
    b.add_argument("--plan", required=True)
    b.add_argument("--shard", required=True, type=int)
    b.add_argument("--output", required=True)
    c = sub.add_parser("combine")
    c.add_argument("--plan", required=True)
    c.add_argument("--input-dir", required=True)
    c.add_argument("--output", required=True)
    args = p.parse_args()
    if args.command == "plan":
        try:
            inventory = build_inventory(ROOT, download_feed())
        except (URLError, TimeoutError, ValueError, OSError) as exc:
            print("Official feed unavailable: " + type(exc).__name__)
            inventory = None
        plan = make_plan(ROOT, inventory)
        save(args.output, plan)
        print("Planned", plan["pendingCount"], "pending countries;", plan["slotCount"], "slots; no approvals.")
    elif args.command == "research":
        report = research_shard(read(args.plan), args.shard)
        save(args.output, report)
        print(report["statusCounts"])
    else:
        plan = read(args.plan)
        report = combine(plan, [read(p) for p in sorted(Path(args.input_dir).rglob("shard-*.json"))])
        save(args.output, report)
        import os
        summary = ("### All-country research (not published)\n\n"
                   + f"- Pending countries: {report['pendingCount']}\n"
                   + f"- Reported slots: {report['reportedSlots']}/{report['plannedSlots']}\n"
                   + f"- Status: {report['statusCounts']}\n"
                   + f"- Unreported slots: {len(report['missingSlots'])}\n"
                   + "- No new country or photograph approved.\n")
        print(summary)
        if os.getenv("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
                stream.write(summary)
        if report["missingSlots"]:
            raise SystemExit("Some research shards did not report")

if __name__ == "__main__":
    main()
