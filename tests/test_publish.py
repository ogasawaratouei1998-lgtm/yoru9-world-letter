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
    def test_missing_second_source_blocked(self):
        data=fixture()
        data['stories'][0]['verificationUrls']=data['stories'][0]['verificationUrls'][:1]
        with self.assertRaises(ValueError):validate_approved(data,'2026-11-10')
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
        (self.root/'index.html').write_text('<html></html>')
        (self.root/'manifest.webmanifest').write_text('{}')
        (self.root/'service-worker.js').write_text('/* test worker */')
        (self.root/'notifications.js').write_text('/* test notifications */')
        (self.root/'notification-config.json').write_text('{"enabled":false}')
        (self.root/'country-catalog.json').write_text('[{"code":"JP","name":"日本"}]', encoding='utf-8')
        out=build(self.root,self.root/'_site')
        self.assertTrue((out/'country-catalog.json').exists())
        self.assertTrue((out/'index.html').exists())
        self.assertFalse((out/'data'/'approved').exists())
        self.assertFalse((out/'publish_approved.py').exists())


if __name__ == '__main__': unittest.main()
