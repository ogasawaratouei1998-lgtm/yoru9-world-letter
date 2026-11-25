"""Check the new editorial-only cohort without granting publication eligibility."""
import json
from pathlib import Path
import unittest
from urllib.parse import urlsplit
from country_photo_candidates import draft_queries

ROOT = Path(__file__).resolve().parents[1]
BATCH = "country-expansion-batch-all-remaining-20261125.json"

class RemainingEditorialDraftTests(unittest.TestCase):
    def test_first_drafts_cover_the_entire_previously_empty_cohort(self):
        canonical = json.loads((ROOT / "country-content.json").read_text(encoding="utf-8"))["countries"]
        batch = json.loads((ROOT / BATCH).read_text(encoding="utf-8"))
        self.assertFalse(batch["publicationEligible"])
        self.assertEqual(batch["status"], "pending_photos_not_public")
        countries = batch["countries"]
        self.assertEqual(len(countries), 58)
        missing = {code for code, row in canonical.items()
                   if row["status"] == "pending" and not (row.get("portrait") or {}).get("body")}
        self.assertTrue(missing <= set(countries))
        for code, country in countries.items():
            with self.subTest(code=code):
                self.assertEqual(country["name"], canonical[code]["name"])
                self.assertFalse(country["publicationEligible"])
                self.assertEqual(country["status"], "pending")
                self.assertTrue(country["portrait"]["body"])
                self.assertEqual(country["portrait"]["sourceReviewStatus"], "independent_claim_review_required")
                self.assertFalse(country["portraitPhotos"])
                self.assertFalse(country["quiz"])
                self.assertFalse(country["travelStops"])
                self.assertEqual(len(country["travelDrafts"]), 2)
                self.assertEqual(len({d["place"] for d in country["travelDrafts"]}), 2)
                for d in country["travelDrafts"]:
                    self.assertTrue(d["editorialOnly"])
                    self.assertEqual(d["status"], "pending_source_photo_rights_and_location_review")
                    self.assertEqual(d["photoStatus"], "not_selected_or_licensed")
                    self.assertNotIn("sourceCheckedOn", d)
                    self.assertNotIn("photoAsset", d)
                    self.assertEqual(len(d["paragraphs"]), 2)
                    self.assertIn(d["sourceReviewStatus"], ("reference_page_located_claim_review_required", "independent_source_required"))
                    if d["sourceReviewStatus"] == "independent_source_required":
                        self.assertIsNone(d["sourceUrl"])
                    else:
                        self.assertEqual(urlsplit(d["sourceUrl"]).scheme, "https")
                        self.assertIn(urlsplit(d["sourceUrl"]).hostname, ["biodiversity.gov.tt","dcdd.moha.gov.bt","ecb.bt","historic.tainan.gov.tw","musee.oceano.org","nationaltrust.tt","stlucia.org","timorleste.tl","tourisme.gov.bi","volcano.si.edu","whc.unesco.org","www.bahamas.com","www.bruneitourism.com","www.ramsar.org","www.taroko.gov.tw","www.unesco.org","www.visitepalaisdemonaco.com","www.zambiatourism.com"])
                        if "referenceEvidence" in d:
                            self.assertEqual(d["referenceEvidence"]["observedOn"], "2026-11-25")
                            self.assertTrue(d["referenceEvidence"]["note"])
                    q = d["quizDraft"]
                    self.assertTrue(q["factReviewRequired"])
                    self.assertEqual(len(set(q["options"])), 3)
                    self.assertIn(q["answer"], (0, 1, 2))
                    self.assertNotIn("photoKey", q)
                if canonical[code]["status"] == "pending":
                    self.assertFalse(canonical[code]["portraitPhotos"])
                    self.assertFalse(canonical[code]["quiz"])
                    self.assertFalse(canonical[code]["travelStops"])

    def test_all_first_drafts_enter_the_existing_photo_research_queue(self):
        batch = json.loads((ROOT / BATCH).read_text(encoding="utf-8"))
        rows = list(draft_queries(ROOT))
        for code in batch["countries"]:
            matches = [r for r in rows if r["countryCode"] == code]
            self.assertEqual(len(matches), 3)
            self.assertEqual([r["role"] for r in matches], ["cover", "quizAndTravel", "quizAndTravel"])
            self.assertEqual(len({r["searchQuery"] for r in matches}), 3)

if __name__ == "__main__":
    unittest.main()
