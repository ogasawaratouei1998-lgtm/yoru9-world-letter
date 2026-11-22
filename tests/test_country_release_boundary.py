"""Regression checks for the 196-country editorial release boundary.

Pending drafts may be expanded without becoming publishable. The gate must
not treat a source link, placeholder or photo candidate as approval.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CountryReleaseBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = json.loads((ROOT / "country-content.json").read_text(encoding="utf-8"))
        cls.catalog = json.loads((ROOT / "country-catalog.json").read_text(encoding="utf-8"))

    def test_catalog_and_editorial_registry_match(self):
        codes = [item["code"] for item in self.catalog]
        self.assertEqual(196, len(codes))
        self.assertEqual(len(codes), len(set(codes)), "duplicate catalog country code")
        self.assertEqual(set(codes), set(self.content["countries"]))

    def test_status_is_explicit_and_pending_is_not_preapproved(self):
        for code, country in self.content["countries"].items():
            with self.subTest(code=code):
                self.assertIn(country["status"], ("approved", "pending"))
                if country["status"] == "pending":
                    self.assertEqual([], country.get("portraitPhotos", []),
                                     "unreviewed photos must not be promoted to release metadata")
                    self.assertEqual([], country.get("quiz", []),
                                     "pending country must not carry publishable quizzes")
                    self.assertFalse(country.get("travelStops"),
                                     "pending country must not carry publishable travel stops")

    def test_approved_country_has_independent_photos_and_experiences(self):
        for code, country in self.content["countries"].items():
            if country["status"] != "approved":
                continue
            with self.subTest(code=code):
                self.assertGreaterEqual(len(country.get("portraitPhotos", [])), 1)
                self.assertGreaterEqual(len(country.get("quiz", [])), 2)
                self.assertGreaterEqual(len(country.get("travelStops", {})), 2)
                for photo in country["portraitPhotos"]:
                    for field in ("asset", "url", "author", "license", "place"):
                        self.assertTrue(photo.get(field), f"{code}: missing {field}")


if __name__ == "__main__":
    unittest.main()
