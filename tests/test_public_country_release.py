"""Offline unit regressions for the post-deployment public-site smoke check."""
from pathlib import Path
import unittest
import json
from unittest.mock import patch

from check_public_country_release import (inspect_public_assets, inspect_public_visuals,
                                          required_public_visuals, check)
from reader_asset_split import expected_reader_assets

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("index.html", "world-passport.js", "service-worker.js",
         "country-highlights.json", "travel-stops.json",
         "data/current.json", "data/archive/index.json")


class PublicCountryReleaseSmokeTest(unittest.TestCase):
    def setUp(self):
        self.assets = {name: (ROOT / name).read_bytes() for name in NAMES}
        self.assets.update(expected_reader_assets(ROOT))

    def test_current_source_matches_required_public_assets(self):
        inspect_public_assets(self.assets, ROOT)

    def test_stale_country_highlights_fail(self):
        self.assets["country-highlights.json"] = b'{"version":1,"highlights":{}}'
        with self.assertRaisesRegex(AssertionError, "differ"):
            inspect_public_assets(self.assets, ROOT)

    def test_stale_live_article_list_fails(self):
        import json
        current=json.loads(self.assets["data/current.json"])
        # A stale issue must differ even when the current edition has one story.
        # Also retain a nonempty variant to prove that matching counts alone
        # are insufficient for public verification.
        self.assertTrue(current["stories"])
        current["stories"]=current["stories"][:-1]
        self.assets["data/current.json"]=json.dumps(current).encode("utf-8")
        with self.assertRaisesRegex(AssertionError,"news issue differs"):
            inspect_public_assets(self.assets, ROOT)

    def test_changed_article_with_same_count_fails(self):
        current=json.loads(self.assets["data/current.json"])
        current["stories"][0]["title"]+="（旧版）"
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
        import re
        outdated=re.sub(r"yoru9-shell-v\d+", "yoru9-shell-v21", current, count=1)
        self.assertNotEqual(outdated,current)
        self.assets["service-worker.js"] = outdated.encode("utf-8")
        with self.assertRaisesRegex(AssertionError, "shell"):
            inspect_public_assets(self.assets, ROOT)

    def test_reader_missing_independent_tour_module_fails(self):
        current = self.assets["assets/reader-travel.js"].decode("utf-8")
        self.assets["assets/reader-travel.js"] = current.replace(
            "WORLD POSTCARD · 有名観光地の小旅行",
            "WORLD POSTCARD missing"
        ).encode("utf-8")
        with self.assertRaisesRegex(AssertionError, "stale or altered|separation"):
            inspect_public_assets(self.assets, ROOT)


    def test_live_visual_manifest_covers_map_news_art_and_active_country_photos(self):
        current = json.loads(self.assets["data/current.json"])
        required = required_public_visuals(ROOT, current)
        self.assertIn("assets/world-today-illustrated.svg", required)
        self.assertGreaterEqual(len(current["stories"]),1)
        self.assertTrue(all((ROOT / name).is_file() for name in required
                            if name.startswith("assets/news/")),
                        "Every referenced commissioned news illustration must be present")
        # Check the exact active-country dependencies, not a historical
        # two-country edition's incidental total of nine photographs.
        from country_codes import country_codes
        codes={code for story in current["stories"] for code in country_codes(story["country"])}
        travel=json.loads((ROOT/"travel-stops.json").read_text(encoding="utf-8"))
        expected={stop["photoAsset"] for stop in travel.values()
                  if set(country_codes(stop.get("country")))&codes}
        actual={name for name in required if name.startswith("assets/travel/")}
        self.assertTrue(expected)
        self.assertEqual(actual,expected)
        from check_country_experience import country_coverage
        for country,record in country_coverage(ROOT,current["stories"]).items():
            with self.subTest(country=country):
                self.assertEqual(required[record["cover"]],(1000,540))
                for key in record["quizPhotoKeys"]:
                    self.assertEqual(required[travel[key]["photoAsset"]],(330,200))
                self.assertIn(record["postcard"],actual)
        self.assertTrue(all(required[name] in ((330,200),(1000,540)) for name in actual))

    def test_missing_published_country_photo_blocks_notification(self):
        path = next(name for name in required_public_visuals(
            ROOT, json.loads(self.assets["data/current.json"])
        ) if name.startswith("assets/travel/"))
        with self.assertRaisesRegex(AssertionError, "visual asset missing"):
            inspect_public_visuals({}, ROOT, {path: (330, 200)})

    def test_corrupt_published_jpeg_blocks_notification(self):
        with self.assertRaisesRegex(AssertionError, "JPEG is missing or corrupt"):
            inspect_public_visuals({"assets/travel/invalid.jpg": b"not a jpeg"},
                                   ROOT, {"assets/travel/invalid.jpg": (330, 200)})

    def test_low_resolution_published_photo_blocks_notification(self):
        # SOF0 size header: nominal 200x100, even when file is padded.
        payload = (b"\xff\xd8\xff\xc0\x00\x11\x08" +
                   (100).to_bytes(2, "big") + (200).to_bytes(2, "big") +
                   b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00" +
                   b"\x00" * 3500 + b"\xff\xd9")
        with self.assertRaisesRegex(AssertionError, "low resolution"):
            inspect_public_visuals({"assets/travel/tiny.jpg": payload},
                                   ROOT, {"assets/travel/tiny.jpg": (330, 200)})

    def test_tampered_map_svg_blocks_notification(self):
        name = "assets/world-today-illustrated.svg"
        original = (ROOT / name).read_bytes()
        changed = original.replace(b"<svg", b"<svg data-tampered='yes'", 1)
        self.assertNotEqual(original, changed)
        with self.assertRaisesRegex(AssertionError, "illustration differs"):
            inspect_public_visuals({name: changed}, ROOT, {name: None})

    def test_deploy_smoke_fetches_binary_images_after_core_data(self):
        # Prevent a regression to the previous text-only live-site check.
        with patch("check_public_country_release.fetch_assets",
                   side_effect=[self.assets, {}]) as fetch, patch(
                       "check_public_country_release.inspect_public_visuals"
                   ) as inspect:
            check("https://example.org/reader/", "sha", ROOT, retries=1)
        self.assertEqual(fetch.call_count, 2)
        manifest = required_public_visuals(
            ROOT, json.loads(self.assets["data/current.json"]))
        self.assertEqual(set(fetch.call_args_list[1].args[2]), set(manifest))
        inspect.assert_called_once()
