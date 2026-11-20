import unittest
from collect_candidates import parse_rss, safe_url
import collect_candidates as c


class CollectionTest(unittest.TestCase):
    def test_gdelt_discovers_human_errors_from_several_searches(self):
        import json
        from urllib.parse import parse_qs, urlsplit
        from unittest.mock import patch
        queries=[]
        def fetch(url):
            query=parse_qs(urlsplit(url).query)["query"][0]
            queries.append(query)
            i=len(queries)
            return json.dumps({"articles":[{
                "title":"Worker's wrong order leads to surprise",
                "url":f"https://report{i}.example.com/mistake",
                "seendate":"20261118T010000Z",
                "domain":f"report{i}.example.com",
                "sourcecountry":"GB","language":"English",
            }]}).encode()
        from datetime import date,timedelta
        day=date(2026,11,18)
        with patch.object(c,"fetch_bytes",side_effect=fetch):
            for offset in range(5):
                leads=c.get_gdelt(min_interval_seconds=0,
                                  day=day+timedelta(days=offset))
                self.assertEqual(len(leads),5)
        self.assertEqual(len(queries),25)
        # Four of the five daily GDELT searches now favor substantial
        # personally attributable mistakes; local-market queries remain.
        self.assertGreaterEqual(len(set(queries)),10)
        for phrase in ("million dollar mistake","accidentally bought",
                       "major blunder","AI hoax","wrong country",
                       "wrong price","error millonario","teurer Fehler","誤落札"):
            self.assertTrue(any(phrase in q for q in queries),phrase)
        self.assertTrue(any('"mistake"' in q and '"mix-up"' in q for q in queries))

    def test_unseen_country_discovery_rotates_without_claiming_publisher_origin(self):
        from datetime import date,timedelta
        import re
        from country_codes import catalog
        day=date(2026,11,18)
        first=c.uncovered_country_searches(day)
        second=c.uncovered_country_searches(day+timedelta(days=1))
        self.assertEqual(len(first),3)
        self.assertEqual(len(second),3)
        self.assertNotEqual(first,second)
        self.assertEqual(sum(len(re.findall(r'"[A-Za-z][A-Za-z0-9 .-]{2,64}"',q))
                             for q in first),21)
        for query in first:
            self.assertIn('"mistake"',query)
            self.assertIn('"mix-up"',query)
            self.assertIn('"blunder"',query)
            self.assertNotIn("sourcecountry",query)
        self.assertEqual(len(catalog()),196)

    def test_country_targeting_respects_only_published_archive(self):
        from datetime import date
        from unittest.mock import patch
        from pathlib import Path
        import json,tempfile,os
        from country_codes import catalog
        day=date(2026,11,18)
        codes=sorted(row["code"] for row in catalog())
        # The first rotating window is known, so test publication removes a
        # genuinely targeted location and draft content does not.
        selected=codes[(day.toordinal()*9)%len(codes)]
        entry=next(x for x in catalog() if x["code"]==selected)
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/"data"/"archive";archive.mkdir(parents=True)
            (archive/"2026-11-16.json").write_text(json.dumps({
                "status":"draft","editionDate":"2026-11-16",
                "stories":[{"country":selected}]
            }),encoding="utf-8")
            old=os.getcwd()
            try:
                os.chdir(tmp)
                baseline=c.uncovered_country_searches(day)
                (archive/"2026-11-16.json").write_text(json.dumps({
                    "status":"published","editionDate":"2026-11-16",
                    "stories":[{"country":selected}]
                }),encoding="utf-8")
                after=c.uncovered_country_searches(day)
            finally:
                os.chdir(old)
        self.assertNotEqual(baseline,after)

    def test_targeted_gdelt_adds_original_article_leads_before_generic_queries(self):
        import json
        from urllib.parse import parse_qs,urlsplit
        from unittest.mock import patch
        queries=[]
        def fetch(url):
            q=parse_qs(urlsplit(url).query)["query"][0]
            queries.append(q)
            return json.dumps({"articles":[{
                "title":"Local street sign mistake",
                "url":f"https://original{len(queries)}.example.org/story",
                "sourcecountry":"FR","language":"English"
            }]}).encode()
        with patch.object(c,"fetch_bytes",side_effect=fetch):
            leads=c.get_gdelt(extra_searches=['("Fiji") ("mistake" OR "blunder")'],
                              min_interval_seconds=0)
        self.assertEqual(len(queries),5)
        self.assertIn('"Fiji"',queries[0])
        self.assertEqual(len(leads),5)
        self.assertTrue(all(lead["status"]=="unverified" for lead in leads))


    def test_gdelt_rate_limit_and_plain_text_failures_are_logged_and_paced(self):
        import json
        from urllib.error import HTTPError
        from unittest.mock import patch
        url="https://api.gdeltproject.org/api/v2/doc/doc"
        calls=[]
        def fetch(request):
            calls.append(request)
            if len(calls)==1:
                raise HTTPError(url,429,"Too Many Requests",None,None)
            if len(calls)==2:
                return b"Please limit requests to one every 5 seconds"
            n=len(calls)
            return json.dumps({"articles":[
                {"title":"Town makes a funny human mistake",
                 "url":f"https://original{n}.example.org/report",
                 "sourcecountry":"FR"}]}).encode()
        health={}
        with (patch.object(c,"fetch_bytes",side_effect=fetch),
              patch.object(c.time,"sleep") as mock_sleep):
            result=c.get_gdelt(min_interval_seconds=5.5,
                               diagnostics=health)
        self.assertEqual(health["planned"],5)
        self.assertEqual(health["attempted"],2)
        self.assertEqual(health["http_429"],1)
        self.assertEqual(health["rate_limit_notice"],1)
        self.assertEqual(health["circuit_open"],1)
        self.assertEqual(health["unverified_original_links"],0)
        self.assertEqual(len(result),0)
        self.assertEqual(mock_sleep.call_count,1)
        self.assertEqual(mock_sleep.call_args.args,(5.5,))
        self.assertTrue(all(x["status"]=="unverified" for x in result))
        self.assertFalse(any("eventCountry" in x for x in result))

    def test_gdelt_delay_is_configurable_for_unit_tests(self):
        from unittest.mock import patch
        with (patch.object(c,"fetch_bytes",return_value=b'{"articles":[]}'),
              patch.object(c.time,"sleep") as sleep):
            result=c.get_gdelt(min_interval_seconds=0)
        self.assertEqual(result,[])
        self.assertEqual(sleep.call_count,4)
        self.assertTrue(all(arg.args==(0,) for arg in sleep.call_args_list))

    def test_gdelt_one_429_can_recover_without_hammering(self):
        import json
        from urllib.error import HTTPError
        from unittest.mock import patch
        count=[0]
        def fetch(url):
            count[0]+=1
            if count[0]==1:
                raise HTTPError(url,429,"Too many requests",None,None)
            return json.dumps({"articles":[{
                "title":"A funny human mix-up",
                "url":f"https://news{count[0]}.example.org/report",
                "sourcecountry":"NG"
            }]}).encode()
        health={}
        with (patch.object(c,"fetch_bytes",side_effect=fetch),
              patch.object(c.time,"sleep") as delay):
            leads=c.get_gdelt(min_interval_seconds=10.5,diagnostics=health)
        self.assertEqual(count[0],5)
        self.assertEqual(health["attempted"],5)
        self.assertEqual(health["http_429"],1)
        self.assertEqual(health["responded"],4)
        self.assertNotIn("circuit_open",health)
        self.assertEqual(len(leads),4)
        self.assertEqual(delay.call_count,4)

    def test_original_comedy_search_is_reserved_even_when_feeds_fill_budget(self):
        """Generic publisher headlines cannot starve targeted original discovery."""
        import tempfile, os, json
        from unittest.mock import patch
        from urllib.error import URLError
        from pathlib import Path
        focused={
            "title":"A cafe mixed up its order","url":"https://localstory.example.org/real",
            "status":"unverified","seendate":"2026-11-18T01:00:00+00:00",
            "provider":"GDELT DOC API","sourcecountry":"Italy","language":"Italian",
        }
        registry=[{
            "title":f"Local general story {i}",
            "url":f"https://publisher{i}.example.net/story",
            "status":"unverified","seendate":"2026-11-18T01:00:00+00:00",
            "provider":"Local publisher RSS","sourcecountry":"US","language":"en",
        } for i in range(750)]
        import news_sources
        counter=[0]
        def local_feed(url,timeout=20):
            counter[0]+=1
            i=counter[0]
            body="".join(
                f"<item><title>General update {i}/{n}</title>"
                f"<link>https://broad{i}.example.net/story/{n}</link></item>"
                for n in range(18))
            return ("<rss><channel>"+body+"</channel></rss>").encode()
        with tempfile.TemporaryDirectory() as temp:
            previous=os.getcwd()
            try:
                os.chdir(temp)
                with (patch.object(c,"get_gdelt",return_value=[focused]),
                      patch.object(news_sources,"fetch_registry_feeds",
                                   return_value=registry),
                      patch.object(c,"fetch_bytes",side_effect=local_feed),
                      patch.object(c.time,"sleep",return_value=None)):
                    self.assertEqual(c.main(),0)
                payload=json.loads(Path("data/candidates.json").read_text())
            finally:
                os.chdir(previous)
        self.assertEqual(len(payload["candidates"]),750)
        self.assertEqual(payload["candidates"][0]["url"],focused["url"])
        self.assertEqual(payload["candidates"][0]["provider"],"GDELT DOC API")
        self.assertEqual(sum(x["provider"]=="GDELT DOC API"
                             for x in payload["candidates"]),1)
        # No article or location can be reported verified by this discovery.
        self.assertEqual(payload["candidates"][0]["status"],"unverified")
        self.assertNotIn("country",payload["candidates"][0])

    def test_original_publisher_search_precedes_broad_feed_collection(self):
        import inspect
        code=inspect.getsource(c.main)
        self.assertLess(code.index("focused=get_gdelt("),
                        code.index("registered=fetch_registry_feeds("))
        self.assertIn("keep(focused,limit=90)",code)

    def test_gdelt_caps_each_search_and_deduplicates(self):
        import json
        from unittest.mock import patch
        def fetch(url):
            self.assertIn('timespan=7d',url)
            self.assertIn('maxrecords=40',url)
            return json.dumps({'articles':[
                {'title':'Local road sign misspelled',
                 'url':f'https://example.org/story-{i}',
                 'seendate':'20261118T003000Z',
                 'domain':'example.org','sourcecountry':'GB',
                 'language':'English'} for i in range(12)]}).encode()
        with patch.object(c,'fetch_bytes',side_effect=fetch):
            leads=c.get_gdelt(min_interval_seconds=0)
        # Ten from the first query, then the remaining two unique URLs.
        # Later queries cannot duplicate already discovered publisher reports.
        self.assertEqual(len(leads),12)
        self.assertEqual(len({v['url'] for v in leads}),12)

    def test_regional_bbc_feeds_support_local_mistakes(self):
        self.assertTrue(any('lancashire/rss.xml' in url for url in c.BBC_FEEDS))
        self.assertTrue(any('leicestershire/rss.xml' in url for url in c.BBC_FEEDS))
        import inspect
        self.assertIn("sourcecountry='GB'",inspect.getsource(c.main))

    def test_google_news_rss_parses(self):
        rss=b'''<rss version="2.0"><channel><item><title>Shocking mix-up at a bakery</title><link>https://news.google.com/articles/abc</link><source>NewsOutlet</source><pubDate>Tue, 10 Nov 2026 03:00:00 GMT</pubDate></item></channel></rss>'''
        result=parse_rss(rss,'Google News RSS')
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['status'],'unverified')
        self.assertEqual(result[0]['domain'],'NewsOutlet')
    def test_local_language_rss_preserves_language_and_country(self):
        rss='<rss><channel><item><title>Une erreur de livraison</title><link>https://www.lemonde.fr/example</link></item></channel></rss>'.encode('utf-8')
        result=parse_rss(rss,'Le Monde RSS',language='fr',sourcecountry='FR')
        self.assertEqual(result[0]['language'],'fr')
        self.assertEqual(result[0]['sourcecountry'],'FR')
        self.assertEqual(result[0]['status'],'unverified')

    def test_german_rdf_feed_is_supported(self):
        rdf='''<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/"><item><title>Fehler bei Lieferung</title><link>https://www.dw.com/de/story</link></item></rdf:RDF>'''.encode('utf-8')
        result=parse_rss(rdf,'DW Deutsch',language='de',sourcecountry='DE')
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['language'],'de')

    def test_direct_publisher_sources_span_undercovered_regions(self):
        from collect_candidates import LOCAL_LANGUAGE_FEEDS
        from country_codes import country_region
        countries={country for _,_,_,country in LOCAL_LANGUAGE_FEEDS}
        for code in ("JP","IN","BR","NG","PH"):
            self.assertIn(code,countries)
        regions={country_region(code) for code in countries}
        self.assertTrue({"アジア","アフリカ","南アメリカ","ヨーロッパ"} <= regions)
        self.assertTrue(all(url.startswith("https://") for url,_,_,_ in LOCAL_LANGUAGE_FEEDS))

    def test_direct_feeds_collected_before_google_aggregator(self):
        from pathlib import Path
        code=(Path(__file__).resolve().parents[1]/"collect_candidates.py").read_text(encoding="utf-8")
        self.assertLess(code.index("for url,provider,language,country in LOCAL_LANGUAGE_FEEDS:"),
                        code.index("for i,(q,lang,country,ceid) in enumerate(SEARCHES):"))
        self.assertIn("sourcecountry is the publisher/search market",code)

    def test_tragedy_filter(self):
        rss=b'<rss><channel><item><title>Two killed in error</title><link>https://news.google.com/articles/abc</link></item></channel></rss>'
        self.assertEqual(parse_rss(rss,'Google News RSS'),[])
    def test_bbc_relevance_filter(self):
        rss=b'<rss><channel><item><title>General politics update</title><link>https://www.bbc.co.uk/news/world-1</link></item></channel></rss>'
        self.assertEqual(parse_rss(rss,'BBC RSS',relevant_only=True),[])
    def test_malicious_link_rejected(self):
        self.assertIsNone(safe_url('javascript:alert(1)'))
        self.assertIsNone(safe_url('http://insecure.example.org/story'))


if __name__=='__main__':unittest.main()
