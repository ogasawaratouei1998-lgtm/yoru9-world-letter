#!/usr/bin/env python3
"""Make a DAILY EDITORIAL INBOX from headline leads; NEVER claim facts verified.

No model calls, and no automatic publication. Human editors must open
original reporting and at least one independent corroborating source.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo
import argparse
import json
import re

JST=ZoneInfo("Asia/Tokyo")
HARM=re.compile(r"\b(killed|death|died|fatal|rape|shooting|bombing|war|suicide|injured|hospitalized)\b|死亡|殺害|重傷|銃撃|自殺|戦争|惨事|死者",re.I)

def timestamp(value):
    value=str(value or "").strip()
    if not value:
        return None
    try:
        if re.fullmatch(r"\d{8}T\d{6}Z",value):
            return datetime.strptime(value,"%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        if re.fullmatch(r"\d{4}[.-]\d{2}[.-]\d{2}",value):
            return datetime.strptime(value.replace(".","-"),"%Y-%m-%d").replace(tzinfo=JST)
        d=datetime.fromisoformat(value.replace("Z","+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError,OverflowError):
        try:
            return parsedate_to_datetime(value)
        except (ValueError,TypeError):
            return None

def prepare(data,now=None,maximum=40):
    now=(now or datetime.now(timezone.utc)).astimezone(JST)
    candidates=data.get("candidates",[])
    if not isinstance(candidates,list):
        raise ValueError("candidates must be a list")
    rows=[]; seen=set();country_counts={}
    for c in candidates:
        if not isinstance(c,dict):
            continue
        title=str(c.get("title") or "").strip()[:350]
        url=str(c.get("url") or "").strip()
        try:
            u=urlsplit(url)
            if u.scheme!="https" or not u.hostname or u.username or u.password:
                continue
        except ValueError:
            continue
        if not title or HARM.search(title) or url in seen:
            continue
        posted=timestamp(c.get("seendate"))
        # Missing publication dates are sent for special manual review, never marked fresh.
        age=(now.date()-posted.astimezone(JST).date()).days if posted else None
        if age is not None and (age<0 or age>7):
            continue
        country=str(c.get("sourcecountry") or "unknown")[:60]
        if country_counts.get(country,0)>=6:
            continue
        seen.add(url);country_counts[country]=country_counts.get(country,0)+1
        publisher=str(c.get("domain") or u.hostname or "")[:130]
        rows.append({
            "id":f"lead-{len(rows)+1:03d}",
            "headline":title,"candidateUrl":url,"publisher":publisher,
            "searchRegion":country,
            "newsPublishedAt":posted.isoformat() if posted else None,
            "reportAgeDays":age,
            "ageVerified":age is not None,
            "isGoogleNewsRedirect":bool(u.hostname and u.hostname.endswith("news.google.com")),
            "factStatus":"NOT_VERIFIED",
            "aiQuipStatus":"NOT_GENERATED",
            "editorAction":"Open primary reporting; cross-check with independent source; confirm original event date, outcome, harms, and context.",
            "independentEvidenceUrls":[],
            "searchToVerify":"https://www.google.com/search?q="+quote('"'+title[:130]+'"'),
        })
        if len(rows)>=maximum:
            break
    return {
      "generatedAt":now.isoformat(timespec="seconds"),
      "editionDate":now.date().isoformat(),
      "status":"EDITORIAL_LEADS_ONLY",
      "automaticVerification":False,
      "automaticPublication":False,
      "readMe":"Headlines are not confirmed facts. Date is a source publication estimate, NOT the event date. Google News links may redirect. No story may be published without independent review and explicit approval.",
      "leads":rows,
    }

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--input",default="data/candidates.json")
    cli.add_argument("--output",default="data/editorial-inbox.json")
    args=cli.parse_args()
    data=json.loads(Path(args.input).read_text(encoding="utf-8"))
    result=prepare(data)
    dest=Path(args.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Prepared {len(result['leads'])} UNSCREENED leads for human review; no AI calls, no publication.")
if __name__=="__main__":
    main()
