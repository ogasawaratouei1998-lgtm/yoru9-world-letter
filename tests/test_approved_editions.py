"""Ensure all committed, manually approved editions satisfy release rules."""
import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from publish_approved import publish, validate_approved

ROOT=Path(__file__).resolve().parents[1]
APPROVED_DIR=ROOT/"data"/"approved"

class ApprovedEditionTest(unittest.TestCase):
    def test_all_approved_editions_validate(self):
        for p in sorted(APPROVED_DIR.glob("????-??-??.json")):
            with self.subTest(issue=p.name):
                data=json.loads(p.read_text(encoding="utf-8"))
                public=validate_approved(data,p.stem)
                self.assertEqual(public["status"],"published")
                # Mirror the publisher's date-scoped limits: normal editions
                # from Nov 19 onward permit 1–5 independently checked stories.
                if data.get("editionType", "regular") == "regular":
                    ceiling = 3 if "2026-11-17" <= p.stem < "2026-11-19" else 5
                    self.assertTrue(1 <= len(public["stories"]) <= ceiling)
                else:
                    self.assertEqual(len(public["stories"]), 5)
                self.assertTrue(all("editorVerified" not in story for story in public["stories"]))
                # Public source URLs are intentional reader-facing evidence links;
                # internal editorial assessments must still remain private.
                # New regular editions (Nov 17 onward) may use one
                # independently verified original publisher. Older approved
                # editions and specials retain the two-source contract.
                one_original_ok = (
                    data.get("editionType", "regular") == "regular"
                    and p.stem >= "2026-11-17"
                )
                minimum_sources = 1 if one_original_ok else 2
                self.assertTrue(all(len(story.get("verificationUrls", [])) >= minimum_sources
                                    for story in public["stories"]))
                self.assertTrue(all("evidence" not in story and "editorVerified" not in story
                                    and "humorSafe" not in story
                                    for story in public["stories"]))

    def test_approved_issue_releases_only_after_jst_nine(self):
        """End-to-end dry-run on a temporary directory (never updates the published site)."""
        for source in sorted(APPROVED_DIR.glob("????-??-??.json")):
            with self.subTest(issue=source.name), tempfile.TemporaryDirectory() as td:
                root=Path(td)
                approved=root/"data"/"approved"
                archive=root/"data"/"archive"
                approved.mkdir(parents=True)
                archive.mkdir(parents=True)
                (approved/source.name).write_bytes(source.read_bytes())
                # This test models the publisher after image preparation. The
                # production workflow must still generate the actual JPEG/WebP
                # artwork and verify all images before writing a public issue.
                for story in json.loads(source.read_text(encoding="utf-8"))["stories"]:
                    if story.get("imagePath"):
                        target=root/story["imagePath"]
                        target.parent.mkdir(parents=True,exist_ok=True)
                        target.write_bytes(b"RIFF"+(22000).to_bytes(4,"little")+b"WEBP"+b"0"*21900)
                (root/"data"/"current.json").write_text(
                    json.dumps({"status":"draft","editionDate":None,"stories":[]}),encoding="utf-8")
                (archive/"index.json").write_text(json.dumps({"issues":[]}),encoding="utf-8")
                before=(root/"data"/"current.json").read_bytes()
                self.assertFalse(publish(root,datetime.fromisoformat(source.stem+"T20:59:00+09:00")))
                self.assertEqual((root/"data"/"current.json").read_bytes(),before)
                self.assertTrue(publish(root,datetime.fromisoformat(source.stem+"T21:07:00+09:00")))
                updated=json.loads((root/"data"/"current.json").read_text(encoding="utf-8"))
                self.assertEqual(updated["editionDate"],source.stem)
                self.assertEqual(updated["status"],"published")
                self.assertEqual(len(updated["stories"]), len(json.loads(source.read_text(encoding="utf-8"))["stories"]))
                self.assertTrue((archive/(source.stem+".json")).is_file())
                self.assertEqual(len(json.loads((archive/"index.json").read_text())["issues"]),1)
                self.assertFalse(publish(root,datetime.fromisoformat(source.stem+"T21:15:00+09:00")))

if __name__=="__main__":
    unittest.main()
