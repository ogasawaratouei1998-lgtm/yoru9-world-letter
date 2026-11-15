import unittest
from unittest.mock import patch
import auto_editorial as editorial

class AutoEditorialSafetyTests(unittest.TestCase):
    def test_reject_private_hosts(self):
        with patch.object(editorial.socket,"getaddrinfo",return_value=[(None,None,None,None,("127.0.0.1",443))]):
            self.assertFalse(editorial.public_host("https://example.org/story"))
    def test_reject_non_https(self):
        self.assertFalse(editorial.public_host("http://example.org/story"))
    def test_extract_text_ignores_script(self):
        parser=editorial.ArticleText()
        parser.feed("<html><body><p>Real article content</p><script>fake evidence</script></body></html>")
        self.assertIn("Real article content",parser.parts)
        self.assertNotIn("fake evidence",parser.parts)
    def test_guardian_article_body_excludes_site_navigation(self):
        html=('<nav>'+'Menu '*300+'</nav>'
              '<div data-gu-name="body"><p>'+'Verified article sentence. '*40+'</p></div>'
              '<footer>'+'More links '*200+'</footer>')
        text=editorial.extracted_article_text(html)
        self.assertIn('Verified article sentence.',text)
        self.assertNotIn('Menu',text)
        self.assertNotIn('More links',text)

    def test_unscoped_html_is_not_treated_as_article_evidence(self):
        self.assertEqual(editorial.extracted_article_text(
            '<html><body><nav>Menu</nav><div>Unrelated headlines</div></body></html>'),'')

    def test_model_catalog_selects_supported_model(self):
        import io
        class FakeResponse:
            def __enter__(self):return io.BytesIO(b'{"models":[{"name":"models/gemini-2.5-flash","supportedGenerationMethods":["generateContent"]}]}')
            def __exit__(self,*args):return False
        with patch.object(editorial,"KEY","test"):
            with patch.object(editorial,"urlopen",return_value=FakeResponse()):
                self.assertEqual(editorial.available_model(),"models/gemini-2.5-flash")
    def test_cross_publisher_groups_same_incident(self):
        items=[
            {"title":"Mayor accidentally sends wedding invitation to entire city","url":"https://one.example/story"},
            {"title":"Mayor accidentally sends wedding invitation to city residents","url":"https://two.example/news"},
            {"title":"Mayor accidentally sends wedding invitation to entire city","url":"https://one.example/copy"},
            {"title":"Sports team wins national championship in final","url":"https://three.example/sport"},
        ]
        groups=editorial.corroboration_groups(items)
        self.assertTrue(groups)
        self.assertTrue(any(len({editorial.host(x["url"]) for x in g})>=2 for g in groups))
        self.assertFalse(any(any("three.example" in x["url"] for x in g) for g in groups))
    def test_unrelated_headlines_not_grouped(self):
        items=[{"title":"Bakery delivers salty cakes by mistake","url":"https://one.example/story"},
               {"title":"Airline sends travelers to wrong airport","url":"https://two.example/story"}]
        self.assertEqual(editorial.corroboration_groups(items),[])

    def test_semantic_pairs_require_exact_distinct_source_urls(self):
        items=[{"title":"Mayor sends invitation","url":"https://one.example/a","text":"Mayor sent invitations to residents"},
               {"title":"Residents receive mistaken invitations","url":"https://two.example/b","text":"Invitations reached residents"}]
        response={"pairs":[
            {"urls":["https://one.example/a","https://two.example/b"]},
            {"urls":["https://one.example/a","https://one.example/a"]},
            {"urls":["https://one.example/a","https://evil.example/forged"]},
            {"urls":["https://one.example/a","https://two.example/b"]}]}
        with patch.object(editorial,"ai",return_value=response):
            groups=editorial.semantic_corroboration_groups(items)
        self.assertEqual(len(groups),1)
        self.assertEqual({x["url"] for x in groups[0]},{items[0]["url"],items[1]["url"]})

    def test_semantic_matching_empty_without_ai_call(self):
        with patch.object(editorial,"ai") as mock_ai:
            self.assertEqual(editorial.semantic_corroboration_groups([]),[])
            mock_ai.assert_not_called()

    def test_without_key_does_not_call_ai(self):
        with patch.object(editorial,"KEY",""):
            with patch.object(editorial,"ai") as mock_ai:
                self.assertEqual(editorial.main(),0)
                mock_ai.assert_not_called()

if __name__=="__main__":
    unittest.main()
