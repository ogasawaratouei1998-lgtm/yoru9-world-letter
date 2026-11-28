import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from urllib.error import HTTPError
from country_review_bundle import make_queue
from country_article_recovery import (checkpoint_research,candidate_resume,
    write_article_previews,photo_urls,discover_authority_leads)
from test_country_review_bundle import candidate,row

DAY="2026-11-28"

class ArticleRecoveryTest(unittest.TestCase):
    def test_partial_distinct_slots_are_preserved(self):
        report={"results":[row("FJ",0,["A.jpg"]),row("FJ",1,["A.jpg","B.jpg"])]}
        data={"FJ":{"name":"Fiji","status":"pending"}}
        old=make_queue(report,data)[0]
        self.assertTrue(all(s["candidate"] is None for s in old["slots"]))
        new=make_queue(report,data,allow_partial=True)[0]
        self.assertFalse(new["threeDistinctCandidates"])
        self.assertEqual([s["candidate"]["commonsPage"] for s in new["slots"] if s["candidate"]],
            [candidate("A.jpg")["commonsPage"],candidate("B.jpg")["commonsPage"]])
        self.assertFalse(new["publicationEligible"])

    def test_same_day_exact_slot_checkpoint_only(self):
        slot={"slot":0,"role":"cover","searchQuery":"Fiji"}
        plan={"countries":[{"code":"FJ","slots":[slot]}]}
        c={**candidate("A.jpg"),"publicationEligible":False}
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)/"123"
            checkpoint_research(folder,plan,DAY,[{"countryCode":"FJ","slot":0,"candidates":[c]}])
            self.assertEqual(candidate_resume(plan,DAY,Path(td)),{("FJ",0):[c]})
            self.assertEqual(candidate_resume(plan,"2026-11-29",Path(td)),{})
            slot["searchQuery"]="not Fiji"
            self.assertEqual(candidate_resume(plan,DAY,Path(td)),{})

    def test_failed_slot_is_searched_again_on_recovery(self):
        slot={"slot":0,"role":"cover","searchQuery":"Fiji"}
        plan={"countries":[{"code":"FJ","slots":[slot]}]}
        c={**candidate("A.jpg"),"publicationEligible":False}
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)/"123"
            checkpoint_research(folder,plan,DAY,[{"countryCode":"FJ","slot":0,"candidates":[c]}])
            photo=folder/"photo-review"
            photo.mkdir()
            (photo/"article-preview-checkpoint.json").write_text(json.dumps({
                "editionDate":DAY,"publicationEligible":False,
                "slots":[{"countryCode":"FJ","slot":0,"status":"download_failed"}]}))
            self.assertEqual(candidate_resume(plan,DAY,Path(td)),{})

    def test_partial_fetch_fallback_and_reuse_never_approves(self):
        report={"results":[row("FJ",0,["A.jpg"]),row("FJ",1,["B.jpg"])]}
        data={"FJ":{"name":"Fiji","status":"pending"}}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);prior=root/"prior";folder=prior/"123"/"photo-review"
            queue=make_queue(report,data,allow_partial=True)
            calls=[]
            def fetch(url):
                calls.append(url)
                if len(calls)==1:raise OSError("temporary")
                return b"x"*4000
            with patch("country_article_recovery.usable_photo",return_value=True),patch("country_article_recovery.jpeg_dimensions",return_value=(1280,960)):
                summary=write_article_previews(queue,folder,DAY,fetch=fetch,sleep_seconds=0)
                self.assertEqual(summary["downloadedUnreviewedPreviews"],2)
                self.assertEqual(len(calls),3)
                self.assertEqual(summary["fullyDownloadedCountries"],0)
                fetch2=Mock(side_effect=AssertionError("already acquired"))
                fresh=make_queue(report,data,allow_partial=True)
                result=write_article_previews(fresh,root/"new",DAY,prior=prior,fetch=fetch2,sleep_seconds=0)
                self.assertEqual(result["downloadedUnreviewedPreviews"],2)
                self.assertFalse(result["publicationEligible"])
                fetch2.assert_not_called()
                records=json.loads((root/"new"/"article-preview-checkpoint.json").read_text())["slots"]
                self.assertTrue(all(not r["visualVerified"] for r in records))

    def test_rate_limit_is_not_bypassed(self):
        queue=make_queue({"results":[row("FJ",0,["A.jpg"]),row("FJ",1,["B.jpg"])]},
                         {"FJ":{"name":"Fiji","status":"pending"}},allow_partial=True)
        fetch=Mock(side_effect=HTTPError("https://example.org",429,"slow",{},None))
        with tempfile.TemporaryDirectory() as td:
            result=write_article_previews(queue,td,DAY,fetch=fetch,sleep_seconds=0)
            self.assertEqual(result["downloadedUnreviewedPreviews"],0)
            fetch.assert_called_once()

    def test_discovery_is_untrusted_and_only_for_missing_sources(self):
        tasks={"editionDate":DAY,"tasks":[{"countryCode":"FJ","topicSourceDiscoveryRequired":True},
                                        {"countryCode":"BE","topicSourceDiscoveryRequired":False}]}
        fetch=Mock(return_value=[{"url":"https://example.org","authorityVerified":False}])
        with tempfile.TemporaryDirectory() as td:
            discover_authority_leads(Path(td),tasks,td,fetch=fetch)
            fetch.assert_called_once_with("FJ")
            result=json.loads((Path(td)/"authority-leads.json").read_text())
            self.assertFalse(result["publicationEligible"])
            self.assertNotIn("BE",result["countries"])
