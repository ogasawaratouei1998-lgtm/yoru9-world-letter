"""Regression: news approval is independent of tourism content."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from country_readiness import article_country_backlog
from check_country_experience import published_country_coverage, country_coverage
from release_contract import validate_release_input

ROOT=Path(__file__).resolve().parents[1]

class ArticleFirstCountryTest(unittest.TestCase):
    def test_pending_country_stays_a_news_country(self):
        countries=json.loads((ROOT/"country-content.json").read_text(encoding="utf-8"))["countries"]
        code=next(k for k,v in countries.items() if v["status"]=="pending")
        stories=[{"id":"synthetic-fixture","country":code}]
        payload={"stories":stories}
        with patch("publish_approved.validate_approved",return_value=payload):
            self.assertIs(validate_release_input(ROOT,payload,"2026-11-27",require_assets=True),payload)
        self.assertEqual(published_country_coverage(ROOT,stories),{})
        with self.assertRaises(ValueError):
            country_coverage(ROOT,stories)
        self.assertEqual(article_country_backlog(stories,ROOT,"2026-11-27"),({code:1},set()))
        self.assertEqual(stories[0]["country"],code)

    def test_missing_optional_topics_do_not_gate_release(self):
        stories=[{"country":"フランス"}]
        payload={"stories":stories}
        with patch("publish_approved.validate_approved",return_value=payload), patch("build_site.validate_country_highlights",return_value={"highlights":{}}):
            self.assertEqual(article_country_backlog(stories,ROOT,"2026-11-27")[0],{"FR":1})
            self.assertIs(validate_release_input(ROOT,payload,"2026-11-27",require_assets=True),payload)
        self.assertIn("FR",published_country_coverage(ROOT,stories))

    def test_unrecognized_country_cannot_be_rendered_as_known(self):
        with self.assertRaises(ValueError):
            published_country_coverage(ROOT,[{"country":"架空の国"}])
