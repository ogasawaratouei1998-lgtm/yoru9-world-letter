#!/usr/bin/env python3
"""One editorial source for country portraits, licensed images, trips and quizzes.

country-content.json is the authoring file. The browser's legacy registries
remain generated compatibility outputs until the frontend is fully modular.
--check never edits; --sync intentionally regenerates the four old artifacts.
Never manufacture missing content or mark pending countries as approved.
"""
import argparse
import ast
import json
from pathlib import Path
import re

from country_codes import country_codes


def _js_object(literal):
    """Parse the restricted, static JS object syntax used by legacy registries.

    No JavaScript execution, eval, network request or source rewriting.
    """
    def quote(match):
        return json.dumps(ast.literal_eval(match.group(0)), ensure_ascii=False)
    value=re.sub(r"'(?:\\.|[^'\\])*'", quote, literal)
    value=re.sub(r'([,{]\s*)([A-Za-z_$][A-Za-z0-9_$]*)(\s*:)',
                 r'\1"\2"\3', value)
    value=re.sub(r',\s*([}\]])',r'\1',value)
    return json.loads(value)


def _extract_object(source, name):
    opening="const "+name+"=Object.freeze({"
    if source.count(opening)!=1:
        raise ValueError(name+": registry missing or ambiguous")
    return _js_object("{"+source.split(opening,1)[1].split("\n});",1)[0]+"}")


def _extract_photos(html):
    lines=[line for line in html.splitlines()
           if line.startswith("const TODAY_COUNTRY_PHOTOS=Object.freeze(")]
    prefix="const TODAY_COUNTRY_PHOTOS=Object.freeze("
    if len(lines)!=1 or not lines[0].endswith(");"):
        raise ValueError("Country cover photographs must have one registry")
    return json.loads(lines[0][len(prefix):-2])


def _legacy(root):
    root=Path(root)
    html=(root/"index.html").read_text(encoding="utf-8")
    passport=(root/"world-passport.js").read_text(encoding="utf-8")
    stops=json.loads((root/"travel-stops.json").read_text(encoding="utf-8"))
    highlights=json.loads((root/"country-highlights.json").read_text(encoding="utf-8"))
    catalog=json.loads((root/"country-catalog.json").read_text(encoding="utf-8"))
    guides=_extract_object(html,"TODAY_COUNTRY_GUIDES")
    quizzes=_extract_object(passport,"WORLD_PASSPORT_QUIZZES")
    covers=_extract_photos(html)
    names={item["name"]:item["code"] for item in catalog}
    if len(names)!=len(catalog):
        raise ValueError("Duplicate country names in geography registry")
    locations={}
    for key,stop in stops.items():
        code=names.get(stop.get("country"))
        if not code:
            raise ValueError("Unmapped travel stop (never reassign): "+key)
        locations.setdefault(code,{})[key]=stop
    known={item["code"] for item in catalog}
    if not (set(guides)|set(quizzes)|set(covers)|set(locations)|
            set(highlights["highlights"])).issubset(known):
        raise ValueError("Unrecognized country content entry")
    countries={}
    for country in catalog:
        code=country["code"]
        countries[code]={
            "name":country["name"],"portrait":guides.get(code),
            "portraitPhotos":covers.get(code,[]),"quiz":quizzes.get(code,[]),
            "travelStops":locations.get(code,{}),
            "highlights":highlights["highlights"].get(code,[]),
        }
    return {"travelOrder":list(stops),
            "highlightsMetadata":{key:highlights[key]
                                  for key in ("version","updatedOn","description")},
            "countries":countries}


def load_country_content(root):
    dataset=json.loads((Path(root)/"country-content.json").read_text(encoding="utf-8"))
    if dataset.get("version")!=1 or not isinstance(dataset.get("countries"),dict):
        raise ValueError("Country editorial dataset version is unsupported")
    catalog=json.loads((Path(root)/"country-catalog.json").read_text(encoding="utf-8"))
    codes={entry["code"] for entry in catalog}
    if set(dataset["countries"])!=codes:
        raise ValueError("Country dataset must cover all 196 reporting locations")
    from urllib.parse import urlsplit
    names={item["code"]:item["name"] for item in catalog}
    if len(names)!=len(catalog):
        raise ValueError("Duplicate location codes in canonical country catalog")
    # A local file path denotes one *specific* verified photograph. The same
    # path may appear in multiple postcards only when country AND Wikimedia
    # provenance agree. Neither pending content nor approved news can relabel
    # a picture as a different country or a different licensed photograph.
    photo_provenance={}
    for code,entry in dataset["countries"].items():
        if entry.get("status") not in ("approved","pending"):
            raise ValueError(code+": unknown country editorial approval status")
        if entry["status"]=="approved":
            portrait=entry.get("portrait")
            if not isinstance(portrait,dict) or not portrait.get("sourceName"):
                raise ValueError(code+": approved portrait requires named cultural source")
            source_url=portrait.get("sourceUrl")
            if not isinstance(source_url,str):
                raise ValueError(code+": approved portrait source URL missing")
            guide_url=urlsplit(source_url)
            if (guide_url.scheme!="https" or not guide_url.hostname
                    or guide_url.username or guide_url.password
                    or guide_url.hostname.endswith("wikimedia.org")
                    or guide_url.hostname.endswith("creativecommons.org")):
                raise ValueError(code+": approved country portrait requires an independent source")
            # Each historical claim needs an independent documentary reference;
            # a CC image credit alone says nothing about the essay's accuracy.
            for key,stop in entry.get("travelStops",{}).items():
                if not stop.get("travelStory"):
                    continue
                sources=stop.get("historicalSources")
                if not isinstance(sources,list) or not sources:
                    raise ValueError(code+": unsourced history/culture for "+key)
                for source in sources:
                    if not isinstance(source,dict) or not isinstance(source.get("name"),str):
                        raise ValueError(code+": malformed historical source for "+key)
                    address=source.get("url")
                    if not isinstance(address,str):
                        raise ValueError(code+": missing historical source URL for "+key)
                    url=urlsplit(address)
                    if (url.scheme!="https" or not url.hostname or url.username
                            or url.password or url.hostname.endswith("wikimedia.org")
                            or url.hostname.endswith("creativecommons.org")):
                        raise ValueError(code+": photo license cannot replace a historical source: "+key)
                    if not isinstance(source.get("checkedOn"),str) or not re.fullmatch(
                            r"\d{4}-\d{2}-\d{2}",source["checkedOn"]):
                        raise ValueError(code+": historical source review date missing: "+key)
        if (not isinstance(entry.get("quiz"),list)
                or not isinstance(entry.get("portraitPhotos"),list)
                or not isinstance(entry.get("travelStops"),dict)
                or not isinstance(entry.get("highlights"),list)):
            raise ValueError(code+": malformed curated country content")
        if entry.get("name")!=names[code]:
            raise ValueError(code+": canonical country name does not match geographic catalog")
        for key,stop in entry["travelStops"].items():
            if not isinstance(stop,dict) or stop.get("country")!=names[code]:
                raise ValueError(code+": wrong-country postcard: "+key)
            asset=stop.get("photoAsset")
            if not isinstance(asset,str) or not re.fullmatch(
                    r"assets/travel/[a-z0-9-]+\.jpg",asset):
                raise ValueError(code+": invalid postcard photograph: "+key)
            provenance=(code,stop.get("photo"),stop.get("photoPage"),
                        stop.get("author"),stop.get("license"),
                        stop.get("licenseUrl"))
            previous=photo_provenance.setdefault(asset,provenance)
            if previous!=provenance:
                raise ValueError(code+": photograph reused with conflicting "
                                 "country/source/creator/license: "+asset)
        if entry["status"]=="approved":
            if not entry.get("portrait") or not entry["portraitPhotos"] or len(entry["quiz"])<2:
                raise ValueError(code+": approval without completed country content")
    order=dataset.get("travelOrder")
    keys=[key for row in dataset["countries"].values()
          for key in row["travelStops"]]
    if (not isinstance(order,list) or len(set(order))!=len(order)
            or set(order)!=set(keys)):
        raise ValueError("Travel stops missing from canonical ordered index")
    return dataset


def check_country_content(root):
    """Fail closed on ANY inconsistent legacy registry, with no silent repair."""
    canonical=load_country_content(root)
    legacy=_legacy(root)
    if canonical["travelOrder"]!=legacy["travelOrder"]:
        raise ValueError("Travel stop order drift: use country_content.py --sync")
    if canonical["highlightsMetadata"]!=legacy["highlightsMetadata"]:
        raise ValueError("Country current-topic metadata drift: use --sync")
    for code,entry in canonical["countries"].items():
        for field,value in legacy["countries"][code].items():
            if entry.get(field)!=value:
                raise ValueError(code+"."+field+": source-of-truth drift; run --sync")
    # A valid JSON/JS export alone does not mean a newly approved country can
    # actually render. Audit *all* approvals, not just today's article countries.
    # This catches cover/quiz reuse, foreign imagery and missing travel options
    # before a future nightly edition is allowed to reference the country.
    from check_country_experience import country_coverage
    for code,entry in canonical["countries"].items():
        if entry["status"]=="approved":
            try:
                country_coverage(root,[{"country":code}])
            except (KeyError,ValueError,TypeError,IndexError,OSError) as exc:
                raise ValueError(code+": approved content fails reader readiness: "+str(exc)) from exc
    return canonical


def _string(value):
    return "'"+value.replace("\\","\\\\").replace("'","\\'").replace(
        "\n","\\n").replace("\r","\\r")+"'"

def _js(value):
    if isinstance(value,str):
        return _string(value)
    if isinstance(value,dict):
        return "{"+",".join(key+":"+_js(item) for key,item in value.items())+"}"
    if isinstance(value,list):
        return "["+",".join(_js(item) for item in value)+"]"
    if value is True:return "true"
    if value is False:return "false"
    if value is None:return "null"
    if isinstance(value,(int,float)):return json.dumps(value)
    raise TypeError("Unsupported editorial field: "+str(type(value)))


def _replace_object(source,name,entries,kind):
    opening="const "+name+"=Object.freeze({"
    if source.count(opening)!=1:
        raise ValueError("Cannot regenerate missing "+name)
    before,tail=source.split(opening,1)
    if "\n});" not in tail:
        raise ValueError("Unterminated "+name)
    _,after=tail.split("\n});",1)
    chunks=[]
    for code,entry in entries:
        if kind=="quiz":
            # Preserve the static shapes required by the reader and readiness gate.
            content="\n".join("  "+_js(question)+"," for question in entry)
            chunks.append(" "+code+":[\n"+content+"\n ],")
        else:
            chunks.append(" "+code+":"+_js(entry)+",")
    # Retain trailing comma: the existing country release gate also expects
    # the final quiz country to end with the same list terminator as others.
    return before+opening+"\n"+"\n".join(chunks)+"\n});"+after


def sync_country_content(root):
    """Deliberate export from the single reviewed JSON file; never auto-approve."""
    root=Path(root)
    doc=load_country_content(root)
    countries=doc["countries"]
    html=(root/"index.html").read_text(encoding="utf-8")
    passport=(root/"world-passport.js").read_text(encoding="utf-8")
    html=_replace_object(html,"TODAY_COUNTRY_GUIDES",
                         ((code,c["portrait"]) for code,c in countries.items()
                          if c["portrait"] is not None),"guide")
    passport=_replace_object(passport,"WORLD_PASSPORT_QUIZZES",
                             ((code,c["quiz"]) for code,c in countries.items()
                              if c["quiz"]),"quiz")
    covers={code:c["portraitPhotos"] for code,c in countries.items()
            if c["portraitPhotos"]}
    line="const TODAY_COUNTRY_PHOTOS=Object.freeze("+json.dumps(
        covers,ensure_ascii=False,separators=(",",":"))+");"
    html,n=re.subn(r"(?m)^const TODAY_COUNTRY_PHOTOS=Object\.freeze\(.*\);$",
                   lambda match:line,html)
    if n!=1:
        raise ValueError("Country cover-photo registry missing")
    stops={key:next(c["travelStops"][key] for c in countries.values()
                    if key in c["travelStops"]) for key in doc["travelOrder"]}
    metadata=doc["highlightsMetadata"]
    highlights={**metadata,"highlights":{
        code:c["highlights"] for code,c in countries.items() if c["highlights"]}}
    (root/"index.html").write_text(html,encoding="utf-8")
    (root/"world-passport.js").write_text(passport,encoding="utf-8")
    (root/"travel-stops.json").write_text(json.dumps(
        stops,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (root/"country-highlights.json").write_text(json.dumps(
        highlights,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    check_country_content(root)


def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check",action="store_true",help="read-only drift and schema audit")
    group.add_argument("--sync",action="store_true",help="export edited country data to legacy files")
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args()
    if args.sync:sync_country_content(args.root)
    else:check_country_content(args.root)
    print("Country editorial source checked: 196 entries; no facts manufactured")


if __name__=="__main__":
    main()
