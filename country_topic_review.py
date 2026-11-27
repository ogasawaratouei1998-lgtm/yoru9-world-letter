"""Second-source-read verification of narrowly scoped official cultural-event notices.

No model inference, photo promotion, or human editorial approval is claimed.
Only a matching, visible, explicitly scheduled cultural event from a registered
official page can become a short factual notice. The read-only main workflow
is the trust boundary; arbitrary draft artifacts are never accepted.
"""
import argparse
from datetime import date, timedelta
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata
from country_topic_drafts import StructuredData, nodes, event_candidates, fetch_official
from audit_country_highlights import missing_topic_dates

CULTURAL_TYPES={"Festival","ExhibitionEvent","MusicEvent","DanceEvent","TheaterEvent",
                "VisualArtsEvent","LiteraryEvent"}
FIELDS=("title","body","validFrom","validThrough","checkedOn","sourceName","sourceUrl")
MAX_PAGES=4
MAX_REPORT_BYTES=100_000

def record_digest(record):
    return hashlib.sha256(json.dumps(record,ensure_ascii=False,sort_keys=True,
                         separators=(",",":")).encode("utf-8")).hexdigest()

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden=0
        self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","template"):
            self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","template"):
            self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden:
            self.parts.append(data)

def normalized(value):
    return " ".join(unicodedata.normalize("NFKC",value).casefold().split())

def safe_name(name):
    return (isinstance(name,str) and 1<=len(name.strip())<=65
            and not re.search(r"[<>\\{}]|https?://",name,re.I)
            and not any(unicodedata.category(ch).startswith("C") for ch in name))

def identity(candidate):
    return tuple(candidate.get(k) for k in ("sourceCountryCode","sourceUrl",
                       "sourceEventName","sourceStartDate","sourceEndDate"))

def second_read(html, code, source, day, dates, candidate):
    """Require a matching event and visible event name; reject generic Event."""
    structured=StructuredData()
    structured.feed(html)
    visible=VisibleText()
    visible.feed(html)
    words=normalized(" ".join(visible.parts))
    for doc in structured.documents:
        for event in nodes(doc):
            types=event.get("@type",[])
            if isinstance(types,str):types=[types]
            if not isinstance(types,list) or not any(isinstance(t,str) and
                    t.rsplit("/",1)[-1] in CULTURAL_TYPES for t in types):
                continue
            name=event.get("name")
            if not safe_name(name) or normalized(name) not in words:
                continue
            if event.get("eventAttendanceMode") in ("https://schema.org/OnlineEventAttendanceMode",
                 "http://schema.org/OnlineEventAttendanceMode","OnlineEventAttendanceMode"):
                continue
            # Re-parse only this matched source object, never use candidate prose.
            escaped=json.dumps(event,ensure_ascii=False).replace("<","\\u003c")
            matched=event_candidates('<script type="application/ld+json">'+escaped+'</script>',
                                     code,source,day,dates)
            for row in matched:
                if identity(row)==identity(candidate):
                    return {k:row[k] for k in FIELDS}, {
                        "name":row["sourceEventName"],"start":row["sourceStartDate"],
                        "end":row["sourceEndDate"],"country":code,"sourceUrl":source["url"]}
    return None

def review(root,day,tasks,drafts,fetch=fetch_official):
    root=Path(root)
    result={"version":1,"editionDate":day,"method":"official-cultural-event-second-read-v1","records":{}}
    if tasks.get("editionDate")!=day or drafts.get("editionDate")!=day:
        return result
    canonical=json.loads((root/"country-content.json").read_text(encoding="utf-8"))["countries"]
    sources=json.loads((root/"country-highlight-sources.json").read_text(encoding="utf-8"))["sources"]
    allowed={t["countryCode"] for t in tasks["tasks"]}
    pages={}
    attempts=0
    for report in drafts.get("countries",[]):
        code=report.get("countryCode")
        old=canonical.get(code,{})
        if code not in allowed or old.get("status")!="approved":
            continue
        dates=missing_topic_dates({code:old["highlights"]},code,date.fromisoformat(day),2)
        if not dates:continue
        registered={s["url"]:s for s in sources.get(code,[])}
        for candidate in report.get("candidates",[])[:20]:
            if not isinstance(candidate,dict):continue
            url=candidate.get("sourceUrl")
            if url not in registered or candidate.get("sourceCountryCode")!=code:continue
            try:
                if url not in pages:
                    if attempts>=MAX_PAGES:continue
                    attempts+=1
                    pages[url]=None
                    pages[url]=fetch(url)
                if pages[url] is None:continue
                verified=second_read(pages[url],code,registered[url],day,dates,candidate)
                if verified:
                    row,evidence=verified
                    result["records"][code]={"baseDigest":record_digest(old),
                         "topic":row,"event":evidence,
                         "sourceSha256":hashlib.sha256(pages[url].encode("utf-8")).hexdigest()}
                    break
            except (OSError,ValueError,TypeError,KeyError,RecursionError):
                continue
    return result

def validated_topic(old,record,code,day,registered):
    """Reconstruct the only permitted append from the trusted report; no arbitrary prose."""
    if old.get("status")!="approved" or record.get("baseDigest")!=record_digest(old):
        raise ValueError("Stale or pending country")
    evidence=record["event"]
    url=evidence["sourceUrl"]
    source=next((s for s in registered if s["url"]==url),None)
    name=evidence["name"]
    if (not source or evidence["country"]!=code or not safe_name(name)
        or not re.fullmatch("[0-9a-f]{64}",record.get("sourceSha256",""))):
        raise ValueError("Unbound official evidence")
    start=date.fromisoformat(evidence["start"])
    end=date.fromisoformat(evidence["end"])
    today=date.fromisoformat(day)
    dates=missing_topic_dates({code:old["highlights"]},code,today,2)
    if not any(start<=date.fromisoformat(d)<=end for d in dates):
        raise ValueError("No current coverage gap")
    valid_from=max(today,start)
    expected={"title":"現地の催し「"+name.strip()+"」",
        "body":source["name"]+"の公式案内では、"+str(start.month)+"月"+str(start.day)+"日から"+
        str(end.month)+"月"+str(end.day)+"日までの開催予定が掲載されています。詳細は公式案内をご確認ください。",
        "validFrom":valid_from.isoformat(),"validThrough":min(end,valid_from+timedelta(days=30)).isoformat(),
        "checkedOn":day,"sourceName":source["name"],"sourceUrl":url}
    if record["topic"]!=expected or expected in old["highlights"]:
        raise ValueError("Changed or duplicate topic")
    return {**old,"highlights":[*old["highlights"],expected]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--day",required=True)
    args=p.parse_args()
    if not (args.directory/"material-tasks.json").is_file():return
    tasks=json.loads((args.directory/"material-tasks.json").read_text())
    drafts=json.loads((args.directory/"topic-drafts.json").read_text())
    report=review(Path(__file__).resolve().parent,args.day,tasks,drafts)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Official cultural events revalidated:",sorted(report["records"]))
if __name__=="__main__":main()
