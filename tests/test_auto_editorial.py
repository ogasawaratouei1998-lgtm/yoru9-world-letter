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

    def test_without_key_does_not_call_ai(self):
        with patch.object(editorial,"KEY",""):
            with patch.object(editorial,"ai") as mock_ai:
                self.assertEqual(editorial.main(),0)
                mock_ai.assert_not_called()

if __name__=="__main__":
    unittest.main()
