"""New draft cohort and free Commons photo research must never silently promote countries."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from country_content import check_country_content
from country_photo_candidates import draft_queries, generate_report, plain, valid_candidate

ROOT = Path(__file__).resolve().parents[1]
COHORT = {"IS", "IE", "HR", "KH", "NP", "TZ", "JO", "LK"}


class BulkCountryExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = check_country_content(ROOT)
        cls.batch = json.loads((ROOT / "country-expansion-batch-unesco-eight-20261121.json").read_text(encoding="utf-8"))

    def test_eight_additional_countries_are_fact_referenced_but_unpublished(self):
        self.assertEqual(set(self.batch["countries"]), COHORT)
        self.assertEqual(self.batch["status"], "pending_photos_not_public")
        for code, draft in self.batch["countries"].items():
            with self.subTest(country=code):
                country = self.doc["countries"][code]
                if code in ("HR", "IE", "IS", "KH", "NP", "TZ", "JO", "LK"):
                    # Original batch is a historical draft snapshot. Croatia is
                    # Ireland and Iceland are now released only after separately licensed photos.
                    self.assertEqual(country["status"], "approved")
                    if code == "JO":
                        self.assertTrue(country["portrait"]["body"].startswith(draft["portrait"]["body"]))
                        self.assertIn("危険レベル2", country["portrait"]["body"])
                    else:
                        self.assertEqual(country["portrait"]["body"], draft["portrait"]["body"])
                    self.assertEqual(len(country["portraitPhotos"]), 1)
                    self.assertEqual(len(country["travelStops"]), 3)
                    self.assertEqual(len(country["quiz"]), 2)
                else:
                    self.assertEqual(country["status"], "pending")
                    self.assertEqual(country["portrait"], draft["portrait"])
                    self.assertEqual(country["portraitPhotos"], [])
                    self.assertEqual(country["travelStops"], {})
                    self.assertEqual(country["quiz"], [])
                self.assertGreaterEqual(len(country["portrait"]["body"]), 145)
                self.assertTrue(country["portrait"]["sourceUrl"].startswith("https://whc.unesco.org/en/statesparties/"))
                self.assertEqual(len(draft["travelDrafts"]), 2)

    def test_sixteen_unique_sourced_travel_essays_and_photo_quizzes(self):
        places = set()
        source_urls = set()
        for draft in self.batch["countries"].values():
            for stop in draft["travelDrafts"]:
                with self.subTest(place=stop["place"]):
                    self.assertNotIn(stop["place"], places)
                    places.add(stop["place"])
                    self.assertEqual(stop["photoStatus"], "not_selected_or_licensed")
                    self.assertEqual(len(stop["travelStory"]), 2)
                    self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
                    self.assertNotEqual(stop["travelStory"][0], stop["travelStory"][1])
                    self.assertEqual(len(stop["historicalSources"]), 1)
                    source = stop["historicalSources"][0]
                    self.assertEqual(source["checkedOn"], "2026-11-21")
                    self.assertTrue(source["url"].startswith("https://whc.unesco.org/en/list/"))
                    self.assertNotIn(source["url"], source_urls)
                    source_urls.add(source["url"])
                    quiz = stop["quizDraft"]
                    self.assertEqual(len(quiz["options"]), 3)
                    self.assertEqual(len(set(quiz["options"])), 3)
                    self.assertIn(quiz["answer"], (0, 1, 2))
                    self.assertGreaterEqual(len(quiz["fact"]), 20)
        self.assertEqual(len(places), 16)
        self.assertEqual(len(source_urls), 16)

    def test_candidate_queue_covers_two_cohorts_without_auto_publish(self):
        tasks = list(draft_queries(ROOT))
        self.assertGreaterEqual(len(tasks), 48)
        self.assertTrue((COHORT | {"ID", "VN", "ZA", "KE", "MA", "NO", "CL", "PE"}).issubset({row["countryCode"] for row in tasks}))
        for row in tasks:
            self.assertIn(row["role"], ("cover", "quizAndTravel"))
            self.assertGreaterEqual(len(row["searchQuery"]), 8)

    def test_candidates_require_author_license_https_and_do_not_approve_photos(self):
        page = {"title": "File:Example.jpg", "imageinfo": [{
            "mime": "image/jpeg", "width": 1200, "height": 800,
            "url": "https://upload.wikimedia.org/wikipedia/commons/a/a1/Example.jpg",
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Example.jpg",
            "extmetadata": {
                "Artist": {"value": "<span>Photographer</span>"},
                "LicenseShortName": {"value": "CC BY-SA 4.0"},
                "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/"}
            }
        }]}
        accepted = valid_candidate(page)
        self.assertIsNotNone(accepted)
        self.assertFalse(accepted["publicationEligible"])
        self.assertFalse(accepted["placeVisuallyVerified"])
        self.assertEqual(accepted["author"], "Photographer")
        page["imageinfo"][0]["extmetadata"]["LicenseShortName"]["value"] = "CC BY-NC 4.0"
        self.assertIsNone(valid_candidate(page))
        self.assertEqual(plain("A <em>clean</em> credit"), "A clean credit")


class StandalonePhotoThrottlingTests(unittest.TestCase):
    def test_rate_limit_defers_remaining_tasks_without_more_network_requests(self):
        tasks = [{"countryCode": "AA", "searchQuery": "first place", "role": "cover"},
                 {"countryCode": "BB", "searchQuery": "second place", "role": "cover"},
                 {"countryCode": "CC", "searchQuery": "third place", "role": "cover"}]
        for code in (429, 503):
            with self.subTest(code=code):
                calls = []
                def fetch(query):
                    calls.append(query)
                    if query == "second place":
                        raise HTTPError("https://commons.wikimedia.org/", code, "temporary restriction", {}, None)
                    return []
                with patch("country_photo_candidates.draft_queries", return_value=tasks):
                    report = generate_report(fetch=fetch, sleep_seconds=0)
                self.assertEqual(calls, ["first place", "second place"])
                self.assertEqual(report["searchCount"], 3)
                self.assertEqual(report["failedSearches"], 1)
                self.assertEqual(report["deferredSearches"], 1)
                self.assertEqual([row["status"] for row in report["results"]],
                                 ["no_matching_metadata", "search_failed", "rate_limited_deferred"])
                self.assertEqual(report["results"][1]["httpStatus"], code)
                self.assertTrue(all(row["manualVisualReviewRequired"] for row in report["results"]))
                self.assertTrue(all(not row["candidates"] for row in report["results"]))


if __name__ == "__main__":
    unittest.main()
