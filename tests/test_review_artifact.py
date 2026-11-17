"""Only final publisher-valid, current-date approvals can enter review artifacts."""
import json
import tempfile
import unittest
from pathlib import Path
from stage_review import stage_review

ROOT=Path(__file__).resolve().parents[1]
DAY="2026-11-17"


class ReviewStageTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        (self.root/"data"/"approved").mkdir(parents=True)
        (self.root/"data"/"archive").mkdir(parents=True)
        self.source=self.root/"data"/"approved"/(DAY+".json")
        self.source.write_bytes((ROOT/"data"/"approved"/(DAY+".json")).read_bytes())
        self.destination=self.root/"staged"

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_exact_valid_review_is_uploaded(self):
        dest=stage_review(self.root,DAY,self.destination)
        self.assertIsNotNone(dest)
        self.assertEqual(dest.read_bytes(),self.source.read_bytes())
        self.assertEqual([p.name for p in self.destination.iterdir()],[DAY+".json"])

    def test_missing_review_does_not_stage_file(self):
        self.source.unlink()
        self.assertIsNone(stage_review(self.root,DAY,self.destination))
        self.assertFalse(self.destination.exists())

    def test_published_issue_does_not_stage_file(self):
        (self.root/"data"/"archive"/(DAY+".json")).write_text("{}")
        self.assertIsNone(stage_review(self.root,DAY,self.destination))

    def test_single_source_is_not_publishable(self):
        item=json.loads(self.source.read_text(encoding="utf-8"))
        item["stories"][0]["verificationUrls"]=[item["stories"][0]["sourceUrl"]]
        self.source.write_text(json.dumps(item,ensure_ascii=False),encoding="utf-8")
        with self.assertRaises(ValueError):
            stage_review(self.root,DAY,self.destination)
        self.assertFalse(self.destination.exists())

    def test_unverified_story_is_not_publishable(self):
        item=json.loads(self.source.read_text(encoding="utf-8"))
        item["stories"][0]["editorVerified"]=False
        self.source.write_text(json.dumps(item,ensure_ascii=False),encoding="utf-8")
        with self.assertRaises(ValueError):
            stage_review(self.root,DAY,self.destination)
        self.assertFalse(self.destination.exists())


if __name__=="__main__":
    unittest.main()
