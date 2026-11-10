#!/usr/bin/env python3
"""Collect unverified news leads from GDELT DOC 2.0; not publication-ready news."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
import json
import re
import sys
import time

API = "https://api.gdeltproject.org/api/v2/doc/doc"
QUERIES = [
    '("accidentally ordered" OR "wrong order")',
    '("wrong destination" OR "mistakenly sent")',
    '("blunder" OR "mix-up")',
    '("accidental email" OR "reply all")',
    '("ordered by mistake" OR "wrong sign")',
]
EXCLUDE = re.compile(r'\b(killed|murder|fatal|death|died|suicide|rape|shooting|injured|hospitalized|war|bombing|disaster)\b', re.I)

def safe_url(raw):
    try:
        p = urlsplit(raw)
        return p._replace(fragment="").geturl() if p.scheme == "https" and p.hostname and not p.username and not p.password and p.port in (None, 80, 443) else None
    except (ValueError, TypeError):
        return None

def main():
    articles, errors, seen = [], [], set()
    for index, query in enumerate(QUERIES):
        if index:
            time.sleep(5.2)
        params = {"query": query, "mode": "ArtList", "format": "json", "maxrecords": 30, "timespan": "7d", "sort": "DateDesc"}
        url = API + "?" + urlencode(params)
        try:
            request = Request(url, headers={"User-Agent": "Yoru9WorldLetter-NewsLeadCollector/1.0"})
            with urlopen(request, timeout=30) as response:
                body = json.load(response)
            if not isinstance(body, dict) or not isinstance(body.get("articles"), list):
                raise ValueError("Invalid GDELT API response")
            for article in body["articles"]:
                if not isinstance(article, dict):
                    continue
                title = str(article.get("title", "")).strip()
                link = safe_url(str(article.get("url", "")).strip())
                if not title or not link or link in seen or EXCLUDE.search(title):
                    continue
                seen.add(link)
                articles.append({
                    "title": title[:400],
                    "url": link,
                    "domain": str(article.get("domain", ""))[:120],
                    "seendate": str(article.get("seendate", ""))[:30],
                    "sourcecountry": str(article.get("sourcecountry", ""))[:100],
                    "language": str(article.get("language", ""))[:40],
                    "status": "unverified"
                })
                if len(articles) >= 75:
                    break
        except Exception as error:
            errors.append(f"{type(error).__name__}: {error}")
        if len(articles) >= 75:
            break
    if not articles:
        print("No candidates retrieved: " + "; ".join(errors), file=sys.stderr)
        return 1
    result = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "provider": "GDELT DOC 2.0 API (https://www.gdeltproject.org/)",
        "note": "These are unverified headline leads, NOT confirmed facts. Editor must independently verify each original source, dates and harms before publication. No automatic publication.",
        "errors": errors,
        "candidates": articles
    }
    destination = Path("data/candidates.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Collected {len(articles)} unverified leads. Saved for human review only.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
