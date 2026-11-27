"""Regression checks for extending a recovered preview without losing approval."""
import copy
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from release_contract import (
    should_refill_recovered, load_refill_seed, save_refilled_preview,
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

    def test_only_automatic_recovered_one_story_before_final_window(self):
        check = lambda state,count,hour: should_refill_recovered(
            self.root, DAY, state, count, self.now(hour))
        self.assertTrue(check("recovered",1,18))
        self.assertFalse(check("recovered",1,19))
        self.assertFalse(check("recovered",2,18))
        self.assertFalse(check("existing",1,18))
        self.assertFalse(should_refill_recovered(self.root, DAY, "recovered",1,
                                               self.now(18,"2026-11-24")))
        manual = {**self.seed,"approvedBy":"chatgpt-editorial-review"}
        self.target.write_text(json.dumps(manual), encoding="utf-8")
        self.assertFalse(check("recovered",1,18))
        with self.assertRaises(ValueError):
            load_refill_seed(self.root,DAY)

    def test_valid_addition_preserves_original_and_accepts_variable_count(self):
        seed = load_refill_seed(self.root,DAY)
        expanded = {**seed,"stories":seed["stories"]+approved_current_issue(3)["stories"][1:]}
        self.assertTrue(save_refilled_preview(self.root,DAY,seed,expanded))
        saved=json.loads(self.target.read_text())
        self.assertEqual(saved["stories"][0],seed["stories"][0])
        self.assertEqual(len(saved["stories"]),3)

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
