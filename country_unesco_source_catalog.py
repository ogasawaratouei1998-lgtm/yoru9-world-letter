#!/usr/bin/env python3
"""Inventory official UNESCO World Heritage sources for ALL pending countries.

This is a free, read-only preparation report. A place appearing under a country
in UNESCO XML does not approve a portrait, tourist essay, photograph or news.
Never manufacture substitute UNESCO sites for countries without any entries.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
FEED = "https://whc.unesco.org/en/list/xml/"
MAX_BYTES = 18 * 1024 * 1024


def clean_text(value):
    return " ".join((value or "").split())


def collect_sites(xml_data):
    root = ET.fromstring(xml_data)
    rows = [element for element in root.iter()
            if element.tag.rsplit("}", 1)[-1].lower() == "row"]
    if not rows:
        raise ValueError("The official UNESCO feed has no property rows")
    found = {}
    for row in rows:
        fields = {child.tag.rsplit("}", 1)[-1].lower(): clean_text(child.text)
                  for child in row}
        number = fields.get("id_number", "")
        name = fields.get("site") or fields.get("name_en") or ""
        code_field = fields.get("iso_code", "")
        if not number.isdigit() or not name or not code_field:
            continue
        record = {"name": name, "sourceUrl": "https://whc.unesco.org/en/list/" + str(int(number)) + "/"}
        year=fields.get("date_inscribed","")
        if re.fullmatch(r"(?:19|20)[0-9]{2}",year):
            record["inscribedYear"]=int(year)
        for iso in re.findall(r"(?<![A-Za-z])[A-Za-z]{2}(?![A-Za-z])", code_field):
            code = iso.upper()
            by_country = found.setdefault(code, {})
            by_country[record["sourceUrl"]] = record
    return {code: sorted(items.values(), key=lambda item: item["name"])
            for code, items in found.items()}


def build_inventory(root, xml_data):
    canonical = json.loads((Path(root) / "country-content.json").read_text(encoding="utf-8"))
    catalog = json.loads((Path(root) / "country-catalog.json").read_text(encoding="utf-8"))
    if len(catalog) != 196:
        raise ValueError("Unexpected canonical geography size")
    grouped = collect_sites(xml_data)
    results = {}
    for country in catalog:
        code = country["code"]
        editorial = canonical["countries"][code]
        if editorial["status"] == "approved":
            continue
        available = grouped.get(code, [])
        results[code] = {
            "name": country["name"],
            "editorialStatus": "pending",
            "unescoRegisteredSiteCount": len(available),
            "sampleSourcePages": available[:5],
            "sourceFound": bool(available),
            "portraitApproved": False,
            "photographApproved": False,
        }
    return {
        "version": 1,
        "observedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": FEED,
        "catalogCount": len(catalog),
        "pendingCount": len(results),
        "pendingWithUNESCOSites": sum(row["sourceFound"] for row in results.values()),
        "pendingWithoutUNESCOSites": sorted(code for code, row in results.items()
                                           if not row["sourceFound"]),
        "note": "Source candidates only. Site identity, text, images and licenses must pass independent review. No approval status changed.",
        "countries": results,
    }


def download_feed():
    request = Request(FEED, headers={
        "Accept": "application/xml,text/xml;q=0.9",
        "User-Agent": "Yoru9OfficialHeritageInventory/1.0 (https://github.com/ogasawaratouei1998-lgtm/yoru9-world-letter; via GitHub issues)",
    })
    with urlopen(request, timeout=40) as response:
        data = response.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise ValueError("UNESCO XML size is empty or outside permitted limit")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=Path("reports/country-official-source-inventory.json"))
    args = parser.parse_args()
    inventory = build_inventory(args.root, download_feed())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("UNESCO source inventory: " + str(inventory["pendingWithUNESCOSites"]) +
          "/" + str(inventory["pendingCount"]) +
          " pending countries with registered properties; no approvals modified.")
    import os
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
            stream.write("### UNESCO source inventory (not published)\n\n" +
                         str(inventory["pendingWithUNESCOSites"]) + "/" +
                         str(inventory["pendingCount"]) + " pending country source records.\n")


if __name__ == "__main__":
    main()
