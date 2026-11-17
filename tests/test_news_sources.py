"""The source catalog is a discovery list, never an automatic publication permit."""
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import news_sources as sources
from collect_candidates import parse_rss


class NewsSourceRegistryTest(unittest.TestCase):
    def test_registry_has_many_distinct_publisher_feeds_and_world_regions(self):
        rows=sources.source_registry()
        self.assertGreaterEqual(len(rows),60)
        self.assertGreaterEqual(len({r["site"] for r in rows}),40)
        self.assertGreaterEqual(len({r["market"] for r in rows}),10)
        self.assertIn("https://rss.upi.com/news/odd_news.rss",{r["url"] for r in rows})
        self.assertIn("oddities",{r["focus"] for r in rows})
        self.assertTrue(all(r["url"].startswith("https://") for r in rows))
        # Every candidate still requires verified ORIGINAL article text.
        self.assertFalse(any("news.google.com" in r["url"] for r in rows))

    def test_feed_link_must_resolve_to_real_registered_publisher(self):
        self.assertTrue(sources.host_matches("www.upi.com","upi.com"))
        self.assertTrue(sources.host_matches("local.upi.com","upi.com"))
        self.assertFalse(sources.host_matches("upi.com.attacker.example","upi.com"))
        self.assertFalse(sources.host_matches("fakeupi.com","upi.com"))
        self.assertFalse(sources.host_matches("example.net","upi.com"))

    def test_invalid_feed_and_duplicate_definition_are_rejected(self):
        valid=sources.source_registry()[0]
        for bad in (
            [{**valid, "url":"http://rss.upi.com/news/odd_news.rss"}],
            [{**valid, "market":"US/JP"}],
            [{**valid, "focus":"unrestricted"}],
            [{**valid, "site":"upi.com.evil/source"}],
            [valid,valid],
        ):
            with tempfile.TemporaryDirectory() as d:
                path=Path(d)/"feeds.json"
                path.write_text(json.dumps({"version":1,"feeds":bad}))
                with self.assertRaises(ValueError):
                    sources.source_registry(path)

    def test_parallel_feed_fetch_keeps_publishers_and_isolates_broken_feeds(self):
        good={"id":"upi-odd","name":"UPI Odd News",
              "url":"https://rss.upi.com/news/odd_news.rss",
              "market":"US","language":"en","focus":"oddities","site":"upi.com"}
        broken={"id":"failed-site","name":"Other News",
                "url":"https://feed.example.org/rss",
                "market":"NG","language":"en","focus":"general","site":"example.org"}
        xml=b"""<rss><channel><item><title>Friendly mistake at a town shop</title>
        <link>https://www.upi.com/Odd_News/2026/11/17/mistake/123/</link>
        <pubDate>Tue, 17 Nov 2026 05:00:00 GMT</pubDate></item><item>
        <title>Malicious lookalike article</title><link>https://upi.com.evil.example/news</link>
        <pubDate>Tue, 17 Nov 2026 05:00:00 GMT</pubDate></item></channel></rss>"""
        def fetch(url,timeout):
            self.assertEqual(timeout,8)
            if "feed.example.org" in url:
                raise OSError("offline")
            return xml
        leads=sources.fetch_registry_feeds(
            sources=[good,broken],fetch=fetch,parse=parse_rss,max_workers=2)
        self.assertEqual(len(leads),1)
        self.assertEqual(leads[0]["url"],"https://www.upi.com/Odd_News/2026/11/17/mistake/123/")
        self.assertEqual(leads[0]["focus"],"oddities")
        self.assertEqual(leads[0]["registeredSource"],"upi-odd")
        self.assertEqual(leads[0]["sourcecountry"],"US")
        self.assertEqual(leads[0]["status"],"unverified")

    def test_unsupported_network_response_never_creates_a_lead(self):
        src=sources.source_registry()[0]
        self.assertEqual(
            sources.fetch_registry_feeds(sources=[src],
            fetch=lambda url,timeout: b"<html>broken</html>",
            parse=parse_rss,max_workers=1),[])


if __name__=="__main__":
    unittest.main()
