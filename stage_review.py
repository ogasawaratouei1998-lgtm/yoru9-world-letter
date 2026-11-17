#!/usr/bin/env python3
"""Safely stage only the current day's publication-valid AI approval."""
import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from publish_approved import validate_approved

JST=ZoneInfo("Asia/Tokyo")


def stage_review(root: Path, day: str, destination: Path):
    """Return a private, validated artifact file or None; never publish."""
    if (root/"data"/"archive"/(day+".json")).is_file():
        return None
    approved=root/"data"/"approved"/(day+".json")
    if not approved.is_file():
        return None
    data=json.loads(approved.read_text(encoding="utf-8"))
    validate_approved(data,day)
    destination.mkdir(parents=True,exist_ok=True)
    staged=destination/(day+".json")
    staged.write_bytes(approved.read_bytes())
    return staged


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--day",required=True)
    p.add_argument("--destination",required=True,type=Path)
    p.add_argument("--root",default=Path(__file__).resolve().parent,type=Path)
    args=p.parse_args()
    if args.day!=datetime.now(JST).date().isoformat():
        raise SystemExit("Review date changed; no artifact staged")
    staged=stage_review(args.root,args.day,args.destination)
    print(("Staged publisher-valid review" if staged else "No new publisher-valid review")+": "+args.day)
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as f:
            f.write("ready="+("true" if staged else "false")+"\n")
            if staged:f.write("path="+str(staged.resolve())+"\n")


if __name__=="__main__":
    main()
