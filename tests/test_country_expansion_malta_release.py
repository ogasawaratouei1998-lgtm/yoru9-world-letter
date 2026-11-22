"""Malta's 61st-country release must be fully source-backed and photo-safe."""
import json
from pathlib import Path
import unittest

from country_content import check_country_content, _commons_identity
from check_country_experience import country_coverage
from build_site import photo_cache_path

ROOT = Path(__file__).resolve().parents[1]


class MaltaReleaseTests(unittest.TestCase):
    def test_canonical_runtime_and_distinct_historical_landmarks(self):
        entry = check_country_content(ROOT)["countries"]["MT"]
        self.assertEqual(entry["status"], "approved")
        self.assertEqual(len(entry["portraitPhotos"]), 1)
        self.assertEqual(len(entry["quiz"]), 2)
        self.assertEqual(len(entry["travelStops"]), 3)
        expected = {
            "mt-mdina-cathedral-cover": ("Berthold Werner", "CC BY-SA 3.0"),
            "mt-valletta-harbour-postcard": ("Mike McBey", "CC BY 2.0"),
            "mt-hagar-qim-temple-postcard": ("Diego Delso (delso.photo)", "CC BY-SA 4.0"),
        }
        self.assertEqual(set(entry["travelStops"]), set(expected))
        self.assertEqual(len({_commons_identity(stop["photoPage"]) for stop in entry["travelStops"].values()}), 3)
        for key, (author, license_name) in expected.items():
            stop = entry["travelStops"][key]
            self.assertEqual(stop["author"], author)
            self.assertEqual(stop["license"], license_name)
        for quiz in entry["quiz"]:
            stop = entry["travelStops"][quiz["photoKey"]]
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            self.assertTrue(any(x["url"].startswith("https://whc.unesco.org/") for x in stop["historicalSources"]))
            self.assertTrue(any(x["url"].startswith("https://www.anzen.mofa.go.jp/") for x in stop["historicalSources"]))
        self.assertEqual(set(country_coverage(ROOT, [{"country": "MT"}])), {"MT"})

    def test_reviewed_postcards_are_provenance_pinned_and_cover_not_seeded(self):
        entry = check_country_content(ROOT)["countries"]["MT"]
        records = json.loads((ROOT / "editorial-country-photo-reviews/cache-seeds.json").read_text(encoding="utf-8"))["photos"]
        own = [x for x in records if x["country"] == "マルタ"]
        self.assertEqual({x["file"] for x in own}, {"MT-1.jpg", "MT-2.jpg"})
        keys = {x["photoAsset"] for x in own}
        self.assertEqual(keys, {entry["travelStops"][q["photoKey"]]["photoAsset"] for q in entry["quiz"]})
        self.assertNotIn(entry["portraitPhotos"][0]["asset"], keys)
        for record in own:
            stop = next(x for x in entry["travelStops"].values() if x["photoAsset"] == record["photoAsset"])
            for field in ("photoAsset", "photo", "photoPage", "author", "license",
                          "licenseUrl", "country", "place"):
                self.assertEqual(stop[field], record[field])
            self.assertRegex(record["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(record["runId"], 44974749380)
            self.assertFalse(record["cover"])
        cover = entry["travelStops"]["mt-mdina-cathedral-cover"]
        self.assertTrue(cover["coverOnly"])
        self.assertIn("/960px-", cover["photo"])
        self.assertNotIn(cover["photoAsset"], keys)
