"""Article-scoped recovery checkpoints. Evidence only; never writes approval.

Same-day trusted workflow artifacts may avoid repeated metadata searches and
downloads, but they never authorize publication. Unreviewed bytes cannot enter
the public photo cache. Official authority candidates are leads, not trusted
sources; no arbitrary URL from Wikidata is fetched.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from country_review_bundle import candidate_identity, download_preview, review_image_url, valid_preview_url
from country_photo_candidates import valid_candidate, API
from country_bulk_research import make_plan, research_shard
from country_content import _commons_identity
from check_release_candidate import jpeg_dimensions
from country_codes import country_codes

ROOT=Path(__file__).resolve().parent
MAX_REPORT=1_000_000
MAX_BYTES=2_000_000
MAX_COUNTRIES=4

def atomic_json(path,value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(path)

def read_json(path):
    try:
        path=Path(path)
        if path.is_symlink() or path.stat().st_size>MAX_REPORT:return {}
        value=json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError,TypeError):return {}

def slot_signature(slot):
    keys=("slot","role","place","searchQuery","alternateSearchQuery","officialSourceCandidate","origin")
    return hashlib.sha256(json.dumps({k:slot.get(k) for k in keys},sort_keys=True,
                          ensure_ascii=False,separators=(",",":")).encode()).hexdigest()

def checkpoint_research(output,plan,day,rows):
    signatures={(r["code"],s["slot"]):slot_signature(s) for r in plan.get("countries",[]) for s in r["slots"]}
    atomic_json(Path(output)/"research-checkpoint.json",{"editionDate":day,"publicationEligible":False,
        "rows":[{"countryCode":r["countryCode"],"slot":r["slot"],
                 "slotSignature":signatures.get((r["countryCode"],r["slot"])),
                 "candidates":r["candidates"]} for r in rows]})

def prior_dirs(prior):
    if not prior or not Path(prior).is_dir():return []
    return sorted((p for p in Path(prior).iterdir() if p.is_dir() and not p.is_symlink() and p.name.isdecimal()),
                  key=lambda p:int(p.name),reverse=True)[:3]

def read_prefetched_candidates(path):
    if not path:return {}
    path=Path(path)
    return read_json(path/"yoru9-country-prefetch-photos.json" if path.is_dir() else path)

def candidate_resume(plan,day,prior=None,early=None):
    allowed={(r["code"],s["slot"]):slot_signature(s) for r in plan.get("countries",[]) for s in r["slots"]}
    result={}
    reports=[(read_json(p/"research-checkpoint.json"),p) for p in prior_dirs(prior)]
    reports.append((read_prefetched_candidates(early),None))
    failed=set()
    for report,directory in reports:
        if report.get("editionDate")!=day or report.get("publicationEligible") is not False:continue
        for row in report.get("rows",[])[:196*3]:
            if not isinstance(row,dict):continue
            key=(row.get("countryCode"),row.get("slot"))
            if key not in allowed or row.get("slotSignature")!=allowed[key] or key in result or key in failed:continue
            if directory:
                index=read_json(directory/"photo-review"/"article-preview-checkpoint.json")
                if index.get("editionDate")==day:
                    slot=next((s for s in index.get("slots",[]) if isinstance(s,dict)
                              and (s.get("countryCode"),s.get("slot"))==key),None)
                    if slot and slot.get("status")!="downloaded_unreviewed":
                        failed.add(key)
                        continue
            try:
                candidates=[x for x in row.get("candidates",[])[:3] if isinstance(x,dict)
                            and x.get("publicationEligible") is False and candidate_identity(x)]
            except (ValueError,TypeError,KeyError,AttributeError):continue
            if candidates:result[key]=candidates
    return result

def prefetch_photos(root,drafts,day,output):
    codes=list(dict.fromkeys(code for row in drafts if isinstance(row,dict)
               for code in country_codes(row.get("country",""))))[:MAX_COUNTRIES]
    plan=make_plan(root)
    # At most one country / three slots; preserve editorial priority.
    by_code={r["code"]:r for r in plan["countries"]}
    plan["countries"]=[by_code[code] for code in codes if code in by_code][:1]
    plan["shards"]=1
    for row in plan["countries"]:row["shard"]=0
    def persist(rows):
        signatures={(r["code"],s["slot"]):slot_signature(s) for r in plan["countries"] for s in r["slots"]}
        atomic_json(output,{"editionDate":day,"publicationEligible":False,
            "rows":[{"countryCode":r["countryCode"],"slot":r["slot"],
                     "slotSignature":signatures[(r["countryCode"],r["slot"])],
                     "candidates":r["candidates"]} for r in rows]})
    research_shard(plan,0,on_progress=persist,sleep_seconds=0.5)

def commons_exact(titles):
    params={"action":"query","titles":"|".join("File:"+t for t in titles),
            "prop":"imageinfo","iiprop":"url|size|mime|extmetadata","iiurlwidth":960,
            "format":"json","formatversion":2}
    req=Request(API+"?"+urlencode(params),headers={"User-Agent":"Yoru9CountryEditorialResearch/1.0 (https://github.com/ogasawaratouei1998-lgtm/yoru9-world-letter)","Accept":"application/json"})
    with urlopen(req,timeout=12) as response:
        raw=response.read(MAX_REPORT+1)
    if len(raw)>MAX_REPORT:raise ValueError("Commons metadata exceeds limit")
    return [c for page in json.loads(raw).get("query",{}).get("pages",[]) if (c:=valid_candidate(page))]

def add_named_photo_leads(root,report,plan,fetch=commons_exact):
    """Prior editorial leads are searched by exact file name, not blindly trusted."""
    rows={(r["countryCode"],r["slot"]):r for r in report.get("results",[])}
    codes={r["code"] for r in plan.get("countries",[])}
    for code in sorted(codes)[:MAX_COUNTRIES]:
        files=sorted((Path(root)/"editorial-country-photo-reviews").glob("*.json"),reverse=True)
        notes=[read_json(f) for f in files if f.name!="cache-seeds.json"]
        note=next((n for n in notes if n.get("countryCode")==code and n.get("publicationEligible") is False),{})
        hints={p["fileIdentity"]:p["slot"] for p in note.get("photos",[]) if
               isinstance(p,dict) and isinstance(p.get("fileIdentity"),str) and p.get("slot") in (0,1,2)
               and p.get("sourceDescriptionVerified") is True and p.get("webRenderingInspected") is True}
        if not hints:continue
        try:
            for candidate in fetch(list(hints)[:3]):
                name=candidate_identity(candidate)
                if name not in hints:continue
                row=rows.get((code,hints[name]))
                if not row:continue
                row["candidates"]=[candidate,*[c for c in row["candidates"] if candidate_identity(c)!=name]][:3]
                row["status"]="metadata_candidates_only"
        except HTTPError as exc:
            if exc.code in (429,503):break
        except (OSError,ValueError,TypeError,KeyError):continue

def photo_urls(candidate,slot):
    # Alternative URLs must resolve to the exact same Commons original.
    identity=candidate_identity(candidate)
    if not identity:return []
    primary=review_image_url(candidate,slot)
    original=candidate.get("original","")
    preview=candidate.get("preview","")
    if slot!=0:
        preview=re.sub(r"/[0-9]+px-(?=[^/?]+(?:\?|$))","/960px-",preview)
        primary=preview
    return list(dict.fromkeys(u for u in (primary,original) if valid_preview_url(u)
                               and _commons_identity(u)==identity))

def usable_photo(path,slot):
    try:
        if path.is_symlink() or not 3000<=path.stat().st_size<=MAX_BYTES:return False
        data=path.read_bytes()
        if not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):return False
        w,h=jpeg_dimensions(path)
        return (w>=1000 and h>=540) if slot==0 else (w>=330 and h>=200)
    except (OSError,ValueError,TypeError,IndexError):return False

def reuse_photo(candidate,code,slot,dest,day,prior):
    for directory in prior_dirs(prior):
        folder=directory/"photo-review"
        index=read_json(folder/"article-preview-checkpoint.json")
        if index.get("editionDate")!=day or index.get("publicationEligible") is not False:continue
        for row in index.get("slots",[]):
            if not isinstance(row,dict) or row.get("countryCode")!=code or row.get("slot")!=slot:continue
            if row.get("candidate")!=candidate or row.get("downloadedUrl") not in photo_urls(candidate,slot):continue
            source=folder/(code+"-"+str(slot)+".jpg")
            if not usable_photo(source,slot):continue
            data=source.read_bytes()
            if hashlib.sha256(data).hexdigest()!=row.get("previewSha256"):continue
            dest.write_bytes(data)
            return row["downloadedUrl"]
    return None

def write_article_previews(queue,output,day,prior=None,fetch=download_preview,sleep_seconds=0.5):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    checkpoint=[];throttled=False
    def persist():
        atomic_json(output/"article-preview-checkpoint.json",{"editionDate":day,
                    "publicationEligible":False,"slots":checkpoint})
    for row in queue:
        code=row["code"]
        if not re.fullmatch("[A-Z]{2}",code):raise ValueError("Invalid country code")
        for slot in row["slots"]:
            i=slot["slot"];candidate=slot.get("candidate")
            record={"countryCode":code,"slot":i,"candidate":candidate,"visualVerified":False,
                    "publicationEligible":False,"status":"no_candidate"}
            if candidate:
                dest=output/(code+"-"+str(i)+".jpg")
                url=reuse_photo(candidate,code,i,dest,day,prior)
                if url:record["reused"]=True
                elif throttled:record["status"]="rate_limited_deferred"
                else:
                    for possible in photo_urls(candidate,i):
                        try:
                            dest.write_bytes(fetch(possible))
                            if not usable_photo(dest,i):
                                dest.unlink(missing_ok=True);record["status"]="invalid_jpeg";continue
                            url=possible;break
                        except HTTPError as exc:
                            record["status"]="http_error_"+str(exc.code)
                            if exc.code in (429,503):throttled=True;break
                        except (OSError,ValueError,TypeError):record["status"]="download_failed"
                        finally:
                            if sleep_seconds:time.sleep(sleep_seconds)
                if url:
                    record.update(status="downloaded_unreviewed",downloadedUrl=url,
                         previewSha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
                         dimensions=list(jpeg_dimensions(dest)),previewFile=dest.name)
            slot.update(previewStatus=record["status"])
            if record["status"]=="downloaded_unreviewed":
                slot.update({k:record[k] for k in ("downloadedUrl","previewSha256","previewFile","dimensions")})
            checkpoint.append(record);persist()
    summary={"pendingCountries":len(queue),"downloadedUnreviewedPreviews":sum(r["status"]=="downloaded_unreviewed" for r in checkpoint),
             "fullyDownloadedCountries":sum(all(s["previewStatus"]=="downloaded_unreviewed" for s in r["slots"]) for r in queue),
             "publicationEligible":False}
    atomic_json(output/"review-index.json",{"summary":summary,"queue":queue})
    return summary

def authority_search(code):
    """Find national authority website *leads* via Wikidata P17/P297 and P856.
    No fetched or model-guessed URL is promoted to the trusted registry.
    """
    query='SELECT DISTINCT ?agency ?agencyLabel ?website WHERE { ?country wdt:P297 "'+code+'" . ?agency wdt:P17 ?country ; wdt:P856 ?website ; wdt:P31/wdt:P279* ?kind . VALUES ?kind { wd:Q579167 wd:Q3689421 } SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } } LIMIT 10'
    req=Request("https://query.wikidata.org/sparql?"+urlencode({"query":query,"format":"json"}),
                headers={"User-Agent":"Yoru9AuthorityLeads/1.0 (https://github.com/ogasawaratouei1998-lgtm/yoru9-world-letter)","Accept":"application/sparql-results+json"})
    with urlopen(req,timeout=10) as response:raw=response.read(100_001)
    if len(raw)>100_000:raise ValueError("Authority lead limit")
    leads=[]
    for row in json.loads(raw).get("results",{}).get("bindings",[]):
        url=row.get("website",{}).get("value","")
        label=row.get("agencyLabel",{}).get("value","")
        u=urlsplit(url)
        if u.scheme=="https" and u.hostname and not u.username and not u.password and label:
            leads.append({"name":label[:150],"url":url,"authorityVerified":False,"publicationEligible":False})
    return leads

def discover_authority_leads(root,tasks,output,fetch=authority_search):
    result={}
    for task in tasks.get("tasks",[])[:MAX_COUNTRIES]:
        code=task["countryCode"]
        if not task.get("topicSourceDiscoveryRequired") or not re.fullmatch("[A-Z]{2}",code):continue
        try:result[code]={"status":"unverified_authority_leads","leads":fetch(code)}
        except (OSError,ValueError,TypeError,KeyError):result[code]={"status":"discovery_deferred","leads":[]}
    atomic_json(Path(output)/"authority-leads.json",{"editionDate":tasks.get("editionDate"),"countries":result,"publicationEligible":False})

def write_completion_report(root,payload,day,output):
    from article_country_materials import material_tasks
    tasks=material_tasks(root,payload.get("stories",[]),day)
    checkpoint=read_json(Path(output)/"photo-review"/"article-preview-checkpoint.json")
    slots=checkpoint.get("slots",[]) if checkpoint.get("editionDate")==day else []
    states=[]
    for task in tasks["tasks"]:
        code=task["countryCode"]
        got=sorted(s["slot"] for s in slots if s.get("countryCode")==code and s.get("status")=="downloaded_unreviewed")
        states.append({"countryCode":code,"remainingCanonicalRequirements":task["missing"],
            "photoSlotsDownloadedUnreviewed":got,"sourceDiscoveryRequired":task["topicSourceDiscoveryRequired"],
            "status":"REVIEW_REQUIRED" if task["status"]=="pending" else "TOPIC_REQUIRED",
            "publicationEligible":False})
    result={"editionDate":day,"articleCountries":tasks["articleCountries"],"completeCountries":len(tasks["articleCountries"])-len(states),
            "incompleteCountries":states,"completionStatus":"INCOMPLETE" if states else "COMPLETE"}
    atomic_json(Path(output)/"completion.json",result)
    print("Country material completion:",json.dumps(result,ensure_ascii=False),flush=True)
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--approved",required=True,type=Path)
    p.add_argument("--directory",required=True,type=Path)
    args=p.parse_args()
    payload=read_json(args.approved)
    day=datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()
    if payload.get("editionDate")!=day:
        print("Country completion unavailable: no current validated approval");return
    from release_contract import validate_release_input
    validate_release_input(ROOT,payload,day,require_assets=True)
    write_completion_report(ROOT,payload,day,args.directory)

if __name__=="__main__":main()
