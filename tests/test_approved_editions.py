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
                self.assertEqual(len(public["stories"]),5)
                self.assertTrue(all("editorVerified" not in story for story in public["stories"]))
                self.assertTrue(all("verificationUrls" not in story for story in public["stories"]))

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
                self.assertEqual(len(updated["stories"]),5)
                self.assertTrue((archive/(source.stem+".json")).is_file())
                self.assertEqual(len(json.loads((archive/"index.json").read_text())["issues"]),1)
                self.assertFalse(publish(root,datetime.fromisoformat(source.stem+"T21:15:00+09:00")))

if __name__=="__main__":
    unittest.main()
