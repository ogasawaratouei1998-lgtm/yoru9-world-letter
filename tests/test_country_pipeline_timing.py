"""Country material scheduling and within-run source reuse regressions."""
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError
from country_topic_drafts import discover_topics

ROOT=Path(__file__).resolve().parents[1]

class CountryPipelineTest(unittest.TestCase):
    def test_shared_page_fetched_once_but_country_checked_independently(self):
        source={"name":"Official example","url":"https://example.org/events"}
        event={"@type":"Event","eventStatus":"https://schema.org/EventScheduled",
               "name":"Festival","startDate":"2026-11-28","endDate":"2026-11-29",
               "location":{"address":{"addressCountry":"BE"}}}
        page='<script type="application/ld+json">'+json.dumps(event)+'</script>'
        tasks={"editionDate":"2026-11-28","tasks":[
            {"countryCode":code,"missingTopicDates":["2026-11-28"],"officialTopicSources":[source]}
            for code in ("BE","FR")]}
        fetch=Mock(return_value=page)
        report=discover_topics(tasks,fetch=fetch)
        self.assertEqual(fetch.call_count,1)
        self.assertEqual(len(report["countries"][0]["candidates"]),1)
        self.assertFalse(report["countries"][0]["candidates"][0]["publicationEligible"])
        self.assertEqual(report["countries"][1]["candidates"],[])
        self.assertFalse(report["publicationEligible"])
        discover_topics(tasks,fetch=fetch)
        self.assertEqual(fetch.call_count,2)

    def test_failed_fetch_not_cached_as_success(self):
        source={"name":"Official example","url":"https://example.org/events"}
        tasks={"editionDate":"2026-11-28","tasks":[
            {"countryCode":code,"missingTopicDates":["2026-11-28"],"officialTopicSources":[source]}
            for code in ("BE","FR")]}
        fetch=Mock(side_effect=[URLError("temporary"),""])
        report=discover_topics(tasks,fetch=fetch)
        self.assertEqual(fetch.call_count,2)
        self.assertEqual(report["countries"][0]["sourceErrors"],["URLError"])
        self.assertEqual(report["countries"][1]["sourceErrors"],[])

    def test_topic_only_research_does_not_fetch_heritage_inventory(self):
        import tempfile
        from research_article_countries import main
        with tempfile.TemporaryDirectory() as td:
            approved=Path(td)/"approved.json"
            approved.write_text("{}")
            plan={"countries":[],"articleCountryNeeds":{"BE":1}}
            with patch("sys.argv",["research","--approved",str(approved),"--output",td]), \
                 patch("research_article_countries.article_plan",return_value=plan), \
                 patch("research_article_countries.download_feed") as feed, \
                 patch("research_article_countries.research_shard"), \
                 patch("research_article_countries.combine",return_value={}), \
                 patch("research_article_countries.save"), \
                 patch("research_article_countries.validate_release_input",return_value={"stories":[]}), \
                 patch("research_article_countries.prepare_material_bundle",return_value={"countriesNeedingMaterials":1}), \
                 patch("research_article_countries.discover_topics"):
                main()
                feed.assert_not_called()

    def test_earlier_recovery_and_read_only_handoff(self):
        workflow=(ROOT/".github/workflows/research-article-countries.yml").read_text()
        self.assertIn("30 10 * * *",workflow)
        self.assertNotIn("30 12 * * *",workflow)
        self.assertIn("recover_review(Path.cwd(),day",workflow)
        self.assertIn("contents: read",workflow)
        self.assertNotIn("contents: write",workflow)
        prepare=(ROOT/".github/workflows/prepare-nightly.yml").read_text()
        self.assertLess(prepare.index("python country_content.py --check"),
                        prepare.index("python prepared_release.py seal"))
