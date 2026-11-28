#!/usr/bin/env python3
"""Plan research for every pending country, not just drafted batches.

An inventory entry, search term or Commons metadata is NEVER editorial approval.
No canonical data, reader export or public photo is written.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
import unicodedata
from urllib.error import HTTPError, URLError

from country_photo_candidates import draft_queries, fetch_commons, valid_candidate
from country_unesco_source_catalog import build_inventory, download_feed

ROOT = Path(__file__).resolve().parent
SHARDS = 8

# Bounded alternative search vocabulary for empty results in the 2026-11-22
# all-country research artifact. These are search terms only, not place verification.
DRAFT_SEARCH_ALTERNATIVES = {
    ("AL", 0): "Skanderbeg Square Tirana",
    ("AM", 0): "Yerevan Republic Square",
    ("AM", 1): "Haghpat Monastery",
    ("BO", 0): "La Paz Bolivia city",
    ("BO", 2): "Potosi Bolivia historic city",
    ("BW", 0): "Chobe River Botswana",
    ("GH", 1): "Besease shrine",
    ("HN", 0): "Comayagua Cathedral",
    ("HN", 1): "Copan ruins",
    ("HN", 2): "Rio Platano Honduras",
    ("KZ", 0): "Turkestan Kazakhstan",
    ("KZ", 1): "Mausoleum of Khoja Ahmed Yasawi",
    ("KZ", 2): 'Tanbaly petroglyphs Kazakhstan -"Tamgaly-Tas" -Buddha',
    ("MT", 0): "Mdina Malta",
    ("MT", 2): "Hagar Qim temple",
    ("MY", 0): "Penang shophouses",
    ("UZ", 0): "Samarkand Registan panorama",
    ("UZ", 2): "Bukhara Kalyan minaret",
}
# The latest results for these searches were the wrong subject despite
# containing the named site in their metadata. Use a more specific subject.
DRAFT_SEARCH_REFINEMENTS = {
    ("ZA", 0): 'Cape Town skyline Table Mountain South Africa panorama -penguins -birds',
    ("ZA", 1): 'Robben Island historic prison courtyard South Africa -road',
    ("ZA", 2): 'Cape Floral Region fynbos protea botanical landscape South Africa -map',
    ("KZ", 2): 'Tamgaly Chu Ili petroglyphs Kazakhstan -"Tamgaly-Tas" -Buddha',
    ("BW", 0): '"Chobe River" Botswana landscape -Anhinga -bird',
    ("KE", 0): 'Lamu Kenya waterfront old town -pharmacy',
    ("MY", 2): '"Deer Cave" Mulu Sarawak entrance cave -skink -lizard -planarian -repairs',
    ("HN", 2): '"Río Plátano Biosphere Reserve" Honduras rainforest -Patuca',
    ("TN", 2): '"Antonine Baths" Carthage -Dougga',
}


# Unverified place-name research leads, not source evidence or editorial copy.
# These cover the 58 countries without a portrait as of 2026-11-25.
UNDRAFTED_PLACE_LEADS = {
    "BI": ("Rusizi National Park", "Gishora Drum Sanctuary"),
    "BS": ("Exuma Cays Land and Sea Park", "Fort Fincastle Nassau"),
    "BB": ("Historic Bridgetown and its Garrison", "Harrison's Cave"),
    "BN": ("Omar Ali Saifuddien Mosque", "Ulu Temburong National Park"),
    "BT": ("Paro Taktsang", "Punakha Dzong"),
    "CG": ("Odzala-Kokoua National Park", "Basilique Sainte-Anne Brazzaville"),
    "KM": ("Mount Karthala", "Old Friday Mosque Moroni"),
    "CV": ("Cidade Velha Santiago", "Pico do Fogo"),
    "DJ": ("Lake Assal", "Day Forest National Park"),
    "DM": ("Morne Trois Pitons National Park", "Scotts Head Dominica"),
    "ER": ("Asmara modernist architecture", "Massawa old town"),
    "FM": ("Nan Madol Pohnpei", "Lelu ruins Kosrae"),
    "GN": ("Fouta Djallon", "Mount Nimba Guinea"),
    "GW": ("Bijagós Archipelago", "Bolama historic town"),
    "GQ": ("Pico Basilé", "Malabo Cathedral"),
    "GD": ("Grand Etang National Park", "Fort George St George's Grenada"),
    "GY": ("Kaieteur Falls", "St George's Cathedral Georgetown"),
    "HT": ("Citadelle Laferrière", "Sans-Souci Palace Haiti"),
    "JM": ("Blue and John Crow Mountains", "Port Royal Jamaica"),
    "KI": ("Kiritimati atoll", "Phoenix Islands Protected Area"),
    "KN": ("Brimstone Hill Fortress", "Nevis Peak"),
    "KW": ("Kuwait Towers", "Failaka Island archaeological site"),
    "LR": ("Providence Island Monrovia", "Sapo National Park"),
    "LY": ("Leptis Magna", "Sabratha archaeological site"),
    "LC": ("Pitons Saint Lucia", "Pigeon Island National Landmark"),
    "LI": ("Vaduz Castle", "Gutenberg Castle Balzers"),
    "LS": ("Thaba Bosiu", "Maletsunyane Falls"),
    "MC": ("Prince's Palace of Monaco", "Oceanographic Museum Monaco"),
    "MD": ("Orheiul Vechi", "Soroca Fortress"),
    "MV": ("Malé Friday Mosque", "Baa Atoll"),
    "MH": ("Bikini Atoll", "Laura Beach Majuro"),
    "MK": ("Ohrid old town", "Kokino archaeological site"),
    "MZ": ("Island of Mozambique", "Gorongosa National Park"),
    "NE": ("Historic Centre of Agadez", "Aïr and Ténéré Natural Reserves"),
    "NR": ("Buada Lagoon", "Anibare Bay"),
    "PW": ("Rock Islands Southern Lagoon", "Badrulchau stone monoliths"),
    "PG": ("Kuk Early Agricultural Site", "Varirata National Park"),
    "QA": ("Al Zubarah Archaeological Site", "Museum of Islamic Art Doha"),
    "SB": ("East Rennell", "Vilu War Museum"),
    "SL": ("Bunce Island", "Tiwai Island Wildlife Sanctuary"),
    "SV": ("Joya de Cerén", "Santa Ana Volcano"),
    "SM": ("San Marino historic centre", "Guaita tower"),
    "SO": ("Laas Geel rock art", "Mogadishu historic lighthouse"),
    "SS": ("Boma National Park", "Sudd wetland"),
    "ST": ("Pico Cão Grande", "Roça Agostinho Neto"),
    "SZ": ("Mlilwane Wildlife Sanctuary", "Ngwenya Mine"),
    "SY": ("Ancient City of Damascus", "Crac des Chevaliers"),
    "TG": ("Koutammakou Togo", "Lake Togo"),
    "TL": ("Cristo Rei of Dili", "Jaco Island"),
    "TO": ("Haʻamonga ʻa Maui", "Mapu ʻa Vaea blowholes"),
    "TT": ("Caroni Swamp", "Pitch Lake Trinidad"),
    "TV": ("Funafuti Conservation Area", "Funafuti lagoon"),
    "TW": ("Taroko Gorge", "National Palace Museum Taipei"),
    "VA": ("St Peter's Basilica", "Vatican Museums"),
    "VC": ("La Soufrière Saint Vincent", "Tobago Cays Marine Park"),
    "VU": ("Chief Roi Mata's Domain", "Mount Yasur"),
    "WS": ("To Sua Ocean Trench", "Saleaula lava fields"),
    "ZM": ("Victoria Falls Zambia", "South Luangwa National Park"),
}

def _normalized_words(value):
    if not isinstance(value, str):
        return ""
    return " ".join(re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", value).casefold()))


def cover_metadata_matches_country(candidate, country_names):
    """Triage only: require a complete country-name phrase in cover metadata.

    Commons search can return files containing only a generic word such as
    "landscape" from a different country. Match whole words to avoid treating
    Nigeria as Niger. This check cannot replace a review of the actual image.
    """
    fields = [_normalized_words(candidate.get(key)) for key in ("file", "description")]
    for name in country_names:
        phrase = _normalized_words(name)
        if len(phrase) >= 4 and any(" " + phrase + " " in " " + field + " " for field in fields):
            return True
    return False


def make_plan(root, inventory=None):
    root = Path(root)
    canonical = json.loads((root / "country-content.json").read_text(encoding="utf-8"))["countries"]
    catalog = json.loads((root / "country-catalog.json").read_text(encoding="utf-8"))
    index = {r["code"]: r for r in catalog}
    if len(index) != 196 or len(catalog) != 196 or set(index) != set(canonical):
        raise ValueError("Catalog/canonical country mismatch")
    if inventory is not None:
        expected = {c for c, row in canonical.items() if row["status"] == "pending"}
        if set(inventory["countries"]) != expected:
            raise ValueError("Inventory and canonical pending set differ")
    drafts = {}
    for row in draft_queries(root):
        drafts.setdefault(row["countryCode"], []).append(row)
    countries = []
    for code, entry in sorted(canonical.items()):
        if entry["status"] != "pending":
            continue
        country = index[code]
        english = next((a for a in country.get("aliases", []) if isinstance(a, str) and a.strip()), country["name"])
        # Prefer explicit longer aliases over an abbreviation, e.g. UAE.
        aliases = [a.strip() for a in country.get("aliases", []) if isinstance(a, str) and a.strip()]
        latin_aliases = [a for a in aliases if re.search(r"[A-Za-z]", a)]
        english = max(latin_aliases or aliases, key=len, default=english)
        source = (inventory or {}).get("countries", {}).get(code, {})
        official = source.get("sampleSourcePages", [])
        existing = drafts.get(code, [])
        slots = []
        for slot in range(3):
            role = "cover" if slot == 0 else "quizAndTravel"
            item = {"slot": slot, "role": role, "place": None, "searchQuery": None,
                    "officialSourceCandidate": None, "publicationEligible": False}
            if existing:
                if len(existing) != 3 or existing[slot]["role"] != role:
                    raise ValueError("Draft photo roles invalid: " + code)
                item.update(place=existing[slot]["place"], searchQuery=existing[slot]["searchQuery"],
                            origin="existing_draft")
                if existing[slot].get("firstDraftSourceReviewRequired"):
                    item.update(origin="independent_source_required",
                                independentSourceReviewRequired=True,
                                referencePageCandidate=existing[slot].get("referencePageCandidate"))
                    if slot == 0:
                        item.update(origin="country_cover_research", countryNames=[country["name"], *aliases])
                key = (code, slot)
                if key in DRAFT_SEARCH_REFINEMENTS:
                    item["originalSearchQuery"] = item["searchQuery"]
                    item["searchQuery"] = DRAFT_SEARCH_REFINEMENTS[key]
                if key in DRAFT_SEARCH_ALTERNATIVES:
                    item["alternateSearchQuery"] = DRAFT_SEARCH_ALTERNATIVES[key]
            elif slot == 0:
                # Quote the full country name and avoid unrelated generic search hits.
                item.update(searchQuery='"' + english.replace('"', '') + '" landscape',
                            origin="country_cover_research",
                            countryNames=[country["name"], *aliases])
            elif len(official) >= slot:
                site = official[slot - 1]
                item.update(place=site["name"], searchQuery=site["name"] + " " + english,
                            officialSourceCandidate=site["sourceUrl"], origin="unesco_inventory_candidate")
            elif code in UNDRAFTED_PLACE_LEADS:
                place = UNDRAFTED_PLACE_LEADS[code][slot - 1]
                # An independent lead is a search hint only. It has no reviewed
                # source or established site identity and cannot become a draft
                # or a release record automatically.
                item.update(place=place, searchQuery=place + " " + english,
                            origin="independent_source_required",
                            independentSourceReviewRequired=True)
            else:
                item["origin"] = "independent_source_required"
            slots.append(item)
        countries.append({"code": code, "country": entry["name"], "region": country["region"],
                          "portraitDraftExists": bool((entry.get("portrait") or {}).get("body")),
                          "officialInventoryAvailable": inventory is not None,
                          "officialSourceCandidates": official, "slots": slots,
                          "publicationEligible": False})
    for i, row in enumerate(countries):
        row["shard"] = i % SHARDS
    return {"version": 1, "catalogCount": len(canonical), "approvedCount": len(canonical)-len(countries),
            "pendingCount": len(countries), "slotCount": 3*len(countries), "shards": SHARDS,
            "officialInventoryAvailable": inventory is not None, "countries": countries,
            "rule": "Research only. Source evidence, visual identity, exact license and full editorial review required. No automatic approval."}

def research_shard(plan, shard, fetch=fetch_commons, sleep_seconds=1.0, *,
                   resume=None, retry_transient=False, on_progress=None):
    if not 0 <= shard < plan["shards"]:
        raise ValueError("Invalid shard")
    rows = []
    throttled = False
    for country in plan["countries"]:
        if country["shard"] != shard:
            continue
        for slot in country["slots"]:
            row = dict(slot, countryCode=country["code"], country=country["country"],
                       candidates=[], manualVisualReviewRequired=True)
            query = slot["searchQuery"]
            saved=(resume or {}).get((country["code"],slot["slot"]))
            if saved:
                row.update(candidates=saved, status="metadata_candidates_only",
                           reusedCandidateMetadata=True)
            elif not query:
                row["status"] = "independent_source_required"
            elif throttled:
                row["status"] = "rate_limited_deferred"
            else:
                row["status"] = "no_matching_metadata"
                seen = set()
                # At most two requests per slot; no retry after errors or throttling.
                queries = [query]
                alternate = slot.get("alternateSearchQuery")
                if (slot.get("origin") == "existing_draft" and isinstance(alternate, str)
                        and alternate.strip() and alternate != query):
                    queries.append(alternate)
                row["attemptedQueries"] = []
                for term in queries:
                    row["attemptedQueries"].append(term)
                    try:
                        for page in fetch(term):
                            candidate = valid_candidate(page)
                            if candidate and slot.get("origin") == "country_cover_research":
                                if not cover_metadata_matches_country(candidate, slot.get("countryNames", [])):
                                    continue
                            if candidate and candidate["commonsPage"] not in seen:
                                row["candidates"].append(candidate)
                                seen.add(candidate["commonsPage"])
                                if len(seen) == 3:
                                    break
                        if seen:
                            row["status"] = "metadata_candidates_only"
                    except HTTPError as exc:
                        row["status"] = "search_failed"
                        row["httpStatus"] = exc.code
                        if exc.code in (429, 503):
                            throttled = True
                    except (URLError, TimeoutError, ValueError, OSError) as exc:
                        row["status"] = "search_failed"
                        row["errorType"] = type(exc).__name__
                    finally:
                        if sleep_seconds:
                            time.sleep(sleep_seconds)
                    if seen or (row["status"] == "search_failed" and
                                (not retry_transient or throttled)):
                        break
            rows.append(row)
            if on_progress:
                on_progress(rows)
    return {"shard": shard, "results": rows, "statusCounts": dict(Counter(r["status"] for r in rows))}

def combine(plan, reports):
    expected = {(c["code"], s["slot"]) for c in plan["countries"] for s in c["slots"]}
    seen = {}
    for report in reports:
        for row in report["results"]:
            key = (row["countryCode"], row["slot"])
            if key in seen or key not in expected:
                raise ValueError("Duplicate or unknown research slot")
            seen[key] = row
    missing = sorted(expected - set(seen))
    return {"catalogCount": plan["catalogCount"], "approvedCount": plan["approvedCount"],
            "pendingCount": plan["pendingCount"], "plannedSlots": len(expected),
            "reportedSlots": len(seen), "missingSlots": missing,
            "statusCounts": dict(Counter(r["status"] for r in seen.values())),
            "results": [seen[key] for key in sorted(seen)],
            "publicationEligible": False}

def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("plan")
    a.add_argument("--output", required=True)
    b = sub.add_parser("research")
    b.add_argument("--plan", required=True)
    b.add_argument("--shard", required=True, type=int)
    b.add_argument("--output", required=True)
    c = sub.add_parser("combine")
    c.add_argument("--plan", required=True)
    c.add_argument("--input-dir", required=True)
    c.add_argument("--output", required=True)
    args = p.parse_args()
    if args.command == "plan":
        try:
            inventory = build_inventory(ROOT, download_feed())
        except (URLError, TimeoutError, ValueError, OSError) as exc:
            print("Official feed unavailable: " + type(exc).__name__)
            inventory = None
        plan = make_plan(ROOT, inventory)
        save(args.output, plan)
        print("Planned", plan["pendingCount"], "pending countries;", plan["slotCount"], "slots; no approvals.")
    elif args.command == "research":
        report = research_shard(read(args.plan), args.shard)
        save(args.output, report)
        print(report["statusCounts"])
    else:
        plan = read(args.plan)
        report = combine(plan, [read(p) for p in sorted(Path(args.input_dir).rglob("shard-*.json"))])
        save(args.output, report)
        import os
        summary = ("### All-country research (not published)\n\n"
                   + f"- Pending countries: {report['pendingCount']}\n"
                   + f"- Reported slots: {report['reportedSlots']}/{report['plannedSlots']}\n"
                   + f"- Status: {report['statusCounts']}\n"
                   + f"- Unreported slots: {len(report['missingSlots'])}\n"
                   + "- No new country or photograph approved.\n")
        print(summary)
        if os.getenv("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
                stream.write(summary)
        if report["missingSlots"]:
            raise SystemExit("Some research shards did not report")

if __name__ == "__main__":
    main()
