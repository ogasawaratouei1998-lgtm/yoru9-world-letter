"""Algeria release must have real, independently licensed site photos and safety cues."""
import json
from pathlib import Path
import unittest
from country_content import check_country_content, _commons_identity
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]


class AlgeriaReleaseTests(unittest.TestCase):
    def test_travel_photo_provenance_unesco_and_reader_gate(self):
        entry = check_country_content(ROOT)["countries"]["DZ"]
        self.assertEqual(entry["status"], "approved")
        self.assertEqual(len(entry["portraitPhotos"]), 1)
        self.assertEqual(len(entry["quiz"]), 2)
        expected = {
            "dz-hassania-mountains-cover": ("FETHI BOUHAOUCHINE", "CC BY-SA 4.0"),
            "dz-beni-hammad-minaret-postcard": ("Yelles", "CC BY-SA 3.0"),
            "dz-djemila-roman-ruins-postcard": ("habib kaki", "CC BY 3.0"),
        }
        self.assertEqual(set(entry["travelStops"]), set(expected))
        self.assertEqual(len({_commons_identity(stop["photoPage"]) for stop in entry["travelStops"].values()}), 3)
        for key, (author, license_name) in expected.items():
            stop = entry["travelStops"][key]
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["license"], license_name)
            self.assertTrue(stop["licenseUrl"].startswith("https://creativecommons.org/licenses/"))
        self.assertIn("レベル4", entry["portrait"]["body"])
        cover = entry["travelStops"]["dz-hassania-mountains-cover"]
        self.assertTrue(cover["coverOnly"])
        self.assertIn("レベル3", cover["note"])
        self.assertIn("撮影点ではありません", cover["note"])
        for quiz in entry["quiz"]:
            stop = entry["travelStops"][quiz["photoKey"]]
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            self.assertTrue(any(x["url"].startswith("https://whc.unesco.org/") for x in stop["historicalSources"]))
            self.assertTrue(any(x["url"].startswith("https://www.anzen.mofa.go.jp/") for x in stop["historicalSources"]))
        self.assertEqual(set(country_coverage(ROOT, [{"country": "DZ"}])), {"DZ"})

    def test_all_three_verified_jpegs_pinned_with_cover_1280_resolution(self):
        entry = check_country_content(ROOT)["countries"]["DZ"]
        records = json.loads((ROOT / "editorial-country-photo-reviews/cache-seeds.json").read_text(encoding="utf-8"))["photos"]
        own = [x for x in records if x["country"] == "アルジェリア"]
        self.assertEqual({x["file"] for x in own}, {"DZ-0.jpg", "DZ-1.jpg", "DZ-2.jpg"})
        self.assertEqual({x["photoAsset"] for x in own},
                         {p["photoAsset"] for p in entry["travelStops"].values()})
        self.assertEqual(sum(x["cover"] for x in own), 1)
        for record in own:
            stop = next(p for p in entry["travelStops"].values()
                        if p["photoAsset"] == record["photoAsset"])
            for field in ("photoAsset", "photo", "photoPage", "author", "license",
                          "licenseUrl", "country", "place"):
                self.assertEqual(record[field], stop[field])
            self.assertRegex(record["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(record["runId"], 44986532608)
            self.assertEqual(record["cover"], bool(stop.get("coverOnly")))
        review = json.loads((ROOT / "editorial-country-photo-reviews/algeria-20261122.json").read_text(encoding="utf-8"))
        self.assertEqual(review["coverDimensions"], [1280, 817])
        self.assertEqual(review["coverHash"], next(x for x in own if x["cover"])["sha256"])
