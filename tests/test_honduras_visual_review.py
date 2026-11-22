"""Review-only Honduras images do not misidentify Río Patuca or publish a country."""
import json
from pathlib import Path
import unittest

from country_content import _commons_identity, check_country_content

ROOT = Path(__file__).resolve().parents[1]


class HondurasReviewTests(unittest.TestCase):
    def test_three_distinct_license_attributed_images_remain_nonpublishing(self):
        doc = json.loads((ROOT / "editorial-country-photo-reviews/honduras-20261122.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["countryCode"], "HN")
        self.assertFalse(doc["publicationEligible"])
        self.assertEqual(len(doc["photos"]), 3)
        self.assertEqual({p["file"] for p in doc["photos"]}, {"HN-0.jpg", "HN-1.jpg", "HN-2.jpg"})
        self.assertEqual([p["dimensions"] for p in doc["photos"]], [[1280,960], [960,640], [960,464]])
        self.assertEqual(len({_commons_identity(p["commonsPage"]) for p in doc["photos"]}), 3)
        for p in doc["photos"]:
            self.assertRegex(p["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(p["author"])
            self.assertTrue(p["license"].startswith("CC BY"))
            self.assertTrue(p["licenseUrl"].startswith("https://creativecommons.org/"))
        self.assertIn("パトゥカ川", doc["photos"][2]["photoCaption"])
        self.assertIn("文化圏", doc["photos"][2]["photoCaption"])
        self.assertIn("レベル2", doc["photos"][0]["photoCaption"])
        self.assertIn("World Heritage in Danger", doc["safetyNote"])
        self.assertIn("https://whc.unesco.org/en/decisions/?id_decision=9032", doc["independentSources"])
        self.assertEqual(check_country_content(ROOT)["countries"]["HN"]["name"], "ホンジュラス")
