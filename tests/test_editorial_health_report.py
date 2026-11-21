"""Private editorial progress reporting never exposes article material."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from editorial_health_report import summarize_funnel


class EditorialHealthReportTests(unittest.TestCase):
    def test_scarce_sources_and_four_story_gate_have_distinct_messages(self):
        cases={
            "publisher_leads_below_four":"記事候補が4件未満",
            "publisher_articles_below_four":"本文を読める記事が4件未満",
            "draft_empty":"採用候補を生成できなかった",
            "four_story_gate":"4本に届かず前回号を維持",
            "model_quota_blocked":"利用枠が不足",
            "selected":"実際の公開は別途確認",
        }
        for phase,fragment in cases.items():
            with self.subTest(phase=phase):
                report=summarize_funnel({"phase":phase,"fresh":3})
                self.assertIn(fragment,report)
                self.assertIn("配信成功",report) if phase not in ("selected",) else None
                self.assertNotIn("https://",report)

    def test_counts_are_aggregated_and_free_text_is_never_emitted(self):
        fake={
            "phase":"four_story_gate","fresh":12,
            "country_ready_articles":3,
            "rejection_reasons":{"unsupported_country":4,
                                 "https://secret.example/article":3},
            "articleBody":"NEVER EXPOSE BODY",
            "title":"NEVER EXPOSE HEADLINE",
            "source_url":"https://secret.example/article",
        }
        report=summarize_funnel(fake)
        self.assertIn("country_ready_articles: 3",report)
        self.assertIn("rejection unsupported_country: 4",report)
        for private in ("NEVER EXPOSE","secret.example","articleBody","source_url"):
            self.assertNotIn(private,report)

    def test_missing_diagnostic_is_nonfatal_in_runner(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(__file__).resolve().parents[1]
            target=Path(td)/"summary.md"
            process=subprocess.run(
                [sys.executable,str(repo/"editorial_health_report.py")],
                cwd=td,env={**os.environ,"GITHUB_STEP_SUMMARY":str(target)},
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                text=True,check=True)
            self.assertIn("記録がありません",process.stdout)
            self.assertIn("記録がありません",target.read_text(encoding="utf-8"))


if __name__=="__main__":
    unittest.main()
