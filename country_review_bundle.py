#!/usr/bin/env python3
"""Rank research records and fetch bounded JPEG previews for editorial review.

A downloaded preview, license metadata or unique assignment does not verify
where a photo was taken, prove historical facts, or approve any content.
Never write to country-content.json or the published site.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from itertools import product
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from country_content import _commons_identity

ROOT = Path(__file__).resolve().parent
MAX_PREVIEW_BYTES = 3_000_000
HOSTS = {"upload.wikimedia.org", "thumb.wikimedia.org"}

def valid_preview_url(url):
    try:
        u = urlsplit(url)
        return (u.scheme == "https" and u.hostname in HOSTS and not u.username
                and not u.password and u.port in (None, 443)
                and u.path.startswith("/wikipedia/commons/"))
    except (TypeError, ValueError):
        return False

class WikimediaRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not valid_preview_url(newurl):
            raise ValueError("Unsafe image redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def candidate_identity(candidate):
    identities = [_commons_identity(candidate.get(k))
                  for k in ("commonsPage", "original", "preview")]
    if (not candidate.get("metadataChecked") or not candidate.get("author")
            or not candidate.get("license") or not candidate.get("licenseUrl")
            or not valid_preview_url(candidate.get("preview"))):
        return None
    return identities[0] if all(identities) and len(set(identities)) == 1 else None

def make_queue(report, canonical):
    grouped = defaultdict(dict)
    pending = {c for c, row in canonical.items() if row["status"] == "pending"}
    for row in report["results"]:
        code, slot = row["countryCode"], row["slot"]
        if code not in pending:
            continue
        if slot not in (0, 1, 2) or slot in grouped[code]:
            raise ValueError("Invalid or duplicate research slot")
        grouped[code][slot] = row
    queued = []
    for code in sorted(pending):
        slots = grouped.get(code, {})
        drafted = bool((canonical[code].get("portrait") or {}).get("body"))
        existing = len(slots) == 3 and all(r.get("origin") == "existing_draft" for r in slots.values())
        choices = [[c for c in slots.get(i, {}).get("candidates", [])
                    if candidate_identity(c)][:3] for i in range(3)]
        selection = next((combo for combo in product(*choices)
                          if len({candidate_identity(c) for c in combo}) == 3), None)
        queued.append({
            "code": code, "name": canonical[code]["name"],
            "portraitDraftExists": drafted, "twoTravelDraftsInResearch": existing,
            "candidateCounts": [len(c) for c in choices],
            "threeDistinctCandidates": selection is not None,
            "slots": [{"slot": i, "place": slots.get(i, {}).get("place"),
                       "searchStatus": slots.get(i, {}).get("status", "not_reported"),
                       "candidate": selection[i] if selection else None,
                       "visualVerified": False, "previewStatus": "not_attempted"}
                      for i in range(3)],
            "publicationEligible": False})
    queued.sort(key=lambda r: (not (r["threeDistinctCandidates"] and r["twoTravelDraftsInResearch"] and r["portraitDraftExists"]),
                               not r["threeDistinctCandidates"], not r["portraitDraftExists"],
                               -sum(n > 0 for n in r["candidateCounts"]), r["code"]))
    return queued

def download_preview(url):
    if not valid_preview_url(url):
        raise ValueError("Invalid preview URL")
    req = Request(url, headers={"User-Agent": "Yoru9EditorialReview/1.0 (https://github.com/ogasawaratouei1998-lgtm/yoru9-world-letter; contact via GitHub issues)", "Accept": "image/jpeg"})
    with build_opener(WikimediaRedirects()).open(req, timeout=12) as response:
        if response.headers.get_content_type() != "image/jpeg":
            raise ValueError("Preview is not JPEG")
        data = response.read(MAX_PREVIEW_BYTES + 1)
    if len(data) > MAX_PREVIEW_BYTES or not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
        raise ValueError("Preview size or JPEG markers invalid")
    return data

def write_bundle(queue, output, limit, fetch=download_preview, sleep_seconds=1.0):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    countries = [r for r in queue if r["threeDistinctCandidates"]][:limit]
    throttled = False
    for row in countries:
        if not re.fullmatch(r"[A-Z]{2}", row["code"]):
            raise ValueError("Invalid country code")
        for slot in row["slots"]:
            candidate = slot["candidate"]
            if throttled:
                slot["previewStatus"] = "rate_limited_deferred"
                continue
            try:
                data = fetch(candidate["preview"])
                dest = row["code"] + "-" + str(slot["slot"]) + ".jpg"
                (output / dest).write_bytes(data)
                slot.update(previewFile=dest, previewStatus="downloaded_unreviewed")
            except HTTPError as exc:
                slot["previewStatus"] = "http_error_" + str(exc.code)
                if exc.code in (429, 503):
                    throttled = True
            except (URLError, OSError, ValueError, TimeoutError) as exc:
                slot["previewStatus"] = type(exc).__name__
            if sleep_seconds:
                time.sleep(sleep_seconds)
    summary = {
        "pendingCountries": len(queue),
        "countriesWithThreeDistinctMetadataCandidates": sum(r["threeDistinctCandidates"] for r in queue),
        "draftedCountriesWithThreeDistinctMetadataCandidates": sum(r["threeDistinctCandidates"] and r["portraitDraftExists"] and r["twoTravelDraftsInResearch"] for r in queue),
        "countriesSelectedForPreview": len(countries),
        "downloadedUnreviewedPreviews": sum(s["previewStatus"] == "downloaded_unreviewed" for r in countries for s in r["slots"]),
        "fullyDownloadedCountries": sum(all(s["previewStatus"] == "downloaded_unreviewed" for s in r["slots"]) for r in countries),
        "publicationEligible": False,
    }
    (output / "review-index.json").write_text(json.dumps({"summary": summary, "queue": queue}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--limit", type=int, choices=range(1, 21), default=12)
    args = p.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    canonical = json.loads((ROOT / "country-content.json").read_text(encoding="utf-8"))["countries"]
    summary = write_bundle(make_queue(report, canonical), args.output, args.limit)
    print(json.dumps(summary, ensure_ascii=False))
    import os
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
            stream.write("### Editorial review bundle — not published\n\n")
            for key, value in summary.items():
                stream.write(f"- {key}: {value}\n")

if __name__ == "__main__":
    main()
