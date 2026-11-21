"""Poland's 36th country release requires three real, licensed Wikimedia Commons photos."""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
import unittest

from check_country_experience import country_coverage
from country_content import check_country_content
from country_readiness import ready_country_codes

ROOT = Path(__file__).resolve().parents[1]
PHOTOS = {
    "pl-warsaw-old-town-cover": (
        "Warszawa Rynek Starego Miasta 4.jpg", "Andrzej Otrębski"),
    "pl-wawel-castle-postcard": ("Wawel Castle Krakow.jpg", "Lotse8"),
    "pl-wieliczka-salt-chapel-postcard": (
        "Saint Kinga Chapel in Wieliczka Salt Mine.jpg", "Андрей Романенко"),
}
UNESCO = {
    "https://whc.unesco.org/en/list/29/",
    "https://whc.unesco.org/en/list/32/",
}


class PolandPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = check_country_content(ROOT)
        cls.poland = cls.dataset["countries"]["PL"]

    def test_poland_is_approved_with_three_independent_photos_and_quizzes(self):
        approved = {code for code, entry in self.dataset["countries"].items()
                    if entry["status"] == "approved"}
        self.assertIn("PL", approved)
        self.assertGreaterEqual(len(approved), 36)
        self.assertEqual(self.poland["status"], "approved")
        self.assertEqual(len(self.poland["portraitPhotos"]), 1)
        self.assertEqual(len(self.poland["quiz"]), 2)
        self.assertEqual(set(self.poland["travelStops"]), set(PHOTOS))
        self.assertTrue(set(PHOTOS).issubset(self.dataset["travelOrder"]))
        ready, broken = ready_country_codes(ROOT)
        self.assertEqual(ready, approved)
        self.assertNotIn("PL", broken)
        report = country_coverage(ROOT, [{"country": "ポーランド"}])
        self.assertEqual(report["PL"]["cover"], "assets/travel/pl-warsaw-old-town-cover.jpg")
        self.assertEqual(report["PL"]["quizRounds"], 2)

    def test_exact_commons_photo_origin_credits_and_offline_assets(self):
        exported = json.loads((ROOT / "travel-stops.json").read_text(encoding="utf-8"))
        assets, sources = set(), set()
        for key, (filename, author) in PHOTOS.items():
            with self.subTest(photo=key):
                stop = self.poland["travelStops"][key]
                self.assertEqual(stop, exported[key])
                normalized = filename.replace(" ", "_")
                encoded = quote(normalized, safe="-_.()")
                md5 = hashlib.md5(normalized.encode("utf-8")).hexdigest()
                self.assertEqual(
                    stop["photo"],
                    "https://thumb.wikimedia.org/wikipedia/commons/thumb/"
                    + md5[0] + "/" + md5[:2] + "/" + encoded
                    + "/500px-" + encoded,
                )
                self.assertEqual(
                    stop["photoPage"],
                    "https://commons.wikimedia.org/wiki/File:" + encoded,
                )
                self.assertEqual(stop["country"], "ポーランド")
                self.assertEqual(stop["author"], author)
                self.assertEqual(stop["license"], "CC BY-SA 4.0")
                self.assertEqual(
                    stop["licenseUrl"],
                    "https://creativecommons.org/licenses/by-sa/4.0/",
                )
                self.assertTrue(49 <= stop["latitude"] <= 53)
                self.assertTrue(19 <= stop["longitude"] <= 22)
                self.assertNotIn(stop["photoAsset"], assets)
                self.assertNotIn(stop["photoPage"], sources)
                assets.add(stop["photoAsset"])
                sources.add(stop["photoPage"])
        cover = self.poland["portraitPhotos"][0]["asset"]
        quiz_assets = {self.poland["travelStops"][q["photoKey"]]["photoAsset"]
                       for q in self.poland["quiz"]}
        self.assertEqual(len(quiz_assets), 2)
        self.assertNotIn(cover, quiz_assets)
        self.assertEqual(
            set(self.poland["portrait"]["photos"]),
            set(PHOTOS) - {"pl-warsaw-old-town-cover"},
        )
        worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        self.assertRegex(worker, r"yoru9-shell-v[0-9]+")
        for asset in assets:
            self.assertIn("'" + asset + "'", worker)

    def test_krakow_and_wieliczka_long_trips_have_independent_unesco_sources(self):
        source_urls = set()
        for key, stop in self.poland["travelStops"].items():
            if stop.get("coverOnly"):
                self.assertNotIn("travelStory", stop)
                continue
            self.assertTrue(stop["famousTourist"])
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(p) <= 360 for p in stop["travelStory"]))
            self.assertEqual(len(stop["historicalSources"]), 1)
            source = stop["historicalSources"][0]
            self.assertEqual(source["checkedOn"], "2026-11-21")
            source_urls.add(source["url"])
        self.assertEqual(source_urls, UNESCO)
        self.assertEqual(
            {q["photoKey"] for q in self.poland["quiz"]},
            set(PHOTOS) - {"pl-warsaw-old-town-cover"},
        )


if __name__ == "__main__":
    unittest.main()
