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
        self.assertNotIn("2026-11-17",[v["date"] for v in a["issues"]])

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

    def test_publishing_and_deployment_include_only_public_collection(self):
        build=(ROOT/"build_site.py").read_text(encoding="utf-8")
        self.assertIn("'data/retrospective/2026-11-17.json'",build)
        for name in ("deploy-site.yml","test-publishing.yml"):
            workflow=(ROOT/".github/workflows"/name).read_text(encoding="utf-8")
            self.assertIn("      - 'data/retrospective/**'",workflow)
if __name__=="__main__":
    unittest.main()
