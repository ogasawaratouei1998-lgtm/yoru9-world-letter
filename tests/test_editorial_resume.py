import json
import tempfile
import unittest
from pathlib import Path
from editorial_resume import EditorialResume, fingerprint
from local_editorial import normalize_category

class EditorialResumeTests(unittest.TestCase):
    def test_pending_is_recoverable_and_attempted_is_not_permanently_excluded(self):
        first="https://www.bbc.com/news/first"
        second="https://apnews.com/article/second"
        leads=[{"url":url,"title":"not stored","seendate":"2026-11-27T00:00:00Z"} for url in (first,second)]
        groups=[{"groupId":i,"articles":[{"url":row["url"],"text":"not stored"}]} for i,row in enumerate(leads)]
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"queue.json"
            queue=EditorialResume("2026-11-27",path)
            queue.checkpoint_queue(groups,leads)
            queue.record_attempt(groups[0])
            raw=json.loads(path.read_text())
            self.assertEqual(raw["pending"],[{"url":second,"seendate":leads[1]["seendate"]}])
            self.assertEqual(raw["attempted"],[fingerprint(first)])
            self.assertNotIn(first,path.read_text())
            self.assertNotIn("not stored",path.read_text())
            restored=EditorialResume("2026-11-27",path)
            combined=restored.restore_pending(leads[:1])
            self.assertEqual([x["url"] for x in restored.order_leads(combined,combined,2)],[second,first])
            self.assertEqual(restored.order_groups(groups),[groups[1],groups[0]])
            self.assertFalse(EditorialResume("2026-11-28",path).pending)

    def test_untrusted_or_wrong_day_cannot_restore(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"queue.json"
            path.write_text(json.dumps({"version":1,"day":"2026-11-27","pending":[
                {"url":"https://bbc.com.evil.example/article","seendate":"2026-11-27T00:00:00Z"}],
                "attempted":["untrusted text"]}))
            queue=EditorialResume("2026-11-27",path)
            self.assertEqual(queue.pending,{})
            self.assertEqual(queue.attempted,set())

    def test_category_aliases_repair_format_without_changing_subject(self):
        for value,expected in (("個人","person"),("Personal","person"),("ＷＯＲＫ","work"),("スポーツ","sports"),("企業・組織","company")):
            self.assertEqual(normalize_category(value),expected)
        self.assertIsNone(normalize_category("unknown"))

    def test_collection_no_longer_requires_country_assets(self):
        import inspect
        from collect_candidates import main
        self.assertIn("extra_searches=uncovered_country_searches()",inspect.getsource(main))
        self.assertNotIn("ready_country_codes",inspect.getsource(main))

    def test_registry_ranks_before_per_feed_limit(self):
        from news_sources import fetch_registry_feeds
        source={"id":"test-bbc","name":"BBC","url":"https://www.bbc.com/rss","market":"GB","language":"en","focus":"general","site":"bbc.com"}
        items=[{"url":"https://www.bbc.com/news/routine","title":"Routine market update"},
               {"url":"https://www.bbc.com/news/major","title":"Man accidentally sold million dollar artwork with wrong bid"}]
        leads=fetch_registry_feeds(sources=[source],fetch=lambda *a,**k:b"",parse=lambda *a,**k:items,per_feed=1)
        self.assertEqual([x["url"] for x in leads],[items[1]["url"]])
