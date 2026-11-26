import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from send_release_notice import notice_for,dispatch
JST=ZoneInfo("Asia/Tokyo")

class PushDispatchTest(unittest.TestCase):
    def test_unpublished_cannot_send(self):
        self.assertIsNone(notice_for({"status":"approved","editionDate":"2026-11-11","stories":[{}]*5},
                      datetime(2026,11,11,21,40,tzinfo=JST)))
    def test_past_edition_cannot_send(self):
        self.assertIsNone(notice_for({"status":"published","editionDate":"2026-11-10","stories":[{}]*5},
                      datetime(2026,11,11,21,40,tzinfo=JST)))
    def test_five_published_special_story_notice(self):
        p=notice_for({"status":"published","editionDate":"2026-11-11","editionType":"special","stories":[{}]*5},
                     datetime(2026,11,11,21,40,tzinfo=JST))
        self.assertEqual(p["editionDate"],"2026-11-11")
        self.assertIn("特集",p["body"])
    def test_regular_one_to_three_published_stories_are_eligible(self):
        for count in (1,2,3):
            with self.subTest(stories=count):
                issue={"status":"published","editionDate":"2026-11-17",
                       "editionType":"regular","stories":[{}]*count}
                payload=notice_for(issue,datetime(2026,11,17,21,25,tzinfo=JST))
                self.assertIsNotNone(payload)
                self.assertIn(str(count)+"本",payload["body"])
                self.assertEqual(payload["editionDate"],"2026-11-17")

    def test_november_19_onwards_one_to_five_published_stories_are_eligible(self):
        for count in (1, 2, 3, 4, 5):
            with self.subTest(stories=count):
                issue={"status":"published","editionDate":"2026-11-19",
                       "editionType":"regular","stories":[{}]*count}
                payload=notice_for(issue,datetime(2026,11,19,21,51,tzinfo=JST))
                self.assertIsNotNone(payload)
                self.assertEqual(payload["editionDate"],"2026-11-19")
                self.assertIn(str(count)+"本",payload["body"])

    def test_november_19_zero_or_six_stories_never_notify(self):
        for count in (0, 6):
            with self.subTest(stories=count):
                self.assertIsNone(notice_for(
                    {"status":"published","editionDate":"2026-11-19",
                     "editionType":"regular","stories":[{}]*count},
                    datetime(2026,11,19,21,51,tzinfo=JST)))

    def test_new_regular_issues_have_no_number_quota_for_notification(self):
        for day in ("2026-11-21","2026-11-23"):
            for count in (0,1,2,3,4,5,6):
                with self.subTest(day=day,count=count):
                    doc={"status":"published","editionDate":day,
                         "editionType":"regular","stories":[{}]*count}
                    at=datetime.fromisoformat(day+"T21:45:00").replace(tzinfo=JST)
                    result=notice_for(doc,at)
                    self.assertEqual(result is not None,count>=1)
                    if result:
                        self.assertIn(str(count)+"本",result["body"])

    def test_new_special_issues_have_no_number_quota_for_notification(self):
        for count in (0,1,2,5,6):
            with self.subTest(count=count):
                issue={"status":"published","editionDate":"2026-11-23",
                       "editionType":"special","stories":[{}]*count}
                result=notice_for(issue,datetime(2026,11,23,22,0,tzinfo=JST))
                self.assertEqual(result is not None,count>=1)
                if result:
                    self.assertIn("特集",result["body"])
                    self.assertIn(str(count)+"本",result["body"])

    def test_four_story_notice_not_sent_prior_to_nine(self):
        self.assertIsNone(notice_for(
            {"status":"published","editionDate":"2026-11-19",
             "editionType":"regular","stories":[{}]*4},
            datetime(2026,11,19,20,59,tzinfo=JST)))

    def test_legacy_regular_four_or_five_and_empty_do_not_notify(self):
        for count in (0,4,5):
            with self.subTest(stories=count):
                self.assertIsNone(notice_for(
                    {"status":"published","editionDate":"2026-11-17",
                     "stories":[{}]*count},
                    datetime(2026,11,17,21,25,tzinfo=JST)))

    def test_push_notification_is_not_sent_before_nine_jst(self):
        self.assertIsNone(notice_for(
            {"status":"published","editionDate":"2026-11-17","stories":[{}]*3},
            datetime(2026,11,17,20,59,tzinfo=JST)))

    def test_current_two_story_release_is_notification_eligible(self):
        import json
        from pathlib import Path
        issue=json.loads((Path(__file__).resolve().parents[1]/"data/current.json").read_text(encoding="utf-8"))
        if issue.get("editionDate")=="2026-11-23":
            self.assertEqual(len(issue["stories"]),2)
            payload=notice_for(issue,datetime(2026,11,23,22,15,tzinfo=JST))
            self.assertIsNotNone(payload)
            self.assertEqual(payload["editionDate"],"2026-11-23")

    def test_workflow_reports_distinct_safe_dispatch_outcomes(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from send_release_notice import record_notice_result
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/"output"
            with patch.dict("os.environ",{"GITHUB_OUTPUT":str(output)}):
                for result in ("accepted","not_configured","not_eligible","failed"):
                    record_notice_result(result)
                with self.assertRaises(ValueError):
                    record_notice_result("unknown")
            self.assertEqual(output.read_text().splitlines(),
                             ["result=accepted","result=not_configured","result=not_eligible","result=failed"])

    def test_missing_backend_does_not_send(self):
        self.assertFalse(dispatch("","",{"editionDate":"2026-11-11"}))
    def test_insecure_dispatch_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            dispatch("http://example.org/dispatch","secret",{"editionDate":"2026-11-11"})

if __name__=="__main__":unittest.main()
