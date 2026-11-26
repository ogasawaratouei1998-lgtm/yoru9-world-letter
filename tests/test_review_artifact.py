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

    def test_staged_review_publishes_only_after_2100_jst(self):
        from datetime import datetime
        from publish_approved import publish
        from shutil import copyfile

        artifact=stage_review(self.root,DAY,self.destination)
        self.assertIsNotNone(artifact)
        # Simulate a separate GitHub Actions release job recovering the artifact.
        self.source.unlink()
        copyfile(artifact,self.source)
        early=datetime.fromisoformat("2026-11-17T20:59:00+09:00")
        late=datetime.fromisoformat("2026-11-17T21:05:00+09:00")
        self.assertFalse(publish(self.root,early))
        self.assertFalse((self.root/"data"/"current.json").exists())
        self.assertTrue(publish(self.root,late))
        archive=self.root/"data"/"archive"/(DAY+".json")
        current=json.loads((self.root/"data"/"current.json").read_text(encoding="utf-8"))
        self.assertEqual(current,json.loads(archive.read_text(encoding="utf-8")))
        self.assertEqual(current["editionDate"],DAY)
        self.assertTrue(1<=len(current["stories"])<=3)
        self.assertIsNone(stage_review(self.root,DAY,self.destination))
        self.assertFalse(publish(self.root,late))

    def test_single_verified_original_is_stageable(self):
        item=json.loads(self.source.read_text(encoding="utf-8"))
        from trusted_originals import SINGLE_SOURCE_NOTE
        story=item["stories"][0]
        story["sourceUrl"]="https://www.bbc.com/news/articles/verified-local-report"
        story["verificationUrls"]=[story["sourceUrl"]]
        story["sourceBasis"]="original-report"
        story["originalReportingVerified"]=True
        story["attributionNote"]=SINGLE_SOURCE_NOTE
        self.source.write_text(json.dumps(item,ensure_ascii=False),encoding="utf-8")
        staged=stage_review(self.root,DAY,self.destination)
        self.assertIsNotNone(staged)
        self.assertEqual(json.loads(staged.read_text(encoding="utf-8"))["stories"][0]["verificationUrls"],
                         [item["stories"][0]["sourceUrl"]])

    def test_release_handoff_skips_invalid_latest_and_preserves_existing(self):
        from release_contract import recover_review
        incoming=self.root/"incoming"
        original=self.source.read_bytes()
        self.source.unlink()
        for i in ("100","200"):
            folder=incoming/i
            folder.mkdir(parents=True)
            (folder/(DAY+".json")).write_bytes(original if i=="100" else b'{"status":"bad"}')
        self.assertEqual(recover_review(self.root,DAY,incoming,require_assets=False)[0],"recovered")
        self.assertEqual(json.loads(self.source.read_bytes()),json.loads(original))
        self.assertEqual(recover_review(self.root,DAY,incoming,require_assets=False)[0],"existing")
        (self.root/"data"/"archive"/(DAY+".json")).write_text("{}")
        self.assertEqual(recover_review(self.root,DAY,incoming,require_assets=False)[0],"archived")

    def test_modern_handoff_missing_reader_assets_fails_closed(self):
        from release_contract import validate_release_input
        data=json.loads((ROOT/"data"/"approved"/"2026-11-25.json").read_text())
        with self.assertRaisesRegex(ValueError,"Missing release reader assets"):
            validate_release_input(self.root,data,"2026-11-25",require_assets=True)

    def test_no_sources_is_not_stageable(self):
        item=json.loads(self.source.read_text(encoding="utf-8"))
        item["stories"][0]["verificationUrls"]=[]
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
