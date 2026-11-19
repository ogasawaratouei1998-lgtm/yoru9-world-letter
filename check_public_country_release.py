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
import time
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen


def inspect_public_assets(assets: dict[str, bytes], root: Path) -> None:
    index = assets["index.html"].decode("utf-8")
    worker = assets["service-worker.js"].decode("utf-8")
    highlights = json.loads(assets["country-highlights.json"])
    current = json.loads(assets["data/current.json"])
    expected = json.loads((root / "country-highlights.json").read_text(encoding="utf-8"))
    expected_worker = (root / "service-worker.js").read_text(encoding="utf-8")
    if highlights != expected:
        raise AssertionError("Public source-backed country topics differ from main")
    for text in ("COUNTRY PORTRAIT · 国の魅力",
                 "WORLD POSTCARD · 有名観光地の小旅行",
                 "FAMOUS_TOURIST_LANDMARKS",
                 "currentCountryHighlight(all,currentCode)"):
        if text not in index:
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


def fetch_assets(site_url: str, revision: str) -> dict[str, bytes]:
    base = site_url.rstrip("/") + "/"
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Deployment URL must be a secure public site")
    result = {}
    for name in ("index.html", "service-worker.js", "country-highlights.json",
                 "data/current.json"):
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
            inspect_public_assets(fetch_assets(site_url, revision), root)
            print("Published Country Portrait + microtravel smoke: PASS")
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
