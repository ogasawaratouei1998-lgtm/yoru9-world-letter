"""The dated four-story issue uses four distinct free illustrations and three factual countries."""
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from country_codes import country_codes

ROOT=Path(__file__).resolve().parents[1]
ART={
    "italy-toilet-ai-python-48-hour-search-2026":"ai-python-toilet.svg",
    "drew-carey-price-right-early-reveal-2026":"game-show-price-board.svg",
    "mainz-sewer-search-lost-drone-2026":"drone-sewer-search.svg",
    "kusel-lost-handcuff-key-police-help-2026":"lost-handcuff-key.svg",
}


class IllustratedCountryCountTest(unittest.TestCase):
    def test_nov20_four_stories_three_real_countries_and_four_distinct_images(self):
        issue=json.loads((ROOT/"data/archive/2026-11-20.json").read_text(encoding="utf-8"))
        self.assertEqual(len(issue["stories"]),4)
        self.assertEqual({c for story in issue["stories"] for c in country_codes(story["country"])},
                         {"IT","US","DE"})
        self.assertEqual({story["id"] for story in issue["stories"]},set(ART))
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        service=(ROOT/"service-worker.js").read_text(encoding="utf-8")
        for story_id,filename in ART.items():
            asset=ROOT/"assets/news"/filename
            with self.subTest(story=story_id):
                self.assertIn("'"+story_id+"':'"+filename+"'",html)
                self.assertIn("assets/news/"+filename,service)
                self.assertTrue(asset.is_file())
                content=asset.read_text(encoding="utf-8")
                svg=ET.fromstring(content)
                self.assertEqual(svg.tag,"{http://www.w3.org/2000/svg}svg")
                self.assertEqual(svg.get("viewBox"),"0 0 800 480")
                self.assertNotIn("<script",content)
                self.assertNotIn("<foreignObject",content)
                self.assertNotIn("href=",content)
                self.assertGreater(len(list(svg.iter())),10)

    def test_map_distinguishes_four_articles_from_three_country_stamps(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("const countries=currentIssueCountries();",html)
        self.assertIn("const countNote='実話'+edition.stories.length+'本・'+countries.length+'カ国'",html)
        self.assertIn("重複を除いた国数",html)
        self.assertIn("c.name+' '+c.indices.length+'本'",html)
        self.assertIn("newsArt(story)",html)


if __name__=="__main__":
    unittest.main()
