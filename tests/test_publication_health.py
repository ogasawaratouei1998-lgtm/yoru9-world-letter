"""Exercise the actual monitoring script with fake Actions and Pages responses."""
from datetime import datetime, timedelta
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import urllib.request
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]

class PublicationHealthTest(unittest.TestCase):
    def run_monitor(self, conclusions):
        workflow=(ROOT/".github/workflows/publication-health.yml").read_text(encoding="utf-8")
        script=workflow.split("          python - <<'PY'\n",1)[1].split("\n          PY",1)[0]
        script="\n".join(line[10:] for line in script.splitlines())
        now=datetime.now(ZoneInfo("Asia/Tokyo"))
        day=(now.date()-timedelta(days=1)).isoformat()
        runs=[{"event":"workflow_run" if i==0 else "schedule",
               "status":"completed","conclusion":conclusion,
               "created_at":(now-timedelta(minutes=i+1)).isoformat(),
               "html_url":"https://example.invalid/run/"+str(i)}
              for i,conclusion in enumerate(conclusions)]
        def gh(args, **kwargs):
            if "/actions/workflows/" in args[-1]:
                return json.dumps({"workflow_runs":runs})
            if "/issues?" in args[-1]:
                return "[]"
            raise AssertionError(args)
        live=json.dumps({"editionDate":day,"status":"published","stories":[{"id":"fixture"}]}).encode()
        with tempfile.TemporaryDirectory() as tmp:
            summary=Path(tmp)/"summary"
            with patch.dict(os.environ,{"GH_REPO":"example/repo","GITHUB_STEP_SUMMARY":str(summary),"PAGES_URL":"https://example.invalid/current.json"}), \
                 patch.object(subprocess,"check_output",side_effect=gh), \
                 patch.object(subprocess,"run") as report, \
                 patch.object(urllib.request,"urlopen",return_value=io.BytesIO(live)):
                if conclusions[-1]=="failure":
                    with self.assertRaisesRegex(SystemExit,"Health check detected failures"):
                        exec(compile(script,"publication-health.yml","exec"),{})
                    report.assert_called_once()
                else:
                    exec(compile(script,"publication-health.yml","exec"),{})
                    report.assert_not_called()
                return summary.read_text(encoding="utf-8")

    def test_skipped_and_cancelled_runs_are_not_failed_release_attempts(self):
        result=self.run_monitor(["skipped","cancelled","success"])
        self.assertIn("Latest workflow: https://example.invalid/run/2",result)
        self.assertIn("Failures: none",result)

    def test_real_failure_is_not_hidden_by_skipped_runs(self):
        result=self.run_monitor(["skipped","failure"])
        self.assertIn("Failures: Latest completed publication workflow: failure",result)

    def test_only_skipped_runs_do_not_invent_a_failed_attempt(self):
        result=self.run_monitor(["skipped","cancelled"])
        self.assertIn("No completed scheduled/manual release attempt",result)
        self.assertIn("Failures: none",result)
