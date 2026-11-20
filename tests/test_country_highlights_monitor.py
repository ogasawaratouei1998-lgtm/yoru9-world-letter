"""Regression tests for the daily, non-publishing country topic audit."""
from datetime import date
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from audit_country_highlights import audit

ROOT = Path(__file__).resolve().parents[1]


class CountryHighlightMonitorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "data").mkdir()
        for name in ("country-catalog.json", "country-highlights.json", "country-highlight-sources.json"):
            shutil.copy2(ROOT / name, self.root / name)
        # Historical fixture: 2026-11-19 covered ES, GB, JP and NZ.
        shutil.copy2(ROOT / "data/archive/2026-11-19.json", self.root / "data/current.json")

    def test_current_countries_have_a_verified_note_through_next_week(self):
        report = audit(self.root, date(2026, 11, 19))
        self.assertTrue(report["editionIsRecent"])
        self.assertEqual(report["countriesChecked"], ["ES", "GB", "JP", "NZ"])
        self.assertFalse(report["needsEditorialReview"])
        self.assertEqual(report["urgent"], [])
        self.assertEqual(report["upcoming"], [])

    def test_imminent_expiry_is_raised_only_for_relevant_published_country(self):
        issue = json.loads((self.root / "data/current.json").read_text(encoding="utf-8"))
        issue["editionDate"] = "2026-11-28"
        (self.root / "data/current.json").write_text(
            json.dumps(issue, ensure_ascii=False), encoding="utf-8"
        )
        report = audit(self.root, date(2026, 11, 28))
        self.assertTrue(report["needsEditorialReview"])
        self.assertIn("NZ", [row["country"] for row in report["urgent"]])
        self.assertIn("2026-11-29", next(
            row["missingDates"] for row in report["urgent"] if row["country"] == "NZ"
        ))

    def test_missing_country_notes_are_flagged_and_not_fabricated(self):
        payload = json.loads((self.root / "country-highlights.json").read_text(encoding="utf-8"))
        del payload["highlights"]["GB"]
        (self.root / "country-highlights.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        report = audit(self.root, date(2026, 11, 19))
        self.assertTrue(report["needsEditorialReview"])
        self.assertIn("GB", [row["country"] for row in report["urgent"]])

    def test_new_italy_us_issue_flags_missing_country_notes_without_invention(self):
        shutil.copy2(ROOT / "data/current.json", self.root / "data/current.json")
        report=audit(self.root,date(2026,11,20))
        self.assertTrue(report["editionIsRecent"])
        self.assertEqual(report["countriesChecked"],["IT","US"])
        if report["urgent"]:
            self.assertTrue(report["needsEditorialReview"])

    def test_stale_edition_never_triggers_a_spurious_alert(self):
        report = audit(self.root, date(2026, 11, 26))
        self.assertFalse(report["editionIsRecent"])
        self.assertEqual(report["countriesChecked"], [])
        self.assertFalse(report["needsEditorialReview"])


    def test_rejects_a_official_site_from_the_wrong_country(self):
        from build_site import validate_country_highlights
        payload = json.loads((self.root / "country-highlights.json").read_text(encoding="utf-8"))
        payload["highlights"]["JP"][0]["sourceUrl"] = "https://www.esmadrid.com/en/whats-on/autumn-festival"
        (self.root / "country-highlights.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "JP:"):
            validate_country_highlights(self.root)

    def test_invalid_horizon_is_rejected(self):
        with self.assertRaises(ValueError):
            audit(self.root, date(2026, 11, 19), horizon=0)

    def test_daily_job_never_modifies_release_or_editorial_records(self):
        before = (self.root / "data/current.json").read_bytes()
        audit(self.root, date(2026, 11, 19))
        self.assertEqual(before, (self.root / "data/current.json").read_bytes())
