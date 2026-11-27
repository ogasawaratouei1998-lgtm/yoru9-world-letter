"""Nightly health alerts must ignore cancelled code-push runs."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class PublicationMonitoringTests(unittest.TestCase):
    def test_no_false_failure_from_superseded_code_pushes(self):
        wf=(ROOT/".github/workflows/publication-health.yml").read_text(encoding="utf-8")
        self.assertIn("r.get('event') in ('schedule','workflow_dispatch','workflow_run')",wf)
        self.assertIn("r.get('conclusion') not in ('cancelled','skipped')",wf)
        self.assertIn("a zero-story evening is permitted",wf)
        self.assertNotIn("warnings.append('No completed publication workflow",wf)
        self.assertIn("if newest.get('conclusion')!='success':",wf)
        self.assertIn("Live Pages data is not a valid published edition",wf)


if __name__=="__main__":
    unittest.main()
