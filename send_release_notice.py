#!/usr/bin/env python3
"""Dispatch ONE release notification only after GitHub Pages deployment succeeded.

Never sends unless both secrets are configured. Backend must atomically dedupe by
editionDate: network retries must never result in duplicate alerts to readers.
"""
from __future__ import annotations
from datetime import datetime
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
    if (not isinstance(stories,list)
            or (kind=="regular" and not 1<=len(stories)<=3)
            or (kind=="special" and len(stories)!=5)
            or kind not in ("regular","special")):
        return None
    # Same rule as the public nightly publisher: never notify before 21:00 JST.
    if now.hour<21:
        return None
    count=len(stories)
    title="よる9じの世界便り"
    body=("創刊特集号が届きました。世界の大失敗、実話5本。今夜はちょっと笑って寝よう。"
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

def main():
    issue=json.loads((Path(__file__).resolve().parent/"data"/"current.json").read_text(encoding="utf-8"))
    payload=notice_for(issue)
    if payload is None:
        print("No current approved release eligible for a notification.")
        return 0
    dispatch(os.getenv("PUSH_DISPATCH_URL",""),os.getenv("PUSH_DISPATCH_TOKEN",""),payload)
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("Notification dispatch not completed: "+type(e).__name__,file=sys.stderr)
        sys.exit(1)
