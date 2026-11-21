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
    return {
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
             "- No pending location is automatically published or substituted with another country's photo.\n")
    print(summary)
    path=os.getenv("GITHUB_STEP_SUMMARY")
    if path:
        with open(path,"a",encoding="utf-8") as f:
            f.write(summary)

if __name__=="__main__":
    main()
