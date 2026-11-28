"""Bounded, optional research while editorial review runs. Never approves news or materials."""
import json
import os
from pathlib import Path
import threading
from country_codes import country_codes
from country_topic_drafts import discover_topics
from audit_country_highlights import missing_topic_dates
from datetime import date

MAX_COUNTRIES=4
MAX_PAGES=4

def prefetch(root, drafts, day, output, *, discover=discover_topics):
    root=Path(root)
    sources=json.loads((root/"country-highlight-sources.json").read_text(encoding="utf-8"))["sources"]
    canonical=json.loads((root/"country-content.json").read_text(encoding="utf-8"))["countries"]
    codes=list(dict.fromkeys(code for row in drafts if isinstance(row,dict)
                             for code in country_codes(row.get("country",""))))[:MAX_COUNTRIES]
    tasks=[]
    budget=MAX_PAGES
    for code in codes:
        dates=missing_topic_dates({code:canonical[code]["highlights"]},code,date.fromisoformat(day),2)
        official=sources.get(code,[])[:budget]
        if dates and official:
            tasks.append({"countryCode":code,"missingTopicDates":dates,"officialTopicSources":official})
            budget-=len(official)
    result=discover({"editionDate":day,"tasks":tasks})
    result["publicationEligible"]=False
    dest=Path(output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(result,ensure_ascii=False)+"\n",encoding="utf-8")
    tmp.replace(dest)
    return result

def start_prefetch(root,drafts,day):
    target=os.environ.get("YORU9_COUNTRY_PREFETCH_PATH")
    if not target:
        return
    def worker():
        try:
            prefetch(root,drafts,day,target)
        except Exception as exc:
            print("Optional country prefetch deferred:",type(exc).__name__,flush=True)
    threading.Thread(target=worker,daemon=True,name="country-prefetch").start()
    photo_target=os.environ.get("YORU9_COUNTRY_PHOTO_PREFETCH_PATH")
    if photo_target:
        def photo_worker():
            try:
                from country_article_recovery import prefetch_photos
                prefetch_photos(root,drafts,day,photo_target)
            except Exception as exc:
                print("Optional photo lead prefetch deferred:",type(exc).__name__,flush=True)
        threading.Thread(target=photo_worker,daemon=True,name="country-photo-prefetch").start()

def merge_prefetch(tasks, fresh, path):
    """Only preserve same-day, same-country, allowlisted unapproved draft leads."""
    if path is None or not Path(path).is_file():
        return fresh
    try:
        if Path(path).stat().st_size>250000:
            return fresh
        early=json.loads(Path(path).read_text(encoding="utf-8"))
        if early.get("editionDate")!=tasks["editionDate"] or early.get("publicationEligible") is not False:
            return fresh
        if not isinstance(early.get("countries"),list):
            return fresh
        from datetime import date
        allowed={t["countryCode"]:t for t in tasks["tasks"]}
        for report in fresh["countries"]:
            code=report["countryCode"]
            task=allowed[code]
            urls={s["url"] for s in task["officialTopicSources"]}
            needed=set(task["missingTopicDates"])
            for row in early["countries"]:
                if not isinstance(row,dict) or row.get("countryCode")!=code:
                    continue
                for item in row.get("candidates",[])[:20]:
                    if not isinstance(item,dict) or item.get("sourceUrl") not in urls or item.get("sourceCountryCode")!=code:
                        continue
                    if item.get("checkedOn")!=tasks["editionDate"] or item.get("editorialReviewRequired") is not True or item.get("publicationEligible") is not False:
                        continue
                    start=date.fromisoformat(item["validFrom"]); end=date.fromisoformat(item["validThrough"])
                    if not any(start<=date.fromisoformat(d)<=end for d in needed):
                        continue
                    if item not in report["candidates"]:
                        report["candidates"].append(item)
            if report["candidates"]:
                report["status"]="source_bound_candidates"
    except (ValueError,TypeError,KeyError,OSError,AttributeError):
        # Never treat malformed speculation as verified material.
        return fresh
    return fresh
