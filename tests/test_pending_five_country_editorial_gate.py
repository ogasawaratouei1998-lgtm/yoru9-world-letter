"""Regression checks for the five-country editorial staging batch.

Pending drafts may be written and reviewed, but must never become published
travel stops without separate photo, provenance and location clearance.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("AD", "AO", "AE", "BJ", "BF")


class PendingFiveCountryEditorialGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.countries = json.loads(
            (ROOT / "country-content.json").read_text(encoding="utf-8")
        )["countries"]

    def test_pending_country_drafts_remain_editorial_only(self):
        for code in TARGETS:
            with self.subTest(country=code):
                country = self.countries[code]
                self.assertEqual(country["status"], "pending")
                self.assertEqual(country.get("travelStops"), {})
                self.assertEqual(country.get("portraitPhotos"), [])
                drafts = country.get("travelDrafts", [])
                self.assertEqual(len(drafts), 2)
                for draft in drafts:
                    self.assertTrue(draft.get("editorialOnly"))
                    self.assertEqual(len(draft.get("paragraphs", [])), 2)
                    self.assertTrue(all(len(p.strip()) >= 40 for p in draft["paragraphs"]))
                    self.assertTrue(draft.get("sourceUrl", "").startswith("https://"))
                    self.assertIn("pending", draft.get("status", ""))

    def test_quizzes_are_complete_but_do_not_approve_country(self):
        for code in TARGETS:
            with self.subTest(country=code):
                country = self.countries[code]
                self.assertEqual(country["status"], "pending")
                quizzes = country.get("quiz", [])
                self.assertEqual(len(quizzes), 2)
                for quiz in quizzes:
                    self.assertEqual(len(quiz["options"]), 3)
                    self.assertIn(quiz["answer"], (0, 1, 2))
                    self.assertTrue(quiz.get("fact", "").strip())
                    self.assertTrue(quiz.get("quip", "").strip())


if __name__ == "__main__":
    unittest.main()
