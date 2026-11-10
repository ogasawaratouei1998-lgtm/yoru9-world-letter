"""Ensure all committed, manually approved editions satisfy release rules."""
import json
from pathlib import Path
import unittest
from publish_approved import validate_approved

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

if __name__=="__main__":
    unittest.main()
