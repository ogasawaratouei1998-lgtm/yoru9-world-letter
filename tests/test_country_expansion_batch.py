"""Regression contract for consented bulk country-content preparation.

Stand-alone official place essays may be prepared ahead of licensed photographs.
Only fully photographed, individually sourced countries may enter the reader.
"""
import json
from pathlib import Path
import re
import unittest

from country_content import check_country_content
from check_country_experience import country_coverage
from country_readiness import ready_country_codes

ROOT=Path(__file__).resolve().parents[1]
BATCH=("AT","CH","GR","TR","EG","PT")
PHOTO_READY=("GR",)


class CountryExpansionBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=check_country_content(ROOT)
        cls.batch=json.loads((ROOT/"country-expansion-batch-20261121.json").read_text(
            encoding="utf-8"))

    def test_six_new_country_portraits_are_sourced_and_tourism_essays_are_detailed(self):
        self.assertEqual(set(self.batch["countries"]),set(BATCH))
        total=0
        unesco_sources=set()
        for code in BATCH:
            with self.subTest(code=code):
                country=self.data["countries"][code]
                draft=self.batch["countries"][code]
                self.assertEqual(country["name"],draft["name"])
                self.assertGreaterEqual(len(country["portrait"]["body"]),145)
                self.assertTrue(country["portrait"]["sourceUrl"].startswith(
                    "https://whc.unesco.org/en/statesparties/"))
                self.assertEqual(draft["portraitSource"],
                                 country["portrait"]["sourceUrl"])
                self.assertEqual(len(draft["travelDrafts"]),2)
                for record in draft["travelDrafts"]:
                    paragraphs=record["travelStory"]
                    self.assertEqual(len(paragraphs),2)
                    self.assertTrue(all(110<=len(p)<=360 for p in paragraphs))
                    self.assertNotEqual(paragraphs[0],paragraphs[1])
                    self.assertEqual(len(record["historicalSources"]),1)
                    source=record["historicalSources"][0]
                    self.assertRegex(source["url"],
                                     r"^https://whc\.unesco\.org/en/list/[0-9]+$")
                    self.assertEqual(source["checkedOn"],"2026-11-21")
                    self.assertNotIn(source["url"],unesco_sources)
                    unesco_sources.add(source["url"])
                    quiz=record["quizDraft"]
                    self.assertEqual(len(quiz["options"]),3)
                    self.assertEqual(len(set(quiz["options"])),3)
                    self.assertIn(quiz["answer"],(0,1,2))
                    self.assertTrue(quiz["fact"])
                    self.assertGreaterEqual(len(quiz["photoGoal"]),24)
                    total+=1
        self.assertEqual(total,12)

    def test_only_greece_is_newly_promoted_and_other_five_do_not_leak_to_reader(self):
        ready,_=ready_country_codes(ROOT)
        self.assertEqual(len(ready),19)
        self.assertEqual(len(self.data["countries"]),196)
        self.assertEqual(self.data["countries"]["MX"]["status"],"approved")
        self.assertEqual(self.data["countries"]["NL"]["status"],"approved")
        self.assertEqual(self.data["countries"]["SG"]["status"],"approved")
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        for code in BATCH:
            c=self.data["countries"][code]
            draft=self.batch["countries"][code]
            with self.subTest(country=code):
                if code in PHOTO_READY:
                    self.assertEqual(c["status"],"approved")
                    self.assertEqual(draft["status"],"approved")
                    self.assertIn(code,ready)
                    self.assertIn("\n "+code+":{lead:",page)
                else:
                    self.assertEqual(c["status"],"pending")
                    self.assertEqual(draft["status"],"pending")
                    self.assertNotIn(code,ready)
                    self.assertNotIn("\n "+code+":{lead:",page)
                    self.assertEqual(c["portraitPhotos"],[])
                    self.assertEqual(c["quiz"],[])
                    self.assertEqual(c["travelStops"],{})
                    self.assertTrue(all(
                        stop["photoStatus"]=="not_selected_or_licensed"
                        for stop in draft["travelDrafts"]))

    def test_greece_has_three_independent_real_photo_credits_and_two_unique_quizzes(self):
        country=self.data["countries"]["GR"]
        self.assertEqual(country["status"],"approved")
        self.assertEqual(len(country["portraitPhotos"]),1)
        self.assertEqual(len(country["quiz"]),2)
        self.assertEqual(len(country["travelStops"]),3)
        credits={stop["author"] for stop in country["travelStops"].values()}
        self.assertEqual(credits,{"ArticCynda","Geomel","Skyring"})
        stops=list(country["travelStops"].values())
        self.assertEqual(len({s["photoPage"] for s in stops}),3)
        self.assertEqual(len({s["photoAsset"] for s in stops}),3)
        self.assertTrue(all(s["photo"].startswith(
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/")
            for s in stops))
        self.assertTrue(all(s["license"]=="CC BY-SA 4.0" for s in stops))
        self.assertEqual(country["portraitPhotos"][0]["author"],"ArticCynda")
        keys=[quiz["photoKey"] for quiz in country["quiz"]]
        self.assertEqual(len(set(keys)),2)
        self.assertTrue(all(quiz["photoLabel"].startswith("正解") for quiz in
                            country["quiz"]))
        self.assertTrue(all(country["travelStops"][key]["author"] in
                            {"Geomel","Skyring"} for key in keys))
        for i,key in enumerate(keys):
            self.assertEqual(country["travelStops"][key]["travelStory"],
                             self.batch["countries"]["GR"]["travelDrafts"][i]["travelStory"])
            self.assertEqual(self.batch["countries"]["GR"]["travelDrafts"][i]["photoStatus"],
                             "licensed_commons_and_approved")
        actual=country_coverage(ROOT,[{"country":"ギリシャ"}])
        self.assertIn("GR",actual)
        self.assertEqual(actual["GR"]["quizRounds"],2)


if __name__=="__main__":
    unittest.main()
