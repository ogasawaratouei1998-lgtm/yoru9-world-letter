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

# Exact Commons originals rejected after inspecting the downloaded JPEG.
# A rejection is scoped to the country and slot; it does not allege a license
# problem or prohibit the photograph in other editorial contexts.
VISUAL_REJECTIONS = {
    ("KE", 0): {"Lamu Pharmacy.jpg": "Shop window and merchandise, not an informative country landscape."},
    ("BD", 1): {"A view from the Mosque (8540808429).jpg": "View through a dark arch; the mosque complex itself is not shown."},
    ("IQ", 1): {"Assur stuck.jpg": "Isolated decorated object instead of a view of the archaeological site."},
    ("LB", 0): {"The landscape of Lebanon with its famous tree cedar of Lebanon (FL63289561).jpg": "Portrait-oriented archival photograph, unsuitable for the landscape cover."},
    ("LB", 2): {"Lebanon mountains from near Maqial el Qalaa.jpg": "Mountain road without the Baalbek archaeological monuments."},
    ("LY", 0): {"The Romantic Landscape - geograph.org.uk - 1803291.jpg": "Unrelated geograph UK landscape, not Libya."},
    ("MM", 2): {"Hanlin - Pyu Ancient City.JPG": "Heritage marker rather than the archaeological remains."},
    ("MU", 1): {"Aapravasi ghat museum, Port Louis, Mauritius.jpg": "Entrance sign dominates the view; insufficient historical building context."},
    ("NE", 0): {"Aso Rock 52 - landscape in Abuja, Nigeria (2026).jpg": "Abuja is in Nigeria, not Niger."},
    ("CR", 0): {"1999 casona santa rosa Panorama.jpg": "Historical pre-fire house panorama; too narrow for the present-day country cover."},
    ("CR", 1): {"Santa Rosa guanacaste.jpg": "Very narrow pasture panorama; insufficient visual context for the conservation-area story."},
    ("KE", 1): {
        "Lamu Pharmacy.jpg": "Close-up of pharmacy merchandise, not a useful depiction of the historic townscape.",
        "Lamu Pharmacy2021.jpg": "Second pharmacy interior showing shelves of goods rather than the historic townscape.",
    },
    ("MU", 0): {"Hausdülmen -- 2014 -- 5879.jpg": "Photograph of a German landscape, not Mauritius.",
                 "Landscape near Les Mariannes, Mauritius, 2007-09-09.jpg": "Five-to-one panorama, too narrow for the cover."},
    ("ZA", 0): {"Cape Town (ZA), Cape Point Nature Reserve, Ausblick -- 2024 -- 3377.jpg": "Deliberate zoom effect obscures the natural landscape; unsuitable for a documentary country cover."},
    ("ZA", 2): {"Cape Floral Region Protected Areas map.jpg": "Annotated map, not an actual landscape photograph of the protected region."},
}

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
        choices, rejected = [], []
        for i in range(3):
            allowed, omitted = [], []
            seen = set()
            for candidate in slots.get(i, {}).get("candidates", []):
                identity = candidate_identity(candidate)
                if not identity or identity in seen:
                    continue
                seen.add(identity)
                reason = VISUAL_REJECTIONS.get((code, i), {}).get(identity)
                if reason:
                    omitted.append({"originalIdentity": identity, "reason": reason})
                else:
                    allowed.append(candidate)
            choices.append(allowed[:3])
            rejected.append(omitted)
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
                       "visualRejections": rejected[i],
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
