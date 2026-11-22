"""All-country research is complete in scope, but never auto-approves."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from country_bulk_research import make_plan, research_shard, combine, SHARDS, cover_metadata_matches_country

ROOT = Path(__file__).resolve().parents[1]

class AllCountryResearchTests(unittest.TestCase):
    def test_honduras_reserve_search_excludes_different_patuca_river(self):
        plan = make_plan(ROOT)
        honduras = next(row for row in plan["countries"] if row["code"] == "HN")
        slot = honduras["slots"][2]
        self.assertEqual(slot["origin"], "existing_draft")
        self.assertIn("Plátano", slot["searchQuery"])
        self.assertIn("-Patuca", slot["searchQuery"])
        self.assertFalse(honduras["publicationEligible"])

    def test_every_pending_country_and_three_slots_without_approval(self):
        d = json.loads((ROOT/"country-content.json").read_text(encoding="utf-8"))["countries"]
        pending = {code for code, row in d.items() if row["status"] == "pending"}
        plan = make_plan(ROOT)
        self.assertEqual({c["code"] for c in plan["countries"]}, pending)
        self.assertEqual(plan["slotCount"], len(pending)*3)
        self.assertEqual(plan["catalogCount"], 196)
        for c in plan["countries"]:
            self.assertFalse(c["publicationEligible"])
            self.assertEqual([s["slot"] for s in c["slots"]], [0, 1, 2])
            self.assertTrue(all(not s["publicationEligible"] for s in c["slots"]))
        reports = [research_shard(plan, i, fetch=lambda q: [], sleep_seconds=0) for i in range(SHARDS)]
        combined = combine(plan, reports)
        self.assertEqual(combined["reportedSlots"], plan["slotCount"])
        self.assertEqual(combined["missingSlots"], [])
        self.assertFalse(combined["publicationEligible"])
        self.assertGreater(len(combine(plan, reports[:-1])["missingSlots"]), 0)
        with self.assertRaises(ValueError):
            combine(plan, reports+[reports[0]])

    def test_south_africa_photo_search_targets_distinct_documentary_subjects(self):
        plan = make_plan(ROOT)
        za = next(c for c in plan["countries"] if c["code"] == "ZA")
        self.assertEqual(len(za["slots"]), 3)
        self.assertIn("Table Mountain", za["slots"][0]["searchQuery"])
        self.assertIn("prison courtyard", za["slots"][1]["searchQuery"])
        self.assertIn("fynbos protea", za["slots"][2]["searchQuery"])
        self.assertEqual(len({s["searchQuery"] for s in za["slots"]}), 3)
        self.assertTrue(all(s["origin"] == "existing_draft" for s in za["slots"]))
        self.assertFalse(za["publicationEligible"])

    def test_undrafted_country_uses_official_site_only_when_available(self):
        d = json.loads((ROOT/"country-content.json").read_text(encoding="utf-8"))["countries"]
        pending = {code for code, row in d.items() if row["status"] == "pending"}
        with patch("country_bulk_research.draft_queries", return_value=[]):
            inventory = {"countries": {code: {"sampleSourcePages": []} for code in pending}}
            code = sorted(pending)[0]
            inventory["countries"][code]["sampleSourcePages"] = [{"name": "Fixture heritage", "sourceUrl": "https://whc.unesco.org/en/list/123/"}]
            plan = make_plan(ROOT, inventory)
            row = next(c for c in plan["countries"] if c["code"]==code)
            self.assertEqual(row["slots"][1]["officialSourceCandidate"], "https://whc.unesco.org/en/list/123/")
            self.assertIsNone(row["slots"][2]["searchQuery"])
            self.assertEqual(row["slots"][2]["origin"], "independent_source_required")

    def test_rate_limit_defers_remaining_searches_without_inventing_results(self):
        plan = make_plan(ROOT)
        calls = []
        def fail(query):
            calls.append(query)
            raise HTTPError("https://commons.wikimedia.org/", 429, "Too many requests", {}, None)
        report = research_shard(plan, 0, fetch=fail, sleep_seconds=0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(report["statusCounts"]["search_failed"], 1)
        self.assertGreater(report["statusCounts"].get("rate_limited_deferred", 0), 0)
        self.assertTrue(all(not r["candidates"] for r in report["results"]))

    def test_country_cover_metadata_rejects_unrelated_landscape_and_partial_country_names(self):
        self.assertFalse(cover_metadata_matches_country(
            {"file": "File:Black and white Paris landscape.jpg", "description": "Paris, France"},
            ["Central African Republic", "中央アフリカ共和国"]))
        self.assertFalse(cover_metadata_matches_country(
            {"file": "File:Landscape Nigeria.jpg"}, ["Niger"]))
        self.assertTrue(cover_metadata_matches_country(
            {"file": "File:Port_Louis,_MAURITIUS.jpg"}, ["Mauritius"]))
        self.assertTrue(cover_metadata_matches_country(
            {"file": "File:Coast.jpg", "description": "Coast of the Central African Republic"},
            ["Central African Republic"]))
        self.assertFalse(cover_metadata_matches_country(
            {"file": "File:Hausdülmen.jpg", "description": "Germany"}, ["Mauritius"]))

    def test_undrafted_cover_search_filters_before_accepting_metadata(self):
        candidate = {"file": "File:Paris landscape.jpg", "description": "France",
                     "commonsPage": "wrong"}
        right = {"file": "File:Mauritius coast.jpg", "description": "Port Louis",
                 "commonsPage": "right"}
        plan = {"shards": 8, "countries": [{"code": "MU", "country": "Mauritius", "shard": 0,
            "slots": [{"slot": 0, "searchQuery": '"Mauritius" landscape',
                       "origin": "country_cover_research", "countryNames": ["Mauritius"]}]}]}
        with patch("country_bulk_research.valid_candidate", side_effect=lambda x: x):
            result = research_shard(plan, 0, fetch=lambda query: [candidate, right], sleep_seconds=0)
        self.assertEqual(result["results"][0]["candidates"], [right])
        self.assertFalse(result["results"][0].get("publicationEligible", False))

    def test_draft_alternate_search_uses_at_most_two_queries(self):
        plan = {"shards": 8, "countries": [{"code": "BW", "country": "Botswana", "shard": 0,
            "slots": [{"slot": 0, "searchQuery": "long query", "alternateSearchQuery": "Chobe River Botswana",
                       "origin": "existing_draft", "publicationEligible": False}]}]}
        candidate = {"commonsPage": "fixture", "publicationEligible": False}
        calls = []
        def fetch(query):
            calls.append(query)
            return [] if query == "long query" else [candidate, candidate]
        with patch("country_bulk_research.valid_candidate", side_effect=lambda x: x):
            row = research_shard(plan, 0, fetch=fetch, sleep_seconds=0)["results"][0]
        self.assertEqual(calls, ["long query", "Chobe River Botswana"])
        self.assertEqual(row["attemptedQueries"], calls)
        self.assertEqual(row["candidates"], [candidate])
        self.assertFalse(row["publicationEligible"])
        self.assertEqual(row["status"], "metadata_candidates_only")
        with patch("country_bulk_research.valid_candidate", side_effect=lambda x: x):
            row = research_shard(plan, 0, fetch=lambda q: [candidate], sleep_seconds=0)["results"][0]
        self.assertEqual(row["attemptedQueries"], ["long query"])

    def test_alternate_not_attempted_after_rate_limit(self):
        plan = {"shards": 8, "countries": [{"code": "BW", "country": "Botswana", "shard": 0,
            "slots": [{"slot": 0, "searchQuery": "first", "alternateSearchQuery": "second",
                       "origin": "existing_draft"},
                      {"slot": 1, "searchQuery": "third", "origin": "existing_draft"}]}]}
        calls = []
        def fetch(query):
            calls.append(query)
            raise HTTPError("https://commons.wikimedia.org/", 429, "rate limited", {}, None)
        rows = research_shard(plan, 0, fetch=fetch, sleep_seconds=0)["results"]
        self.assertEqual(calls, ["first"])
        self.assertEqual(rows[1]["status"], "rate_limited_deferred")

    def test_targeted_search_preserves_draft_place_and_no_approval(self):
        plan = make_plan(ROOT)
        countries = {c["code"]: c for c in plan["countries"]}
        for code, slot, query in [
            ("BW", 0, "Chobe River Botswana"), ("GH", 1, "Besease shrine"),
            ("HN", 1, "Copan ruins")
        ]:
            if code in countries:
                row = countries[code]["slots"][slot]
                self.assertEqual(row["alternateSearchQuery"], query)
                self.assertFalse(row["publicationEligible"])
        if "TN" in countries:
            row = countries["TN"]["slots"][2]
            self.assertIn("Carthage", row["searchQuery"])
            self.assertIn("-Dougga", row["searchQuery"])
            self.assertIn("originalSearchQuery", row)
