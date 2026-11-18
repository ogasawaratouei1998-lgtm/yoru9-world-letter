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
        self.assertGreaterEqual(len(rows),100)
        self.assertGreaterEqual(len({r["site"] for r in rows}),75)
        self.assertGreaterEqual(len({r["market"] for r in rows}),40)
        from country_codes import country_code, country_region
        # Hong Kong is a valid publisher locale, but it is not a separate
        # location in our 196-country editorial coverage convention.
        self.assertTrue(all(country_code(r["market"]) or r["market"]=="HK"
                            for r in rows))
        regions={country_region(r["market"]) for r in rows}
        regions.discard(None)
        self.assertEqual(len(regions),6)
        for market in ("NG","KE","GH","MA","MW","TZ","ID","VN","PK",
                       "BD","FJ","PG","IT","PL","AR","PY","EC","UY"):
            self.assertIn(market,{r["market"] for r in rows})
        self.assertIn("https://rss.upi.com/news/odd_news.rss",{r["url"] for r in rows})
        self.assertIn("oddities",{r["focus"] for r in rows})
        self.assertTrue(all(r["url"].startswith("https://") for r in rows))
        # Every candidate still requires verified ORIGINAL article text.
        self.assertFalse(any("news.google.com" in r["url"] for r in rows))

    def test_new_local_sources_are_editorial_candidates_not_automatic_proof(self):
        from trusted_originals import trusted_original_domain
        catalog=sources.source_registry()
        by_market={}
        for entry in catalog:
            by_market.setdefault(entry["market"],[]).append(entry)
            self.assertIn(entry["language"],sources.ALLOWED_LANGUAGES)
        for market in ("NG","GH","KE","ID","VN","FJ","PG","AR","EC","PY"):
            self.assertTrue(any(x["focus"]=="local" for x in by_market[market]))
        self.assertIn("vi",sources.ALLOWED_LANGUAGES)
        self.assertIn("it",sources.ALLOWED_LANGUAGES)
        self.assertTrue(trusted_original_domain("https://www.myjoyonline.com/story/news"))
        self.assertTrue(trusted_original_domain("https://www.abc.com.py/noticias/story"))
        self.assertFalse(trusted_original_domain("https://abc.com.py.evil.invalid/story"))
        self.assertFalse(trusted_original_domain("http://www.myjoyonline.com/story"))

    def test_sources_with_same_market_rotate_between_publishers(self):
        publishers=[]
        for label,focus in (("general","general"),("sports","sports"),("local","local")):
            publishers.append({
                "id":label+"-news","name":label,"url":"https://"+label+".example.org/rss",
                "market":"NG","language":"en","focus":focus,"site":label+".example.org"
            })
        def fetch(url,timeout):
            from urllib.parse import urlsplit
            name=urlsplit(url).hostname
            items="".join("<item><title>Small business mix-up {0}</title>"
                          "<link>https://{1}/news/{0}</link></item>".format(i,name)
                          for i in range(5))
            return ("<rss><channel>"+items+"</channel></rss>").encode()
        records=sources.fetch_registry_feeds(
            sources=publishers,fetch=fetch,parse=parse_rss,max_workers=3)
        self.assertEqual(len(records),15)
        self.assertEqual([record["registeredSource"] for record in records[:6]],
                         ["local-news","sports-news","general-news"]*2)

    def test_global_local_feed_health_is_observable_by_publisher_market(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            srcs=sources.source_registry()
            nigeria=next(x for x in srcs if x["market"]=="NG")
            italy=next(x for x in srcs if x["market"]=="IT")
            def fetch(url,timeout):
                if url==italy["url"]:
                    raise OSError("feed temporarily unavailable")
                return ("<rss><channel><item><title>Local human mix-up</title>"
                        "<link>https://www."+nigeria["site"]+"/story</link>"
                        "</item></channel></rss>").encode()
            report_path=Path(tmp)/"health.json"
            source_news=sources.fetch_registry_feeds(
                sources=[nigeria,italy],fetch=fetch,parse=parse_rss,
                max_workers=2,report_path=report_path)
            report=json.loads(report_path.read_text())
            self.assertEqual(len(source_news),1)
            self.assertEqual(report["marketHealth"]["NG"],
                             {"attempted":1,"usable":1,"links":1})
            self.assertEqual(report["marketHealth"]["IT"],
                             {"attempted":1,"usable":0,"links":0})
            self.assertIn("NOT verified event locations",report["marketNote"])

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

    def test_first_results_rotate_between_world_markets(self):
        us={"id":"us-first","name":"US Publisher",
            "url":"https://rss.upi.com/news/news.rss","market":"US",
            "language":"en","focus":"general","site":"upi.com"}
        nz={"id":"nz-first","name":"NZ Publisher",
            "url":"https://www.rnz.co.nz/rss/news.xml","market":"NZ",
            "language":"en","focus":"local","site":"rnz.co.nz"}
        def xml(base):
            items="".join(
                f"<item><title>Unexpected local mixup {i}</title>"
                f"<link>https://www.{base}/story{i}</link>"
                f"<pubDate>Tue, 17 Nov 2026 05:00:00 GMT</pubDate></item>"
                for i in range(3))
            return f"<rss><channel>{items}</channel></rss>".encode()
        def fetch(url,timeout):
            return xml("upi.com" if "upi.com" in url else "rnz.co.nz")
        items=sources.fetch_registry_feeds(
            sources=[us,nz],fetch=fetch,parse=parse_rss,max_workers=2)
        self.assertEqual([x["sourcecountry"] for x in items[:4]],
                         ["US","NZ","US","NZ"])

    def test_feed_health_report_only_records_diagnostic_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"source-health.json"
            src=sources.source_registry()[0]
            sources.fetch_registry_feeds(
                sources=[src],fetch=lambda url,timeout:b"<rss><channel></channel></rss>",
                parse=parse_rss,max_workers=1,report_path=path)
            report=json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"],"unverified-feed-health")
            self.assertEqual(report["attempted"],1)
            self.assertEqual(report["usable"],0)
            self.assertEqual(report["feeds"][0]["status"],"empty_or_unusable")
            self.assertEqual(report["feeds"][0]["rawPublisherLeads"],0)
            self.assertNotIn("articleBody",json.dumps(report))
            self.assertNotIn("stories",report)

    def test_unsupported_network_response_never_creates_a_lead(self):
        src=sources.source_registry()[0]
        self.assertEqual(
            sources.fetch_registry_feeds(sources=[src],
            fetch=lambda url,timeout: b"<html>broken</html>",
            parse=parse_rss,max_workers=1),[])


if __name__=="__main__":
    unittest.main()
