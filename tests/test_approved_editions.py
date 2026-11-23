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
                # Historical issues retain their historical limits; modern
                # editions have neither a minimum beyond one nor a fixed cap.
                if data.get("editionType", "regular") == "regular":
                    self.assertGreaterEqual(len(public["stories"]),1)
                    if p.stem < "2026-11-23":
                        ceiling = 3 if "2026-11-17" <= p.stem < "2026-11-19" else 5
                        self.assertLessEqual(len(public["stories"]),ceiling)
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

    def test_major_individual_failure_cannot_follow_minor_story(self):
        # A model-audited priority flag is consumed by the publisher in
        # addition to the editor's ranking, without a numeric article quota.
        source=APPROVED_DIR/"2026-11-23.json"
        data=json.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(len(data["stories"]),2)
        self.assertEqual(data["approvedBy"],"automated-two-stage-review")
        self.assertFalse(any(s.get("majorPersonalFailureVerified") for s in data["stories"]))
        data["stories"][1]["majorPersonalFailureVerified"]=True
        with self.assertRaisesRegex(ValueError,"重大な個人の失敗より前"):
            validate_approved(data,"2026-11-23")

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
                # Free illustrations ship with the reader; no image-generation
                # files or external API calls are required to publish an issue.
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
