"""Time budgets, topic-first ordering, and source coverage reporting."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile
ROOT=Path(__file__).resolve().parents[1]
class CountryDeadlineTest(unittest.TestCase):
    def test_optional_photo_work_is_after_review_artifact_and_bounded(self):
        w=(ROOT/".github/workflows/research-article-countries.yml").read_text()
        import re
        job_budget=int(re.search(r"^    timeout-minutes: (\d+)$",w,re.M).group(1))
        self.assertLessEqual(job_budget,24)
        steps_budget=sum(int(v) for v in re.findall(r"^        timeout-minutes: (\d+)$",w,re.M))
        # Leave headroom for checkout/setup; bound both artifact uploads.
        self.assertLessEqual(steps_budget,job_budget-2)
        self.assertLess(w.index("--topics-only"),w.index("python country_topic_review.py"))
        self.assertLess(w.index("name: reviewed-country-topics"),w.index("--skip-topics"))
        photo_step=w.split("name: Prepare missing photo and heritage materials within remaining time",1)[1].split("      - name:",1)[0]
        self.assertIn("timeout-minutes: 7",photo_step)
        self.assertIn("continue-on-error: true",photo_step)
        self.assertIn("30 10 * * *",w)  # 19:30 JST recovery
        prepare=(ROOT/".github/workflows/prepare-nightly.yml").read_text()
        prepare_budget=int(re.search(r"^    timeout-minutes: (\d+)$",prepare,re.M).group(1))
        # 90 minutes from recovery schedule to release; reserve >=30 minutes
        # against queue delays and publication checks.
        self.assertLessEqual(job_budget+prepare_budget,60)
        self.assertIn("if: always()",w.split("name: Report material completion separately from news readiness",1)[1])
    def test_topic_only_does_not_start_photo_inventory(self):
        from research_article_countries import main
        with tempfile.TemporaryDirectory() as td:
            approved=Path(td)/"approved.json"
            approved.write_text("{}")
            tasks={"editionDate":"2026-11-28","tasks":[]}
            with patch("sys.argv",["research","--approved",str(approved),"--output",td,"--topics-only"]), patch("research_article_countries.validate_release_input",return_value={"stories":[]}), patch("research_article_countries.material_tasks",return_value=tasks), patch("research_article_countries.discover_topics",return_value={"countries":[]}), patch("research_article_countries.article_plan") as plan:
                main()
                plan.assert_not_called()
                self.assertTrue((Path(td)/"topic-drafts.json").is_file())
    def test_registry_and_remaining_queue_cover_all_196(self):
        from country_batch_progress import expansion_progress
        p=expansion_progress(ROOT)
        self.assertEqual(p["registeredTopicSourceCountries"]+len(p["missingTopicSourceCountries"]),196)
        self.assertGreaterEqual(p["registeredTopicSourceCountries"],28)
        self.assertTrue(set(p["approvedCountriesMissingTopicSources"])<=set(p["missingTopicSourceCountries"]))
