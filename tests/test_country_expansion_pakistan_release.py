"""Pakistan country content must be source-verified and never encourage unsafe travel."""
import json
from pathlib import Path
import unittest

from country_content import check_country_content, _commons_identity
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]


class PakistanReleaseTests(unittest.TestCase):
    def test_heritage_content_and_danger_warning(self):
        row = check_country_content(ROOT)["countries"]["PK"]
        self.assertEqual(row["status"], "approved")
        self.assertEqual(len(row["portraitPhotos"]), 1)
        self.assertEqual(len(row["travelStops"]), 3)
        self.assertEqual(len(row["quiz"]), 2)
        self.assertIn("危険レベル2～4", row["portrait"]["body"])
        self.assertIn("渡航中止勧告", row["portrait"]["body"])
        self.assertIn("現地訪問を勧めない", row["portrait"]["body"])
        expected = {
            "pk-hingol-rock-cover": ("Bilal Mirza", "CC BY-SA 3.0"),
            "pk-moenjodaro-ruins-postcard": ("Usman.pg", "CC BY-SA 3.0"),
            "pk-takht-bahi-postcard": ("Bakhtiar Ahmed", "CC BY-SA 3.0"),
        }
        self.assertEqual(set(row["travelStops"]), set(expected))
        self.assertEqual(len({_commons_identity(s["photoPage"]) for s in row["travelStops"].values()}), 3)
        for key, (author, license_name) in expected.items():
            s = row["travelStops"][key]
            self.assertEqual(s["author"], author)
            self.assertEqual(s["license"], license_name)
            self.assertIn("撮影座標ではありません", s["note"])
            self.assertIn("渡航は推奨しません", s["note"])
        for quiz in row["quiz"]:
            s = row["travelStops"][quiz["photoKey"]]
            self.assertEqual(len(s["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in s["travelStory"]))
            self.assertTrue(any(x["url"].startswith("https://whc.unesco.org/") for x in s["historicalSources"]))
            self.assertTrue(any(x["url"].startswith("https://www.anzen.mofa.go.jp/") for x in s["historicalSources"]))
        self.assertEqual(set(country_coverage(ROOT, [{"country": "PK"}])), {"PK"})

    def test_exact_photo_provenance_and_distinct_landmarks(self):
        row = check_country_content(ROOT)["countries"]["PK"]
        records = json.loads((ROOT / "editorial-country-photo-reviews/cache-seeds.json").read_text(encoding="utf-8"))["photos"]
        own = [s for s in records if s["country"] == "パキスタン"]
        self.assertEqual({s["file"] for s in own}, {"PK-0.jpg", "PK-1.jpg", "PK-2.jpg"})
        self.assertEqual(sum(s["cover"] for s in own), 1)
        self.assertEqual({s["photoAsset"] for s in own},
                         {s["photoAsset"] for s in row["travelStops"].values()})
        for record in own:
            stop = next(s for s in row["travelStops"].values() if s["photoAsset"] == record["photoAsset"])
            for key in ("photoAsset", "photo", "photoPage", "author", "license",
                        "licenseUrl", "country", "place"):
                self.assertEqual(stop[key], record[key])
            self.assertEqual(record["runId"], 45017850362)
            self.assertRegex(record["sha256"], r"^[a-f0-9]{64}$")
        review = json.loads((ROOT / "editorial-country-photo-reviews/pakistan-20261122.json").read_text(encoding="utf-8"))
        self.assertFalse(review["publicationEligible"])
        self.assertEqual(review["photos"][0]["dimensions"], [1280, 960])
        self.assertFalse(review["travelAdvice"])
