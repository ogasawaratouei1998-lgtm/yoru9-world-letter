"""Apply explicitly reviewed, repository-tracked country records, never draft artifacts.

Trust boundary: a committed country-material-reviews/<day>-<code>.json on the
trusted main checkout is a separate editorial approval, not a model assertion.
The exact record and prior canonical digest are bound to that approval.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from datetime import date
from country_codes import country_codes
from country_content import sync_country_content
from country_manifest_format import format_manifest, LIMIT
from build_site import validate_country_highlights

EXPORTS=("country-content.json","country-highlights.json","index.html","world-passport.js",
         "travel-stops.json","reader_sources/country-data.js")
INPUTS=("country-catalog.json","country-highlight-sources.json")

def digest(record):
    return hashlib.sha256(json.dumps(record,ensure_ascii=False,sort_keys=True,
                         separators=(",",":")).encode("utf-8")).hexdigest()

def reviewed_record(old, packet, day, code):
    if (packet.get("version")!=1 or packet.get("editionDate")!=day or packet.get("countryCode")!=code
            or packet.get("sourceReviewed") is not True or packet.get("editorialReviewed") is not True
            or not isinstance(packet.get("reviewer"),str) or not packet["reviewer"].strip()
            or not isinstance(packet.get("reviewEvidence"),list) or not packet["reviewEvidence"]
            or not all(isinstance(x,str) and x.strip() for x in packet["reviewEvidence"])):
        raise ValueError("Missing explicit independent review")
    new=packet["reviewedRecord"]
    if not isinstance(new,dict) or packet.get("recordDigest")!=digest(new):
        raise ValueError("Reviewed record changed")
    if digest(old)==digest(new):
        return old
    if packet.get("baseDigest")!=digest(old):
        raise ValueError("Canonical record changed since review")
    if new.get("status")!="approved" or new.get("name")!=old.get("name"):
        raise ValueError("Country mismatch or pending record")
    if not set(old["travelStops"])<=set(new["travelStops"]):
        raise ValueError("Reviewed update may not remove existing destinations")
    visual_fields=("portraitPhotos","travelStops","quiz")
    if old.get("status")!="approved" or any(old.get(k)!=new.get(k) for k in visual_fields):
        if packet.get("visualReviewed") is not True or packet.get("licenseReviewed") is not True:
            raise ValueError("Exact photo identity and license review required")
    return new

def check_reviewed_photos(old,new,packet,cache):
    """Optional enrichment cannot add a network-dependent photo to tonight's issue."""
    if old.get("status")=="approved" and all(old.get(k)==new.get(k) for k in
            ("portraitPhotos","travelStops","quiz")):
        return
    from build_site import photo_cache_path
    from check_release_candidate import jpeg_dimensions
    if not cache:
        raise ValueError("Reviewed photo cache not available")
    covers={p.get("asset") for p in new["portraitPhotos"] if not p.get("avoidCover")}
    proof=packet.get("reviewedPhotoSha256",{})
    for stop in new["travelStops"].values():
        asset=stop["photoAsset"]
        cover=asset in covers or stop.get("coverOnly") is True
        path=photo_cache_path(cache,stop,cover)
        if not path.is_file() or not 3000<=path.stat().st_size<=2_000_000:
            raise ValueError("Reviewed photo bytes not ready")
        if hashlib.sha256(path.read_bytes()).hexdigest()!=proof.get(asset):
            raise ValueError("Exact photo bytes differ from independent review")
        w,h=jpeg_dimensions(path)
        if (w<1000 or h<540) if cover else (w<330 or h<200):
            raise ValueError("Reviewed photo resolution inadequate")

def apply(root,day,cache=None,auto_directory=None):
    root=Path(root)
    date.fromisoformat(day)
    issue=json.loads((root/"data/current.json").read_text(encoding="utf-8"))
    if issue.get("editionDate")!=day or issue.get("status")!="published":
        return []
    codes=sorted({code for s in issue["stories"] for code in country_codes(s["country"])})
    doc=json.loads((root/"country-content.json").read_text(encoding="utf-8"))
    changed=[]
    from country_topic_review import validated_topic, MAX_REPORT_BYTES
    auto_reports=[]
    if auto_directory:
        for path in sorted(Path(auto_directory).glob("*/reviewed-topics.json"),
                           key=lambda p:int(p.parent.name) if p.parent.name.isdecimal() else -1,
                           reverse=True)[:4]:
            try:
                if path.is_symlink() or not path.parent.name.isdecimal() or path.stat().st_size>MAX_REPORT_BYTES:
                    continue
                report=json.loads(path.read_text(encoding="utf-8"))
                if (report.get("version")==1 and report.get("editionDate")==day
                    and report.get("method")=="official-cultural-event-second-read-v1"
                    and isinstance(report.get("records"),dict)):
                    auto_reports.append(report["records"])
            except (OSError,ValueError,TypeError,AttributeError):
                continue
    registered=json.loads((root/"country-highlight-sources.json").read_text(encoding="utf-8"))["sources"]
    for code in codes:
        path=root/"country-material-reviews"/(day+"-"+code+".json")
        try:
            old=doc["countries"][code]
            if path.is_file() and not path.is_symlink():
                packet=json.loads(path.read_text(encoding="utf-8"))
                new=reviewed_record(old,packet,day,code)
                if new==old:
                    continue
                check_reviewed_photos(old,new,packet,cache)
            else:
                new=old
                if old.get("status")=="pending" and auto_directory and cache:
                    from country_gemini_review import restore_reviewed_country
                    auto=restore_reviewed_country(root,old,code,day,auto_directory,cache)
                    if auto:
                        new,packet=auto
                        check_reviewed_photos(old,new,packet,cache)
                # Newest valid report wins; a stale or malformed report never
                # prevents a different valid same-day report from being used.
                for report in auto_reports:
                    if new!=old:break
                    if code not in report:continue
                    try:
                        new=validated_topic(old,report[code],code,day,registered.get(code,[]))
                        break
                    except (ValueError,TypeError,KeyError,AttributeError):
                        continue
                if new==old:continue
            # Validate each update in isolation; a bad optional record must
            # not suppress independently approved news or unrelated reviews.
            proposed=json.loads(json.dumps(doc))
            proposed["countries"][code]=new
            extra=sorted(set(new["travelStops"])-set(old["travelStops"]))
            proposed["travelOrder"].extend(extra)
            raw=format_manifest(proposed)
            if len(raw.encode("utf-8"))>=LIMIT:
                raise ValueError("Canonical file size limit")
            with tempfile.TemporaryDirectory() as td:
                stage=Path(td)
                for name in EXPORTS+INPUTS:
                    dest=stage/name
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(root/name,dest)
                for name in ("template.html","core.css","core.js","travel.js"):
                    shutil.copyfile(root/"reader_sources"/name,stage/"reader_sources"/name)
                (stage/"country-content.json").write_text(raw,encoding="utf-8")
                sync_country_content(stage)
                validate_country_highlights(stage)
                # Preserve original files until every structural/source gate passes.
                result={name:(stage/name).read_bytes() for name in EXPORTS}
            for name,data in result.items():
                (root/name).write_bytes(data)
            doc=proposed
            changed.append(code)
        except (ValueError,TypeError,KeyError,OSError,AttributeError) as exc:
            print("Reviewed country material deferred:",code,type(exc).__name__)
    return changed

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--day",required=True)
    p.add_argument("--photo-cache",type=Path)
    p.add_argument("--auto-directory",type=Path)
    p.add_argument("--root",type=Path,default=Path(__file__).resolve().parent)
    args=p.parse_args()
    print("Applied independently reviewed country records:",apply(args.root,args.day,args.photo_cache,args.auto_directory))

if __name__=="__main__":
    main()
