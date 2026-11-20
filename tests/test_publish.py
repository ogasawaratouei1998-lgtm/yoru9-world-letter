import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from publish_approved import publish, validate_approved
from build_site import build


def fixture(date='2026-11-10'):
    stories=[]
    for i in range(3):
        original = f'https://news.example.com/story-{i}'
        stories.append({'id': f'case-{i}', 'country': '日本', 'category': 'work', 'categoryLabel': '仕事の勘違い', 'label': '検証用', 'title': f'検証用タイトル {i}', 'summary': '検証用の短い紹介文です。', 'detail': '検証用の詳細記事です。', 'quip': 'ツッコミのサンプルです。', 'sourceName': '出典', 'sourceUrl': original, 'reported': '2026.11.10', 'flag': '🇯🇵', 'verificationUrls': [original, f'https://another.example.org/story-{i}'], 'editorVerified': True, 'humorSafe': True})
    return {'status':'approved', 'editionDate':date,'title':'今夜の世界の大失敗５連発','editorApproved':True,'factChecked':True,'humorReviewed':True,'approvedBy':'編集担当者','stories':stories}


class NightlyQuoteTest(unittest.TestCase):
    def test_closing_line_is_stable_and_depends_on_edition(self):
        from publish_approved import nightly_line, NIGHT_LINES
        stories=[{'id':'story-a','category':'work'}, {'id':'story-b','category':'person'}]
        first=nightly_line('2026-11-16', stories)
        self.assertEqual(first,nightly_line('2026-11-16',stories))
        self.assertIn(first, [line for group in NIGHT_LINES.values() for line in group])
        self.assertGreater(len({nightly_line(f'2026-11-{day:02d}',stories) for day in range(1,29)}),1)

    def test_nightly_message_rejects_newlines_but_accepts_plain_letters(self):
        approved=fixture()
        approved['nightlyMessage']='A warm reminder for tonight: a small mistake does not define the whole day.'
        public=validate_approved(approved,'2026-11-10')
        self.assertEqual(public['nightlyMessage'],approved['nightlyMessage'])
        approved['nightlyMessage']='ひと息ついて、今夜は休みましょう。\n明日はまた明日。'
        public=validate_approved(approved,'2026-11-10')
        self.assertNotEqual(public['nightlyMessage'],approved['nightlyMessage'])

    def test_intentionally_blank_nightly_punchline_stays_blank(self):
        approved=fixture()
        # A deliberate empty line differs from a missing legacy field:
        # publishing should not invent a decorative replacement joke.
        self.assertTrue(validate_approved(approved,'2026-11-10')['nightlyMessage'])
        approved['nightlyMessage']=""
        public=validate_approved(approved,'2026-11-10')
        self.assertEqual(public['nightlyMessage'],"")
        self.assertEqual(len(public['stories']),3)
        self.assertTrue(public['nightQuote'])

    def test_published_issue_contains_nightly_quote(self):
        public=validate_approved(fixture(),'2026-11-10')
        self.assertTrue(public['nightQuote'])
        self.assertEqual(public['nightQuote'], __import__('publish_approved').nightly_line('2026-11-10',public['stories']))


class PublishingTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        (self.root/'data'/'approved').mkdir(parents=True)
        (self.root/'data'/'archive').mkdir(parents=True)
        self.path=self.root/'data'/'approved'/'2026-11-10.json'
        self.path.write_text(json.dumps(fixture(),ensure_ascii=False),encoding='utf-8')
        (self.root/'data'/'current.json').write_text('{"status":"demo", "stories":[]}',encoding='utf-8')
        (self.root/'data'/'archive'/'index.json').write_text('{"issues":[]}',encoding='utf-8')
    def tearDown(self):
        self.tmp.cleanup()
    def test_sports_category_is_valid_and_has_closing_lines(self):
        from publish_approved import NIGHT_MESSAGES, NIGHT_LINES
        data=fixture()
        data['stories'][0]['category']='sports'
        data['stories'][0]['categoryLabel']='スポーツ'
        result=validate_approved(data,'2026-11-10')
        self.assertEqual(result['stories'][0]['category'],'sports')
        self.assertTrue(NIGHT_MESSAGES['sports'])
        self.assertTrue(NIGHT_LINES['sports'])

    def test_before_nine_does_not_publish(self):
        self.assertFalse(publish(self.root,datetime.fromisoformat('2026-11-10T20:59:00+09:00')))
        self.assertFalse((self.root/'data'/'archive'/'2026-11-10.json').exists())
    def test_after_nine_publishes_and_archives(self):
        self.assertTrue(publish(self.root,datetime.fromisoformat('2026-11-10T21:08:00+09:00')))
        current=json.loads((self.root/'data'/'current.json').read_text())
        self.assertEqual(current['status'],'published')
        self.assertEqual(len(current['stories']),3)
        self.assertNotIn('editorVerified',current['stories'][0])
        self.assertEqual(len(json.loads((self.root/'data'/'archive'/'index.json').read_text())['issues']),1)
        self.assertFalse(publish(self.root,datetime.fromisoformat('2026-11-10T21:12:00+09:00')))
    def test_missing_approval_does_not_replace_public_issue(self):
        self.path.unlink()
        self.assertFalse(publish(self.root,datetime.fromisoformat('2026-11-10T21:15:00+09:00')))
        self.assertEqual(json.loads((self.root/'data'/'current.json').read_text())['status'],'demo')
    def test_november_17_and_later_regular_editions_allow_one_to_three(self):
        data=fixture('2026-11-17')
        for story in data['stories']:
            story['reported']='2026-11-17'
        for count in (1,2,3):
            with self.subTest(approved_count=count):
                result=validate_approved(
                    {**data,'stories':data['stories'][:count]},'2026-11-17')
                self.assertEqual(len(result['stories']),count)
        with self.assertRaisesRegex(ValueError,'1〜3本'):
            validate_approved({**data,'stories':[]},'2026-11-17')
        # Four or more vetted CANDIDATES are allowed by the editorial
        # selector, but the final approved edition contains at most three.
        fourth={
            **data['stories'][0],
            'id':'fourth-unique-event',
            'sourceUrl':'https://third.example.com/unique',
            'verificationUrls':['https://third.example.com/unique','https://other.example.org/unique']
        }
        with self.assertRaisesRegex(ValueError,'1〜3本'):
            validate_approved({**data,'stories':data['stories']+[fourth]},'2026-11-17')

    def test_one_and_two_story_evenings_publish_without_filler(self):
        for day,count in [('2026-11-17',1),('2026-11-18',2)]:
            with self.subTest(date=day,count=count):
                approved=fixture(day)
                approved['stories']=approved['stories'][:count]
                for story in approved['stories']:
                    story['reported']=day
                path=self.root/'data'/'approved'/f'{day}.json'
                path.write_text(json.dumps(approved,ensure_ascii=False),encoding='utf-8')
                now=datetime.fromisoformat(day+'T21:07:00+09:00')
                self.assertTrue(publish(self.root,now))
                archive=json.loads((self.root/'data'/'archive'/f'{day}.json').read_text(encoding='utf-8'))
                current=json.loads((self.root/'data'/'current.json').read_text(encoding='utf-8'))
                self.assertEqual(len(archive['stories']),count)
                self.assertEqual(len(current['stories']),count)
                self.assertEqual(current['editionDate'],day)

    def test_zero_verified_stories_never_replace_existing_publication(self):
        today='2026-11-17'
        empty=fixture(today)
        empty['stories']=[]
        path=self.root/'data'/'approved'/f'{today}.json'
        path.write_text(json.dumps(empty,ensure_ascii=False),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'1〜3本'):
            publish(self.root,datetime.fromisoformat(today+'T21:07:00+09:00'))
        self.assertFalse((self.root/'data'/'archive'/f'{today}.json').exists())
        self.assertEqual(
            json.loads((self.root/'data'/'current.json').read_text())['status'],'demo')

    def test_historical_regular_editions_keep_original_rules(self):
        old=fixture('2026-11-10')
        self.assertEqual(len(validate_approved(
            {**old,'stories':old['stories'][:1]},'2026-11-10')['stories']),1)

    def test_english_only_detail_is_rejected(self):
        data=fixture()
        data['editionDate']='2026-11-17'
        for story in data['stories']:
            story['reported']='2026.11.17'
        data['stories'][0]['detail']='An English-only expanded article.'
        with self.assertRaisesRegex(ValueError, 'detailが日本語ではありません'):
            validate_approved(data,'2026-11-17')

    def test_legacy_approved_english_detail_is_not_retroactively_blocked(self):
        data=fixture()
        data['stories'][0]['detail']='An English-only expanded article.'
        public=validate_approved(data,'2026-11-10')
        self.assertEqual(public['stories'][0]['detail'],data['stories'][0]['detail'])

    def test_second_ai_quip_survives_publication_and_archive(self):
        data=fixture()
        second='最初と違う角度から、あとで笑える追撃ツッコミを届けます。'
        data['stories'][0]['quipSecond']=second
        self.path.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        self.assertTrue(publish(self.root,datetime.fromisoformat('2026-11-10T21:08:00+09:00')))
        current=json.loads((self.root/'data'/'current.json').read_text(encoding='utf-8'))
        archive=json.loads((self.root/'data'/'archive'/'2026-11-10.json').read_text(encoding='utf-8'))
        self.assertEqual(current['stories'][0]['quipSecond'],second)
        self.assertEqual(archive['stories'][0]['quipSecond'],second)
        self.assertNotIn('editorVerified',current['stories'][0])

    def test_second_ai_quip_must_be_distinct_and_valid(self):
        data=fixture()
        data['stories'][0]['quipSecond']=data['stories'][0]['quip']
        with self.assertRaisesRegex(ValueError,'重複'):
            validate_approved(data,'2026-11-10')
        data['stories'][0]['quipSecond']='短い'
        with self.assertRaisesRegex(ValueError,'15'):
            validate_approved(data,'2026-11-10')

    def test_unverified_story_blocked(self):
        data=fixture()
        data['stories'][2]['editorVerified']=False
        with self.assertRaises(ValueError):validate_approved(data,'2026-11-10')
    def test_historical_issue_retains_original_two_source_rule(self):
        data=fixture()
        data['stories'][0]['verificationUrls']=data['stories'][0]['verificationUrls'][:1]
        with self.assertRaises(ValueError):validate_approved(data,'2026-11-10')

    def test_current_regular_one_source_is_publishable(self):
        from trusted_originals import SINGLE_SOURCE_NOTE
        data=fixture('2026-11-17')
        for story in data['stories']:
            story['reported']='2026-11-17'
        story=data['stories'][0]
        story['sourceUrl']='https://www.bbc.com/news/articles/verified-local-report'
        story['verificationUrls']=[story['sourceUrl']]
        story['sourceBasis']='original-report'
        story['originalReportingVerified']=True
        story['attributionNote']=SINGLE_SOURCE_NOTE
        public=validate_approved(data,'2026-11-17')
        self.assertEqual(public['stories'][0]['verificationUrls'],[story['sourceUrl']])
        self.assertEqual(public['stories'][0]['attributionNote'],SINGLE_SOURCE_NOTE)
        self.assertNotIn('originalReportingVerified',public['stories'][0])

    def test_one_source_requires_preapproved_publisher_and_fact_review(self):
        from trusted_originals import SINGLE_SOURCE_NOTE
        data=fixture('2026-11-17')
        for story in data['stories']:
            story['reported']='2026-11-17'
        story=data['stories'][0]
        story['verificationUrls']=[story['sourceUrl']]
        story['sourceBasis']='original-report'
        story['originalReportingVerified']=True
        story['attributionNote']=SINGLE_SOURCE_NOTE
        with self.assertRaises(ValueError):
            validate_approved(data,'2026-11-17')
        story['sourceUrl']='https://www.bbc.com/news/articles/verified-local-report'
        story['verificationUrls']=[story['sourceUrl']]
        story['originalReportingVerified']=False
        with self.assertRaises(ValueError):
            validate_approved(data,'2026-11-17')

    def test_new_automated_approval_needs_independent_editorial_quality_proof(self):
        data=fixture("2026-11-17")
        data["editionDate"]="2026-11-18"
        data["approvedBy"]="automated-two-stage-review"
        for story in data["stories"]:
            story["reported"]="2026-11-17"
        with self.assertRaises(ValueError):
            validate_approved(data,"2026-11-18")
        for story in data["stories"]:
            story["editorQualityVerified"]=True
            story["humanFailureVerified"]=True
            story["humanActor"]="行政の事務担当者"
            story["humanMistake"]="指示された書類の内容を間違えて処理してしまった"
        published=validate_approved(data,"2026-11-18")
        self.assertEqual(len(published["stories"]),len(data["stories"]))
        self.assertNotIn("editorQualityVerified",published["stories"][0])

    def test_automated_second_joke_requires_its_own_review_proof(self):
        data=fixture("2026-11-18")
        data["approvedBy"]="automated-two-stage-review"
        for story in data["stories"]:
            story["reported"]="2026-11-17"
            story["editorQualityVerified"]=True
            story["humanFailureVerified"]=True
            story["humanActor"]="市の掲示担当者"
            story["humanMistake"]="案内文を誤った文字で掲示した"
        data["stories"][0]["quipSecond"]="道しるべを作ったら、文字のほうが先に道に迷った。"
        with self.assertRaisesRegex(ValueError,"2本目"):
            validate_approved(data,"2026-11-18")
        data["stories"][0]["secondQuipVerified"]=True
        published=validate_approved(data,"2026-11-18")
        self.assertIn("quipSecond",published["stories"][0])
        self.assertNotIn("secondQuipVerified",published["stories"][0])
        del data["stories"][0]["quipSecond"]
        del data["stories"][0]["secondQuipVerified"]
        self.assertNotIn("quipSecond",validate_approved(data,"2026-11-18")["stories"][0])

    def test_automated_country_must_be_one_of_the_196_real_reporting_locations(self):
        data=fixture("2026-11-18")
        data["approvedBy"]="automated-two-stage-review"
        for story in data["stories"]:
            story["reported"]="2026-11-17"
            story["editorQualityVerified"]=True
            story["humanFailureVerified"]=True
            story["humanActor"]="広報担当者"
            story["humanMistake"]="案内板に間違った文章を印刷した"
        data["stories"][0]["country"]="未確認"
        with self.assertRaises(ValueError):
            validate_approved(data,"2026-11-18")
        data["stories"][0]["country"]="パレスチナ"
        self.assertEqual(validate_approved(data,"2026-11-18")["stories"][0]["country"],"パレスチナ")

    def test_automated_daily_news_cannot_publish_animal_novelty(self):
        data=fixture("2026-11-17")
        data["editionDate"]="2026-11-18"
        data["approvedBy"]="automated-two-stage-review"
        for item in data["stories"]:
            item["reported"]="2026-11-17"
            item["editorQualityVerified"]=True
            item["humanFailureVerified"]=True
            item["humanActor"]="市役所の担当者"
            item["humanMistake"]="申請用紙の数字を間違えて発注してしまった"
        published=validate_approved(data,"2026-11-18")
        self.assertEqual(len(published["stories"]),3)
        self.assertNotIn("humanFailureVerified",published["stories"][0])
        data["stories"][0]["title"]="珍しいシカが現れた"
        with self.assertRaises(ValueError):
            validate_approved(data,"2026-11-18")
        data["stories"][0]["title"]="誤発注してしまった市役所"
        data["stories"][0]["humanFailureVerified"]=False
        with self.assertRaises(ValueError):
            validate_approved(data,"2026-11-18")

    def test_automated_editor_cannot_publish_deliberate_student_dispute(self):
        data=fixture("2026-11-17")
        data["editionDate"]="2026-11-18"
        data["approvedBy"]="automated-two-stage-review"
        for item in data["stories"]:
            item["reported"]="2026-11-17"
            item["editorQualityVerified"]=True
            item["humanFailureVerified"]=True
            item["humanActor"]="学校関係者"
            item["humanMistake"]="式典で別の原稿を読んでしまった"
        data["stories"][0]["title"]="学位授与式を妨害、学生に懲戒処分"
        with self.assertRaises(ValueError):
            validate_approved(data,"2026-11-18")
        data["stories"][0]["title"]="式典の担当者が原稿を読み間違えた"
        published=validate_approved(data,"2026-11-18")
        self.assertEqual(len(published["stories"]),3)

    def test_automated_editor_cannot_publish_emergency_harassment_as_comedy(self):
        data=fixture("2026-11-17")
        data["editionDate"]="2026-11-18"
        data["approvedBy"]="automated-two-stage-review"
        for item in data["stories"]:
            item["reported"]="2026-11-17"
            item["editorQualityVerified"]=True
            item["humanFailureVerified"]=True
            item["humanActor"]="配送担当者"
            item["humanMistake"]="商品を宛先とは異なる住所へ配送してしまった"
        data["stories"][0]["title"]="救急出動中の消防士に嫌がらせが続く"
        data["stories"][0]["summary"]="住民が消防団員に暴言を浴びせた。"
        with self.assertRaises(ValueError):
            validate_approved(data,"2026-11-18")

    def test_current_regular_zero_sources_is_rejected(self):
        data=fixture('2026-11-17')
        for story in data['stories']:
            story['reported']='2026-11-17'
        data['stories'][0]['verificationUrls']=[]
        with self.assertRaises(ValueError):validate_approved(data,'2026-11-17')

    def test_independent_domains_required(self):
        data=fixture()
        data['stories'][0]['verificationUrls']=[data['stories'][0]['sourceUrl'], 'https://news.example.com/mirror']
        with self.assertRaises(ValueError):validate_approved(data,'2026-11-10')
    def test_more_than_five_regular_blocked(self):
        data=fixture()
        for n in range(2,7):
            story=dict(data['stories'][0])
            story['id']=f'extra-{n}'
            story['sourceUrl']=f'https://news{n}.example.com/extra'
            story['verificationUrls']=[story['sourceUrl'], f'https://another{n}.example.org/extra']
            data['stories'].append(story)
        with self.assertRaises(ValueError):
            validate_approved(data,'2026-11-10')

    def test_zero_regular_blocked(self):
        data=fixture()
        data['stories']=[]
        with self.assertRaises(ValueError):validate_approved(data,'2026-11-10')
    def test_unapproved_blocked(self):
        data=fixture()
        data['editorApproved']=False
        with self.assertRaises(ValueError):validate_approved(data,'2026-11-10')
    def test_old_regular_story_is_rejected(self):
        data=fixture()
        data['stories'][0]['reported']='2026.10.13'
        with self.assertRaisesRegex(ValueError, '8日以上古い'):
            validate_approved(data,'2026-11-10')
    def test_historical_special_requires_explanation(self):
        data=fixture()
        data['stories'][0]['reported']='2026.10.13'
        data['editionType']='special'
        for i in (3, 4):
            original=f'https://news.example.com/story-{i}'
            data['stories'].append(dict(data['stories'][0], id=f'case-{i}', sourceUrl=original, verificationUrls=[original, f'https://another.example.org/story-{i}']))
        data['title']='創刊特集号｜世界の大失敗５連発'
        data['specialReason']='初回特集号で過去約一か月の話題を集めています。'
        public=validate_approved(data,'2026-11-10')
        self.assertEqual(public['editionType'],'special')
        self.assertIn('specialReason',public)
        del data['specialReason']
        with self.assertRaises(ValueError):validate_approved(data,'2026-11-10')
    def test_future_report_date_is_rejected(self):
        data=fixture()
        data['stories'][0]['reported']='2026.11.11'
        with self.assertRaises(ValueError):validate_approved(data,'2026-11-10')
    def test_hyphenated_reported_date_is_accepted(self):
        data=fixture()
        data['stories'][0]['reported']='2026-11-09'
        self.assertEqual(validate_approved(data,'2026-11-10')['status'],'published')
    def test_build_excludes_approved_files(self):
        (self.root/'assets').mkdir()
        (self.root/'assets'/'icon.svg').write_text('<svg></svg>')
        # The production reader includes bundled original news illustrations;
        # the isolated publication fixture must provide them, too.
        import shutil
        shutil.copytree(Path(__file__).resolve().parents[1]/'assets'/'news',
                        self.root/'assets'/'news')
        (self.root/'index.html').write_text('<html></html>')
        (self.root/'manifest.webmanifest').write_text('{}')
        (self.root/'service-worker.js').write_text('/* test worker */')
        (self.root/'notifications.js').write_text('/* test notifications */')
        (self.root/'world-passport.js').write_text('/* test passport */')
        (self.root/'notification-config.json').write_text('{"enabled":false}')
        (self.root/'country-catalog.json').write_text('[{"code":"JP","name":"日本"}]', encoding='utf-8')
        # The production build requires the separately reviewed cultural
        # highlights and their country-specific official source allowlist.
        # An empty registry is valid for this isolated packaging/privacy test.
        (self.root/'country-highlights.json').write_text('{"version":1,"highlights":{}}', encoding='utf-8')
        (self.root/'country-highlight-sources.json').write_text('{"version":1,"sources":{}}', encoding='utf-8')
        (self.root/'assets'/'world-today-illustrated.svg').write_text('<svg></svg>')
        (self.root/'travel-stops.json').write_text('{}', encoding='utf-8')
        out=build(self.root,self.root/'_site')
        self.assertTrue((out/'country-catalog.json').exists())
        self.assertTrue((out/'country-highlights.json').is_file())
        self.assertTrue((out/'assets'/'world-today-illustrated.svg').is_file())
        self.assertFalse((out/'data'/'retrospective').exists())
        self.assertFalse((out/'data'/'monthly').exists())
        self.assertTrue((out/'travel-stops.json').exists())
        self.assertTrue((out/'index.html').exists())
        self.assertTrue((out/'assets'/'news'/'coffee-rescue.svg').is_file())
        self.assertTrue((out/'assets'/'news'/'category-sports.svg').is_file())
        self.assertFalse((out/'data'/'approved').exists())
        self.assertFalse((out/'publish_approved.py').exists())


if __name__ == '__main__': unittest.main()


class November20EditorialCorrectionTest(unittest.TestCase):
    def test_source_checked_correction_preserves_original_and_rejects_unauthorized(self):
        from zoneinfo import ZoneInfo
        import copy
        root=Path(__file__).resolve().parents[1]
        day="2026-11-20"
        approved=json.loads((root/"data/approved"/(day+".json")).read_text(encoding="utf-8"))
        current=json.loads((root/"data/current.json").read_text(encoding="utf-8"))
        original=json.loads((root/"data/archive/revisions"/(day+"-before-correction.json")).read_text(encoding="utf-8"))
        self.assertEqual(approved["approvedBy"],"editorial-source-checked-correction-2026-11-20")
        self.assertEqual(len(original["stories"]),1)
        self.assertEqual(len(current["stories"]),2)
        self.assertEqual(validate_approved(approved,day),current)
        self.assertTrue(approved["stories"][0]["majorPersonalFailureVerified"])
        self.assertFalse(approved["stories"][1]["majorPersonalFailureVerified"])
        for story in approved["stories"]:
            self.assertTrue(story["originalReportingVerified"] and story["editorQualityVerified"])
            self.assertTrue(story["surpriseVerified"] and story["stageTsukkomiVerified"])
            self.assertIn("差し替え",story["correctionNote"])
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)
            (dest/"data"/"approved").mkdir(parents=True)
            (dest/"data"/"archive").mkdir(parents=True)
            (dest/"data"/"approved"/(day+".json")).write_text(json.dumps(approved,ensure_ascii=False),encoding="utf-8")
            (dest/"data"/"archive"/(day+".json")).write_text(json.dumps(original,ensure_ascii=False),encoding="utf-8")
            (dest/"data"/"current.json").write_text(json.dumps(original,ensure_ascii=False),encoding="utf-8")
            now=datetime(2026,11,20,22,0,tzinfo=ZoneInfo("Asia/Tokyo"))
            self.assertTrue(publish(dest,now))
            self.assertEqual(json.loads((dest/"data"/"current.json").read_text(encoding="utf-8")),current)
            self.assertEqual(json.loads((dest/"data"/"archive/revisions"/(day+"-before-correction.json")).read_text(encoding="utf-8")),original)
            self.assertFalse(publish(dest,now))
            unauthorized=copy.deepcopy(approved)
            unauthorized["approvedBy"]="automated-two-stage-review"
            unauthorized["stories"][0]["quip"]="別のツッコミを無断で入れてはならない！"
            (dest/"data"/"approved"/(day+".json")).write_text(json.dumps(unauthorized,ensure_ascii=False),encoding="utf-8")
            with self.assertRaises(ValueError):
                publish(dest,now)
