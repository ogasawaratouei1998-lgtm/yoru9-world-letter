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
        with patch.object(c,"fetch_bytes",side_effect=fetch):
            leads=c.get_gdelt()
        self.assertEqual(len(queries),6)
        self.assertEqual(len(leads),6)
        self.assertTrue(any("wrong recipient" in item for item in queries))
        self.assertTrue(any("AI-generated mural" in item for item in queries))
        self.assertTrue(any("misspelled" in item for item in queries))

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
                             for q in first),18)
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
            leads=c.get_gdelt(extra_searches=['("Fiji") ("mistake" OR "blunder")'])
        self.assertEqual(len(queries),7)
        self.assertIn('"Fiji"',queries[0])
        self.assertEqual(len(leads),7)
        self.assertTrue(all(lead["status"]=="unverified" for lead in leads))

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
            leads=c.get_gdelt()
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
