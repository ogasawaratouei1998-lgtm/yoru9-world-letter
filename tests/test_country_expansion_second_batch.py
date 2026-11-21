"""Second independent expansion batch: exact Commons photo identity and reader QA."""
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
import unittest

from country_content import check_country_content
from country_readiness import ready_country_codes
from check_country_experience import country_coverage

ROOT=Path(__file__).resolve().parents[1]


class SecondCountryExpansionTests(unittest.TestCase):
    def test_all_three_countries_are_fully_published_not_faked(self):
        source=check_country_content(ROOT)
        ready, incomplete=ready_country_codes(ROOT)
        for code in ("NL","SG","MX"):
            with self.subTest(code=code):
                row=source["countries"][code]
                self.assertEqual(row["status"],"approved")
                self.assertIn(code,ready)
                self.assertNotIn(code,incomplete)
                self.assertEqual(len(row["portraitPhotos"]),1)
                self.assertEqual(len(row["quiz"]),2)
                self.assertEqual(len(row["travelStops"]),3)
                cover=row["portraitPhotos"][0]["asset"]
                answers={row["travelStops"][q["photoKey"]]["photoAsset"]
                         for q in row["quiz"]}
                self.assertEqual(len(answers),2)
                self.assertNotIn(cover,answers)
                self.assertEqual(set(country_coverage(ROOT,[{"country":code}])),{code})
        self.assertEqual(len(ready),25)
        self.assertEqual(sum(row["status"]=="pending"
                             for row in source["countries"].values()),171)

    def test_new_photo_paths_are_exact_commons_file_hashes_not_other_countries(self):
        source=check_country_content(ROOT)
        assigned=set()
        for code in ("NL","SG","MX"):
            for key,photo in source["countries"][code]["travelStops"].items():
                with self.subTest(code=code,key=key):
                    page=photo["photoPage"]
                    self.assertTrue(page.startswith("https://commons.wikimedia.org/wiki/File:"))
                    file=unquote(page.split("File:",1)[1])
                    md5=hashlib.md5(file.encode("utf-8")).hexdigest()
                    prefix=md5[0]+"/"+md5[:2]
                    thumb=photo["photo"]
                    self.assertIn("/wikipedia/commons/thumb/"+prefix+"/",thumb)
                    self.assertTrue(thumb.endswith("/500px-"+page.split("File:",1)[1]))
                    self.assertEqual(photo["country"],source["countries"][code]["name"])
                    self.assertEqual(photo["license"],"CC BY-SA 4.0")
                    self.assertEqual(photo["licenseUrl"],
                                     "https://creativecommons.org/licenses/by-sa/4.0/")
                    self.assertTrue(photo["author"])
                    self.assertNotIn(photo["photoAsset"],assigned)
                    assigned.add(photo["photoAsset"])
        self.assertEqual(len(assigned),9)

    def test_new_travel_essays_are_distinct_and_officially_sourced(self):
        data=check_country_content(ROOT)
        urls={
            "NL":{"https://whc.unesco.org/en/list/1349/",
                  "https://whc.unesco.org/en/list/818/"},
            "SG":{"https://whc.unesco.org/en/list/1483/",
                  "https://www.gardensbythebay.com.sg/en/things-to-do/attractions/supertree-grove.html"},
            "MX":{"https://whc.unesco.org/en/list/414/",
                  "https://whc.unesco.org/en/list/483/"},
        }
        for code in urls:
            stories=[]
            actual=set()
            for stop in data["countries"][code]["travelStops"].values():
                if stop.get("coverOnly"):
                    continue
                self.assertEqual(len(stop["travelStory"]),2)
                self.assertTrue(all(110<=len(p)<=360 for p in stop["travelStory"]))
                stories.extend(stop["travelStory"])
                actual.update(src["url"] for src in stop["historicalSources"])
            self.assertEqual(actual,urls[code])
            self.assertEqual(len(stories),4)
            self.assertEqual(len(set(stories)),4)


if __name__=="__main__":
    unittest.main()
