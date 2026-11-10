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
        (self.root / "data" / "approved" / "2026-11-11.json").write_text("{}")
        ok, _ = check_release(self.root, self.time)
        self.assertFalse(ok)
    def test_published_edition_and_archive_succeed(self):
        import json
        (self.root / "data" / "approved" / "2026-11-11.json").write_text("{}")
        (self.root / "data" / "current.json").write_text(json.dumps({"status":"published","editionDate":"2026-11-11","stories":[{}]*5}))
        (self.root / "data" / "archive" / "2026-11-11.json").write_text("{}")
        (self.root / "data" / "archive" / "index.json").write_text('{"issues":[{"date":"2026-11-11"}]}')
        self.assertTrue(check_release(self.root, self.time)[0])
    def test_early_run_does_not_raise_alarm(self):
        (self.root / "data" / "approved" / "2026-11-11.json").write_text("{}")
        self.assertTrue(check_release(self.root, datetime.fromisoformat("2026-11-11T21:15:00+09:00"))[0])


if __name__ == "__main__":
    unittest.main()
