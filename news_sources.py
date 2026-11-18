"""Reviewed publisher RSS source registry and bounded, fault-isolated discovery.

This collects links and headline metadata ONLY. It never verifies or publishes
news. The evidence pipeline must retrieve each publisher's original article
body, check attribution and dates, and pass its editorial safeguards.
"""
from __future__ import annotations

from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import json
import re

REGISTRY_PATH = Path(__file__).resolve().parent / "data/news-source-registry.json"
ALLOWED_FOCUS = {"oddities", "general", "local", "regional", "culture",
                 "sports", "science", "technology"}
ALLOWED_LANGUAGES = {"en", "ja", "ko", "de", "es", "fr", "pt", "ar", "id", "it", "vi", "pl", "tr"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{3,90}$")
ISO_RE = re.compile(r"^[A-Z]{2}$")

# Cheap discovery-only hints. They do NOT classify a report as true, comic or
# geographically verified. Prioritizing them *within each publisher's feed*
# avoids burying a small local mistake under dozens of general headlines.
SMALL_MISSTEP = re.compile(
    r"\b(?:typo|misspell\w*|misprint\w*|mix[- ]?up|by mistake|"
    r"accidentally|mistook|wrong (?:order|address|delivery|recipient|sign|name)|"
    r"wrongly delivered|mistaken identity|"
    r"verwechslung|aus versehen|versehentlich|"
    r"per sbaglio|per errore|sbagli\w*|"
    r"por engano|por error|equivocaci[oó]n|"
    r"par erreur|m[eé]prise|"
    r"salah kirim|tertukar|keliru|"
    r"nh[aầ]m|pomy[lł]k\w*|yanl[iı][sş]|"
    r"실수|착각|오류|잘못)\b|"
    r"誤字|誤記|誤発注|誤配達|誤送信|手違い|勘違い|取り違え|"
    r"خطأ|بالخطأ",
    re.I,
)
GENERAL_MISSTEP = re.compile(
    r"\b(?:mistake|blunder|error|fiasco|confusion|mishap|"
    r"fehler|panne|erreur|errore|erro|falha|"
    r"confus[aã]o|equ[ií]voc\w*|kesalahan|hata)\b|"
    r"間違|失敗|ミス|착오",
    re.I,
)
DISTRESS_HEADLINE = re.compile(
    r"\b(?:death|died|killed|murder|fatal|shooting|war|rape|"
    r"injured|hospitalized|suicide|bombing|abuse|harassment)\b|"
    r"死亡|殺害|負傷|災害|戦争|自殺|銃撃|死者|犠牲者",
    re.I,
)


def provisional_headline_priority(title):
    """Order unverified leads, never approve or infer an incident's country."""
    value=str(title or "")
    if DISTRESS_HEADLINE.search(value):
        return 3
    if SMALL_MISSTEP.search(value):
        return 0
    if GENERAL_MISSTEP.search(value):
        return 1
    return 2



def host_matches(domain, expected):
    """Restrict candidate article links to the registered publisher.

    RSS feeds may be hosted at a separate distribution subdomain. The story
    link must still point back to the original outlet, not an RSS syndicator.
    """
    if not isinstance(expected, str):
        return False
    d, e = str(domain or "").lower().removeprefix("www."), expected.lower().removeprefix("www.")
    return bool(d and e and (d == e or d.endswith("." + e)))


def source_registry(path=REGISTRY_PATH):
    """Validate schema and reject unsafe, duplicate or malformed feed entries."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("feeds"), list):
        raise ValueError("invalid source registry version or feed list")
    result, seen_ids, seen_urls = [], set(), set()
    for x in data["feeds"]:
        if not isinstance(x, dict):
            raise ValueError("invalid source entry")
        keys=("id","name","url","market","language","focus","site")
        if any(not isinstance(x.get(k),str) or not x[k].strip() for k in keys):
            raise ValueError("source registry entry missing fields")
        url=urlsplit(x["url"])
        site=x["site"].lower()
        if (not ID_RE.fullmatch(x["id"]) or x["id"] in seen_ids or
                x["url"] in seen_urls or url.scheme!="https" or
                not url.hostname or url.username or url.password or url.port not in (None,443) or
                url.fragment or len(x["url"])>600 or
                not ISO_RE.fullmatch(x["market"]) or
                x["language"] not in ALLOWED_LANGUAGES or
                x["focus"] not in ALLOWED_FOCUS or
                "://" in site or "/" in site or ":" in site or
                site.startswith(".") or site.endswith(".") or "." not in site or
                len(x["name"])>100):
            raise ValueError("invalid/duplicate or unsafe source registry entry")
        seen_ids.add(x["id"])
        seen_urls.add(x["url"])
        result.append(x)
    return result


def fetch_registry_feeds(*, sources=None, fetch, parse, max_workers=10, per_feed=35, report_path=None):
    """Fetch distinct publisher feeds concurrently with per-source isolation.

    Handles unavailable/retired feeds without excluding good publications.
    Counters distinguish *attempts* from genuinely usable news leads.
    """
    if sources is None:
        sources=source_registry()
    if not 1 <= max_workers <= 12:
        raise ValueError("bad concurrency")
    if not 1 <= per_feed <= 50:
        raise ValueError("bad per-feed limit")
    results=[[] for _ in sources]
    health=[None] * len(sources)

    def attempt(item):
        try:
            # Bounded network request: an unavailable feed must not stall the
            # entire daily/monthly publication or lower evidence standards.
            body=fetch(item["url"], timeout=8)
            items=parse(body, item["name"]+" publisher RSS",
                        language=item["language"],
                        sourcecountry=item["market"])
            leads=[]
            for lead in items[:per_feed]:
                href=lead.get("url", "")
                parts=urlsplit(href)
                if (parts.scheme!="https" or not parts.hostname or parts.username or
                        parts.password or parts.port not in (None,443) or
                        not host_matches(parts.hostname,item["site"])):
                    continue
                leads.append({**lead,"focus":item["focus"],
                              "registeredSource":item["id"],
                              "sourcecountry":item["market"]})
            return leads, "ok" if leads else "empty_or_unusable"
        except Exception as exc:
            # Invalid feeds, redirects, XML and network errors are isolated.
            # We log the error type only, not untrusted RSS payloads.
            return [], type(exc).__name__

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures={pool.submit(attempt,source):i for i,source in enumerate(sources)}
        for future in as_completed(futures):
            i=futures[future]
            results[i],health[i]=future.result()
    # Preserve market/outlet round-robin while moving clearly relevant,
    # source-dated human mistakes to the front of EACH publisher's queue.
    # This does not drop unrelated headlines or assign a story location.
    # Global budget truncation previously buried rare local mishaps in
    # general-news RSS lists, leaving the AI with few draftable sources.
    for group in results:
        group.sort(key=lambda lead: (
            provisional_headline_priority(lead.get("title")),
            not bool(lead.get("seendate")),
        ))
    counts=Counter(health)
    # Group source health by *publisher* market, never reported event country.
    market_health={}
    for i,src in enumerate(sources):
        row=market_health.setdefault(src["market"],{"attempted":0,"usable":0,"links":0})
        row["attempted"]+=1
        row["usable"]+=int(health[i]=="ok")
        row["links"]+=len(results[i])
    if report_path is not None:
        # Diagnostic artifact, never part of the public site or article data.
        # Feed errors are descriptive only and must never authorize a story.
        report={"status":"unverified-feed-health",
                "checkedAt":datetime.now(timezone.utc).isoformat(),
                "attempted":len(sources),
                "usable":counts.get("ok",0),
                "marketHealth":dict(sorted(market_health.items())),
                "marketNote":"Publisher markets are NOT verified event locations.",
                "feeds":[{"id":src["id"],"name":src["name"],
                          "market":src["market"],"focus":src["focus"],
                          "status":health[i],
                          "rawPublisherLeads":len(results[i])}
                         for i,src in enumerate(sources)]}
        dest=Path(report_path)
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",
                        encoding="utf-8")
    print("Publisher RSS registry:",len(sources),"attempted,",
          counts.get("ok",0),"usable,",
          counts.get("empty_or_unusable",0),"empty/stale/unusable,",
          len(sources)-counts.get("ok",0)-counts.get("empty_or_unusable",0),
          "fetch/parser failures,",
          sum(len(group) for group in results),"raw publisher leads",
          flush=True)
    # Round-robin BOTH publisher markets and individual outlets within each
    # market. The earlier implementation placed the first 18-35 items from the
    # first outlet ahead of all other outlets in that country. That exhausted
    # a market's slice before its local competitors could ever be seen.
    #
    # This is unverified source exploration only; a publisher's market is NOT
    # the location of any event in the article it reports.
    focus_rank={"oddities":0,"local":1,"sports":2,"culture":3,
                "regional":4,"technology":5,"general":6,"science":7}
    markets={}
    for index,(source,group) in enumerate(zip(sources,results)):
        if group:
            markets.setdefault(source["market"],[]).append(
                (focus_rank.get(source["focus"],8),index,deque(group)))
    markets={market:deque(deq for _,_,deq in sorted(groups,key=lambda x:(x[0],x[1])))
             for market,groups in markets.items()}
    ordered=[]
    while markets:
        for market in list(markets):
            outlets=markets[market]
            outlet=outlets.popleft()
            ordered.append(outlet.popleft())
            if outlet:
                outlets.append(outlet)
            if not outlets:
                del markets[market]
    return ordered
