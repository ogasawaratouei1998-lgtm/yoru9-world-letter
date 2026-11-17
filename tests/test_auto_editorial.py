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

    def test_region_catalog_requires_a_recognized_country(self):
        from country_codes import country_region
        self.assertEqual(country_region("日本"),"アジア")
        self.assertEqual(country_region("BR"),"南アメリカ")
        self.assertEqual(country_region("USA"),"北アメリカ")
        self.assertIsNone(country_region("未確認"))
        self.assertIsNone(country_region("架空の国"))

    def test_evidence_retrieval_rotates_geographic_source_markets(self):
        leads=[{"title":"Company error","url":f"https://us{i}.example/story",
                "sourcecountry":"US"} for i in range(20)]
        for market in ("FR","BR","NG","IN"):
            leads.extend({"title":"Workplace mistake",
                          "url":f"https://{market.lower()}{i}.example/story",
                          "sourcecountry":market} for i in range(3))
        leads.append({"title":"Google result","url":"https://news.google.com/articles/abc",
                      "sourcecountry":"US"})
        ordered=editorial.balanced_source_retrieval(leads,limit=5)
        from country_codes import country_region
        regions={country_region(lead["sourcecountry"]) for lead in ordered}
        self.assertEqual(len(ordered),5)
        self.assertEqual(len(regions),5)
        self.assertTrue(all("news.google.com" not in lead["url"] for lead in ordered))
        self.assertEqual(leads[0]["sourcecountry"],"US")

    def test_evidence_retrieval_keeps_per_host_limit(self):
        leads=[{"title":"Mistake","url":f"https://www.theguardian.com/article-{i}",
                "sourcecountry":"GB"} for i in range(15)]
        leads.extend({"title":"Mistake","url":f"https://local{i}.example/story",
                      "sourcecountry":"NG"} for i in range(30))
        ordered=editorial.balanced_source_retrieval(leads,limit=50)
        self.assertEqual(sum("theguardian.com" in lead["url"] for lead in ordered),5)
        self.assertEqual(len(ordered),35)

    def test_verified_selection_prefers_regions_and_perspectives_in_three_stories(self):
        from collections import Counter
        pool=[{"id":f"us{i}","country":"US","category":"company"} for i in range(5)]
        pool.extend([
            {"id":"br","country":"BR","category":"person"},
            {"id":"fr","country":"FR","category":"work"},
            {"id":"ng","country":"NG","category":"sports"},
            {"id":"in","country":"IN","category":"person"},
        ])
        chosen=editorial.select_diverse_verified_stories(pool,Counter(),Counter())
        from country_codes import country_region
        self.assertEqual(len(chosen),3)
        self.assertEqual(len({country_region(s["country"]) for s in chosen}),3)
        self.assertEqual(len({s["category"] for s in chosen}),3)

    def test_verified_selection_prioritizes_underrepresented_countries_in_tie(self):
        from collections import Counter
        pool=[{"id":v,"country":v,"category":"work"} for v in ("US","CA","MX","FR")]
        chosen=editorial.select_diverse_verified_stories(
            pool,Counter({"US":18,"CA":1,"MX":2,"FR":1}),Counter())
        self.assertEqual({s["country"] for s in chosen},{"CA","MX","FR"})

    def test_editorial_fitness_requires_real_plan_and_observed_failure(self):
        story={"title":"会社の発注ミスが発覚","summary":"想定とは異なる部品が納入された。",
               "detail":"作業の確認を誤った。","quip":"計画と現実の差が出た。",
               "expectedPlan":"正しい部品を指定して納入する予定でした。",
               "observedOutcome":"誤った番号の部品が納入されたと報じられた。"}
        self.assertIsNone(editorial.editorial_fit_rejection(story))
        self.assertEqual(editorial.editorial_fit_rejection(
            {**story,"expectedPlan":""}),"missing_source_grounded_plan_or_outcome")
        self.assertEqual(editorial.editorial_fit_rejection(
            {**story,"observedOutcome":story["expectedPlan"]}),"no_observed_failure_contrast")

    def test_editorial_fitness_rejects_private_life_gossip(self):
        story={"title":"CEOの私生活と交際相手を報じた記事",
               "summary":"会社トップの退任を発表した。",
               "detail":"詳しい事情を公表していない。","quip":"会議が増える。",
               "expectedPlan":"会社は通常の経営運営を続ける計画だった。",
               "observedOutcome":"トップの退任と暫定CEOの選任が発表された。"}
        self.assertEqual(editorial.editorial_fit_rejection(story),"private_gossip")

    def test_editorial_fit_rejects_coercive_self_help_not_natural_warmth(self):
        story={"title":"仕事の勘違い","summary":"注文の数を間違えた。",
               "detail":"予定の数より多く届いた。","quip":"注文だけ張り切りすぎた。",
               "expectedPlan":"職場では正しい数を注文する予定だった。",
               "observedOutcome":"実際には想定より多く注文してしまった。"}
        self.assertIsNone(editorial.editorial_fit_rejection(story))
        for phrase in ("あなたより大変", "感謝すべき", "もっと頑張れ",
                       "必ず元気になる", "笑わなければならない"):
            with self.subTest(phrase=phrase):
                self.assertEqual(editorial.editorial_fit_rejection(
                    {**story,"detail":phrase}),"coercive_reader_tone")

    def test_ai_approved_json_matches_one_source_publisher_rules(self):
        from pathlib import Path
        code=(Path(__file__).resolve().parents[1]/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn("1<=len(urls)<=3",code)
        self.assertIn("trusted_original_domain(urls[0])",code)
        self.assertIn("single_original_not_verified",code)
        self.assertIn("if len(evidence)<1",code)
        self.assertIn("validate_approved(payload,day)",code)
        self.assertIn("a syndicated copy, social media repost",code)

    def test_ai_audit_does_not_require_a_compulsory_life_lesson(self):
        from pathlib import Path
        code=(Path(__file__).resolve().parents[1]/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertNotIn("missing compassionate reframing",code)
        self.assertNotIn("offer a specific perspective shift",code)
        self.assertIn("prescriptive or humiliating reader commentary",code)

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
            self.assertEqual(countries["JP"],2)
            self.assertEqual(sum(countries.values()),2)
            self.assertEqual(categories["work"],2)

    def test_global_perspective_comes_from_verified_worldly_incidents_not_pain_comparisons(self):
        mission=editorial.EDITORIAL_MISSION
        craft=editorial.WRITING_CRAFT
        self.assertIn("world beyond that view is wider",mission)
        self.assertIn("reader's burdens are not smaller",mission)
        self.assertIn("never a quota or substitute for evidence",mission)
        self.assertIn("publication's market is never evidence",craft)
        self.assertIn("Never invent local customs",craft)
        source=(__import__("pathlib").Path(__file__).resolve().parents[1]/
                "auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn("Reject location claims inferred from the feed's language",source)
        document=(__import__("pathlib").Path(__file__).resolve().parents[1]/
                  "EDITORIAL_PROMISE.md").read_text(encoding="utf-8")
        self.assertIn("世界の広さを、実話で感じる",document)
        self.assertIn("視界に別の場所をそっと増やす",document)
        self.assertIn("国全体の特徴として語らない",document)

    def test_editorial_voice_respects_exhausted_readers(self):
        mission=editorial.EDITORIAL_MISSION
        craft=editorial.WRITING_CRAFT
        self.assertIn("quiet place",mission)
        self.assertIn("reader owes us no smile",mission)
        self.assertIn("Do not diagnose the reader",mission)
        self.assertIn("never a compulsory lesson",craft)
        self.assertIn("a joke can stand without any advice",craft)
        self.assertIn("Never write moral lessons",craft)
        source=(__import__("pathlib").Path(__file__).resolve().parents[1]/
                "auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn('Reject if the writing shames a person',source)
        self.assertIn('気が向かなければ笑わなくてもよい',source)
        charter=(__import__("pathlib").Path(__file__).resolve().parents[1]/
                 "EDITORIAL_PROMISE.md").read_text(encoding="utf-8")
        self.assertIn("読者に何も求めない",charter)
        self.assertIn("読者の心を測らない",charter)

    def test_editorial_mission_requires_real_failure_and_reframing(self):
        mission=editorial.EDITORIAL_MISSION
        self.assertIn("real, consequential failures",mission)
        self.assertIn("warm, witty AI quip",mission)
        self.assertIn("humane aftertaste is optional",mission)
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
    def test_valueless_class_attribute_does_not_crash_article_parser(self):
        html = '<article class><p>' + 'Verified article sentence. ' * 40 + '</p></article>'
        body=editorial.extracted_article_text(html)
        self.assertIn('Verified article sentence.',body)

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

    def test_quota_http_error_fails_fast_without_leaking_credentials(self):
        from urllib.error import HTTPError
        from io import BytesIO
        error=HTTPError("https://example.test",429,"quota",{},BytesIO(
            b'{"error":{"status":"RESOURCE_EXHAUSTED","message":"secret key EXAMPLE_SECRET"}}'))
        with patch.object(editorial,"KEY","test-secret"), \
             patch.object(editorial,"available_models",return_value=["models/gemini-2.5-flash"]), \
             patch.object(editorial,"urlopen",side_effect=error) as request, \
             patch("builtins.print") as prints:
            with self.assertRaisesRegex(RuntimeError,"HTTP 429 RESOURCE_EXHAUSTED"):
                editorial.ai("return JSON")
            self.assertEqual(request.call_count,1)
            self.assertNotIn("test-secret",str(prints.call_args_list))
            self.assertNotIn("EXAMPLE_SECRET",str(prints.call_args_list))

    def test_http_404_tries_other_version(self):
        import io
        from urllib.error import HTTPError
        def response(req,timeout=None):
            if "/v1beta/" in req.full_url:
                raise HTTPError(req.full_url,404,"missing",{},io.BytesIO(
                    b'{"error":{"status":"NOT_FOUND"}}'))
            return io.BytesIO(b'{"candidates":[{"content":{"parts":[{"text":"{\\\"ok\\\":true}"}]}}]}')
        with patch.object(editorial,"KEY","test-secret"), \
             patch.object(editorial,"available_models",return_value=["models/gemini-2.5-flash"]), \
             patch.object(editorial,"urlopen",side_effect=response) as requests:
            self.assertEqual(editorial.ai("return JSON"),{"ok":True})
            self.assertEqual(requests.call_count,2)

    def test_model_fallback_prefers_current_flash_models_before_legacy(self):
        import io
        import json
        names=["gemini-2.5-flash-lite","gemini-3.5-flash-lite","gemini-3.8-flash",
               "gemini-3.6-flash","gemini-3.5-flash","gemini-3.7-flash"]
        payload={"models":[{"name":"models/"+name,"supportedGenerationMethods":["generateContent"]}
                          for name in names]}
        class FakeResponse:
            def __enter__(self):return io.BytesIO(json.dumps(payload).encode())
            def __exit__(self,*args):return False
        with patch.object(editorial,"urlopen",return_value=FakeResponse()), \
             patch.object(editorial,"MODEL","gemini-3.5-flash-lite"):
            selected=editorial.available_models()
        self.assertEqual(selected[0],"models/gemini-3.5-flash-lite")
        self.assertIn("models/gemini-3.8-flash",selected)
        self.assertIn("models/gemini-3.7-flash",selected)
        self.assertNotIn("models/gemini-2.5-flash-lite",selected)

    def test_503_provider_overload_uses_bounded_backoff(self):
        import io
        from urllib.error import HTTPError
        def provider(req,timeout=None):
            if provider.count<2:
                provider.count+=1
                raise HTTPError(req.full_url,503,"unavailable",{},
                                io.BytesIO(b'{"error":{"status":"UNAVAILABLE"}}'))
            return io.BytesIO(b'{"candidates":[{"content":{"parts":[{"text":"{\\\"ok\\\":true}"}]}}]}')
        provider.count=0
        with patch.object(editorial,"KEY","test-key"), \
             patch.object(editorial,"available_models",return_value=["models/gemini-3.5-flash-lite"]), \
             patch.object(editorial,"urlopen",side_effect=provider) as mocked, \
             patch.object(editorial.time,"sleep") as pause:
            self.assertEqual(editorial.ai("Return valid JSON"),{"ok":True})
            self.assertEqual(mocked.call_count,3)
            self.assertEqual([c.args[0] for c in pause.call_args_list],[2,6])

    def test_live_editorial_workflows_are_not_triggered_by_code_push(self):
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        preview=(root/".github/workflows/ai-editorial-preview.yml").read_text(encoding="utf-8")
        monthly=(root/".github/workflows/monthly-editorial.yml").read_text(encoding="utf-8")
        nightly=(root/".github/workflows/publish-nightly.yml").read_text(encoding="utf-8")
        for name,text in (("preview",preview),("monthly",monthly)):
            with self.subTest(workflow=name):
                self.assertNotIn("\n  push:\n",text)
                self.assertIn("workflow_dispatch:",text)
                self.assertIn("schedule:",text)
        self.assertIn("workflow_run:",nightly)
        self.assertIn("github.event.workflow_run.event != 'push'",nightly)
        self.assertIn("- 'data/approved/*.json'",nightly)
        self.assertNotIn("- 'auto_editorial.py'",nightly)
        self.assertNotIn("- 'tests/**'",nightly)

    def test_quota_circuit_prevents_repeat_api_requests(self):
        from urllib.error import HTTPError
        from io import BytesIO
        def quota(*args,**kwargs):
            raise HTTPError("https://example.test",429,"quota",{},
                            BytesIO(b'{"error":{"status":"RESOURCE_EXHAUSTED"}}'))
        with patch.object(editorial,"KEY","test-key"), \
             patch.object(editorial,"RUN_DEADLINE",None), \
             patch.object(editorial,"AI_QUOTA_BLOCKED",False), \
             patch.object(editorial,"available_models",return_value=["models/gemini-3.5-flash-lite"]), \
             patch.object(editorial,"urlopen",side_effect=quota) as api:
            with self.assertRaisesRegex(RuntimeError,"HTTP 429"):editorial.ai("first")
            self.assertTrue(editorial.AI_QUOTA_BLOCKED)
            with self.assertRaisesRegex(RuntimeError,"circuit open"):editorial.ai("second")
            self.assertEqual(api.call_count,1)

    def test_editorial_deadline_stops_api_before_call(self):
        with patch.object(editorial,"KEY","test-key"), \
             patch.object(editorial,"AI_QUOTA_BLOCKED",False), \
             patch.object(editorial,"RUN_DEADLINE",editorial.time.monotonic()-1), \
             patch.object(editorial,"available_models") as model:
            with self.assertRaisesRegex(RuntimeError,"time budget exhausted"):
                editorial.ai("Return JSON")
            model.assert_not_called()

    def test_editorial_drafting_keeps_time_for_fact_checking(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn("editorial_seconds_remaining()<150",source)
        self.assertIn("editorial_seconds_remaining()<45",source)
        self.assertIn('group_reasons.get(g["groupId"])=="same_incident_supported"',source)
        self.assertIn("if len(draft)>=6:",source)

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

    def test_four_or_more_verified_candidates_result_in_three_selected_stories(self):
        import auto_editorial
        from collections import Counter
        pool=[
            {'id':'Japan','country':'日本','category':'work'},
            {'id':'Korea','country':'韓国','category':'person'},
            {'id':'Brazil','country':'ブラジル','category':'company'},
            {'id':'France','country':'フランス','category':'sports'},
        ]
        # Four articles may be vetted; selection must reduce to three.
        selected=auto_editorial.select_diverse_verified_stories(pool,Counter(),Counter())
        self.assertEqual(len(selected),3)
        self.assertTrue(all(story in pool for story in selected))
        self.assertEqual(len({story['id'] for story in selected}),3)
        # Publishing a short edition must remain possible: neither one nor
        # two should be discarded merely because the target is three.
        for count in (1,2):
            self.assertEqual(len(auto_editorial.select_diverse_verified_stories(
                pool[:count],Counter(),Counter())),count)

    def test_new_editorial_caps_three_and_legacy_publisher_supports_five(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        editorial = (root / "auto_editorial.py").read_text(encoding="utf-8")
        publisher = (root / "publish_approved.py").read_text(encoding="utf-8")
        self.assertIn("min(3,len(pool))", editorial)
        self.assertIn("1 <= len(stories) <= 5", publisher)
        self.assertIn("if not selected:", editorial)

    def test_single_original_report_can_pass_independent_ai_review(self):
        from pathlib import Path
        pipeline=(Path(__file__).resolve().parents[1] / "auto_editorial.py").read_text(encoding="utf-8")
        # One real publisher's article is acceptable, but still must be
        # fetched, source-grounded and independently audited by the AI.
        self.assertIn("groups.extend([[item] for item in source_leads",pipeline)
        self.assertIn("not (1<=len(urls)<=3)",pipeline)
        self.assertIn("if len(evidence)<1",pipeline)
        self.assertIn("originalReportingVerified",pipeline)
        self.assertIn('validate_approved(payload,day)',pipeline)
        self.assertIn('if not valid_recent_reported(story["reported"],now):',pipeline)

    def test_same_day_reporting_with_timezone_buffer(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now=datetime(2026,11,15,21,0,tzinfo=ZoneInfo("Asia/Tokyo"))
        self.assertTrue(editorial.valid_recent_reported("2026-11-15",now))
        self.assertTrue(editorial.valid_recent_reported("2026-11-14",now))
        self.assertFalse(editorial.valid_recent_reported("2026-11-13",now))
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
