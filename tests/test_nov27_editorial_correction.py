"""A dated correction must not be misrepresented as an automatic quality pass."""
import json
from pathlib import Path
import unittest
from publish_approved import validate_approved
from local_editorial import japanese_copy_fields

ROOT=Path(__file__).resolve().parents[1]
DAY="2026-11-27"

class Nov27CorrectionTest(unittest.TestCase):
    def test_corrected_issue_is_consistent_and_original_is_retained(self):
        read=lambda path:json.loads((ROOT/path).read_text(encoding="utf-8"))
        approved=read("data/approved/"+DAY+".json")
        archive=read("data/archive/"+DAY+".json")
        original=read("data/archive/revisions/"+DAY+"-before-correction.json")
        self.assertEqual(len(original["stories"]),3)
        self.assertEqual(len(archive["stories"]),1)
        self.assertEqual(validate_approved(approved,DAY),archive)
        current=read("data/current.json")
        if current["editionDate"]==DAY:self.assertEqual(current,archive)
        story=archive["stories"][0]
        self.assertFalse(japanese_copy_fields(story,("title","summary","detail","label","quip")))
        self.assertIn("サンチェス",story["title"])
        self.assertIn("26日",story["summary"])
        self.assertIn("撤回",story["correctionNote"])
        self.assertNotIn("editorialScores",approved["stories"][0])
        self.assertEqual(approved["approvedBy"],"editorial-correction-2026-11-27")
        self.assertTrue((ROOT/"assets/news/spain-stadium-name-correction.svg").is_file())
        with self.assertRaises(ValueError):
            validate_approved({**approved,"editionDate":"2026-11-28"},"2026-11-28")

if __name__=="__main__":unittest.main()
