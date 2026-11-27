"""Regression tests for speculative enrichment and explicit review boundary."""
import json
import tempfile
import unittest
from pathlib import Path
from country_review_apply import digest, reviewed_record, check_reviewed_photos
from country_material_prefetch import merge_prefetch, prefetch

class CountryReviewHandoffTest(unittest.TestCase):
    def setUp(self):
        self.old={"name":"Belgium","status":"approved","travelStops":{},"quiz":[],"portraitPhotos":[],"highlights":[]}
        self.new={**self.old,"highlights":[{"title":"Reviewed topic"}]}
        self.packet={"version":1,"editionDate":"2026-11-28","countryCode":"BE",
            "sourceReviewed":True,"editorialReviewed":True,"reviewer":"independent editor",
            "reviewEvidence":["explicit source review"],"baseDigest":digest(self.old),
            "recordDigest":digest(self.new),"reviewedRecord":self.new}
    def test_reviewed_record_is_idempotent_and_bound_to_exact_bytes(self):
        self.assertEqual(reviewed_record(self.old,self.packet,"2026-11-28","BE"),self.new)
        self.assertEqual(reviewed_record(self.new,self.packet,"2026-11-28","BE"),self.new)
        with self.assertRaises(ValueError):
            reviewed_record(self.old,{**self.packet,"recordDigest":"wrong"},"2026-11-28","BE")
        with self.assertRaises(ValueError):
            reviewed_record({**self.old,"highlights":[{"title":"newer"}]},self.packet,"2026-11-28","BE")
    def test_candidate_or_wrong_day_never_approved(self):
        for packet in ({**self.packet,"editorialReviewed":False},{**self.packet,"countryCode":"FR"},
                       {**self.packet,"editionDate":"2026-11-27"}):
            with self.assertRaises(ValueError):
                reviewed_record(self.old,packet,"2026-11-28","BE")
    def test_photo_changes_require_separate_review(self):
        new={**self.new,"quiz":[{"photoKey":"example"}]}
        packet={**self.packet,"reviewedRecord":new,"recordDigest":digest(new)}
        with self.assertRaises(ValueError):
            reviewed_record(self.old,packet,"2026-11-28","BE")
        self.assertEqual(reviewed_record(self.old,{**packet,"visualReviewed":True,"licenseReviewed":True},
                         "2026-11-28","BE"),new)
    def test_photo_change_defers_without_verified_cache(self):
        new={**self.new,"quiz":[{"photoKey":"example"}]}
        with self.assertRaises(ValueError):
            check_reviewed_photos(self.old,new,self.packet,None)
        check_reviewed_photos(self.old,self.new,self.packet,None)
    def test_prefetch_has_bounded_scope_and_never_approves(self):
        root=Path(__file__).resolve().parents[1]
        seen=[]
        def discover(tasks):
            seen.extend(tasks["tasks"])
            return {"editionDate":tasks["editionDate"],"countries":[],"publicationEligible":False}
        with tempfile.TemporaryDirectory() as td:
            report=prefetch(root,[{"country":c} for c in ("BE","FR","ES","US","GB","JP")],
                            "2027-01-01",Path(td)/"drafts.json",discover=discover)
        self.assertLessEqual(len(seen),4)
        self.assertLessEqual(sum(len(t["officialTopicSources"]) for t in seen),4)
        self.assertFalse(report["publicationEligible"])
    def test_prefetch_wrong_day_and_country_are_not_reused(self):
        tasks={"editionDate":"2026-11-28","tasks":[{"countryCode":"BE","officialTopicSources":[],
                                                   "missingTopicDates":["2026-11-28"]}]}
        fresh={"editionDate":"2026-11-28","countries":[{"countryCode":"BE","candidates":[]}],"publicationEligible":False}
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"prefetch.json"
            p.write_text(json.dumps({"editionDate":"2026-11-27","publicationEligible":False,"countries":[]}))
            self.assertEqual(merge_prefetch(tasks,fresh,p),fresh)
