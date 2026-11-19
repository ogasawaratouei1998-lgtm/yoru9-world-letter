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

    def test_196_reporting_locations_have_unique_names_aliases_and_map_points(self):
        from country_codes import catalog, country_code, country_codes, country_region
        import re
        rows=catalog()
        self.assertEqual(len(rows),196)
        self.assertEqual(len({row["code"] for row in rows}),196)
        self.assertEqual({row["region"] for row in rows},
                         {"アフリカ","アジア","ヨーロッパ","北アメリカ","南アメリカ","オセアニア"})
        all_aliases={}
        for item in rows:
            self.assertRegex(item["code"],r"^[A-Z]{2}$")
            self.assertTrue(item["name"])
            self.assertTrue(-180<=item["lon"]<=180)
            self.assertTrue(-90<=item["lat"]<=90)
            for label in [item["code"],item["name"],*item["aliases"]]:
                normalized=label.casefold().strip()
                self.assertEqual(all_aliases.get(normalized,item["code"]),
                                 item["code"],(label,item["code"]))
                all_aliases[normalized]=item["code"]
                self.assertEqual(country_code(label),item["code"])
        for name,code in (("パレスチナ","PS"),("台湾","TW"),
                          ("バチカン市国","VA"),("ミクロネシア連邦","FM"),
                          ("コンゴ民主共和国","CD"),("コソボ",None)):
            self.assertEqual(country_code(name),code)
        self.assertEqual(country_codes("イギリス・アメリカ"),["GB","US"])
        self.assertEqual(country_codes("アンティグア・バーブーダ"),["AG"])
        self.assertEqual(country_codes("未確認"),[])
        self.assertIsNone(country_region("発行元が不明"))

    def test_all_time_country_selection_prefers_uncovered_not_repeated(self):
        from collections import Counter
        pool=[{"id":key,"country":key,"category":"work","title":"A workplace mix-up"}
              for key in ("US","FR","TW","JP")]
        chosen=editorial.select_diverse_verified_stories(
            pool,Counter(),Counter(),Counter(),
            Counter({"US":50,"FR":12,"JP":3}))
        self.assertIn("TW",{item["country"] for item in chosen})
        self.assertEqual(len(chosen),4)

    def test_older_cross_border_editions_contribute_two_real_locations(self):
        from datetime import date
        from pathlib import Path
        import tempfile,os,json
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/"data"/"archive"
            archive.mkdir(parents=True)
            for filename,status,name in [
                ("2026-11-11","published","イギリス・アメリカ"),
                ("2026-11-12","draft","台湾"),
                ("2026-11-13","published","未確認"),
                ("2026-11-14","published","アンティグア・バーブーダ")
            ]:
                (archive/(filename+".json")).write_text(json.dumps({
                    "editionDate":filename,"status":status,
                    "stories":[{"country":name,"category":"person"}]
                },ensure_ascii=False),encoding="utf-8")
            old=os.getcwd()
            try:
                os.chdir(tmp)
                all_time=editorial.lifetime_country_counts(date(2026,11,18))
                recent,categories=editorial.recent_diversity_counts(date(2026,11,18))
            finally:
                os.chdir(old)
            self.assertEqual(dict(all_time),{"GB":1,"US":1,"AG":1})
            self.assertEqual(dict(recent),{"GB":1,"US":1,"AG":1})
            self.assertEqual(categories["person"],3)

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
        self.assertEqual(len(chosen),5)
        self.assertEqual(len({country_region(s["country"]) for s in chosen}),5)
        self.assertEqual(len({s["category"] for s in chosen}),4)

    def test_verified_selection_prioritizes_underrepresented_countries_in_tie(self):
        from collections import Counter
        pool=[{"id":v,"country":v,"category":"work"} for v in ("US","CA","MX","FR","JP","BR")]
        chosen=editorial.select_diverse_verified_stories(
            pool,Counter({"US":18,"CA":1,"MX":2,"FR":1}),Counter())
        self.assertEqual({s["country"] for s in chosen},{"CA","MX","FR","JP","BR"})

    def test_final_selection_prioritizes_neglected_categories_not_corporate_volume(self):
        from collections import Counter
        pool=[
            {"id":"co1","country":"US","category":"company","title":"Company sign error"},
            {"id":"co2","country":"FR","category":"company","title":"Company mural error"},
            {"id":"co3","country":"DE","category":"company","title":"Company typo error"},
            {"id":"sp","country":"BR","category":"sports","title":"Referee makes a mistake"},
            {"id":"pe","country":"JP","category":"person","title":"Tourist mistaken identity"},
            {"id":"wo","country":"GB","category":"work","title":"Chef wrong order"},
            {"id":"pe2","country":"IT","category":"person","title":"Funny personal decision"},
            {"id":"sp2","country":"CA","category":"sports","title":"Sports surprise"},
        ]
        chosen=editorial.select_diverse_verified_stories(
            pool,Counter(),Counter({"company":16,"work":2,"person":0,"sports":1}))
        self.assertLessEqual(sum(s["category"]=="company" for s in chosen),1)
        self.assertEqual(len(chosen),5)
        self.assertTrue({"work","person","sports"}.issubset({s["category"] for s in chosen}))

    def test_published_topic_rotation_avoids_repeating_same_gag(self):
        from collections import Counter
        pool=[
            {"id":"sign","country":"JP","category":"person","title":"道路の看板に誤字"},
            {"id":"order","country":"JP","category":"person","title":"注文が別の人へ"},
            {"id":"work","country":"GB","category":"work","title":"店員が勘違い"},
            {"id":"sports","country":"BR","category":"sports","title":"審判の珍事"},
            {"id":"other","country":"US","category":"work","title":"仕事の珍事"},
            {"id":"bonus","country":"FR","category":"person","title":"家族の勘違い"},
        ]
        chosen=editorial.select_diverse_verified_stories(
            pool,Counter(),Counter(),Counter({"signs":12,"orders":0}))
        self.assertIn("order",{s["id"] for s in chosen})
        self.assertNotIn("sign",{s["id"] for s in chosen})
        self.assertEqual(editorial.surprise_topic(pool[0]),"signs")
        self.assertEqual(editorial.surprise_topic(pool[1]),"orders")

    def test_discovery_slots_spread_our_four_desks(self):
        dominant=[
            [{"title":"Company accidentally prints wrong name",
              "url":f"https://company{i}.example/story"}] for i in range(30)]
        others=[
            [{"title":"Tourist accidentally boards wrong train",
              "url":"https://person.example/story"}],
            [{"title":"Waiter accidentally brings wrong order",
              "url":"https://work.example/story"}],
            [{"title":"Referee mistakenly selects wrong player",
              "url":"https://sports.example/story"}],
        ]
        proposed=editorial.prioritize_comic_groups(dominant+others,limit=12)
        desks={editorial.discovery_desk(group[0]) for group in proposed}
        self.assertEqual(desks,{"person","work","sports","company"})
        self.assertLessEqual(len(proposed),12)

    def test_local_language_headlines_are_not_discarded_as_generic(self):
        headlines={
            "it":"Comune pubblica un cartello con errore di stampa",
            "fr":"Le restaurant commande par erreur 500 pizzas",
            "pt":"Prefeitura admite engano em entrega",
            "id":"Petugas salah mengirim pesanan ke kota lain",
            "vi":"Nhân viên nhầm địa chỉ giao hàng",
            "pl":"Urzędnik przyznaje pomyłkę w zamówieniu",
            "tr":"Yetkili yanlış sipariş verdi",
            "ar":"خطأ في الطلب يربك الموظف",
            "ko":"직원이 실수로 잘못 배달했다",
        }
        for language,title in headlines.items():
            with self.subTest(language=language):
                rank=editorial.incident_priority({
                    "title":title,"url":"https://local.example/story"
                })[0]
                self.assertEqual(rank,0,title)
        self.assertGreater(editorial.incident_priority({
            "title":"New market quarterly update",
            "url":"https://local.example/boring"
        })[0],0)

    def test_global_editorial_shortlist_preserves_all_six_publisher_regions(self):
        from country_codes import country_region
        # Ninety US original articles might rank ahead of the local ones by
        # discovery order, although each regional source reports a human error.
        dominant=[[{"title":"Company accidentally publishes wrong name",
                    "url":f"https://us{i}.example/story",
                    "sourcecountry":"US"}] for i in range(90)]
        markets=("NG","BR","IN","FJ","FR","US")
        local=[[{"title":f"Worker sends wrong delivery {code}",
                 "url":f"https://{code.lower()}.example/story",
                 "sourcecountry":code}] for code in markets]
        selected=editorial.prioritize_comic_groups(dominant+local,limit=24)
        regions={country_region(x.get("sourcecountry"))
                 for group in selected for x in group}
        self.assertEqual(len(selected),24)
        self.assertEqual(len(regions),6)
        self.assertTrue(all(editorial.incident_priority(g[0])[0]==0
                            for g in selected))
        # Publisher markets are discovery metadata, not events' countries.
        self.assertFalse(any("country" in x for g in selected for x in g))

    def test_single_original_reports_are_filtered_after_not_before_geographic_review(self):
        import inspect
        code=inspect.getsource(editorial.main)
        self.assertIn("groups.extend([[item] for item in unpaired])",code)
        self.assertIn("groups=prioritize_comic_groups(groups,limit=36)",code)
        self.assertIn("'sourcecountry':lead.get('sourcecountry','')",code)
        self.assertIn("trusted_original_domain(urls[0])",code)
        self.assertIn("independent_editorial_quality_passed(audit)",code)

    def test_funnel_audit_logs_counts_only_and_never_mistakes_media_market_for_event(self):
        import json, tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"funnel.json"
            saved=editorial.save_editorial_funnel("shortlist",{
                "collected":750,"fresh":600,"planned_fetches":240,
                "fetchable_original_bodies":130,
                "candidate_review_groups":36,"first_ai_batch_groups":24,
                "publisher_regions_shortlist":{"アフリカ":6,"アジア":9},
                "rejection_reasons":{"missing_original":7},
                "articleUrl":"https://private.example/story",
                "articleBody":"Never expose this news body",
                "unverifiedEventCountry":"Fiji",
            },path=target)
            self.assertEqual(saved["collected"],750)
            self.assertEqual(saved["publisher_regions_shortlist"]["アフリカ"],6)
            self.assertNotIn("articleUrl",saved)
            self.assertNotIn("articleBody",saved)
            self.assertNotIn("unverifiedEventCountry",saved)
            self.assertNotIn("private.example",target.read_text())
            self.assertIn("not incident locations",saved["meaning"])
            with self.assertRaises(ValueError):
                editorial.save_editorial_funnel("published",{},path=target)
        import inspect
        code=inspect.getsource(editorial.main)
        for stage in ("fresh_filter","fetch_plan","body_fetch",
                      "shortlist","draft","audit","selected"):
            self.assertIn("checkpoint(\""+stage+"\"",code)

    def test_concise_human_reversal_need_not_be_verbose(self):
        draft={"expectedPlan":"注文を届ける","observedOutcome":"隣の家へ配達"}
        self.assertIsNone(editorial.editorial_fit_rejection(draft))
        self.assertEqual(editorial.editorial_fit_rejection(
            {**draft,"expectedPlan":""}),"missing_source_grounded_plan_or_outcome")

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

    def test_incident_retrieval_prefers_human_errors_over_animals(self):
        from auto_editorial import incident_priority
        human={"title":"店員が注文の数を間違えた","url":"https://publisher.example/human"}
        deer={"title":"珍しいユニコーンのようなシカが出現","url":"https://publisher.example/animal"}
        self.assertLess(incident_priority(human),incident_priority(deer))
        self.assertIn("animal_novelty_headline(title)",__import__("inspect").getsource(incident_priority))

    def test_editorial_mission_requires_real_failure_and_reframing(self):
        mission=editorial.EDITORIAL_MISSION
        self.assertIn("source-supported extraordinary human actions",mission)
        self.assertIn("warm, witty AI quip",mission)
        self.assertIn("humane aftertaste is optional",mission)
        self.assertIn("Never replace a genuine hard-to-believe sourced human episode",mission)
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

    def test_independent_japanese_headline_and_humor_review_is_required(self):
        from pathlib import Path
        code=(Path(__file__).resolve().parents[1]/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn("headline_fidelity_risk(story,evidence)",code)
        self.assertIn("independent_editorial_quality_passed(audit)",code)
        self.assertIn('story["editorQualityVerified"]=True',code)
        self.assertIn("legalStatusAccurate",code)
        self.assertIn("translationAccurate",code)

    def test_semantic_matching_is_optional_to_preserve_fact_review_quota(self):
        from auto_editorial import semantic_matching_needed
        self.assertTrue(semantic_matching_needed(0))
        self.assertTrue(semantic_matching_needed(1))
        self.assertFalse(semantic_matching_needed(2))
        self.assertFalse(semantic_matching_needed(3))

    def test_human_failure_must_be_central_not_animal_novelty(self):
        from editorial_identity import human_failure_rejection, comic_line_rejection
        base={"humanActor":"道路工事の作業員",
              "humanMistake":"道路に書く指示のつづりを間違えてしまった",
              "title":"道路標示を誤記し市が看板を直した"}
        self.assertIsNone(human_failure_rejection(base))
        for title in ("森に珍しいユニコーンのような鹿が出現",
                      "クモザルが逃げて警察に保護された",
                      "アシカが植物の育苗施設に入り込んだ",
                      "クリスマス島でカニ専用の橋が活躍"):
            with self.subTest(title=title):
                self.assertEqual(human_failure_rejection({**base,"title":title}),
                                 "animal_novelty_not_human_failure")
        self.assertEqual(human_failure_rejection({**base,"humanActor":"サル"}),
                         "missing_human_mistake_actor")
        self.assertEqual(human_failure_rejection({**base,"humanMistake":"ただ見かけた"}),
                         "missing_concrete_human_error")
        self.assertIsNone(human_failure_rejection({
            **base,"humanActor":"動物管理局の担当者",
            "humanMistake":"ワニだと見間違えて救助に出動した",
            "title":"担当者がワニと勘違いして出動、実は浮き輪"}))
        # Do not reject source-grounded human errors on their wording alone.
        self.assertIsNone(human_failure_rejection({
            **base, "humanMistake":"宛名と異なる住所へ商品を配送してしまった"}))
        self.assertEqual(human_failure_rejection({
            **base, "humanMistake":"珍しい生物を見つけた"}),
            "animal_sighting_is_not_a_human_error")
        self.assertIsNone(comic_line_rejection(
            "配達員、コーヒーの注文を受けたら救助まで兼任することに。"))
        self.assertEqual(comic_line_rejection("世界は予想外です。"),
                         "no_usable_first_punchline")

    def test_deliberate_university_disciplinary_dispute_is_not_a_funny_mistake(self):
        from editorial_identity import human_failure_rejection
        row={
            "humanActor":"学生たち",
            "humanMistake":"大学の学位授与式で大臣が退席する事態を招いた",
            "title":"学位授与式を乱して学生らが停学処分に",
            "summary":"式典の妨害をめぐって大学評議会と学生が対立した"}
        self.assertEqual(human_failure_rejection(row),
                         "institutional_confrontation_not_comic_miscalculation")
        # Mere graduation/ceremony context must not ban a harmless human error.
        harmless={
            "humanActor":"式典の司会者",
            "humanMistake":"卒業式の祝辞で別の式典の原稿を読んでしまった",
            "title":"卒業式で別の日の原稿を読んだ司会者"}
        self.assertIsNone(human_failure_rejection(harmless))

    def test_emergency_responder_harassment_is_not_a_comedy_story(self):
        from editorial_identity import human_failure_rejection
        emergency={"humanActor":"地元の住民たち",
                   "humanMistake":"消防団への嫌がらせを続けて緊急対応を妨害した",
                   "title":"救急出動中の消防士へ嫌がらせが続いた",
                   "summary":"サイレンを鳴らした消防団員が住民から暴言を受けた"}
        self.assertEqual(human_failure_rejection(emergency),
                         "emergency_responder_harassment_not_comic_blunder")
        harmless={"humanActor":"動物管理担当の職員",
                  "humanMistake":"ワニの浮き輪を本物だと勘違いして出動した",
                  "title":"ワニを本物と見間違えて出動、正体は浮き輪"}
        self.assertIsNone(human_failure_rejection(harmless))
        # An ordinary workplace blunder stays eligible.
        self.assertIsNone(human_failure_rejection({
            "humanActor":"配送担当者",
            "humanMistake":"宛名と異なる住所へ商品を配送してしまった",
            "title":"配送担当が荷物の宛先を取り違えた"}))

    def test_editorial_requires_human_error_and_earned_comic_punch(self):
        from pathlib import Path
        code=(Path(__file__).resolve().parents[1]/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn("human_failure_rejection(story)",code)
        self.assertIn("comic_line_rejection(story",code)
        self.assertIn('story["humanFailureVerified"]=True',code)
        self.assertIn("humanFailureConfirmed:boolean",code)
        self.assertIn("comicPunchlineWorks:boolean",code)
        self.assertIn("quipSecond (OPTIONAL",code)
        self.assertIn("HUMAN_FAILURE_MISSION",code)

    def test_serious_incident_veto_checks_original_source_before_comedy(self):
        from pathlib import Path
        code=(Path(__file__).resolve().parents[1]/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn("noncomic_incident_rejection(story,evidence)",code)
        self.assertIn("harassment of firefighters or emergency responders",code)

    def test_small_batch_provenance_rejects_cross_story_and_invented_urls(self):
        groups=[
            {"groupId":1,"articles":[
                {"url":"https://original-a.example/story"},
                {"url":"https://original-b.example/story"}]},
            {"groupId":2,"articles":[
                {"url":"https://local-c.example/story"}]},
        ]
        a={"sourceUrl":"https://original-a.example/story",
           "verificationUrls":["https://original-a.example/story"]}
        b={"sourceUrl":"https://local-c.example/story",
           "verificationUrls":["https://local-c.example/story"]}
        wrong_cross={"sourceUrl":"https://original-a.example/story",
                     "verificationUrls":[
                         "https://original-a.example/story",
                         "https://local-c.example/story"]}
        invented={"sourceUrl":"https://invented.example/story",
                  "verificationUrls":["https://invented.example/story"]}
        duplicate={**a,"quip":"Another joke for same incident"}
        self.assertEqual(editorial.source_bound_batch_drafts(
            {"stories":[wrong_cross,invented,a,duplicate,b]},groups),[a,b])
        self.assertEqual(editorial.source_bound_batch_drafts(
            {"stories":[wrong_cross,invented]},groups),[])
        self.assertEqual(editorial.source_bound_batch_drafts(
            {"stories":"invalid"},groups),[])
        self.assertEqual(editorial.source_bound_batch_drafts({},groups),[])

    def test_provenance_prefilter_does_not_approve_articles_by_itself(self):
        from pathlib import Path
        import inspect
        source=inspect.getsource(editorial.source_bound_batch_drafts)
        self.assertNotIn('editorVerified',source)
        self.assertNotIn('originalReportingVerified',source)
        code=inspect.getsource(editorial.main)
        self.assertIn('source_bound_batch_drafts(retry_result,batch)',code)
        self.assertIn('independent_editorial_quality_passed(audit)',code)
        self.assertIn('noncomic_incident_rejection(story,evidence)',code)
        self.assertIn('trusted_original_domain(urls[0])',code)
        self.assertIn('if AI_QUOTA_BLOCKED:',code)

    def test_editorial_drafting_keeps_time_for_fact_checking(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn("editorial_seconds_remaining()<150",source)
        self.assertIn("editorial_seconds_remaining()<45",source)
        self.assertIn('group_reasons.get(g["groupId"])=="same_incident_supported"',source)
        self.assertIn("draft_preflight_viable(item,now) for item in draft",source)
        self.assertIn("for start in range(0,min(len(retry_candidates),20),2):",source)
        self.assertIn("Five eligible comedy drafts reserved: moving to independent fact review.",source)

    def test_draft_recovery_targets_three_before_fact_review_and_respects_quota(self):
        import inspect
        code=inspect.getsource(editorial.main)
        self.assertIn('draft_preflight_viable(item,now) for item in draft)<5',code)
        self.assertIn('for start in range(0,min(len(retry_candidates),20),2):',code)
        self.assertIn('editorial_seconds_remaining()<150',code)
        self.assertIn('if AI_QUOTA_BLOCKED:',code)
        self.assertIn('supplemental_attempts+=1',code)
        self.assertIn('supplemental_generated+=len(retry_stories)',code)
        self.assertIn('retry_stories=source_bound_batch_drafts(retry_result,batch)',code)
        self.assertIn('independent_editorial_quality_passed(audit)',code)
        self.assertIn('if len(selected)>=9:break',code)
        self.assertIn('select_diverse_verified_stories(selected,',code)

    def test_comedy_draft_pairing_preserves_individual_evidence_and_review_budget(self):
        import inspect
        code=inspect.getsource(editorial.main)
        self.assertIn('for start in range(0,min(len(retry_candidates),20),2):',code)
        self.assertIn('batch=retry_candidates[start:min(start+2,20,len(retry_candidates))]',code)
        self.assertIn('supplemental_groups_examined+=len(batch)',code)
        self.assertIn('draft.extend(retry_stories)',code)
        self.assertIn('NEVER merge facts, people, locations, or sources from different groups',code)
        self.assertIn('editorial_seconds_remaining()<150',code)
        self.assertIn('independent_editorial_quality_passed(audit)',code)
        self.assertIn('if AI_QUOTA_BLOCKED:',code)

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

    def test_four_or_more_verified_candidates_are_not_discarded_until_five(self):
        import auto_editorial
        from collections import Counter
        pool=[
            {'id':'Japan','country':'日本','category':'work'},
            {'id':'Korea','country':'韓国','category':'person'},
            {'id':'Brazil','country':'ブラジル','category':'company'},
            {'id':'France','country':'フランス','category':'sports'},
        ]
        # Four independently verified articles are all eligible; five is the cap.
        selected=auto_editorial.select_diverse_verified_stories(pool,Counter(),Counter())
        self.assertEqual(len(selected),4)
        self.assertTrue(all(story in pool for story in selected))
        self.assertEqual(len({story['id'] for story in selected}),4)
        expanded=pool+[
            {"id":"India","country":"インド","category":"person"},
            {"id":"UK","country":"イギリス","category":"work"},
        ]
        self.assertEqual(len(auto_editorial.select_diverse_verified_stories(expanded,Counter(),Counter())),5)
        # Publishing a short edition must remain possible: neither one nor
        # two should be discarded merely because the target is three.
        for count in (1,2):
            self.assertEqual(len(auto_editorial.select_diverse_verified_stories(
                pool[:count],Counter(),Counter())),count)

    def test_new_editorial_caps_five_and_publisher_supports_five(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        editorial = (root / "auto_editorial.py").read_text(encoding="utf-8")
        publisher = (root / "publish_approved.py").read_text(encoding="utf-8")
        self.assertIn("min(5,len(pool))", editorial)
        self.assertIn("1 <= len(stories) <= 5", publisher)
        self.assertIn("if not selected:", editorial)

    def test_single_original_report_can_pass_independent_ai_review(self):
        from pathlib import Path
        pipeline=(Path(__file__).resolve().parents[1] / "auto_editorial.py").read_text(encoding="utf-8")
        # One real publisher's article is acceptable, but still must be
        # fetched, source-grounded and independently audited by the AI.
        self.assertIn("groups.extend([[item] for item in unpaired",pipeline)
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
        self.assertTrue(editorial.valid_recent_reported("2026-11-13",now))
        self.assertTrue(editorial.valid_recent_reported("2026-11-08",now))
        self.assertFalse(editorial.valid_recent_reported("2026-11-07",now))
        self.assertFalse(editorial.valid_recent_reported("2026-11-16",now))
        self.assertFalse(editorial.valid_recent_reported("unverified",now))

    def test_bad_drafts_do_not_stop_search_for_funny_human_blunders(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now=datetime(2026,11,18,9,0,tzinfo=ZoneInfo("Asia/Tokyo"))
        acceptable={"id":"delivery-mixup-2026","country":"日本",
            "category":"work","categoryLabel":"仕事","label":"世界のまさか",
            "title":"誤配送で注文品が別の家に届いた",
            "summary":"従業員が送り先を取り違えました。",
            "detail":"配達先の番地を見間違えたため違う家に届きました。",
            "quip":"送り先を間違えたのに、到着通知だけは正確だった。",
            "sourceName":"BBC","sourceUrl":"https://www.bbc.com/news/example",
            "reported":"2026-11-17","humanActor":"店員",
            "humanMistake":"住所を見間違えて別の家へ配送した",
            "expectedPlan":"注文主の正しい住所へ品物を届ける予定だった。",
            "observedOutcome":"実際には別の住所へ誤って配達してしまった。"}
        self.assertTrue(editorial.draft_preflight_viable(acceptable,now))
        serious={**acceptable,
            "title":"消防団員にサイレンの苦情と嫌がらせ",
            "humanActor":"住民","humanMistake":"消防団員に暴言を浴びせた"}
        self.assertFalse(editorial.draft_preflight_viable(serious,now))
        self.assertFalse(editorial.draft_preflight_viable({
            **acceptable,"quip":"まさかの展開でした。"},now))
        self.assertFalse(editorial.draft_preflight_viable({
            **acceptable,"reported":"2026-11-09"},now))

    def test_primary_editor_prompt_prefers_small_sourced_blunders(self):
        from pathlib import Path
        code=(Path(__file__).resolve().parents[1]/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn("Small and harmless mistakes are ideal",code)
        self.assertNotIn("Do not prioritize trivial typos",code)
        self.assertIn("already_drafted_urls",code)
        self.assertIn("min(incident_priority(article)",code)

    def test_light_human_blunders_get_retrieval_priority_over_disputes(self):
        ordinary={"title":"Company accidentally sent the wrong order to customers",
                  "url":"https://news.example.org/work"}
        generic={"title":"Company announces new quarter",
                 "url":"https://news.example.org/company"}
        serious={"title":"Minister faces protest after student suspensions",
                 "url":"https://news.example.org/dispute"}
        animal={"title":"Rare deer appears at island nursery",
                "url":"https://news.example.org/wildlife"}
        ranked=sorted([serious,animal,generic,ordinary],key=editorial.incident_priority)
        self.assertEqual([x["url"] for x in ranked],
                         [ordinary["url"],generic["url"],serious["url"],animal["url"]])

    def test_wrong_ai_landmark_is_prioritized_as_comic_blunder(self):
        mural={'title':"McDonald's AI-generated mural riddled with errors",
               'url':'https://www.bbc.com/news/a'}
        generic={'title':'Local economic forecasts updated',
                 'url':'https://www.bbc.com/news/b'}
        conflict={'title':'Minister faces protests after suspensions',
                  'url':'https://www.bbc.com/news/c'}
        self.assertLess(editorial.incident_priority(mural),editorial.incident_priority(generic))
        self.assertLess(editorial.incident_priority(mural),editorial.incident_priority(conflict))

    def test_incident_relevance_ranking_is_not_fact_approval(self):
        leads=[{"title":"World leaders meet at summit","url":"https://example.org/a"},
               {"title":"Company accidentally sends wrong invoices","url":"https://example.org/b"}]
        ranked=sorted(leads,key=editorial.incident_priority)
        self.assertEqual(ranked[0]["url"],"https://example.org/b")
        self.assertEqual(ranked[1]["url"],"https://example.org/a")

    def test_comic_original_outweighs_serious_two_source_dispute(self):
        comic={"title":"Cafe accidentally delivered wrong order",
               "url":"https://www.bbc.com/news/comic"}
        serious_a={"title":"Minister faces protest and student discipline",
                   "url":"https://www.bbc.com/news/serious"}
        serious_b={"title":"Suspended students in minister row",
                   "url":"https://www.theguardian.com/news/serious"}
        animal={"title":"Rare monkey appears at a station",
                "url":"https://www.bbc.com/news/animal"}
        groups=[[serious_a,serious_b],[animal],[comic]]
        ranked=editorial.prioritize_comic_groups(groups,limit=2)
        self.assertEqual(ranked[0],[comic])
        self.assertEqual(ranked[1],[serious_a,serious_b])
        self.assertEqual(len(groups),3)
        self.assertEqual(editorial.prioritize_comic_groups([],limit=24),[])

    def test_current_comedy_prompt_preserves_one_source_and_seven_days(self):
        from pathlib import Path
        code=(Path(__file__).resolve().parents[1]/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn("groups=prioritize_comic_groups(groups,limit=36)",code)
        self.assertIn("unpaired=sorted",code)
        self.assertIn("trusted_original_domain(item['url'])",code)
        self.assertIn("within the preceding seven days",code)
        self.assertIn("independent_editorial_quality_passed(audit)",code)
        self.assertIn("draft_preflight_viable(item,now)",code)

    def test_second_window_reviews_new_fetched_articles(self):
        from pathlib import Path
        code=(Path(__file__).resolve().parents[1]/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn("json.dumps(grouped_evidence[:24],ensure_ascii=False)",code)
        self.assertIn("enumerate(groups[:36])",code)
        self.assertIn('0 if g["groupId"]>24 else 1',code)
        self.assertIn("min(len(retry_candidates),20),2",code)
        self.assertIn('"fresh_backup_groups"',code)
        # No shortcut around original source, comedy, independent and publisher gates.
        self.assertIn("trusted_original_domain(urls[0])",code)
        self.assertIn("noncomic_incident_rejection(story,evidence)",code)
        self.assertIn("independent_editorial_quality_passed(audit)",code)
        self.assertIn("validate_approved(payload,day)",code)

    def test_explainer_only_reporting_is_not_a_comic_incident(self):
        title="What S'pore's proposed social media rules mean for young people"
        self.assertTrue(editorial.source_title_is_policy_explainer(title))
        bbc="McDonald's AI-generated mural riddled with errors"
        self.assertFalse(editorial.source_title_is_policy_explainer(bbc))
        self.assertLess(editorial.incident_priority({'title':bbc,'url':'https://bbc.com/a'}),
                        editorial.incident_priority({'title':title,'url':'https://straitstimes.com/b'}))
        source=__import__('inspect').getsource(editorial.main)
        self.assertIn('publisher_titles={',source)
        self.assertIn('source_title_is_policy_explainer(publisher_titles.get(u,""))',source)
        self.assertIn('policy_explainer_without_incident_reporting',source)
    def test_creative_scope_relaxed_but_source_and_safety_guards_retained(self):
        from pathlib import Path
        src=(Path(__file__).resolve().parents[1]/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn("no literal error is required",src)
        self.assertIn("trusted_original_domain(urls[0])",src)
        self.assertIn("noncomic_incident_rejection(story,evidence)",src)
        self.assertIn("independent_editorial_quality_passed(audit)",src)
        self.assertIn("validate_approved(payload,day)",src)

    def test_without_key_does_not_call_ai(self):
        with patch.object(editorial,"KEY",""):
            with patch.object(editorial,"ai") as mock_ai:
                self.assertEqual(editorial.main(),0)
                mock_ai.assert_not_called()

if __name__=="__main__":
    unittest.main()
