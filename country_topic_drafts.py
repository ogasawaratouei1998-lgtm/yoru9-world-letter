"""Collect dated cultural-event draft candidates from registered official pages.

Only explicit structured Event records are used. No model-generated dates,
unregistered URLs, inferred country, or fabricated current events.
"""
from datetime import date, timedelta
from html.parser import HTMLParser
import json
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import URLError
import re

MAX_BYTES=2_000_000
EVENT_TYPES={"Event","Festival","ExhibitionEvent","MusicEvent","DanceEvent",
             "TheaterEvent","VisualArtsEvent","LiteraryEvent"}


class StructuredData(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active=False
        self.parts=[]
        self.documents=[]
    def handle_starttag(self,tag,attrs):
        if tag=="script" and dict(attrs).get("type","").lower()=="application/ld+json":
            self.active=True
            self.parts=[]
    def handle_data(self,data):
        if self.active:
            self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=="script" and self.active:
            self.active=False
            try:
                self.documents.append(json.loads("".join(self.parts)))
            except (ValueError,RecursionError):
                pass


class SameHostRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        a,b=urlsplit(req.full_url),urlsplit(newurl)
        if b.scheme!="https" or a.netloc!=b.netloc or b.username or b.password:
            raise URLError("Unapproved official source redirect")
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def fetch_official(url):
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.port not in (None,443)):
        raise ValueError("Invalid official source URL")
    request=Request(url,headers={"User-Agent":"Yoru9CountryTopics/1.0",
                                 "Accept":"text/html,application/xhtml+xml"})
    with build_opener(SameHostRedirect()).open(request,timeout=15) as response:
        raw=response.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:
            raise ValueError("Official page exceeds safe extraction budget")
        return raw.decode("utf-8",errors="replace")


def nodes(value):
    stack=[value]
    while stack:
        item=stack.pop()
        if isinstance(item,dict):
            yield item
            stack.extend(item.values())
        elif isinstance(item,list):
            stack.extend(item)


def iso_day(value):
    if not isinstance(value,str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}.*)?",value):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def event_candidates(html,code,source,day,missing_dates):
    day=date.fromisoformat(day) if isinstance(day,str) else day
    required={date.fromisoformat(d) for d in missing_dates}
    parser=StructuredData()
    parser.feed(html)
    result=[];seen=set()
    for doc in parser.documents:
        for event in nodes(doc):
            types=event.get("@type",[])
            if isinstance(types,str):types=[types]
            if not isinstance(types,list) or not any(
                    isinstance(t,str) and t.rsplit("/",1)[-1] in EVENT_TYPES for t in types):
                continue
            status=event.get("eventStatus")
            if status not in ("https://schema.org/EventScheduled","http://schema.org/EventScheduled","EventScheduled"):
                continue
            name=event.get("name")
            if not isinstance(name,str) or not 1<=len(name.strip())<=65:
                continue
            location=event.get("location")
            address=location.get("address") if isinstance(location,dict) else None
            country=address.get("addressCountry") if isinstance(address,dict) else None
            if isinstance(country,dict):country=country.get("identifier") or country.get("name")
            if not isinstance(country,str) or country.upper()!=code:
                continue
            start=iso_day(event.get("startDate"));end=iso_day(event.get("endDate"))
            if not start or not end or end<start or not any(start<=d<=end for d in required):
                continue
            valid_from=max(day,start);valid_through=min(end,valid_from+timedelta(days=30))
            if valid_through<valid_from:
                continue
            identity=(name,start,end)
            if identity in seen:continue
            seen.add(identity)
            result.append({"title":"現地の催し「"+name.strip()+"」",
                "body":source["name"]+"の公式案内では、"+str(start.month)+"月"+str(start.day)+"日から"+
                str(end.month)+"月"+str(end.day)+"日までの開催予定が掲載されています。詳細は公式案内をご確認ください。",
                "validFrom":valid_from.isoformat(),"validThrough":valid_through.isoformat(),
                "checkedOn":day.isoformat(),"sourceName":source["name"],"sourceUrl":source["url"],
                "sourceEventName":name,"sourceStartDate":start.isoformat(),
                "sourceEndDate":end.isoformat(),"sourceCountryCode":code,
                "editorialReviewRequired":True,"publicationEligible":False})
    return result


def discover_topics(tasks,fetch=fetch_official):
    output=[]
    for task in tasks["tasks"]:
        if not task["missingTopicDates"]:continue
        candidates=[];errors=[]
        for source in task["officialTopicSources"]:
            try:
                candidates.extend(event_candidates(fetch(source["url"]),
                    task["countryCode"],source,tasks["editionDate"],task["missingTopicDates"]))
            except (URLError,OSError,ValueError,TypeError,RecursionError) as exc:
                errors.append(type(exc).__name__)
        output.append({"countryCode":task["countryCode"],"missingDates":task["missingTopicDates"],
                       "candidates":candidates,"sourceErrors":errors,
                       "status":"source_bound_candidates" if candidates else "no_verified_structured_event_found"})
    return {"editionDate":tasks["editionDate"],"countries":output,"publicationEligible":False}
