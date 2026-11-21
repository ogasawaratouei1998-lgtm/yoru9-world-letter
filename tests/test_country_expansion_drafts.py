"""Public country data must never promote draft descriptions or invented photos."""
import json
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit

from country_content import check_country_content

ROOT=Path(__file__).resolve().parents[1]
COUNTRIES={"AU","CA","IN"}
SITE_HOSTS={"whc.unesco.org","parks.canada.ca"}


class CountryExpansionDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.draft=json.loads((ROOT/"country-expansion-drafts.json").read_text(encoding="utf-8"))
        cls.country=check_country_content(ROOT)

    def test_draft_countries_are_source_backed_but_never_approved(self):
        self.assertEqual(set(self.draft["countries"]),COUNTRIES)
        self.assertEqual(self.draft["visibility"],"EDITORIAL_ONLY_NOT_FOR_READER")
        for code in COUNTRIES:
            with self.subTest(code=code):
                row=self.country["countries"][code]
                entry=self.draft["countries"][code]
                self.assertEqual(row["status"],"pending")
                self.assertEqual(entry["status"],"pending")
                self.assertEqual(entry["name"],row["name"])
                self.assertGreaterEqual(len(row["portrait"]["body"]),145)
                self.assertTrue(row["portrait"]["sourceName"])
                self.assertEqual(len(row["portrait"]["facts"]),3)
                self.assertIn(urlsplit(row["portrait"]["sourceUrl"]).hostname,
                              ("www.australia.com","travel.destinationcanada.com",
                               "www.incredibleindia.gov.in"))
                self.assertEqual(row["portraitPhotos"],[])
                self.assertEqual(row["quiz"],[])
                self.assertEqual(row["travelStops"],{})
                self.assertGreaterEqual(len(entry["coverPhotoGoal"]),30)
                self.assertEqual(len(entry["travelDrafts"]),2)

    def test_six_destinations_have_individual_official_sources_and_nonfiller_essays(self):
        destinations=set()
        for code,country in self.draft["countries"].items():
            quiz_photos=set()
            for record in country["travelDrafts"]:
                with self.subTest(code=code,place=record["place"]):
                    self.assertNotIn(record["place"],destinations)
                    destinations.add(record["place"])
                    paras=record["travelStory"]
                    self.assertEqual(len(paras),2)
                    self.assertTrue(all(110<=len(p.strip())<=360 for p in paras))
                    self.assertNotEqual(paras[0],paras[1])
                    src=record["historicalSource"]
                    self.assertIn(urlsplit(src["url"]).hostname,SITE_HOSTS)
                    self.assertTrue(src["name"])
                    self.assertRegex(src["checkedOn"],r"^\\d{4}-\\d{2}-\\d{2}$")
                    self.assertEqual(record["photoStatus"],"not_selected_or_licensed")
                    self.assertNotIn("photoAsset",record)
                    self.assertNotIn("photo",record)
                    q=record["quizDraft"]
                    self.assertGreaterEqual(len(q["question"]),10)
                    self.assertEqual(len(q["options"]),3)
                    self.assertEqual(len(set(q["options"])),3)
                    self.assertIn(q["answer"],(0,1,2))
                    self.assertGreaterEqual(len(q["fact"]),20)
                    self.assertGreaterEqual(len(q["photoGoal"]),24)
                    quiz_photos.add(q["photoGoal"])
            self.assertEqual(len(quiz_photos),2,
                             "Quiz answer photographs must be distinct, not reused")
        self.assertEqual(len(destinations),6)

    def test_reader_exposes_only_existing_twelve_approved_countries(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        for code in COUNTRIES:
            self.assertNotRegex(html,r"(?m)^ "+code+r":\\{lead:")
        match=re.search(
            r"(?m)^const APPROVED_COUNTRY_CODES=Object\\.freeze\\((\\[[^\\n]+\\])\\);$",
            html)
        self.assertIsNotNone(match)
        atlas=json.loads(match.group(1))
        self.assertEqual(len(atlas),12)
        self.assertFalse(COUNTRIES.intersection(atlas))
        self.assertFalse(COUNTRIES.intersection(
            {code for code,country in self.country["countries"].items()
             if country["status"]=="approved"}))


if __name__=="__main__":
    unittest.main()
