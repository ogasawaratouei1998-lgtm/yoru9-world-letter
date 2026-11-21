#!/usr/bin/env python3
"""Actionable, read-only country editorial queue; never changes approvals.

A location in the 196-location map index is NOT automatically eligible for
publication. This report identifies missing source, photograph, trip and quiz
work without ever manufacturing substitute photographs or article locations.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from country_content import load_country_content


def country_editorial_queue(root: Path) -> dict:
    dataset=load_country_content(root)
    names={code:record["name"] for code,record in dataset["countries"].items()}
    result=[]
    approved=[]
    for code,entry in dataset["countries"].items():
        if entry["status"]=="approved":
            approved.append(code)
            continue
        missing=[]
        portrait=entry.get("portrait") or {}
        if not portrait.get("body") or len(portrait.get("body",""))<145:
            missing.append("substantive_portrait")
        if not portrait.get("sourceName") or not portrait.get("sourceUrl"):
            missing.append("portrait_history_culture_source")
        # Cover attribution lives in the postcard manifest for legacy photos.
        # Never call it uncredited just because the optional cover-level
        # sourcePage field was not duplicated in index.html.
        stops=entry.get("travelStops",{})
        local_covers=[]
        for cover in entry.get("portraitPhotos",[]):
            if cover.get("avoidCover") or cover.get("remoteOnly"):
                continue
            if not cover.get("asset") or not cover.get("author") or not cover.get("license"):
                continue
            licensed=next((stop for stop in stops.values()
                if stop.get("country")==entry["name"]
                and stop.get("photoAsset")==cover["asset"]
                and stop.get("author")==cover["author"]
                and stop.get("license")==cover["license"]
                and stop.get("photoPage","").startswith(
                    "https://commons.wikimedia.org/wiki/File:")
                and (not cover.get("sourcePage")
                     or cover["sourcePage"]==stop["photoPage"])),None)
            if licensed:
                local_covers.append(cover)
        if not local_covers:
            missing.append("attributed_country_portrait_photo")
        quizzes=entry.get("quiz",[])
        photo_keys=[q.get("photoKey") for q in quizzes if q.get("photoKey")]
        quiz_photos=[stops.get(key) for key in photo_keys]
        if (len(quizzes)<2 or len(set(photo_keys))<2
                or not all(q and q.get("country")==entry["name"]
                           and q.get("photoPage","").startswith(
                               "https://commons.wikimedia.org/wiki/File:")
                           and q.get("licenseUrl","").startswith(
                               "https://creativecommons.org/")
                           for q in quiz_photos)):
            missing.append("two_distinct_licensed_photo_quizzes")
        if (local_covers and any(
                q and q.get("photoAsset")==cover["asset"]
                for q in quiz_photos for cover in local_covers)):
            # Every possible fallback portrait must differ from quiz reveals.
            missing.append("portrait_photo_reused_in_quiz")
        postcards=[s for s in entry.get("travelStops",{}).values()
                   if not s.get("quizOnly") and not s.get("coverOnly")
                   and isinstance(s.get("travelStory"),list)
                   and len(s["travelStory"])==2]
        if not postcards:
            missing.append("two_paragraph_microtravel")
        if not any(s.get("historicalSources") for s in postcards):
            missing.append("independent_travel_history_culture_source")
        if not entry.get("highlights"):
            # Fresh country topics are an optional enhancement; their absence
            # must not be substituted with fabricated events.
            missing.append("optional_current_topic")
        # Queue ranking is an editorial hint only and does NOT confer approval.
        result.append({"code":code,"name":names[code],"missing":missing,
                       "requiredRemaining":sum(not x.startswith("optional_")
                                               for x in missing)})
    result.sort(key=lambda r:(r["requiredRemaining"],len(r["missing"]),r["code"]))
    return {
        "reportingLocations":len(dataset["countries"]),
        "approvedCountries":sorted(approved),
        "pendingCountries":len(result),
        "nearReadyPending":[row for row in result if row["requiredRemaining"]<=2],
        "prioritizedPending":result,
        "missingRequirements":dict(sorted(Counter(
            missing for row in result for missing in row["missing"]).items())),
        "rule":"No pending country is publishable without separate editorial approval and a release readiness check."
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument("--top",type=int,default=12)
    args=parser.parse_args()
    if not 1<=args.top<=196:
        parser.error("--top must be between 1 and 196")
    report=country_editorial_queue(args.root)
    print(json.dumps({
        key:value for key,value in report.items() if key!="prioritizedPending"
    }|{"nextToPrepare":report["prioritizedPending"][:args.top]},
    ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
