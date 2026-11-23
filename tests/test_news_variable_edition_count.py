"""Current nightly issues have no article-number quota, but retain all reviews."""
import copy
import json
from pathlib import Path
import unittest

from publish_approved import validate_approved

ROOT=Path(__file__).resolve().parents[1]
DAY="2026-11-23"


def approved_current_issue(count):
    historical=json.loads((ROOT/"data/approved/2026-11-20.json").read_text(encoding="utf-8"))
    seed=historical["stories"][0]
    stories=[]
    for index in range(count):
        row=copy.deepcopy(seed)
        row.update({
            "id":f"editorial-test-event-{index}",
            "sourceUrl":f"https://www.bbc.com/news/test-unique-event-{index}",
            "verificationUrls":[f"https://www.bbc.com/news/test-unique-event-{index}"],
            "reported":DAY,
            "eventKey":f"editorial-test-event-key-{index}",
            "editorVerified":True,
            "editorQualityVerified":True,
            "humorSafe":True,
            "humanFailureVerified":True,
            "surpriseVerified":True,
            "stageTsukkomiVerified":True,
            "editorialScores":{"surprise":5,"mistakeClarity":5,
                               "outcomeIrony":5,"safety":5},
        })
        row.pop("correctionNote",None)
        stories.append(row)
    return {"status":"approved","editionDate":DAY,
            "title":"検証済み記事の可変本数公開テスト",
            "editionType":"regular","editorApproved":True,
            "humorReviewed":True,"approvedBy":"automated-two-stage-review",
            "stories":stories}


class NoDailyStoryQuotaTests(unittest.TestCase):
    def test_one_two_three_five_and_six_are_valid_without_padding_or_dropping(self):
        for count in (1,2,3,5,6):
            with self.subTest(count=count):
                doc=approved_current_issue(count)
                public=validate_approved(doc,DAY)
                self.assertEqual(len(public["stories"]),count)
                self.assertEqual([s["id"] for s in public["stories"]],
                                 [s["id"] for s in doc["stories"]])

    def test_zero_stories_remains_unpublishable(self):
        with self.assertRaisesRegex(ValueError,"1本もない"):
            validate_approved(approved_current_issue(0),DAY)

    def test_editorial_safety_gate_cannot_be_bypassed_by_short_edition(self):
        for field,value in [
            ("humorSafe",False),
            ("editorQualityVerified",False),
            ("surpriseVerified",False),
            ("stageTsukkomiVerified",False),
        ]:
            with self.subTest(field=field):
                issue=approved_current_issue(1)
                issue["stories"][0][field]=value
                with self.assertRaises(ValueError):
                    validate_approved(issue,DAY)

    def test_quality_rubric_still_required_for_every_story_in_long_issue(self):
        doc=approved_current_issue(6)
        doc["stories"][-1]["editorialScores"]["safety"]=4
        with self.assertRaises(ValueError):
            validate_approved(doc,DAY)


if __name__=="__main__":
    unittest.main()
