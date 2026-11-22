"""Botswana release must show exactly reviewed natural and cultural heritage."""
import json
import unittest
from pathlib import Path

from country_content import check_country_content, _commons_identity
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]


class BotswanaReleaseTests(unittest.TestCase):
    def test_heritage_and_photo_credits(self):
        entry = check_country_content(ROOT)["countries"]["BW"]
        self.assertEqual(entry["status"], "approved")
        self.assertEqual(len(entry["portraitPhotos"]), 1)
        self.assertEqual(len(entry["quiz"]), 2)
        self.assertEqual(len(entry["travelStops"]), 3)
        expected = {
            "bw-chobe-elephant-cover": ("E.A.A.Oliveira", "CC BY-SA 4.0"),
            "bw-okavango-delta-postcard": ("Diego Delso (delso.photo)", "CC BY-SA 4.0"),
            "bw-tsodilo-hills-postcard": ("Joachim Huber", "CC BY-SA 2.0"),
        }
        self.assertEqual(set(entry["travelStops"]), set(expected))
        self.assertEqual(len({_commons_identity(s["photoPage"]) for s in entry["travelStops"].values()}), 3)
        for key, (author, license_name) in expected.items():
            stop = entry["travelStops"][key]
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["license"], license_name)
        for q in entry["quiz"]:
            stop = entry["travelStops"][q["photoKey"]]
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(t) <= 360 for t in stop["travelStory"]))
            self.assertTrue(any(x["url"].startswith("https://whc.unesco.org/") for x in stop["historicalSources"]))
            self.assertTrue(any(x["url"].startswith("https://www.anzen.mofa.go.jp/") for x in stop["historicalSources"]))
        self.assertIn("岩絵そのものは写真には写っていません",
                      entry["travelStops"]["bw-tsodilo-hills-postcard"]["photoCaption"])
        self.assertEqual(set(country_coverage(ROOT, [{"country": "BW"}])), {"BW"})

    def test_three_exact_preview_hashes_are_pinned_without_false_coordinates(self):
        canonical = check_country_content(ROOT)["countries"]["BW"]
        seeds = json.loads((ROOT / "editorial-country-photo-reviews/cache-seeds.json").read_text(encoding="utf-8"))["photos"]
        own = [s for s in seeds if s["country"] == "ボツワナ"]
        self.assertEqual({s["file"] for s in own}, {"BW-0.jpg", "BW-1.jpg", "BW-2.jpg"})
        self.assertEqual(len(own), 3)
        self.assertEqual(sum(s["cover"] for s in own), 1)
        self.assertEqual({s["photoAsset"] for s in own},
                         {x["photoAsset"] for x in canonical["travelStops"].values()})
        for s in own:
            stop = next(x for x in canonical["travelStops"].values() if x["photoAsset"] == s["photoAsset"])
            for key in ("photoAsset", "photo", "photoPage", "author", "license",
                        "licenseUrl", "country", "place"):
                self.assertEqual(s[key], stop[key])
            self.assertEqual(s["runId"], 44986532608)
            self.assertRegex(s["sha256"], r"^[0-9a-f]{64}$")
            self.assertIn("代表地点", stop["region"])
            self.assertIn("撮影座標ではありません", stop["note"])
        review = json.loads((ROOT / "editorial-country-photo-reviews/botswana-20261122.json").read_text(encoding="utf-8"))
        self.assertFalse(review["publicationEligible"])
        self.assertEqual(review["photos"][0]["width"], 1280)
        self.assertEqual(review["photos"][0]["height"], 853)
