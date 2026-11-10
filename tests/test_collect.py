import unittest
from collect_candidates import parse_rss, safe_url


class CollectionTest(unittest.TestCase):
    def test_google_news_rss_parses(self):
        rss=b'''<rss version="2.0"><channel><item><title>Shocking mix-up at a bakery</title><link>https://news.google.com/articles/abc</link><source>NewsOutlet</source><pubDate>Tue, 10 Nov 2026 03:00:00 GMT</pubDate></item></channel></rss>'''
        result=parse_rss(rss,'Google News RSS')
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['status'],'unverified')
        self.assertEqual(result[0]['domain'],'NewsOutlet')
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
