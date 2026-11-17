"""Safety and integration tests for the independent 30-day monthly editor."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import monthly_research as m

TODAY = datetime(2026, 11, 17, 13, 0, tzinfo=ZoneInfo("Asia/Tokyo")).date()
URLS = ["https://publisher-a.example/story", "https://publisher-b.example/report"]
ORIGINAL = "https://www.bbc.com/news/articles/original-workplace-report"


def sample_story():
    return {
        "id": "friendly-workplace-mixup-2026",
        "eventKey": "independent-workplace-mixup-2026",
        "country": "日本", "category": "work", "categoryLabel": "仕事",
        "label": "世界のまさか",
        "title": "注文の行き先を間違えたら、意外な展開が待っていた",
        "summary": "店員が注文の送り先を間違えたことに気づき、届け先に連絡しました。話し合いの結果、穏やかな形で対応することになりました。",
        "detail": "ある店で、スタッフが注文品の届け先を間違えてしまいました。"
                  "本来の注文者のもとに商品が届かず、スタッフは状況を確認しました。"
                  "相手方に事情を説明し、連絡の行き違いがあったことを認めました。"
                  "双方が話し合って対応を決め、問題の解決に向けて動きました。",
        "quip": "配達先より先に、予想外の結末へ到着しました。",
        "quipSecond": "この注文、行き先の確認がいちばんの難関でした。",
        "sourceName": "Publisher A",
        "sourceUrl": URLS[0],
        "verificationUrls": URLS[:],
        "sourceBasis": "independent-reports",
        "reported": TODAY.isoformat(),
        "expectedPlan": "注文品を正しい届け先へ配達する予定でした。",
        "observedOutcome": "届け先を取り違え、予定とは違う対応が必要になりました。",
        "humanActor": "店の担当スタッフ",
        "humanMistake": "注文した品の配達先を間違えて取り違えた",
    }


class MonthlyResearchTest(unittest.TestCase):
    def test_monthly_is_human_failure_not_animals_or_oddities(self):
        import editorial_identity as identity
        self.assertFalse(m.MISHAP.search("Rare unicorn deer caught on camera"))
        self.assertFalse(m.MISHAP.search("Sea lion visits nursery"))
        self.assertTrue(m.MISHAP.search("Worker accidentally emailed wrong customer"))
        story=sample_story()
        # Test the editorial criterion separately from network/DNS validity.
        with patch.object(m.editorial,"public_host",return_value=True):
            self.assertTrue(m.validate_story(story,URLS,TODAY))
            self.assertFalse(m.validate_story({**story,"title":"野生のサルが保護された"},URLS,TODAY))
            self.assertFalse(m.validate_story({**story,"humanActor":"サル"},URLS,TODAY))
            self.assertFalse(m.validate_story({**story,"humanMistake":"珍しい生物を見つけた"},URLS,TODAY))
            self.assertTrue(m.validate_story({
                **story, "humanMistake":"宛名と異なる住所へ商品を配送してしまった"},URLS,TODAY))
        self.assertIn("COMEDY COLUMN ABOUT HUMAN BLUNDERS",m.MONTHLY_BRIEF)
        self.assertTrue(identity.animal_novelty_headline("アシカが植物園に入った"))
        self.assertFalse(identity.animal_novelty_headline("ワニと見間違えて駆けつけた職員"))

    def test_monthly_editor_excludes_emergency_worker_harassment(self):
        story=sample_story()
        story["title"]="消防団員への暴言と嫌がらせ"
        story["summary"]="救急出動中の消防団員に、住民が暴言を浴びせた。"
        with patch.object(m.editorial,"public_host",return_value=True):
            self.assertFalse(m.validate_story(story,URLS,TODAY))
            self.assertTrue(m.validate_story(sample_story(),URLS,TODAY))

    def test_window_is_jst_thirty_calendar_dates(self):
        start, end = m.date_window(TODAY)
        self.assertEqual(start.isoformat(), "2026-10-19")
        self.assertEqual(end.isoformat(), "2026-11-17")
        self.assertEqual((end-start).days, 29)
        self.assertIsNone(m.safe_day("2026-11-31"))

    def test_bing_discovery_extracts_only_safe_original_publisher_urls(self):
        from urllib.parse import quote
        good="https://www.bing.com/news/apiclick.aspx?url="+quote(URLS[0],safe="")
        with patch.object(m.editorial,"public_host",return_value=True):
            self.assertEqual(m.bing_publisher_url(good),URLS[0])
            self.assertIsNone(m.bing_publisher_url("https://www.bing.com/news/search?q=x"))
            self.assertIsNone(m.bing_publisher_url(
                "https://evil.example/news/apiclick.aspx?url="+quote(URLS[0],safe="")))
            self.assertIsNone(m.bing_publisher_url(
                "https://www.bing.com/news/apiclick.aspx?url="+quote("http://unsafe.example",safe="")))
            self.assertIsNone(m.bing_publisher_url(
                good+"&url="+quote(URLS[1],safe="")))

    def test_two_independent_sources_or_vetted_single_original(self):
        with patch.object(m.editorial, "public_host", return_value=True):
            self.assertTrue(m.publisher_pair(URLS))
            self.assertFalse(m.publisher_pair([URLS[0]]))
            self.assertFalse(m.source_urls_ok([URLS[0]]))
            self.assertTrue(m.source_urls_ok([ORIGINAL]))
            self.assertFalse(m.source_urls_ok(["https://unknown.example/story"]))
            self.assertFalse(m.publisher_pair([URLS[0], URLS[0]]))
            self.assertFalse(m.publisher_pair(["https://bbc.co.uk/a", "https://bbc.com/b"]))
            self.assertFalse(m.publisher_pair(["https://publisher-a.example/a", "https://publisher-a.example/b"]))

    def test_invalid_dates_unverified_media_and_harm_are_rejected(self):
        with patch.object(m.editorial, "public_host", return_value=True):
            self.assertTrue(m.validate_story(sample_story(), URLS, TODAY))
            for mutated in (
                {"verificationUrls": [URLS[0]]},
                {"reported": "2026-10-18"},
                {"reported": "2026-11-18"},
                {"id": "犬のまさか"},
                {"title": "事故で負傷者が発生"},
            ):
                story = {**sample_story(), **mutated}
                self.assertFalse(m.validate_story(story, URLS, TODAY), mutated)

    def test_sources_are_both_fetched_and_audited_before_acceptance(self):
        calls = []
        def ask(prompt, temperature=0.1):
            calls.append(prompt)
            if "monthly editor A" in prompt:
                return {"story": sample_story()}
            return {"approved": True, "independent": True,
                    "bothSourcesSupport": True, "factsVerified": True,
                    "originalReporting": True, "dateVerified": True,
                    "safeTone": True, "humanFailureConfirmed":True, "comicPunchlineWorks":True, "reasonCode": "verified"}
        group = [{"url": URLS[0], "title": "mix-up", "seendate": "2026-11-17"},
                 {"url": URLS[1], "title": "mix-up", "seendate": "2026-11-17"}]
        with patch.object(m.editorial, "public_host", return_value=True):
            result = m.make_story(group, TODAY, [], ask_ai=ask,
                                  source_reader=lambda url: "publisher body " * 65)
            self.assertIsNotNone(result)
            self.assertEqual(len(calls), 2)
            self.assertEqual(result["verificationUrls"], URLS)
            self.assertNotIn("evidence", result)
            self.assertEqual(result["sourceBasis"],"independent-reports")
            self.assertIsNone(m.make_story(group, TODAY, [], ask_ai=ask,
                                           source_reader=lambda url: "too short"))
            def reject(prompt, temperature=0.1):
                if "monthly editor A" in prompt:
                    return {"story": sample_story()}
                return {"approved": False, "independent": False,
                        "bothSourcesSupport": False}
            self.assertIsNone(m.make_story(group, TODAY, [], ask_ai=reject,
                                           source_reader=lambda url: "body " * 150))

    def test_single_original_gets_two_stage_audit_and_transparent_label(self):
        single={**sample_story(),"sourceName":"BBC News","sourceUrl":ORIGINAL,
                "verificationUrls":[ORIGINAL],"sourceBasis":"original-report"}
        group=[{"url":ORIGINAL,"title":"Local delivery mix-up",
                "seendate":"2026-11-17"}]
        prompts=[]
        def ask(prompt,temperature=0.1):
            prompts.append(prompt)
            if "monthly editor A" in prompt:
                return {"story":single}
            return {"approved":True,"factsVerified":True,"originalReporting":True,
                    "dateVerified":True,"safeTone":True, "humanFailureConfirmed":True, "comicPunchlineWorks":True,"independent":False,
                    "bothSourcesSupport":False,"reasonCode":"original_verified"}
        with patch.object(m.editorial,"public_host",return_value=True):
            result=m.make_story(group,TODAY,[],ask_ai=ask,
                                 source_reader=lambda url:"Verified primary report. "*35)
        self.assertIsNotNone(result)
        self.assertEqual(len(prompts),2)
        self.assertEqual(result["verificationUrls"],[ORIGINAL])
        self.assertEqual(result["sourceBasis"],"original-report")
        self.assertIn("別媒体による独立した裏付けは確認できていません",result["attributionNote"])

    def test_original_article_without_firsthand_fact_check_is_rejected(self):
        single={**sample_story(),"sourceUrl":ORIGINAL,
                "verificationUrls":[ORIGINAL],"sourceBasis":"original-report"}
        group=[{"url":ORIGINAL,"title":"Social post goes viral",
                "seendate":"2026-11-17"}]
        def weak(prompt,temperature=0.1):
            if "monthly editor A" in prompt:
                return {"story":single}
            return {"approved":True,"factsVerified":True,"originalReporting":False,
                    "dateVerified":True,"safeTone":True, "humanFailureConfirmed":True, "comicPunchlineWorks":True}
        with patch.object(m.editorial,"public_host",return_value=True):
            self.assertIsNone(m.make_story(group,TODAY,[],ask_ai=weak,
                              source_reader=lambda url:"Social post claimed a mistake. "*32))
        # The allowed publisher must also be the actual source URL, not an
        # arbitrary site or another outlet that just republishes headlines.
        other=[{"url":URLS[0],"title":"unverified","seendate":"2026-11-17"}]
        with patch.object(m.editorial,"public_host",return_value=True):
            self.assertIsNone(m.make_story(other,TODAY,[],ask_ai=weak,
                              source_reader=lambda url:"long body "*100))

    def test_single_source_cannot_invent_extra_url_or_source_basis(self):
        single={**sample_story(),"sourceUrl":ORIGINAL,
                "verificationUrls":[ORIGINAL],"sourceBasis":"original-report"}
        with patch.object(m.editorial,"public_host",return_value=True):
            self.assertTrue(m.validate_story(single,[ORIGINAL],TODAY))
            self.assertFalse(m.validate_story(
                {**single,"verificationUrls":[ORIGINAL,URLS[1]]},[ORIGINAL],TODAY))
            self.assertFalse(m.validate_story(
                {**single,"sourceBasis":"independent-reports"},[ORIGINAL],TODAY))
            self.assertFalse(m.validate_story(
                {**single,"sourceUrl":URLS[1]},[ORIGINAL],TODAY))

    def test_pairing_discovery_falls_back_to_vetted_singles(self):
        leads=[{"url":ORIGINAL,"title":"Delivery mix-up",
                "seendate":"2026-11-17"},
               {"url":URLS[0],"title":"Different story in unvetted source",
                "seendate":"2026-11-17"}]
        with patch.object(m.editorial,"public_host",return_value=True):
            groups=m.candidate_pairs(leads,ask_ai=lambda *args,**kw:{"pairs":[]})
        self.assertEqual([[x["url"] for x in group] for group in groups],[[ORIGINAL]])

    def test_broken_two_source_pair_still_allows_original_single_review(self):
        original={"url":ORIGINAL,"title":"Harmless delivery mix-up at local shop",
                  "seendate":"2026-11-17"}
        other={"url":URLS[0],"title":"Harmless delivery mix-up at local shop",
               "seendate":"2026-11-17"}
        with patch.object(m.editorial,"public_host",return_value=True), \
             patch.object(m.editorial,"corroboration_groups",
                          return_value=[[original,other]]):
            groups=m.candidate_pairs([original,other],
                ask_ai=lambda prompt,temperature=0.1:{"pairs":[]})
        self.assertEqual([len(group) for group in groups],[2,1])
        self.assertEqual(groups[1][0]["url"],ORIGINAL)

    def test_short_original_article_can_be_used_only_by_monthly_review(self):
        body="Reporter interviewed the shop owner about a harmless mix-up. "*8
        self.assertGreaterEqual(len(body),350)
        self.assertLess(len(body),600)
        article="<html><body><article><p>"+body+"</p></article></body></html>"
        self.assertEqual(m.editorial.extracted_article_text(article),"")
        self.assertEqual(m.editorial.extracted_article_text(article,min_chars=350),body.strip())
        group=[{"url":ORIGINAL,"title":"Harmless delivery mix-up",
                "seendate":"2026-11-17"}]
        single={**sample_story(),"sourceName":"BBC News","sourceUrl":ORIGINAL,
                "verificationUrls":[ORIGINAL],"sourceBasis":"original-report"}
        def ask(prompt,temperature=0.1):
            if "monthly editor A" in prompt:return {"story":single}
            return {"approved":True,"factsVerified":True,"originalReporting":True,
                    "dateVerified":True,"safeTone":True, "humanFailureConfirmed":True, "comicPunchlineWorks":True,"independent":False,
                    "bothSourcesSupport":False,"reasonCode":"supported"}
        with patch.object(m.editorial,"public_host",return_value=True):
            self.assertIsNotNone(m.make_story(
                group,TODAY,[],ask_ai=ask,source_reader=lambda url:body))

    def test_second_quip_is_optional_when_first_is_source_grounded(self):
        single={**sample_story(),"sourceName":"BBC News","sourceUrl":ORIGINAL,
                "verificationUrls":[ORIGINAL],"sourceBasis":"original-report"}
        single.pop("quipSecond")
        with patch.object(m.editorial,"public_host",return_value=True):
            self.assertTrue(m.validate_story(single,[ORIGINAL],TODAY))
            self.assertFalse(m.validate_story(
                {**single,"quipSecond":single["quip"]},[ORIGINAL],TODAY))
            self.assertFalse(m.validate_story(
                {**single,"quipSecond":"短い"},[ORIGINAL],TODAY))

    def test_matching_headlines_no_longer_requires_ai_call(self):
        original={"url":ORIGINAL,"title":"Local delivery mistake",
                  "seendate":"2026-11-17"}
        def prohibited(*args,**kwargs):
            raise AssertionError("A model should not be called merely to pair headlines")
        with patch.object(m.editorial,"public_host",return_value=True):
            self.assertEqual(m.candidate_pairs([original],ask_ai=prohibited),[[original]])

    def test_monthly_short_article_threshold_does_not_affect_nightly(self):
        with patch.object(m.editorial,"source_text",return_value="documented body") as read:
            self.assertEqual(m.monthly_source_text(ORIGINAL),"documented body")
            read.assert_called_once_with(ORIGINAL,min_chars=350)
        # Normal nightly source_text(url) continues to require 600 chars.
        html="<article>"+("Local report confirmed an unexpected mix-up. "*9)+"</article>"
        self.assertEqual(m.editorial.extracted_article_text(html),"")
        self.assertGreater(len(m.editorial.extracted_article_text(html,min_chars=350)),350)

    def test_optional_second_quip_is_still_safety_checked(self):
        story={**sample_story(),"quipSecond":"これは必ず元気になる。そんな励ましは不要です。"}
        with patch.object(m.editorial,"public_host",return_value=True):
            self.assertFalse(m.validate_story(story,URLS,TODAY))
        story.pop("quipSecond")
        with patch.object(m.editorial,"public_host",return_value=True):
            self.assertTrue(m.validate_story(story,URLS,TODAY))

    def test_malformed_bing_and_rss_do_not_stop_monthly_discovery(self):
        now=datetime(2026,11,17,19,0,tzinfo=ZoneInfo("Asia/Tokyo"))
        bad=b"<not-a-valid-feed><tag\x00>"
        with patch.object(m,"source_registry",return_value=[]), \
             patch.object(m,"fetch_registry_feeds",return_value=[]), \
             patch.object(m,"GDELT_QUERIES",()), \
             patch.object(m,"BING_QUERIES",(("mixup","en-US"),)), \
             patch.object(m,"LOCAL_LANGUAGE_FEEDS",(("https://source.example/rss",
                 "Example","en","JP"),)), \
             patch.object(m,"INDEPENDENT_FEEDS",()), \
             patch.object(m,"BBC_FEEDS",()):
            self.assertEqual(m.discover(now,fetch=lambda url:bad),[])

    def test_no_key_is_safe_skip_with_no_public_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(m.editorial, "KEY", ""):
                self.assertFalse(m.run(root=Path(directory)))
            self.assertFalse((Path(directory)/"data/monthly").exists())

    def test_release_is_immutable_and_manifest_has_real_collection_date(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(m.editorial, "public_host", return_value=True):
                self.assertTrue(m.publish_monthly([sample_story()], TODAY, root))
                self.assertFalse(m.publish_monthly([sample_story()], TODAY, root))
            file = root/"data/monthly/2026-11-17.json"
            index = root/"data/monthly/index.json"
            self.assertEqual(json.loads(file.read_text())["reviewMethod"], m.REVIEW_METHOD)
            self.assertEqual(json.loads(index.read_text())["issues"],
                             [{"date": "2026-11-17", "count": 1}])

    def test_released_archive_and_existing_monthly_stories_prevent_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            archive=root/"data/archive"
            archive.mkdir(parents=True)
            (archive/"2026-11-16.json").write_text(json.dumps({
                "status":"published",
                "stories":[sample_story()]
            },ensure_ascii=False),encoding="utf-8")
            known=m.existing_articles(root)
            self.assertFalse(m.plausible_new(sample_story(),known))
            self.assertIn(sample_story()["eventKey"],known[3])

    def test_monthly_reader_and_public_bundle_only_load_approved_records(self):
        root=Path(__file__).resolve().parents[1]
        html=(root/"index.html").read_text(encoding="utf-8")
        build=(root/"build_site.py").read_text(encoding="utf-8")
        worker=(root/"service-worker.js").read_text(encoding="utf-8")
        self.assertIn("async function loadMonthlyVerified()",html)
        self.assertIn("source-quality-two-stage-AI",html)
        self.assertIn("s.sourceBasis==='original-report'",html)
        self.assertIn("...monthRollingStories,...monthPublishedStories,...monthStories",html)
        self.assertIn("loadMonthlyVerified();",html)
        self.assertIn("data/monthly/index.json",build)
        self.assertIn("validate_story(story, story.get('verificationUrls', []), day)",build)
        self.assertIn("data/monthly/index.json",worker)
        self.assertIn("data/monthly/",worker)
        self.assertIn("published-monthly-index",json.loads((root/"data/monthly/index.json").read_text())["status"])


if __name__ == "__main__":
    unittest.main()
