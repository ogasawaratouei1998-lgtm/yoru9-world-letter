"""Bangladesh cultural heritage release must be licensed, distinct and source-backed."""
import json
from pathlib import Path
import unittest

from country_content import check_country_content, _commons_identity
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]


class BangladeshReleaseTests(unittest.TestCase):
    def test_country_heritage_photo_quiz_contract(self):
        entry = check_country_content(ROOT)["countries"]["BD"]
        self.assertEqual(entry["status"], "approved")
        self.assertEqual(len(entry["portraitPhotos"]), 1)
        self.assertEqual(len(entry["quiz"]), 2)
        self.assertEqual(len(entry["travelStops"]), 3)
        self.assertIn("危険レベル2", entry["portrait"]["body"])
        self.assertIn("危険レベル1", entry["portrait"]["body"])
        expected = {
            "bd-jaflong-tea-country-cover": ("Abdul Momin", "CC BY-SA 4.0"),
            "bd-nine-dome-mosque-postcard": ("Faisal Photography", "CC BY 4.0"),
            "bd-somapura-mahavihara-postcard": ("Khan-Tanvir", "CC BY-SA 3.0"),
        }
        self.assertEqual(set(entry["travelStops"]), set(expected))
        self.assertEqual(len({_commons_identity(s["photoPage"]) for s in entry["travelStops"].values()}), 3)
        for key, (author, license_name) in expected.items():
            stop = entry["travelStops"][key]
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["license"], license_name)
            self.assertIn("撮影位置", stop["note"])
        for q in entry["quiz"]:
            stop = entry["travelStops"][q["photoKey"]]
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            self.assertTrue(any(x["url"].startswith("https://whc.unesco.org/") for x in stop["historicalSources"]))
            self.assertTrue(any(x["url"].startswith("https://www.anzen.mofa.go.jp/") for x in stop["historicalSources"]))
        self.assertIn("六十ドーム・モスクとは別", entry["travelStops"]["bd-nine-dome-mosque-postcard"]["travelStory"][1])
        self.assertEqual(set(country_coverage(ROOT, [{"country": "BD"}])), {"BD"})

    def test_three_sha256_reviewed_photos_and_native_1280_cover(self):
        entry = check_country_content(ROOT)["countries"]["BD"]
        seeds = json.loads((ROOT / "editorial-country-photo-reviews/cache-seeds.json").read_text(encoding="utf-8"))["photos"]
        own = [s for s in seeds if s["country"] == "バングラデシュ"]
        self.assertEqual({s["file"] for s in own}, {"BD-0.jpg", "BD-1.jpg", "BD-2.jpg"})
        self.assertEqual({s["photoAsset"] for s in own}, {s["photoAsset"] for s in entry["travelStops"].values()})
        self.assertEqual(sum(s["cover"] for s in own), 1)
        for s in own:
            stop = next(x for x in entry["travelStops"].values() if x["photoAsset"] == s["photoAsset"])
            for field in ("photoAsset", "photo", "photoPage", "author", "license",
                          "licenseUrl", "country", "place"):
                self.assertEqual(s[field], stop[field])
            self.assertEqual(s["runId"], 44986532608)
            self.assertRegex(s["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(s["cover"], bool(stop.get("coverOnly")))
        review = json.loads((ROOT / "editorial-country-photo-reviews/bangladesh-20261122.json").read_text(encoding="utf-8"))
        self.assertFalse(review["publicationEligible"])
        self.assertEqual([x["width"] for x in review["photos"]], [1280,960,960])
        self.assertEqual([x["height"] for x in review["photos"]], [814,540,706])
        self.assertEqual(review["photos"][0]["sha256"], next(s["sha256"] for s in own if s["cover"]))
