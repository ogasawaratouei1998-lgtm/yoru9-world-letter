#!/usr/bin/env python3
"""Free, attribution-aware Wikimedia Commons candidate search for country drafts.

This is a research queue, NOT a photographic identity verifier or publisher.
A matching file title or CC metadata cannot prove that a photo shows the place.
Only the canonical approved-country release flow can publish new countries.
"""
from __future__ import annotations

import argparse
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
# Automatically discover every future editorial batch without code edits.
# Historical batches with all countries already approved and no photo-search
# terms remain archived, not silently reintroduced into the research queue.
BATCH_GLOB = "country-expansion-batch-*.json"
API = "https://commons.wikimedia.org/w/api.php"
LICENSES = {
    "CC BY-SA 4.0", "CC BY 4.0", "CC BY-SA 3.0", "CC BY 3.0",
    "CC BY-SA 2.0", "CC BY 2.0", "CC0 1.0",
}
# Manual *search vocabulary*, not assertions about any returned image.
LEGACY_SEARCH = {
    "ID": ("Borobudur Indonesia landscape", "Borobudur temple Indonesia", "Prambanan temple Indonesia"),
    "VN": ("Hoi An Vietnam street", "Hoi An Ancient Town Vietnam", "Ha Long Bay Vietnam"),
    "ZA": ("Cape Town South Africa landscape", "Robben Island South Africa", "Cape Floral Region South Africa"),
    "KE": ("Lamu Kenya old town", "Lamu old town Kenya", "Fort Jesus Mombasa Kenya"),
    "MA": ("Fes Morocco medina", "Medina of Fez Morocco", "Ait Ben Haddou Morocco"),
    "NO": ("Bergen Norway landscape", "Bryggen Bergen Norway", "Geirangerfjord Norway"),
    "CL": ("Valparaiso Chile skyline", "Historic Quarter Valparaiso Chile", "Rapa Nui Easter Island Chile"),
    "PE": ("Cusco Peru skyline", "Machu Picchu Peru", "City of Cuzco Peru"),
}


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, value):
        self.parts.append(value)


def plain(value):
    if not isinstance(value, str):
        return ""
    parser = _PlainText()
    parser.feed(value)
    return re.sub(r"\s+", " ", html.unescape("".join(parser.parts))).strip()


def metadata_value(info, name):
    item = info.get("extmetadata", {}).get(name, {})
    return item.get("value", "") if isinstance(item, dict) else ""


def valid_candidate(page):
    """Accept metadata-complete CC JPEGs for human visual checking only."""
    info = (page.get("imageinfo") or [{}])[0]
    if not isinstance(info, dict):
        return None
    title = page.get("title", "")
    if not isinstance(title, str) or not title.startswith("File:"):
        return None
    if info.get("mime") != "image/jpeg":
        return None
    if info.get("width", 0) < 800 or info.get("height", 0) < 500:
        return None
    license_name = plain(metadata_value(info, "LicenseShortName"))
    license_url = metadata_value(info, "LicenseUrl")
    author = plain(metadata_value(info, "Artist"))
    if license_name not in LICENSES or not author or len(author) > 500:
        return None
    parsed = urlparse(license_url)
    if parsed.scheme != "https" or parsed.hostname != "creativecommons.org":
        return None
    photo_url = info.get("url", "")
    photo_page = info.get("descriptionurl", "")
    for address, required in ((photo_url, "upload.wikimedia.org"), (photo_page, "commons.wikimedia.org")):
        parsed = urlparse(address)
        if parsed.scheme != "https" or parsed.hostname != required:
            return None
    # Metadata proves *attribution* only; image identity is explicitly not approved.
    return {
        "file": title,
        "commonsPage": photo_page,
        "original": photo_url,
        "preview": info.get("thumburl", ""),
        "author": author,
        "license": license_name,
        "licenseUrl": license_url,
        "dimensions": [info["width"], info["height"]],
        "description": plain(metadata_value(info, "ImageDescription"))[:500],
        "metadataChecked": True,
        "placeVisuallyVerified": False,
        "publicationEligible": False,
    }


def fetch_commons(query, timeout=18):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 18,
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 600,
        "format": "json",
        "formatversion": 2,
    }
    req = Request(
        API + "?" + urlencode(params),
        headers={"User-Agent": "Yoru9CountryEditorialResearch/1.0 (https://github.com/ogasawaratouei1998-lgtm/yoru9-world-letter; contact via GitHub issues)",
                 "Accept": "application/json"},
    )
    with urlopen(req, timeout=timeout) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or "error" in payload:
        raise ValueError("Commons search returned an error")
    return payload.get("query", {}).get("pages", [])


def draft_queries(root=ROOT):
    """Produce independent cover and two-stop searches for each queued country."""
    seen = set()
    canonical = json.loads((Path(root) / "country-content.json").read_text(encoding="utf-8"))
    files = sorted(Path(root).glob(BATCH_GLOB))
    if not files:
        raise ValueError("No country expansion batch files found")
    for batch_file in files:
        batch = json.loads(batch_file.read_text(encoding="utf-8"))
        if batch.get("status") != "pending_photos_not_public":
            raise ValueError("Unexpected public draft batch: " + batch_file.name)
        for code, country in batch["countries"].items():
            if code in seen:
                raise ValueError("Duplicate active draft country: " + code)
            seen.add(code)
            # Draft-source research is independent of publication state. This
            # also refreshes the original photograph provenance record after a
            # country has already been promoted, without changing approval.
            if code not in canonical["countries"]:
                raise ValueError("Unknown ISO location: " + code)
            if len(country.get("travelDrafts", [])) != 2:
                raise ValueError("Unfinished country draft: " + code)
            if code in LEGACY_SEARCH:
                terms = LEGACY_SEARCH[code]
            else:
                terms = (country.get("coverCommonsSearch", ""),
                         *(stop.get("commonsSearch", "") for stop in country["travelDrafts"]))
            if len(terms) != 3 or not all(isinstance(t, str) and len(t.strip()) >= 8 for t in terms):
                if canonical["countries"][code]["status"] == "approved":
                    # Historical approved-only batches predate this photo
                    # research schema; they do not need new candidate scans.
                    continue
                raise ValueError("Missing country-specific search vocabulary: " + code)
            labels = ("cover", *(stop["place"] for stop in country["travelDrafts"]))
            for idx, (label, query) in enumerate(zip(labels, terms)):
                row = {"countryCode": code, "country": country["name"],
                       "role": "cover" if idx == 0 else "quizAndTravel",
                       "place": label, "searchQuery": query}
                if (country.get("portrait") or {}).get("sourceReviewStatus") == "independent_claim_review_required":
                    row["firstDraftSourceReviewRequired"] = True
                    if idx:
                        row["referencePageCandidate"] = country["travelDrafts"][idx-1].get("sourceUrl")
                yield row


def generate_report(root=ROOT, limit=3, fetch=fetch_commons, sleep_seconds=1.0):
    reports = []
    throttled = False
    for task in draft_queries(root):
        result = dict(task, candidates=[], status="no_matching_metadata", manualVisualReviewRequired=True)
        if throttled:
            result["status"] = "rate_limited_deferred"
            reports.append(result)
            continue
        try:
            items = fetch(task["searchQuery"])
            seen = set()
            for page in items:
                candidate = valid_candidate(page)
                if candidate and candidate["commonsPage"] not in seen:
                    result["candidates"].append(candidate)
                    seen.add(candidate["commonsPage"])
                    if len(result["candidates"]) >= limit:
                        break
        except HTTPError as exc:
            result["status"] = "search_failed"
            result["errorType"] = type(exc).__name__
            result["httpStatus"] = exc.code
            if exc.code in (429, 503):
                throttled = True
        except (URLError, TimeoutError, ValueError, OSError) as exc:
            result["status"] = "search_failed"
            result["errorType"] = type(exc).__name__
        if result["candidates"]:
            result["status"] = "metadata_candidates_only"
        reports.append(result)
        if sleep_seconds:
            time.sleep(sleep_seconds)
    return {
        "version": 1,
        "rule": "No photo or country is automatically approved. A candidate requires visual confirmation of the exact location, local JPEG identity and license compliance.",
        "searchCount": len(reports),
        "countries": sorted(set(r["countryCode"] for r in reports)),
        "withMetadataCandidates": sum(bool(r["candidates"]) for r in reports),
        "failedSearches": sum(r["status"] == "search_failed" for r in reports),
        "deferredSearches": sum(r["status"] == "rate_limited_deferred" for r in reports),
        "results": reports,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=Path("reports/country-photo-candidates.json"))
    parser.add_argument("--limit", type=int, choices=range(1, 9), default=3)
    args = parser.parse_args()
    report = generate_report(args.root, args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = ("Country image candidates: " + str(len(report["countries"])) +
               " countries / " + str(report["searchCount"]) +
               " searches; " + str(report["withMetadataCandidates"]) +
               " searches with metadata candidates; " +
               str(report["failedSearches"]) + " search errors; " +
               str(report["deferredSearches"]) + " deferred after throttling.\n" +
               "No country approved; no photograph accepted without visual and local-JPEG verification.\n")
    print(summary)
    import os
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
            stream.write("### Candidate photos (not published)\n\n" + summary)


if __name__ == "__main__":
    main()
