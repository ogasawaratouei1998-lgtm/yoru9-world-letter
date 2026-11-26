"""Check country-specific reader assets before final editorial selection.

A verified incident in a new country must never be rewritten as a familiar
country or paired with a different country's photographs. This is a readiness
check, not a judgment of source evidence or an approval of an article.
"""
from collections import Counter
import json
from pathlib import Path

from check_country_experience import country_coverage
from country_codes import country_codes


def ready_country_codes(root: Path, day=None):
    """Discover candidates from the runtime photo registry, then fully vet them.

    Do not maintain a parallel hardcoded whitelist: only countries whose
    *actual* portrait, quiz photos, licensed postcard and two-paragraph travel
    feature pass the release validator qualify.
    """
    root=Path(root)
    html=(root/"index.html").read_text(encoding="utf-8")
    prefix="const TODAY_COUNTRY_PHOTOS=Object.freeze("
    rows=[line for line in html.splitlines() if line.startswith(prefix)]
    if len(rows)!=1 or not rows[0].endswith(");"):
        raise ValueError("Country photo registry is missing or malformed")
    registry=json.loads(rows[0][len(prefix):-2])
    if not isinstance(registry,dict):
        raise ValueError("Country photo registry must be a mapping")
    ready=set()
    incomplete={}
    topics=None
    if day is not None:
        from datetime import date
        from audit_country_highlights import missing_topic_dates
        from build_site import validate_country_highlights
        day=date.fromisoformat(day) if isinstance(day,str) else day
        topics=validate_country_highlights(root)['highlights']
    for code in sorted(registry):
        if not isinstance(code,str) or len(code)!=2 or not code.isupper():
            raise ValueError("Invalid country identifier in photo registry")
        try:
            country_coverage(root,[{"country":code}])
        except (KeyError,ValueError,TypeError,OSError,IndexError):
            # Keep only a code, never article text or source details in logs.
            incomplete[code]="incomplete_reader_assets"
        else:
            if topics is not None and missing_topic_dates(topics,code,day,2):
                incomplete[code]='missing_current_country_topics'
            else:
                ready.add(code)
    return frozenset(ready),incomplete



def story_has_prepared_countries(story, ready):
    """Scheduling hint only: draft country is NOT verified before source review."""
    if not isinstance(story,dict):
        return False
    codes=country_codes(story.get("country",""))
    return bool(codes) and all(code in ready for code in codes)


def prioritize_ready_drafts(drafts, ready):
    """Review drafts with ready destinations first, preserving their relative order.

    An AI-written draft country is still an UNVERIFIED claim. This does not
    approve an incident or discard any draft; the original article and
    independent reviewer must confirm its location and event afterwards.
    Cross-border drafts are ready only if every named country is covered.
    The AI fact-review budget is unchanged, avoiding extra free-tier calls.
    """
    return sorted(drafts,key=lambda row:not story_has_prepared_countries(row,ready))


def select_ready_stories(stories, root: Path, day=None):
    """Keep source-reviewed stories in their existing order; don't fabricate.

    A cross-border article is usable only if *all* countries are prepared.
    Return country codes/counts for a separate editorial coverage queue.
    """
    ready,incomplete=ready_country_codes(root,day)
    accepted=[]
    blocked=Counter()
    for story in stories:
        codes=country_codes(story.get("country",""))
        if codes and all(code in ready for code in codes):
            accepted.append(story)
        else:
            for code in codes or ["unrecognized"]:
                if code not in ready:
                    blocked[code]+=1
    return accepted,dict(sorted(blocked.items())),ready,incomplete


def article_country_backlog(stories, root: Path, day):
    """Report enrichment needs after news review; never filter stories."""
    from datetime import date
    from audit_country_highlights import missing_topic_dates
    from build_site import validate_country_highlights
    root=Path(root)
    day=date.fromisoformat(day) if isinstance(day,str) else day
    counts=Counter(code for story in stories
                   for code in set(country_codes(story.get("country",""))))
    try:
        rows=json.loads((root/"country-content.json").read_text(encoding="utf-8"))["countries"]
    except (OSError,ValueError,KeyError,TypeError):
        rows={}
    try:
        topics=validate_country_highlights(root)["highlights"]
    except (OSError,ValueError,KeyError,TypeError):
        topics={}
    ready={code for code in counts if rows.get(code,{}).get("status")=="approved"
           and not missing_topic_dates(topics,code,day,2)}
    return {code:count for code,count in sorted(counts.items()) if code not in ready},ready


if __name__=="__main__":
    root=Path(__file__).resolve().parent
    ready,incomplete=ready_country_codes(root)
    print(json.dumps({"countryCodesReady":sorted(ready),
                      "incompleteCountryCodes":sorted(incomplete),
                      "preparedCountries":len(ready),
                      "totalReportingLocations":196},
                     ensure_ascii=False,sort_keys=True))
