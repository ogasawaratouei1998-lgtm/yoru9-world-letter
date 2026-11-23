"""Unit tests for release monitoring, which does not publish anything."""
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from check_release_health import check_release


class HealthCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data" / "approved").mkdir(parents=True)
        (self.root / "data" / "archive").mkdir(parents=True)
        self.time = datetime.fromisoformat("2026-11-11T22:27:00+09:00")
    def tearDown(self):
        self.tmp.cleanup()
    def test_unapproved_day_skips_without_false_alarm(self):
        ok, _ = check_release(self.root, self.time)
        self.assertTrue(ok)
    def test_missing_published_edition_raises_alert(self):
        (self.root / "data" / "approved" / "2026-11-11.json").write_text('{"editionType":"special","stories":[{},{},{},{},{}]}')
        ok, _ = check_release(self.root, self.time)
        self.assertFalse(ok)
    def test_published_edition_and_archive_succeed(self):
        import json
        (self.root / "data" / "approved" / "2026-11-11.json").write_text('{"editionType":"special","stories":[{},{},{},{},{}]}')
        (self.root / "data" / "current.json").write_text(json.dumps({"status":"published","editionDate":"2026-11-11","stories":[{}]*5}))
        (self.root / "data" / "archive" / "2026-11-11.json").write_text(json.dumps({"status":"published","editionDate":"2026-11-11","stories":[{}]*5}))
        (self.root / "data" / "archive" / "index.json").write_text('{"issues":[{"date":"2026-11-11"}]}')
        self.assertTrue(check_release(self.root, self.time)[0])
    def test_current_three_story_release_is_healthy(self):
        import json
        self.time=datetime.fromisoformat("2026-11-17T22:27:00+09:00")
        (self.root/"data"/"approved"/"2026-11-17.json").write_text(
            json.dumps({"editionType":"regular","stories":[{}]*3}))
        issue={"status":"published","editionDate":"2026-11-17","stories":[{}]*3}
        (self.root/"data"/"current.json").write_text(json.dumps(issue))
        (self.root/"data"/"archive"/"2026-11-17.json").write_text(json.dumps(issue))
        (self.root/"data"/"archive"/"index.json").write_text('{"issues":[{"date":"2026-11-17"}]}')
        ok,detail=check_release(self.root,self.time)
        self.assertTrue(ok,detail)
        self.assertIn("3本",detail)

    def test_four_and_five_story_editions_are_healthy_after_november_19(self):
        import json
        for count in (4, 5):
            with self.subTest(approved_count=count):
                day="2026-11-20"
                now=datetime.fromisoformat(day+"T22:27:00+09:00")
                issue={"status":"published","editionDate":day,"stories":[{}]*count}
                (self.root/"data"/"approved"/(day+".json")).write_text(
                    json.dumps({"editionType":"regular","stories":[{}]*count}))
                (self.root/"data"/"current.json").write_text(json.dumps(issue))
                (self.root/"data"/"archive"/(day+".json")).write_text(json.dumps(issue))
                (self.root/"data"/"archive"/"index.json").write_text(
                    json.dumps({"issues":[{"date":day}]}))
                ok,message=check_release(self.root,now)
                self.assertTrue(ok,message)
                self.assertIn(str(count)+"本",message)

    def test_new_regular_monitor_accepts_any_nonzero_story_count(self):
        import json
        day="2026-11-21"
        for count in (0,1,2,3,4,5,6):
            with self.subTest(count=count):
                issue={"status":"published","editionDate":day,"stories":[{}]*count}
                (self.root/"data/approved"/(day+".json")).write_text(
                    json.dumps({"editionType":"regular","stories":[{}]*count}))
                (self.root/"data/current.json").write_text(json.dumps(issue))
                (self.root/"data/archive"/(day+".json")).write_text(json.dumps(issue))
                (self.root/"data/archive/index.json").write_text(
                    json.dumps({"issues":[{"date":day}]}))
                ok,_=check_release(self.root,
                         datetime.fromisoformat(day+"T22:27:00+09:00"))
                self.assertEqual(ok,count>=1)

    def test_six_story_edition_is_invalid_and_alerts(self):
        import json
        day="2026-11-20"
        (self.root/"data"/"approved"/(day+".json")).write_text(
            json.dumps({"editionType":"regular","stories":[{}]*6}))
        (self.root/"data"/"current.json").write_text(
            json.dumps({"status":"published","editionDate":day,"stories":[{}]*6}))
        ok,message=check_release(
            self.root,datetime.fromisoformat(day+"T22:27:00+09:00"))
        self.assertFalse(ok)
        self.assertIn("配信ルール",message)

    def test_previous_three_story_limit_is_preserved(self):
        import json
        day="2026-11-18"
        (self.root/"data"/"approved"/(day+".json")).write_text(
            json.dumps({"editionType":"regular","stories":[{}]*4}))
        (self.root/"data"/"current.json").write_text(
            json.dumps({"status":"published","editionDate":day,"stories":[{}]*4}))
        ok,message=check_release(
            self.root,datetime.fromisoformat(day+"T22:27:00+09:00"))
        self.assertFalse(ok)
        self.assertIn("配信ルール",message)

    def test_archive_difference_triggers_failure(self):
        import json
        self.time=datetime.fromisoformat("2026-11-17T22:27:00+09:00")
        (self.root/"data"/"approved"/"2026-11-17.json").write_text(
            json.dumps({"editionType":"regular","stories":[{}]*2}))
        (self.root/"data"/"current.json").write_text(
            json.dumps({"status":"published","editionDate":"2026-11-17","stories":[{}]*2}))
        (self.root/"data"/"archive"/"2026-11-17.json").write_text("{}")
        (self.root/"data"/"archive"/"index.json").write_text('{"issues":[{"date":"2026-11-17"}]}')
        ok,message=check_release(self.root,self.time)
        self.assertFalse(ok)
        self.assertIn("一致",message)

    def test_early_run_does_not_raise_alarm(self):
        (self.root / "data" / "approved" / "2026-11-11.json").write_text('{"editionType":"special","stories":[{},{},{},{},{}]}')
        self.assertTrue(check_release(self.root, datetime.fromisoformat("2026-11-11T21:15:00+09:00"))[0])


if __name__ == "__main__":
    unittest.main()
