#!/usr/bin/env python3
"""Dispatch ONE release notification only after GitHub Pages deployment succeeded.

Never sends unless both secrets are configured. Backend must atomically dedupe by
editionDate: network retries must never result in duplicate alerts to readers.
"""
from __future__ import annotations
from datetime import datetime, date
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo
import json,os,sys

JST=ZoneInfo("Asia/Tokyo")

def notice_for(issue,now=None):
    now=(now or datetime.now(JST)).astimezone(JST)
    if not isinstance(issue,dict) or issue.get("status")!="published":
        return None
    day=issue.get("editionDate")
    if not isinstance(day,str) or day!=now.date().isoformat():
        return None
    stories=issue.get("stories")
    kind=issue.get("editionType","regular")
    # The notification gate must match the release gate: from 2026-11-21
    # every nonempty, already published and approved issue can be announced.
    # Historic editions retain their original count validation.
    if (not isinstance(stories,list) or not stories
            or kind not in ("regular","special")):
        return None
    if day < "2026-11-21":
        count=len(stories)
        if kind=="special":
            if count!=5:
                return None
        elif day >= "2026-11-19":
            if not 1<=count<=5:
                return None
        elif not 1<=count<=3:
            return None
    # Same rule as the public nightly publisher: never notify before 21:00 JST.
    if now.hour<21:
        return None
    count=len(stories)
    title="よる9じの世界便り"
    body=(f"今夜の特集号が届きました。世界の「まさか」実話{count}本。ニュースは実話、ツッコミはAIから。"
          if kind=="special"
          else f"今夜の世界の「まさか」{count}本が届きました。ニュースは実話、ツッコミはAIから。")
    return {"editionDate":day,"title":title,"body":body,"url":"./"}

def dispatch(config,secret,payload):
    if not secret or not config:
        print("Push backend is not configured. No notifications sent.")
        return False
    p=urlsplit(config)
    if p.scheme!="https" or not p.hostname or p.username or p.password:
        raise ValueError("PUSH_DISPATCH_URL must be an HTTPS service endpoint")
    req=Request(config,
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type":"application/json","Authorization":"Bearer "+secret},
        method="POST")
    with urlopen(req,timeout=25) as r:
        if r.status<200 or r.status>=300:
            raise RuntimeError("Push backend rejected request")
    print("Release notification accepted by backend. Device delivery is not guaranteed.")
    return True

def record_notice_result(result):
    """Expose only fixed operational codes, never credentials or payloads."""
    if result not in ("accepted","not_configured","not_eligible","failed"):
        raise ValueError("Unknown notice result")
    output=os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output,"a",encoding="utf-8") as sink:
            sink.write("result="+result+"\n")

def main():
    issue=json.loads((Path(__file__).resolve().parent/"data"/"current.json").read_text(encoding="utf-8"))
    now=datetime.now(JST)
    print(f"Notification gate: JST={now:%Y-%m-%d %H:%M}, issue={issue.get('editionDate')}, "
          f"status={issue.get('status')}, count={len(issue.get('stories') or [])}")
    payload=notice_for(issue,now)
    if payload is None:
        if (issue.get("status")=="published"
                and issue.get("editionDate")==now.date().isoformat()
                and issue.get("stories")):
            print("ERROR: same-day published issue was unexpectedly rejected.",file=sys.stderr)
            record_notice_result("failed")
            return 1
        print("No current approved release eligible for a notification.")
        record_notice_result("not_eligible")
        return 0
    # An accepted push is for a verified published edition, never merely a
    # queued editorial candidate. No story-count quota is reintroduced here.
    # The push backend deduplicates per issue date.
    print(f"Retry-safe notice for {payload['editionDate']}: {len(issue['stories'])} published stories.")
    try:
        accepted=dispatch(os.getenv("PUSH_DISPATCH_URL",""),os.getenv("PUSH_DISPATCH_TOKEN",""),payload)
    except Exception:
        record_notice_result("failed")
        raise
    record_notice_result("accepted" if accepted else "not_configured")
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("Notification dispatch not completed: "+type(e).__name__,file=sys.stderr)
        sys.exit(1)
