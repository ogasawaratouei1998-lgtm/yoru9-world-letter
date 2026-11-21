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


def ready_country_codes(root: Path):
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
    for code in sorted(registry):
        if not isinstance(code,str) or len(code)!=2 or not code.isupper():
            raise ValueError("Invalid country identifier in photo registry")
        try:
            country_coverage(root,[{"country":code}])
        except (KeyError,ValueError,TypeError,OSError,IndexError):
            # Keep only a code, never article text or source details in logs.
            incomplete[code]="incomplete_reader_assets"
        else:
            ready.add(code)
    return frozenset(ready),incomplete


def select_ready_stories(stories, root: Path):
    """Keep source-reviewed stories in their existing order; don't fabricate.

    A cross-border article is usable only if *all* countries are prepared.
    Return country codes/counts for a separate editorial coverage queue.
    """
    ready,incomplete=ready_country_codes(root)
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


if __name__=="__main__":
    root=Path(__file__).resolve().parent
    ready,incomplete=ready_country_codes(root)
    print(json.dumps({"countryCodesReady":sorted(ready),
                      "incompleteCountryCodes":sorted(incomplete),
                      "preparedCountries":len(ready),
                      "totalReportingLocations":196},
                     ensure_ascii=False,sort_keys=True))
