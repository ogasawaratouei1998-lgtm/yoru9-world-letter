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
        self.assertEqual(codes,{"IT","US","DE"})
        registry=validate_country_highlights(ROOT)
        sources=json.loads((ROOT/"country-highlight-sources.json").read_text(encoding="utf-8"))
        day=date(2026,11,21).isoformat()
        for code in sorted(codes):
            with self.subTest(country=code):
                entries=registry["highlights"].get(code,[])
                active=[row for row in entries if row["validFrom"]<=day<=row["validThrough"]
                        and row["checkedOn"]<=day]
                self.assertTrue(active,code+" has no sourced, active current topic")
                hosts={item["url"].split("/")[2] for item in sources["sources"][code]}
                self.assertTrue(all(row["sourceUrl"].split("/")[2] in hosts for row in active))

    def test_country_topic_audit_no_missing_current_issue_countries(self):
        report=audit(ROOT,date(2026,11,21))
        self.assertTrue(report["editionIsRecent"])
        self.assertEqual(report["countriesChecked"],["DE","IT","US"])
        self.assertFalse(report["urgent"],report["urgent"])


if __name__=="__main__":
    unittest.main()
