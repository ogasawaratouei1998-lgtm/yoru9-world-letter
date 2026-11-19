"""Regression coverage for 21:00 JST scheduled release redundancy and watchdog."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class NightlyDeliverySafetyNetTest(unittest.TestCase):
    def test_publisher_has_timezone_schedule_and_separate_utc_fallback(self):
        workflow=(ROOT/'.github/workflows/publish-nightly.yml').read_text(encoding='utf-8')
        self.assertIn("timezone: 'Asia/Tokyo'",workflow)
        # UTC slots include late 21:53 / 22:23 recovery checks, not only
        # the original 21:13 / 21:43 and 22:13 schedule.
        self.assertIn("cron: '13,43,53 12 * * *'",workflow)
        self.assertIn("cron: '13,23 13 * * *'",workflow)
        self.assertIn("if [ -f \"data/archive/$DAY.json\" ]; then",workflow)
        self.assertIn('python publish_approved.py',workflow)

    def test_watchdog_checks_only_after_gate_and_requests_guarded_retry(self):
        workflow=(ROOT/'.github/workflows/check-release-health.yml').read_text(encoding='utf-8')
        checker=(ROOT/'check_release_health.py').read_text(encoding='utf-8')
        self.assertIn("cron: '35 12 * * *'",workflow)
        self.assertIn("cron: '5 13 * * *'",workflow)
        self.assertIn('actions: write',workflow)
        self.assertIn('continue-on-error: true',workflow)
        self.assertEqual(workflow.count("if: steps.release_check.outcome == 'failure'"),2)
        self.assertIn('gh workflow run publish-nightly.yml --repo "$GH_REPO" --ref main',workflow)
        self.assertIn('if not approved.is_file():',checker)
        self.assertIn('if now.time() < time(21, 30):',checker)

    def test_midnight_monitor_checks_actual_pages_against_approved_yesterday(self):
        workflow=(ROOT/'.github/workflows/publication-health.yml').read_text(encoding='utf-8')
        self.assertIn("PAGES_URL: https://",workflow)
        self.assertIn("previous_day=(jst.date()-timedelta(days=1)).isoformat()",workflow)
        self.assertIn("if previous_day+'.json' in approved_names:",workflow)
        self.assertIn("issue missing from live Pages",workflow)


if __name__=='__main__':
    unittest.main()
