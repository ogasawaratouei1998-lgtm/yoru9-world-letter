import unittest
from unittest.mock import patch
import auto_editorial as editorial

class AutoEditorialSafetyTests(unittest.TestCase):
    def test_country_aliases_share_iso_code(self):
        from country_codes import country_code, country_key
        for label in ("米国","アメリカ","アメリカ合衆国","USA"):
            self.assertEqual(country_code(label),"US")
            self.assertEqual(country_key(label),"US")
        self.assertEqual(country_code("南アフリカ"),"ZA")
        self.assertIsNone(country_code("不明な国"))

    def test_nightly_fallback_avoids_recent_repetition(self):
        from publish_approved import nightly_message, NIGHT_MESSAGES
        stories=[{"category":"work","id":"one"}]
        first=nightly_message("2026-11-17",stories)
        self.assertIn(first,NIGHT_MESSAGES["work"])
        second=nightly_message("2026-11-17",stories,[first])
        self.assertNotEqual(first,second)

    def test_recent_diversity_counts_only_published_last_30_days(self):
        import json
        import tempfile
        from pathlib import Path
        from datetime import date
        with tempfile.TemporaryDirectory() as directory:
            archive=Path(directory)/"data"/"archive"
            archive.mkdir(parents=True)
            for day,status,country in [
                ("2026-11-15","published","日本"),
                ("2026-11-14","published","日本"),
                ("2026-11-13","draft","フランス"),
                ("2026-09-01","published","米国"),
                ("2026-11-16","published","カナダ"),
            ]:
                (archive/(day+".json")).write_text(json.dumps({
                    "status":status,"editionDate":day,
                    "stories":[{"country":country,"category":"work"}]
                },ensure_ascii=False),encoding="utf-8")
            import os
            previous=os.getcwd()
            try:
                os.chdir(directory)
                countries,categories=editorial.recent_diversity_counts(date(2026,11,16))
            finally:
                os.chdir(previous)
            self.assertEqual(countries["日本"],2)
            self.assertEqual(sum(countries.values()),2)
            self.assertEqual(categories["work"],2)

    def test_editorial_mission_requires_real_failure_and_reframing(self):
        mission=editorial.EDITORIAL_MISSION
        self.assertIn("real, consequential failures",mission)
        self.assertIn("warm, witty AI quip",mission)
        self.assertIn("concrete reframing",mission)
        self.assertIn("Never replace a failure with generic",mission)
        self.assertIn("Do not invent a happy ending",mission)

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

    def test_additional_publisher_article_containers(self):
        for opening in ('<div class="article-content">', '<section class="story-body">',
                        '<div itemprop="articleBody">', '<div data-testid="article-body">'):
            with self.subTest(opening=opening):
                html='<nav>Navigation</nav>'+opening+'Verified detail. '*60+'</div><footer>Links</footer>'
                body=editorial.extracted_article_text(html)
                self.assertIn('Verified detail.',body)
                self.assertNotIn('Navigation',body)
                self.assertNotIn('Links',body)

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

    def test_distinct_group_selection_removes_overlapping_incidents(self):
        a={"title":"Event A","url":"https://one.example/a"}
        b={"title":"Event A corroboration","url":"https://two.example/b"}
        c={"title":"Event A alternate","url":"https://three.example/c"}
        d={"title":"Event B","url":"https://four.example/d"}
        e={"title":"Event B corroboration","url":"https://five.example/e"}
        groups=editorial.select_distinct_groups([[a,b],[a,c],[d,e]])
        self.assertEqual(len(groups),2)
        self.assertEqual(groups[0],[a,b])
        self.assertEqual(groups[1],[d,e])

    def test_distinct_group_selection_avoids_first_match_trap(self):
        a={"url":"https://one.example/a"}
        b={"url":"https://two.example/b"}
        c={"url":"https://three.example/c"}
        d={"url":"https://four.example/d"}
        # The first pair blocks both later pairs, but the later two
        # independently corroborated pairs can coexist.
        groups=editorial.select_distinct_groups([[a,b],[a,c],[b,d]])
        self.assertEqual(len(groups),2)
        self.assertEqual(groups,[[a,c],[b,d]])

    def test_distinct_group_selection_is_bounded(self):
        groups=[[{"url":f"https://one.example/{i}"},
                 {"url":f"https://two.example/{i}"}] for i in range(30)]
        self.assertEqual(len(editorial.select_distinct_groups(groups,limit=5)),5)

    def test_expanded_distinct_group_budget_preserves_30_independent_events(self):
        groups=[[{"url":f"https://source-a.example/{i}"},
                 {"url":f"https://source-b.example/{i}"}] for i in range(30)]
        self.assertEqual(len(editorial.select_distinct_groups(groups,limit=36)),30)

    def test_distinct_group_selection_rejects_single_publisher(self):
        a={"url":"https://one.example/a"}
        b={"url":"https://one.example/b"}
        self.assertEqual(editorial.select_distinct_groups([[a,b]]),[])

    def test_semantic_matching_empty_without_ai_call(self):
        with patch.object(editorial,"ai") as mock_ai:
            self.assertEqual(editorial.semantic_corroboration_groups([]),[])
            mock_ai.assert_not_called()

    def test_seven_day_reporting_window(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now=datetime(2026,11,15,21,0,tzinfo=ZoneInfo("Asia/Tokyo"))
        self.assertTrue(editorial.valid_recent_reported("2026-11-15",now))
        self.assertTrue(editorial.valid_recent_reported("2026-11-08",now))
        self.assertFalse(editorial.valid_recent_reported("2026-11-07",now))
        self.assertFalse(editorial.valid_recent_reported("2026-11-16",now))
        self.assertFalse(editorial.valid_recent_reported("unverified",now))

    def test_incident_relevance_ranking_is_not_fact_approval(self):
        leads=[{"title":"World leaders meet at summit","url":"https://example.org/a"},
               {"title":"Company accidentally sends wrong invoices","url":"https://example.org/b"}]
        ranked=sorted(leads,key=editorial.incident_priority)
        self.assertEqual(ranked[0]["url"],"https://example.org/b")
        self.assertEqual(ranked[1]["url"],"https://example.org/a")

    def test_without_key_does_not_call_ai(self):
        with patch.object(editorial,"KEY",""):
            with patch.object(editorial,"ai") as mock_ai:
                self.assertEqual(editorial.main(),0)
                mock_ai.assert_not_called()

if __name__=="__main__":
    unittest.main()
