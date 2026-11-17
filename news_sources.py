"""Reviewed publisher RSS source registry and bounded, fault-isolated discovery.

This collects links and headline metadata ONLY. It never verifies or publishes
news. The evidence pipeline must retrieve each publisher's original article
body, check attribution and dates, and pass its editorial safeguards.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit
import json
import re

REGISTRY_PATH = Path(__file__).resolve().parent / "data/news-source-registry.json"
ALLOWED_FOCUS = {"oddities", "general", "local", "regional", "culture",
                 "sports", "science", "technology"}
ALLOWED_LANGUAGES = {"en", "ja", "ko", "de", "es", "fr", "pt", "ar", "id"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{3,90}$")
ISO_RE = re.compile(r"^[A-Z]{2}$")


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


def fetch_registry_feeds(*, sources=None, fetch, parse, max_workers=10, per_feed=35):
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
    counts=Counter(health)
    print("Publisher RSS registry:",len(sources),"attempted,",
          counts.get("ok",0),"usable,",
          counts.get("empty_or_unusable",0),"empty/stale/unusable,",
          len(sources)-counts.get("ok",0)-counts.get("empty_or_unusable",0),
          "fetch/parser failures,",
          sum(len(group) for group in results),"raw publisher leads",
          flush=True)
    # Source order stays deterministic despite parallel fetching. Keeping the
    # curated odd-news feeds first improves gentle-mishap recall.
    return [item for group in results for item in group]
