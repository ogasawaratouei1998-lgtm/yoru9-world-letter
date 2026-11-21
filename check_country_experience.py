#!/usr/bin/env python3
"""Fail closed when a published country's portrait, photographs or quiz are unfinished.

Checks the editorially curated runtime artifacts that the shipped browser
actually reads. Never selects a substitute image, invents a country fact,
or contacts a billable AI service.
"""
import json
from pathlib import Path
import re

from country_codes import country_codes, catalog

# Use the SAME 196-location geography as article normalization and the
# country editorial manifest. A second hardcoded name whitelist would block
# a newly prepared country or silently require an unrelated Python edit.
COUNTRY_NAMES = {record["code"]: record["name"] for record in catalog()}
if len(COUNTRY_NAMES) != len(catalog()):
    raise ValueError("Duplicate code in the canonical country catalog")


def country_coverage(root: Path, stories):
    root=Path(root)
    html=(root/"index.html").read_text(encoding="utf-8")
    passport=(root/"world-passport.js").read_text(encoding="utf-8")
    photos=json.loads((root/"travel-stops.json").read_text(encoding="utf-8"))
    prefix="const TODAY_COUNTRY_PHOTOS=Object.freeze("
    photo_lines=[line for line in html.splitlines() if line.startswith(prefix)]
    if len(photo_lines)!=1 or not photo_lines[0].endswith(");"):
        raise ValueError("Country portrait photo registry is missing")
    covers=json.loads(photo_lines[0][len(prefix):-2])
    guide_section=html.split("const TODAY_COUNTRY_GUIDES=Object.freeze({",1)[1].split("\n});",1)[0]
    quiz_section=passport.split("const WORLD_PASSPORT_QUIZZES=Object.freeze({",1)[1].split("\n});",1)[0]
    report={}
    codes=set()
    for story in stories:
        story_codes=country_codes(story.get("country",""))
        if not story_codes:
            raise ValueError("Country not verified for story: "+str(story.get("id","")))
        codes.update(story_codes)
    # New countries stay in the editorial queue until explicitly approved.
    # Legacy test fixtures with no canonical manifest retain their old contract.
    if (root/'country-content.json').is_file():
        from country_content import load_country_content
        manifest=load_country_content(root)
        for code in codes:
            if manifest['countries'][code]['status']!='approved':
                raise ValueError(code+': country content awaiting editorial approval')
    for code in sorted(codes):
        guide=re.search(r"(?m)^ "+re.escape(code)+r":\{lead:'([^']+)',body:'([^']+)',facts:\[([^\]]+)",guide_section)
        if not guide or len(guide.group(2))<145 or len(guide.group(1))<12:
            raise ValueError(code+": substantive country portrait is not curated")
        images=covers.get(code,[])
        if not images:
            raise ValueError(code+": no licensed country-cover photograph")
        verified_covers=[]
        for photo in images:
            # The browser may try every selectable fallback. Do not silently
            # skip a malformed entry when at least one other photo is valid.
            if not isinstance(photo,dict):
                raise ValueError(code+": malformed selectable country portrait")
            if photo.get("avoidCover") or photo.get("remoteOnly"):
                continue
            asset=photo.get("asset")
            stop=next((item for item in photos.values()
                       if item.get("photoAsset")==asset and
                       item.get("country")==COUNTRY_NAMES.get(code) and
                       item.get("quizOnly") is not True),None)
            if not verified_country_cover(photo,stop):
                raise ValueError(code+": selectable cover source/creator does not match local photo manifest")
            verified_covers.append(asset)
        if not verified_covers:
            raise ValueError(code+": cover source/creator does not match local photo manifest")
        # The first vetted photo is the selected national portrait. ALL other
        # eligible photos may become fallbacks when the initial image fails.
        # None may be a quiz answer, even if the primary cover is distinct.
        lead_cover=verified_covers[0]
        match=re.search(r"(?ms)^ "+re.escape(code)+r":\[(.*?)^ \],",quiz_section)
        if not match or match.group(1).count("question:")<2:
            raise ValueError(code+": two meaningful country quiz rounds required")
        keys=re.findall(r"photoKey:'([^']+)'",match.group(1))
        if len(keys)<2 or len(set(keys))<2:
            raise ValueError(code+": both quiz answers need distinct licensed photographs")
        name=COUNTRY_NAMES.get(code)
        if not name:
            # A recognized ISO code must always resolve in the canonical catalog.
            raise ValueError(code+": country not in canonical catalog")
        for key in keys:
            stop=photos.get(key)
            if not stop or stop.get("country")!=name:
                raise ValueError(code+": quiz photograph missing or belongs to wrong country: "+key)
            if stop.get("photoAsset") in verified_covers:
                raise ValueError(code+": portrait cover reused as quiz photograph")
            if not _licensed_photo(stop):
                raise ValueError(code+": quiz photograph license/attribution missing")
        # Older curated postcards predate the famousTourist flag. The
        # exact keys in the reviewed country's guide also certify its
        # independently licensed landmarks, without a blanket exemption.
        guide_photos=set()
        guide_match=re.search(r"(?m)^ "+re.escape(code)+r":\{[^\n]*?photos:\[([^\]]+)\]",guide_section)
        if guide_match:
            guide_photos=set(re.findall(r"'([^']+)'",guide_match.group(1)))
        postcards=[p for key,p in photos.items()
                   if p.get("country")==name and
                   not p.get("coverOnly") and not p.get("quizOnly") and
                   p.get("photoAsset")!=lead_cover and
                   (p.get("famousTourist") is True or key in guide_photos) and
                   _licensed_photo(p)]
        # Older, manually reviewed countries use a validated recognisable
        # landmark list rather than an explicit famousTourist boolean.
        if not postcards:
            raise ValueError(code+": no independent licensed tourist postcard")
        # The postcard must also have the two rich, proofread paragraphs
        # expected by the current optional microtravel reader. A one-line
        # placeholder must never be introduced by the next nightly issue.
        detailed=[p for p in postcards if isinstance(p.get("travelStory"),list)
                  and len(p["travelStory"])==2
                  and all(isinstance(text,str) and len(text.strip())>=70
                          for text in p["travelStory"])]
        if not detailed:
            raise ValueError(code+": curated tourism postcard is missing its detailed essay")
        report[code]={"cover":lead_cover,"quizPhotoKeys":keys,
                      "postcard":detailed[0]["photoAsset"],
                      "quizRounds":match.group(1).count("question:")}
    return report


def _licensed_photo(photo):
    return (isinstance(photo,dict)
            and bool(re.fullmatch(r"assets/travel/[a-z0-9-]+\.jpg",
                                  photo.get("photoAsset","")))
            and photo.get("photo","").startswith("https://thumb.wikimedia.org/wikipedia/commons/thumb/")
            and photo.get("photoPage","").startswith("https://commons.wikimedia.org/wiki/File:")
            and photo.get("licenseUrl","").startswith("https://creativecommons.org/")
            and bool(photo.get("author")) and bool(photo.get("license"))
            and bool(photo.get("photoCaption")))


def verified_country_cover(cover, stop):
    """The exact locally licensed postcard backs every displayed cover field.

    A cover with a missing caption, URL, asset or attribution is not an
    acceptable fallback, even when another cover in that country is valid.
    """
    return (isinstance(cover,dict) and isinstance(stop,dict)
            and all(isinstance(cover.get(key),str) and cover[key].strip()
                    for key in ("asset","url","author","license","place","caption"))
            and _licensed_photo(stop)
            and cover["asset"]==stop.get("photoAsset")
            and cover["url"]==stop.get("photo")
            and cover["caption"]==stop.get("photoCaption")
            and cover["place"]==stop.get("place")
            and cover["author"]==stop.get("author")
            and cover["license"]==stop.get("license")
            and (not cover.get("sourcePage")
                 or cover["sourcePage"]==stop.get("photoPage")))


def main():
    root=Path(__file__).resolve().parent
    issue=json.loads((root/"data/current.json").read_text(encoding="utf-8"))
    result=country_coverage(root,issue["stories"])
    print("Checked complete country portraits, two photo quizzes and independent destinations:",
          ", ".join(result))


if __name__=="__main__":
    main()
