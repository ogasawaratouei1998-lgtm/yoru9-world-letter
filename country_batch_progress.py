#!/usr/bin/env python3
"""Read-only progress view for delegated, quality-gated country expansion.

User editorial authorization does not substitute for source, correct-country
photo and CC license requirements. This report never marks a country approved.
"""
import json
import os
from pathlib import Path
from country_content import load_country_content
from country_editorial_queue import country_editorial_queue

def expansion_progress(root):
    root=Path(root)
    doc=load_country_content(root)
    queue=country_editorial_queue(root)
    pending=queue["prioritizedPending"]
    with_portrait=[c["code"] for c in pending if
                   doc["countries"][c["code"]].get("portrait") and
                   len(doc["countries"][c["code"]]["portrait"].get("body",""))>=145]
    with_portrait.sort()
    # First drafts are deliberately outside canonical release data. Report them
    # separately rather than treating an unverified draft as a reviewed portrait.
    first_drafts = {}
    for path in sorted(root.glob("country-expansion-batch-*.json")):
        batch = json.loads(path.read_text(encoding="utf-8"))
        for code, row in batch.get("countries", {}).items():
            if (code in doc["countries"] and doc["countries"][code]["status"] == "pending"
                    and code not in with_portrait
                    and (row.get("portrait") or {}).get("sourceReviewStatus") == "independent_claim_review_required"):
                first_drafts[code] = row
    draft_stops = [stop for row in first_drafts.values() for stop in row.get("travelDrafts", [])]
    return {
        "firstDraftsAwaitingSourceReview":sorted(first_drafts),
        "firstDraftTravelStops":len(draft_stops),
        "firstDraftReferencePagesLocated":sum(bool(stop.get("sourceUrl")) for stop in draft_stops),
        "catalogCount":len(doc["countries"]),
        "approvedCount":len(queue["approvedCountries"]),
        "pendingCount":len(pending),
        "pendingPortraitsPrepared":with_portrait,
        "photoReady":sorted(queue["approvedCountries"]),
        "pendingCountriesBlocked":{row["code"]:row["missing"] for row in pending
                                   if row["code"] in with_portrait},
    }

def main():
    root=Path(__file__).resolve().parent
    progress=expansion_progress(root)
    summary=(f"### Country editorial expansion (read-only)\n"
             f"- Catalog: {progress['catalogCount']}\n"
             f"- Fully approved: {progress['approvedCount']}\n"
             f"- Pending: {progress['pendingCount']}\n"
             f"- Portraits prepared, photos/quiz still unverified: "
             f"{', '.join(progress['pendingPortraitsPrepared']) or 'none'}\n"
             f"- First drafts awaiting independent source review: {len(progress['firstDraftsAwaitingSourceReview'])}\n"
             f"- Draft travel stops / reference pages located: {progress['firstDraftTravelStops']} / {progress['firstDraftReferencePagesLocated']}\n"
             "- No pending location is automatically published or substituted with another country's photo.\n")
    print(summary)
    path=os.getenv("GITHUB_STEP_SUMMARY")
    if path:
        with open(path,"a",encoding="utf-8") as f:
            f.write(summary)

if __name__=="__main__":
    main()
