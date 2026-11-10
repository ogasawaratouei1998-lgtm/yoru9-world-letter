import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from publish_approved import publish, validate_approved
from build_site import build


def fixture(date='2026-11-10'):
    stories=[]
    for i in range(5):
        original = f'https://news.example.com/story-{i}'
        stories.append({'id': f'case-{i}', 'country': '日本', 'category': 'work', 'categoryLabel': '仕事の勘違い', 'label': '検証用', 'title': f'検証用タイトル {i}', 'summary': '検証用の短い紹介文です。', 'detail': '検証用の詳細記事です。', 'quip': 'ツッコミのサンプルです。', 'sourceName': '出典', 'sourceUrl': original, 'reported': '2026.11.10', 'flag': '🇯🇵', 'verificationUrls': [original, f'https://another.example.org/story-{i}'], 'editorVerified': True, 'humorSafe': True})
    return {'status':'approved', 'editionDate':date,'title':'今夜の世界の大失敗５連発','editorApproved':True,'factChecked':True,'humorReviewed':True,'approvedBy':'編集担当者','stories':stories}


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
    def test_before_nine_does_not_publish(self):
        self.assertFalse(publish(self.root,datetime.fromisoformat('2026-11-10T20:59:00+09:00')))
        self.assertFalse((self.root/'data'/'archive'/'2026-11-10.json').exists())
    def test_after_nine_publishes_and_archives(self):
        self.assertTrue(publish(self.root,datetime.fromisoformat('2026-11-10T21:08:00+09:00')))
        current=json.loads((self.root/'data'/'current.json').read_text())
        self.assertEqual(current['status'],'published')
        self.assertEqual(len(current['stories']),5)
        self.assertNotIn('editorVerified',current['stories'][0])
        self.assertEqual(len(json.loads((self.root/'data'/'archive'/'index.json').read_text())['issues']),1)
        self.assertFalse(publish(self.root,datetime.fromisoformat('2026-11-10T21:12:00+09:00')))
    def test_missing_approval_does_not_replace_public_issue(self):
        self.path.unlink()
        self.assertFalse(publish(self.root,datetime.fromisoformat('2026-11-10T21:15:00+09:00')))
        self.assertEqual(json.loads((self.root/'data'/'current.json').read_text())['status'],'demo')
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
    def test_fewer_than_five_blocked(self):
        data=fixture()
        data['stories']=data['stories'][:4]
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
        out=build(self.root,self.root/'_site')
        self.assertTrue((out/'index.html').exists())
        self.assertFalse((out/'data'/'approved').exists())
        self.assertFalse((out/'publish_approved.py').exists())


if __name__ == '__main__': unittest.main()
