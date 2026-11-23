"""Protect editorial-only country drafts from premature release."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PENDING_PHOTO_REVIEW = ("AD", "AO", "AE", "BJ", "BF")


class PendingPhotoReleaseGate(unittest.TestCase):
    def test_drafts_stay_unpublished_until_photos_are_verified(self):
        countries = json.loads((ROOT / "country-content.json").read_text(encoding="utf-8"))["countries"]
        for code in PENDING_PHOTO_REVIEW:
            with self.subTest(country=code):
                country = countries[code]
                self.assertEqual(country["status"], "pending")
                self.assertFalse(country.get("portrait", {}).get("photos"))
                self.assertFalse(country.get("portraitPhotos"))
                self.assertFalse(country.get("travelStops"))
                drafts = country.get("travelDrafts", [])
                # Drafts may live on a separate unmerged editorial branch.
                for draft in drafts:
                    self.assertTrue(draft.get("editorialOnly"))
                    self.assertTrue(str(draft.get("status", "")).startswith("pending"))
                    self.assertEqual(len(draft.get("paragraphs", [])), 2)


if __name__ == "__main__":
    unittest.main()
