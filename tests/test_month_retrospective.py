"""Check public monthly backfill: source independence and no fake historical releases."""
import json
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"data/retrospective/2026-11-17.json"

class RetrospectiveTest(unittest.TestCase):
    def test_collection_has_real_reporting_dates_not_fake_daily_archives(self):
        d=json.loads(SRC.read_text(encoding="utf-8"))
        self.assertEqual(d["status"],"published-retrospective")
        self.assertEqual(d["collectionDate"],"2026-11-17")
        self.assertEqual(d["windowStart"],"2026-10-17")
        self.assertEqual(d["windowEnd"],"2026-11-17")
        self.assertEqual(len(d["stories"]),5)
        self.assertIn("過去に実際の配信があったように見せるものではなく",d["description"])
        a=json.loads((ROOT/"data/archive/index.json").read_text(encoding="utf-8"))
        # On Nov 17, a real nightly edition may legitimately be released.
        # The retrospective is its own collection and must not fabricate
        # dated archive records: every indexed release must actually exist.
        for record in a["issues"]:
            path=ROOT/"data/archive"/(record["date"]+".json")
            with self.subTest(archive=record["date"]):
                self.assertTrue(path.is_file())
                issue=json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(issue["editionDate"],record["date"])
                self.assertEqual(issue["status"],"published")
        self.assertNotEqual(d["status"],"published")

    def test_stories_use_independent_cited_reporting_without_existing_duplicates(self):
        d=json.loads(SRC.read_text(encoding="utf-8"))
        existing=set()
        sources=[ROOT/"data/current.json",ROOT/"data/approved/2026-11-17.json"]
        sources+=list((ROOT/"data/archive").glob("????-??-??.json"))
        for p in sources:
            existing.update(story["id"] for story in json.loads(p.read_text(encoding="utf-8")).get("stories",[]))
        unique=set()
        for s in d["stories"]:
            with self.subTest(title=s["title"]):
                self.assertNotIn(s["id"],existing|unique)
                unique.add(s["id"])
                self.assertTrue(date.fromisoformat(d["windowStart"])<=date.fromisoformat(s["reported"])<=date.fromisoformat(d["windowEnd"]))
                self.assertTrue(20<=len(s["summary"])<=600)
                self.assertTrue(100<=len(s["detail"])<=2000)
                self.assertTrue(s["quip"] and s["quipSecond"] and s["expectedPlan"] and s["observedOutcome"])
                urls=s["verificationUrls"]
                self.assertGreaterEqual(len(urls),2)
                self.assertIn(s["sourceUrl"],urls)
                self.assertGreaterEqual(len({urlsplit(u).hostname.removeprefix("www.") for u in urls}),2)
                self.assertTrue(all(urlsplit(u).scheme=="https" for u in urls))

    def test_historical_collection_remains_auditable_but_is_not_public(self):
        build=(ROOT/"build_site.py").read_text(encoding="utf-8")
        worker=(ROOT/"service-worker.js").read_text(encoding="utf-8")
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertNotIn("data/retrospective/2026-11-17.json",build)
        self.assertNotIn("data/retrospective/2026-11-17.json",worker)
        self.assertNotIn("monthRetrospective",page)
        self.assertFalse((ROOT/".github/workflows/monthly-editorial.yml").exists())


if __name__=="__main__":
    unittest.main()
