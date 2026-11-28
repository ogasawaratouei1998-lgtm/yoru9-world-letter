"""Regression checks for extending a recovered preview without losing approval."""
import copy
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from release_contract import (
    should_refill_recovered, load_refill_seed, save_refilled_preview, recover_review,
)
from test_news_variable_edition_count import approved_current_issue, DAY
from editorial_resume import EditorialResume


class SameDayPreviewRefillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root/"data"/"approved"/(DAY+".json")
        self.target.parent.mkdir(parents=True)
        for name in ("index.html", "world-passport.js", "travel-stops.json"):
            (self.root/name).touch()
        self.seed = approved_current_issue(1)
        self.target.write_text(json.dumps(self.seed), encoding="utf-8")

    def now(self, hour, day=DAY):
        return datetime.fromisoformat(day+f"T{hour:02d}:00:00").replace(tzinfo=ZoneInfo("Asia/Tokyo"))

    def test_automatic_recovered_preview_at_any_count_before_final_window(self):
        check = lambda state,count,hour: should_refill_recovered(
            self.root, DAY, state, count, self.now(hour))
        self.assertTrue(check("recovered",1,18))
        self.assertFalse(check("recovered",1,19))
        self.assertFalse(check("recovered",0,18))
        self.assertFalse(check("recovered",2,18))  # mismatched count, not a count limit
        for count in (2,3,5,6,12):
            with self.subTest(count=count):
                self.target.write_text(json.dumps(approved_current_issue(count)),encoding="utf-8")
                self.assertTrue(check("recovered",count,18))
                self.assertEqual(len(load_refill_seed(self.root,DAY)["stories"]),count)
        self.target.write_text(json.dumps(self.seed),encoding="utf-8")
        self.assertTrue(check("existing",1,18))
        self.assertTrue(check("extended",1,18))
        self.assertFalse(check("existing",1,19))
        self.assertFalse(should_refill_recovered(self.root, DAY, "recovered",1,
                                               self.now(18,"2026-11-24")))
        manual = {**self.seed,"approvedBy":"chatgpt-editorial-review"}
        self.target.write_text(json.dumps(manual), encoding="utf-8")
        self.assertFalse(check("recovered",1,18))
        self.assertFalse(check("existing",1,18))
        with self.assertRaises(ValueError):
            load_refill_seed(self.root,DAY)

    def test_valid_addition_preserves_original_and_accepts_variable_count(self):
        seed = load_refill_seed(self.root,DAY)
        expanded = {**seed,"stories":seed["stories"]+approved_current_issue(3)["stories"][1:]}
        self.assertTrue(save_refilled_preview(self.root,DAY,seed,expanded))
        saved=json.loads(self.target.read_text())
        self.assertEqual(saved["stories"][0],seed["stories"][0])
        self.assertEqual(len(saved["stories"]),3)

    def test_repeated_refill_never_stops_because_of_article_count(self):
        for count in (2,5,9,12):
            with self.subTest(count=count):
                seed=load_refill_seed(self.root,DAY)
                old_count=len(seed["stories"])
                self.assertTrue(should_refill_recovered(
                    self.root,DAY,"recovered",old_count,self.now(18)))
                additions=approved_current_issue(count)["stories"][old_count:]
                expanded={**seed,"stories":seed["stories"]+additions}
                self.assertTrue(save_refilled_preview(self.root,DAY,seed,expanded))
                self.assertEqual(load_refill_seed(self.root,DAY)["stories"],expanded["stories"])
                self.assertTrue(all(story in expanded["stories"] for story in seed["stories"]))

    def test_no_addition_keeps_bytes_and_invalid_addition_does_not_replace(self):
        seed=load_refill_seed(self.root,DAY)
        before=self.target.read_bytes()
        self.assertFalse(save_refilled_preview(self.root,DAY,seed,seed))
        invalid=approved_current_issue(2)
        invalid["stories"][1]["humorSafe"]=False
        with self.assertRaises(ValueError):
            save_refilled_preview(self.root,DAY,seed,invalid)
        self.assertEqual(self.target.read_bytes(),before)

    def test_cannot_rewrite_original_even_with_more_articles(self):
        seed=load_refill_seed(self.root,DAY)
        expanded=approved_current_issue(2)
        expanded["stories"][0]["title"]+="変更"
        with self.assertRaises(ValueError):
            save_refilled_preview(self.root,DAY,seed,expanded)
        self.assertEqual(json.loads(self.target.read_text()),seed)

    def test_archived_preview_never_refilled(self):
        archive=self.root/"data"/"archive"/(DAY+".json")
        archive.parent.mkdir()
        archive.touch()
        self.assertFalse(should_refill_recovered(self.root,DAY,"recovered",1,self.now(18)))
        with self.assertRaises(ValueError):
            load_refill_seed(self.root,DAY)

    def put_artifact(self,run,payload):
        p=self.root/"incoming"/str(run)/(DAY+".json")
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(payload),encoding="utf-8")

    def test_committed_automatic_issue_extends_across_all_handoffs(self):
        incoming=self.root/"incoming"
        self.assertEqual(recover_review(self.root,DAY,incoming,allow_extension=True),("existing",1))
        self.assertTrue(should_refill_recovered(self.root,DAY,"existing",1,self.now(18)))
        expanded={**self.seed,"stories":approved_current_issue(3)["stories"]}
        self.put_artifact(100,expanded)
        self.assertEqual(recover_review(self.root,DAY,incoming,allow_extension=True),("extended",3))
        self.assertTrue(should_refill_recovered(self.root,DAY,"extended",3,self.now(18)))
        bigger={**self.seed,"stories":approved_current_issue(5)["stories"]}
        self.put_artifact(200,bigger)
        self.put_artifact(300,self.seed)  # newest artifact is stale
        self.assertEqual(recover_review(self.root,DAY,incoming,allow_extension=True),("extended",5))
        self.assertEqual(json.loads(self.target.read_text()),bigger)
        self.assertEqual(recover_review(self.root,DAY,incoming,allow_extension=True),("existing",5))

    def test_artifact_cannot_replace_curated_special_or_archived_issue(self):
        expanded={**self.seed,"stories":approved_current_issue(3)["stories"]}
        self.put_artifact(100,expanded)
        for seed in ({**self.seed,"approvedBy":"chatgpt-editorial-review"},
                     {**self.seed,"editionType":"special","title":"世界の大失敗ニュース・編集特集号","specialReason":"今年の意外な判断を振り返るための編集特集です。"}):
            self.target.write_text(json.dumps(seed))
            before=self.target.read_bytes()
            self.assertEqual(recover_review(self.root,DAY,self.root/"incoming",allow_extension=True),("existing",1))
            self.assertEqual(self.target.read_bytes(),before)
        self.target.write_text(json.dumps(self.seed))
        archive=self.root/"data"/"archive"/(DAY+".json")
        archive.parent.mkdir()
        archive.write_text("{}")
        self.assertEqual(recover_review(self.root,DAY,self.root/"incoming",allow_extension=True),("archived",0))
        self.assertEqual(json.loads(self.target.read_text()),self.seed)

    def test_invalid_or_forked_expansion_does_not_erase_approved_material(self):
        good={**self.seed,"stories":approved_current_issue(2)["stories"]}
        self.put_artifact(100,good)
        fork={**self.seed,"stories":[self.seed["stories"][0],*approved_current_issue(5)["stories"][2:]]}
        self.put_artifact(200,fork)
        invalid={**self.seed,"stories":approved_current_issue(4)["stories"]}
        invalid["stories"][-1]["humorSafe"]=False
        self.put_artifact(300,invalid)
        altered=copy.deepcopy({**self.seed,"stories":approved_current_issue(5)["stories"]})
        altered["stories"][0]["title"]+="変更"
        self.put_artifact(400,altered)
        self.assertEqual(recover_review(self.root,DAY,self.root/"incoming",allow_extension=True),("extended",2))
        self.assertEqual(json.loads(self.target.read_text()),good)

    def test_all_completed_group_urls_are_remembered(self):
        path=self.root/"queue.json"
        resume=EditorialResume(DAY,path)
        urls=["https://www.bbc.com/news/a","https://apnews.com/article/b"]
        group={"articles":[{"url":url} for url in urls]}
        resume.record_attempt(group)
        resumed=EditorialResume(DAY,path)
        self.assertEqual([resumed.rank(url) for url in urls],[2,2])
        self.assertEqual(resumed.rank("https://www.bbc.com/news/c"),1)


if __name__=="__main__":
    unittest.main()
