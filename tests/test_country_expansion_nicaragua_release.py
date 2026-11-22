"""Nicaragua is fully verified by distinct Commons originals and UNESCO references."""
import json
from pathlib import Path
import unittest
from country_content import check_country_content, _commons_identity
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]


class NicaraguaReleaseTests(unittest.TestCase):
    def test_complete_66th_country_content_and_photo_identity(self):
        row = check_country_content(ROOT)["countries"]["NI"]
        self.assertEqual(row["status"], "approved")
        self.assertEqual(len(row["portraitPhotos"]), 1)
        self.assertEqual(len(row["quiz"]), 2)
        self.assertEqual(len(row["travelStops"]), 3)
        self.assertIn("危険レベル1", row["portrait"]["body"])
        expected = {
            "ni-matagalpa-hills-cover": ("Adam Jones from Kelowna, BC, Canada", "CC BY-SA 2.0"),
            "ni-leon-cathedral-postcard": ("eric molina", "CC BY 2.0"),
            "ni-leon-viejo-ruins-postcard": ("HHaefner", "CC BY-SA 3.0"),
        }
        self.assertEqual(set(row["travelStops"]), set(expected))
        self.assertEqual(len({_commons_identity(x["photoPage"]) for x in row["travelStops"].values()}), 3)
        for key, (author, license_name) in expected.items():
            stop = row["travelStops"][key]
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["license"], license_name)
            self.assertIn("撮影", stop["note"])
            self.assertIn("https://creativecommons.org/", stop["licenseUrl"])
        for quiz in row["quiz"]:
            stop = row["travelStops"][quiz["photoKey"]]
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            self.assertTrue(any(src["url"].startswith("https://whc.unesco.org/") for src in stop["historicalSources"]))
            self.assertTrue(any(src["url"].startswith("https://www.anzen.mofa.go.jp/") for src in stop["historicalSources"]))
        self.assertEqual(set(country_coverage(ROOT, [{"country": "NI"}])), {"NI"})

    def test_review_hashes_and_credit_pins_match_exact_three_photos(self):
        row = check_country_content(ROOT)["countries"]["NI"]
        data = json.loads((ROOT / "editorial-country-photo-reviews/nicaragua-20261122.json").read_text(encoding="utf-8"))
        self.assertFalse(data["publicationEligible"])
        self.assertEqual(data["photos"][0]["dimensions"], [1280, 960])
        self.assertEqual(data["safetySource"]["currentRisk"], "全土危険レベル1（十分注意）")
        seeds = json.loads((ROOT / "editorial-country-photo-reviews/cache-seeds.json").read_text(encoding="utf-8"))["photos"]
        own = [x for x in seeds if x["country"] == "ニカラグア"]
        self.assertEqual({x["file"] for x in own}, {"NI-0.jpg", "NI-1.jpg", "NI-2.jpg"})
        self.assertEqual({x["photoAsset"] for x in own}, {x["photoAsset"] for x in row["travelStops"].values()})
        self.assertEqual(sum(x["cover"] for x in own), 1)
        for record in own:
            stop = next(s for s in row["travelStops"].values() if s["photoAsset"] == record["photoAsset"])
            for k in ("photoAsset", "photo", "photoPage", "author", "license",
                      "licenseUrl", "country", "place"):
                self.assertEqual(stop[k], record[k])
            self.assertEqual(record["runId"], 45017850362)
            self.assertRegex(record["sha256"], r"^[a-f0-9]{64}$")
            self.assertEqual(record["cover"], bool(stop.get("coverOnly")))
