"""Offline unit regressions for the post-deployment public-site smoke check."""
from pathlib import Path
import unittest

from check_public_country_release import inspect_public_assets

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("index.html", "world-passport.js", "service-worker.js",
         "country-highlights.json", "travel-stops.json",
         "data/current.json", "data/archive/index.json")


class PublicCountryReleaseSmokeTest(unittest.TestCase):
    def setUp(self):
        self.assets = {name: (ROOT / name).read_bytes() for name in NAMES}

    def test_current_source_matches_required_public_assets(self):
        inspect_public_assets(self.assets, ROOT)

    def test_stale_country_highlights_fail(self):
        self.assets["country-highlights.json"] = b'{"version":1,"highlights":{}}'
        with self.assertRaisesRegex(AssertionError, "differ"):
            inspect_public_assets(self.assets, ROOT)

    def test_stale_live_article_list_fails(self):
        import json
        current=json.loads(self.assets["data/current.json"])
        current["stories"]=current["stories"][:1]
        self.assets["data/current.json"]=json.dumps(current).encode("utf-8")
        with self.assertRaisesRegex(AssertionError,"news issue differs"):
            inspect_public_assets(self.assets, ROOT)

    def test_stale_live_country_quiz_fails(self):
        self.assets["world-passport.js"]=b"stale old stamp book"
        with self.assertRaisesRegex(AssertionError,"quiz script"):
            inspect_public_assets(self.assets, ROOT)

    def test_stale_live_travel_paragraphs_fail(self):
        import json
        travel=json.loads(self.assets["travel-stops.json"])
        first=next(iter(travel))
        travel[first]["travelStory"]=["outdated destination"]
        self.assets["travel-stops.json"]=json.dumps(travel).encode("utf-8")
        with self.assertRaisesRegex(AssertionError,"travel stories"):
            inspect_public_assets(self.assets, ROOT)

    def test_outdated_pwa_shell_fails(self):
        current = self.assets["service-worker.js"].decode("utf-8")
        self.assets["service-worker.js"] = current.replace(
            "yoru9-shell-v37", "yoru9-shell-v21"
        ).encode("utf-8")
        with self.assertRaisesRegex(AssertionError, "shell"):
            inspect_public_assets(self.assets, ROOT)

    def test_reader_missing_independent_tour_module_fails(self):
        current = self.assets["index.html"].decode("utf-8")
        self.assets["index.html"] = current.replace(
            "WORLD POSTCARD · 有名観光地の小旅行",
            "WORLD POSTCARD missing"
        ).encode("utf-8")
        with self.assertRaisesRegex(AssertionError, "stale or altered|separation"):
            inspect_public_assets(self.assets, ROOT)
