#!/usr/bin/env python3
"""Smoke-test actual GitHub Pages bytes after the reader deployment finishes.

The builder and unit tests validate local source files. This step separately
checks that the *published* site serves the same country highlights and a
reader with the portrait/microtravel separation; it cannot emulate an iPhone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import tempfile
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen


def inspect_public_assets(assets: dict[str, bytes], root: Path) -> None:
    index = assets["index.html"].decode("utf-8")
    worker = assets["service-worker.js"].decode("utf-8")
    highlights = json.loads(assets["country-highlights.json"])
    current = json.loads(assets["data/current.json"])
    published_travel=json.loads(assets["travel-stops.json"])
    local_travel=json.loads((root/"travel-stops.json").read_text(encoding="utf-8"))
    published_index=json.loads(assets["data/archive/index.json"])
    local_index=json.loads((root/"data/archive/index.json").read_text(encoding="utf-8"))
    expected = json.loads((root / "country-highlights.json").read_text(encoding="utf-8"))
    expected_worker = (root / "service-worker.js").read_text(encoding="utf-8")
    if highlights != expected:
        raise AssertionError("Public source-backed country topics differ from main")
    if published_travel != local_travel:
        raise AssertionError("Public detailed travel stories differ from current source")
    if published_index != local_index:
        raise AssertionError("Public archive index differs from current release")
    if current != json.loads((root/"data/current.json").read_text(encoding="utf-8")):
        raise AssertionError("Public news issue differs from current release")
    if assets["world-passport.js"] != (root/"world-passport.js").read_bytes():
        raise AssertionError("Public country quiz script is stale or altered")
    from reader_asset_split import expected_reader_assets
    expected_reader=expected_reader_assets(root)
    if assets["index.html"] != expected_reader["index.html"]:
        raise AssertionError("Public reader page is stale or altered")
    for path in ("assets/reader-core.css","assets/reader-core.js",
                 "assets/reader-country-data.js","assets/reader-travel.js"):
        if assets.get(path) != expected_reader[path]:
            raise AssertionError("Published external reader asset stale or altered: "+path)
    runtime=assets["assets/reader-core.js"].decode("utf-8")
    travel_module=assets["assets/reader-travel.js"].decode("utf-8")
    for text in ("COUNTRY PORTRAIT · 国の魅力",
                 "WORLD POSTCARD · 有名観光地の小旅行",
                 "FAMOUS_TOURIST_LANDMARKS",
                 "currentCountryHighlight(all,currentCode)"):
        if text not in index + runtime + travel_module:
            raise AssertionError("Public reader lacks country portrait separation: " + text)
    version = re.compile(r"const SHELL_CACHE = '([^']+)'")
    local = version.search(expected_worker)
    public = version.search(worker)
    if not local or not public or local.group(1) != public.group(1):
        raise AssertionError("Published PWA shell is older than the source")
    if "'country-highlights.json'" not in worker:
        raise AssertionError("PWA does not cache checked country highlights")
    if current.get("status") != "published" or not isinstance(current.get("stories"), list):
        raise AssertionError("Latest released stories missing from public site")
    if len(current["stories"]) < 4 and current.get("editionType")=="regular" and current.get("editionDate","")>="2026-11-21":
        raise AssertionError("Public regular issue violates four-story release gate")
    for obsolete in ('id="todayPassportBoard"','id="todayPassportStamps"',
                     'id="todayPassportCount"'):
        if obsolete in index:
            raise AssertionError("Retired stamp album has reappeared on public reader")
    if 'stop.travelStory.map(paragraph=>' not in travel_module:
        raise AssertionError("Detailed destination essays are missing from public reader")
    from check_country_experience import country_coverage
    checked=country_coverage(root,current["stories"])
    for record in checked.values():
        if record.get("quizRounds",0)<2 or not record.get("postcard"):
            raise AssertionError("Public country guide lacks its full curated quiz/travel data")



def required_public_visuals(root: Path, current: dict) -> dict[str, tuple[int, int] | None]:
    """Identify the actual reader's local image dependencies for this issue.

    All photos from countries present in the issue are checked, not merely
    one representative cover. A fresh nightly story without commissioned
    artwork uses its deterministic inline SVG and needs no external image.
    """
    from check_country_experience import country_coverage
    from country_codes import country_codes

    countries = country_coverage(root, current["stories"])
    codes = set(countries)
    travel = json.loads((root / "travel-stops.json").read_text(encoding="utf-8"))
    visuals: dict[str, tuple[int, int] | None] = {
        "assets/world-today-illustrated.svg": None
    }
    for key, stop in travel.items():
        if not (set(country_codes(stop.get("country"))) & codes):
            continue
        asset = stop.get("photoAsset", "")
        if not re.fullmatch(r"assets/travel/[a-z0-9-]+\.jpg", asset):
            raise ValueError("Invalid active country photo: " + key)
        visuals[asset] = (330, 200)

    # Covers can rotate. The public check must catch missing alternatives
    # even if the editorial release gate verified the first portrait.
    page = (root / "index.html").read_text(encoding="utf-8")
    prefix = "const TODAY_COUNTRY_PHOTOS=Object.freeze("
    rows = [line for line in page.splitlines() if line.startswith(prefix)]
    if len(rows) != 1 or not rows[0].endswith(");"):
        raise ValueError("Reader photo registry is missing")
    registry = json.loads(rows[0][len(prefix):-2])
    for code in codes:
        for candidate in registry.get(code, []):
            if candidate.get("avoidCover") or candidate.get("remoteOnly"):
                continue
            asset = candidate.get("asset")
            if asset in visuals:
                visuals[asset] = (1000, 540)

    section = page.split("const NEWS_ARTWORK=Object.freeze({", 1)[1].split("\n});", 1)[0]
    artworks = dict(re.findall(r"'([^']+)':'([a-z0-9-]+\.svg)'", section))
    for story in current["stories"]:
        filename = artworks.get(story.get("id"))
        if filename:
            visuals["assets/news/" + filename] = None
    return dict(sorted(visuals.items()))


def inspect_public_visuals(assets: dict[str, bytes], root: Path,
                           required: dict[str, tuple[int, int] | None]) -> None:
    """Fail closed on 404s, corrupt/low-resolution photos and stale artwork.

    When the exact built artifact exists, photo bytes must match it as well:
    a different (even visually plausible) photograph must not silently
    replace the reviewed, correctly licensed destination.
    """
    from check_release_candidate import jpeg_dimensions

    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory) / "downloaded.jpg"
        for relative, minimum in required.items():
            if relative not in assets:
                raise AssertionError("Published visual asset missing: " + relative)
            payload = assets[relative]
            if minimum is None:
                if not 150 <= len(payload) <= 2_000_000:
                    raise AssertionError("Published illustration is empty: " + relative)
                try:
                    svg = ET.fromstring(payload)
                except ET.ParseError as exc:
                    raise AssertionError("Published SVG is corrupt: " + relative) from exc
                if svg.tag != "{http://www.w3.org/2000/svg}svg" or any(
                    element.tag.endswith(("script", "foreignObject"))
                    for element in svg.iter()
                ):
                    raise AssertionError("Published illustration is invalid: " + relative)
                original = root / relative
                if not original.is_file() or payload != original.read_bytes():
                    raise AssertionError("Published illustration differs from source: " + relative)
            else:
                if (not 3000 <= len(payload) <= 2_000_000 or
                        not payload.startswith(b"\xff\xd8\xff") or
                        not payload.endswith(b"\xff\xd9")):
                    raise AssertionError("Published JPEG is missing or corrupt: " + relative)
                temp.write_bytes(payload)
                try:
                    width, height = jpeg_dimensions(temp)
                except (OSError, ValueError) as exc:
                    raise AssertionError("Published JPEG has invalid dimensions: " + relative) from exc
                if width < minimum[0] or height < minimum[1]:
                    raise AssertionError("Published photo is low resolution: " + relative)
                packaged = root / "_site" / relative
                if packaged.parent.parent.exists() and not packaged.is_file():
                    raise AssertionError("Built reader is missing photo: " + relative)
                if packaged.is_file() and payload != packaged.read_bytes():
                    raise AssertionError("Published photo differs from licensed build: " + relative)

def fetch_assets(site_url: str, revision: str, names=None) -> dict[str, bytes]:
    base = site_url.rstrip("/") + "/"
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Deployment URL must be a secure public site")
    result = {}
    if names is None:
        names = ("index.html", "assets/reader-core.css", "assets/reader-core.js",
                 "assets/reader-country-data.js", "assets/reader-travel.js",
                 "world-passport.js", "service-worker.js",
                 "country-highlights.json", "travel-stops.json",
                 "data/current.json", "data/archive/index.json")
    for name in names:
        url = urljoin(base, name) + "?deploy=" + quote(revision, safe="")
        request = Request(url, headers={"Cache-Control": "no-cache",
                                       "User-Agent": "Yoru9ReleaseSmoke/1.0"})
        with urlopen(request, timeout=18) as response:
            if not response.geturl().startswith(base):
                raise ValueError("Deployment URL redirected outside its expected site")
            result[name] = response.read(2_000_001)
        if len(result[name]) > 2_000_000:
            raise ValueError("Published asset exceeds smoke test size limit: " + name)
    return result


def check(site_url: str, revision: str, root: Path, retries: int = 5) -> None:
    if not 1 <= retries <= 8:
        raise ValueError("invalid retry count")
    for attempt in range(retries):
        try:
            public = fetch_assets(site_url, revision)
            inspect_public_assets(public, root)
            required = required_public_visuals(root, json.loads(public["data/current.json"]))
            inspect_public_visuals(fetch_assets(site_url, revision, tuple(required)), root, required)
            print("Published reader and "+str(len(required))+" visual assets: PASS")
            return
        except (AssertionError, OSError, ValueError, json.JSONDecodeError) as exc:
            if attempt == retries - 1:
                raise RuntimeError("Published Country Portrait smoke failed") from exc
            print("Published assets not yet consistent:", str(exc))
            time.sleep(8)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    check(args.site, args.revision, args.root)


if __name__ == "__main__":
    main()
