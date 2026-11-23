"""Prioritize strong original-news leads before generic feeds fill the cap."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import collect_candidates as collector
import news_sources


class NewsPriorityCapacityTests(unittest.TestCase):
    def test_late_trusted_major_human_mistake_replaces_generic_news(self):
        focused={"title":"Local cafe mixed up its order",
                 "url":"https://www.bbc.com/news/initial-gdelt",
                 "status":"unverified","seendate":"2026-11-23T01:00:00+00:00",
                 "provider":"GDELT DOC API","sourcecountry":"GB"}
        ordinary=[{"title":f"General world developments {i}",
                   "url":f"https://broad{i}.example.org/story",
                   "status":"unverified","seendate":"2026-11-23T01:00:00+00:00",
                   "provider":"Publisher RSS","sourcecountry":"US"}
                  for i in range(350)]
        great="https://www.bbc.com/news/major-bidder-mistake"
        feeds=[(f"https://feed{i}.example/rss","Regional publisher RSS","en","NG")
               for i in range(25)]

        def fetch(url,timeout=20):
            index=int(url.split("feed",1)[1].split(".",1)[0])
            items=[]
            for j in range(18):
                headline=f"General regional headline {index}-{j}"
                link=f"https://regional{index}.example.org/news/{j}"
                if index==24 and j==17:
                    headline="Man accidentally sold million dollar artwork with wrong bid"
                    link=great
                items.append(f"<item><title>{headline}</title><link>{link}</link></item>")
            return ("<rss><channel>"+"".join(items)+"</channel></rss>").encode()

        with tempfile.TemporaryDirectory() as temp:
            previous=Path.cwd()
            try:
                os.chdir(temp)
                with (patch.object(collector,"get_gdelt",return_value=[focused]),
                      patch.object(news_sources,"source_registry",return_value=[]),
                      patch.object(news_sources,"fetch_registry_feeds",return_value=ordinary),
                      patch.object(collector,"LOCAL_LANGUAGE_FEEDS",feeds),
                      patch.object(collector,"INDEPENDENT_FEEDS",[]),
                      patch.object(collector,"BBC_FEEDS",[]),
                      patch.object(collector,"SEARCHES",[]),
                      patch.object(collector,"fetch_bytes",side_effect=fetch)):
                    self.assertEqual(collector.main(),0)
                data=json.loads(Path("data/candidates.json").read_text(encoding="utf-8"))
            finally:
                os.chdir(previous)
        results=data["candidates"]
        self.assertEqual(len(results),750)
        self.assertEqual(results[0]["url"],focused["url"])
        self.assertIn(great,{item["url"] for item in results})
        new=next(item for item in results if item["url"]==great)
        self.assertEqual(new["status"],"unverified")
        self.assertNotIn("country",new)
        self.assertEqual(sum(item["provider"]=="GDELT DOC API" for item in results),1)

    def test_headline_priority_never_authenticates_an_article(self):
        from auto_editorial import incident_priority
        stronger={"title":"Man accidentally sold million dollar artwork with wrong bid",
                  "url":"https://www.bbc.com/news/mistake","status":"unverified"}
        routine={"title":"Company announces quarterly earnings",
                 "url":"https://www.bbc.com/news/earnings","status":"unverified"}
        self.assertLess(incident_priority(stronger),incident_priority(routine))
        self.assertEqual(stronger["status"],"unverified")
        self.assertNotIn("editorVerified",stronger)


if __name__=="__main__":
    unittest.main()
