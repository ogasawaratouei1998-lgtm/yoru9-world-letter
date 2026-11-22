"""Armenia's desk-based heritage reader must preserve real photos and danger warnings."""
import json
import unittest
from pathlib import Path

from country_content import check_country_content, _commons_identity
from check_country_experience import country_coverage

ROOT = Path(__file__).resolve().parents[1]


class ArmeniaReleaseTests(unittest.TestCase):
    def test_heritage_reader_distinguishes_two_unesco_properties_and_safety(self):
        entry = check_country_content(ROOT)["countries"]["AM"]
        self.assertEqual(entry["status"], "approved")
        self.assertEqual(len(entry["portraitPhotos"]), 1)
        self.assertEqual(len(entry["quiz"]), 2)
        self.assertEqual(len(entry["travelStops"]), 3)
        expected = {
            "am-yerevan-republic-square-cover": ("23artashes", "CC BY-SA 3.0"),
            "am-haghpat-monastery-postcard": ("Ahaik", "CC BY-SA 3.0"),
            "am-geghard-rock-monastery-postcard": ("c a r a m e l", "CC BY-SA 2.0"),
        }
        self.assertEqual(set(entry["travelStops"]), set(expected))
        self.assertEqual(len({_commons_identity(p["photoPage"]) for p in entry["travelStops"].values()}), 3)
        for key, (author, license_name) in expected.items():
            with self.subTest(key=key):
                stop = entry["travelStops"][key]
                self.assertEqual(stop["author"], author)
                self.assertEqual(stop["license"], license_name)
                self.assertTrue(stop["photo"].startswith("https://thumb.wikimedia.org/wikipedia/commons/thumb/"))
        for level in ("レベル4", "レベル2", "レベル1"):
            self.assertIn(level, entry["portrait"]["body"])
        self.assertIn("渡航を推奨するものではありません", entry["portrait"]["body"])
        for q in entry["quiz"]:
            stop = entry["travelStops"][q["photoKey"]]
            self.assertEqual(len(stop["travelStory"]), 2)
            self.assertTrue(all(110 <= len(t) <= 360 for t in stop["travelStory"]))
            self.assertTrue(any(x["url"].startswith("https://whc.unesco.org/") for x in stop["historicalSources"]))
            self.assertTrue(any(x["url"].startswith("https://www.anzen.mofa.go.jp/") for x in stop["historicalSources"]))
        self.assertEqual(set(country_coverage(ROOT, [{"country": "AM"}])), {"AM"})

    def test_all_three_source_matched_bytes_and_safe_camera_context(self):
        entry = check_country_content(ROOT)["countries"]["AM"]
        seeds = json.loads((ROOT / "editorial-country-photo-reviews/cache-seeds.json").read_text(encoding="utf-8"))["photos"]
        own = [x for x in seeds if x["country"] == "アルメニア"]
        self.assertEqual({x["file"] for x in own}, {"AM-0.jpg", "AM-1.jpg", "AM-2.jpg"})
        self.assertEqual(len(own), 3)
        self.assertEqual(sum(x["cover"] for x in own), 1)
        self.assertEqual({x["photoAsset"] for x in own},
                         {p["photoAsset"] for p in entry["travelStops"].values()})
        for seed in own:
            stop = next(p for p in entry["travelStops"].values() if p["photoAsset"] == seed["photoAsset"])
            for key in ("photoAsset", "photo", "photoPage", "author", "license",
                        "licenseUrl", "country", "place"):
                self.assertEqual(seed[key], stop[key])
            self.assertEqual(seed["runId"], 44986532608)
            self.assertEqual(seed["cover"], bool(stop.get("coverOnly")))
            self.assertRegex(seed["sha256"], r"^[0-9a-f]{64}$")
            self.assertIn("撮影位置ではありません", stop["note"])
        review = json.loads((ROOT / "editorial-country-photo-reviews/armenia-20261122.json").read_text(encoding="utf-8"))
        self.assertFalse(review["publicationEligible"])
        self.assertEqual([p["dimensions"] for p in review["photos"]], [[1280, 960], [960, 720], [800, 532]])
        self.assertEqual([p["sha256"] for p in review["photos"]],
                         [next(x for x in own if x["file"] == "AM-" + str(i) + ".jpg")["sha256"] for i in range(3)])
