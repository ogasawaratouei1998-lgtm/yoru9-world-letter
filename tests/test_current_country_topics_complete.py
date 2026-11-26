"""Ensure current issue has sourced, currently valid cultural topics in every mapped country."""
from datetime import date
import json
from pathlib import Path
import unittest

from audit_country_highlights import audit
from build_site import validate_country_highlights
from country_codes import country_codes

ROOT=Path(__file__).resolve().parents[1]


class CurrentCountryTopicCompletenessTest(unittest.TestCase):
    def test_current_issue_countries_have_verified_live_topics(self):
        issue=json.loads((ROOT/"data/current.json").read_text(encoding="utf-8"))
        codes={code for story in issue["stories"] for code in country_codes(story["country"])}
        self.assertTrue(codes,"Current published issue must contain identified countries")
        registry=validate_country_highlights(ROOT)
        sources=json.loads((ROOT/"country-highlight-sources.json").read_text(encoding="utf-8"))
        day=issue["editionDate"]
        for code in sorted(codes):
            with self.subTest(country=code):
                entries=registry["highlights"].get(code,[])
                active=[row for row in entries if row["validFrom"]<=day<=row["validThrough"]
                        and row["checkedOn"]<=day]
                self.assertTrue(active,code+" has no sourced, active current topic")
                hosts={item["url"].split("/")[2] for item in sources["sources"][code]}
                self.assertTrue(all(row["sourceUrl"].split("/")[2] in hosts for row in active))

    def test_future_release_readiness_checks_actual_edition_date(self):
        from audit_country_highlights import require_country_topics, missing_topic_dates
        from country_readiness import ready_country_codes
        from unittest.mock import patch
        from release_contract import validate_release_input
        registry=validate_country_highlights(ROOT)["highlights"]
        day="2026-11-26"
        self.assertEqual(missing_topic_dates(registry,"FR",date.fromisoformat(day),7),[])
        self.assertTrue(require_country_topics(ROOT,[{"country":"フランス"}],day))
        payload=json.loads((ROOT/"data/approved"/(day+".json")).read_text(encoding="utf-8"))
        self.assertEqual(validate_release_input(ROOT,payload,day,require_assets=True)["editionDate"],day)
        with patch("build_site.validate_country_highlights",return_value={"highlights":{}}):
            ready,incomplete=ready_country_codes(ROOT,day)
            self.assertNotIn("FR",ready)
            self.assertEqual(incomplete["FR"],"missing_current_country_topics")
        with patch("audit_country_highlights.validate_country_highlights",return_value={"highlights":{}}):
            with self.assertRaisesRegex(ValueError,"Missing verified country topics"):
                validate_release_input(ROOT,payload,day,require_assets=True)
        stale={"FR":[{"checkedOn":"2026-10-20","validFrom":"2026-11-26","validThrough":"2026-12-02"}]}
        self.assertEqual(len(missing_topic_dates(stale,"FR",date.fromisoformat(day),7)),7)

    def test_country_topic_audit_no_missing_current_issue_countries(self):
        issue=json.loads((ROOT/"data/current.json").read_text(encoding="utf-8"))
        day=date.fromisoformat(issue["editionDate"])
        codes=sorted({code for story in issue["stories"]
                      for code in country_codes(story["country"])})
        report=audit(ROOT,day)
        self.assertTrue(report["editionIsRecent"])
        self.assertEqual(report["countriesChecked"],codes)
        self.assertFalse(report["urgent"],report["urgent"])


if __name__=="__main__":
    unittest.main()
