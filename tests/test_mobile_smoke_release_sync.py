"""Prevent post-deploy smoke from confusing the embedded demo with current.json."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class PublishedMobileSmokeSyncTest(unittest.TestCase):
    def test_live_smoke_waits_for_published_issue_before_snapshot(self):
        smoke=(ROOT/"tests/mobile_visual_smoke.mjs").read_text(encoding="utf-8")
        published=smoke.index("const release=document.querySelector('#editionMessage')")
        snapshot=smoke.index("const editorialCover=await page.evaluate(")
        self.assertLess(published,snapshot)
        self.assertIn("otherArticles===count-1",smoke)
        self.assertIn("cards===count",smoke)
        self.assertIn(r"/^\d{4}-\d{2}-\d{2} 発行 · [1-5]本/",smoke)

    def test_demo_and_current_have_different_article_counts(self):
        import json,re
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        demo=json.loads(re.search(
            r'<script id="embedded-demo" type="application/json">(.*?)</script>',
            page,re.S).group(1))
        published=json.loads((ROOT/"data/current.json").read_text(encoding="utf-8"))
        self.assertNotEqual(len(demo["stories"]),len(published["stories"]),
                            "This regression guards the real asynchronous swap.")


if __name__=="__main__":
    unittest.main()
