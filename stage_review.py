#!/usr/bin/env python3
"""Safely stage only the current day's publication-valid AI approval."""
import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from release_contract import validate_release_input, approval_origin

JST=ZoneInfo("Asia/Tokyo")


def stage_review(root: Path, day: str, destination: Path, *, require_assets=False):
    """Return a private, validated artifact file or None; never publish."""
    if (root/"data"/"archive"/(day+".json")).is_file():
        return None
    approved=root/"data"/"approved"/(day+".json")
    if not approved.is_file():
        return None
    data=json.loads(approved.read_text(encoding="utf-8"))
    validate_release_input(root,data,day,require_assets=require_assets)
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
    staged=stage_review(args.root,args.day,args.destination,require_assets=True)
    count=0
    origin="unknown"
    if staged:
        payload=json.loads(staged.read_text(encoding="utf-8"))
        count=len(payload["stories"])
        origin=approval_origin(payload)
    outcome="PUBLISHER_VALID" if staged else "NO_QUALIFYING_ISSUE"
    print("AI review outcome:",outcome,"date",args.day,"approved_stories",count,"origin",origin,flush=True)
    summary=os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as f:
            f.write("## AIニュース編集の実行結果\n\n"
                    "- 対象日（JST）: "+args.day+"\n"
                    "- 公開検証済みの記事数: "+str(count)+"\n"
                    "- 判定: **"+outcome+"**\n"
                    "- 0件は公開成功ではありません。既存号を維持します。\n")
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as f:
            f.write("ready="+("true" if staged else "false")+"\n")
            f.write("origin="+origin+"\n")
            if staged:f.write("path="+str(staged.resolve())+"\n")


if __name__=="__main__":
    main()
